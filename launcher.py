"""
═══════════════════════════════════════════════════════════╗
║         www.ddot - Universal Program Launcher             ║
║   Real-time Server Sync • User Auth • Auto Update         ║
╚═══════════════════════════════════════════════════════════╝
"""
import sys
import os
import ctypes
import subprocess
import json
import hashlib
import threading
import requests
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except ImportError:
    HAS_CTK = False
    import tkinter as tk

# ============================================================
# CONFIGURATION - แก้ URL นี้ให้เป็น GitHub raw ของคุณ
# ============================================================
CONFIG_URL = "https://raw.githubusercontent.com/nerx999/www-ddot/refs/heads/main/server_config.json"
LAUNCHER_VERSION = "1.0.0"
APP_DIR = Path(__file__).parent
PROGRAMS_DIR = APP_DIR / "programs"
CONFIG_FILE = APP_DIR / "ddot_user.json"

# ============================================================
# Theme
# ============================================================
class Theme:
    BG = "#0a0e14"
    BG2 = "#151b26"
    BG3 = "#1f2937"
    BG4 = "#2d3748"
    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    TEXT = "#f1f5f9"
    TEXT2 = "#94a3b8"
    TEXT3 = "#64748b"


# ============================================================
# USER MANAGER
# ============================================================
class UserManager:
    def __init__(self):
        self.user_key = None
        self.username = None
        self.login_time = None
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
                self.user_key = data.get('user_key')
                self.username = data.get('username')
                self.login_time = data.get('login_time')
        except:
            pass

    def save(self):
        data = {
            'user_key': self.user_key,
            'username': self.username,
            'login_time': self.login_time
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def logout(self):
        self.user_key = None
        self.username = None
        self.login_time = None
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()


# ============================================================
# SERVER MANAGER (Real-time)
# ============================================================
class ServerManager:
    def __init__(self, user_manager):
        self.user = user_manager
        self.config = None
        self.programs = []
        self.last_sync = None
        self.error = None

    def fetch_config(self):
        """ดึง config จาก server แบบ real-time"""
        try:
            headers = {
                'User-Agent': f'DDotLauncher/{LAUNCHER_VERSION}',
                'Cache-Control': 'no-cache'
            }
            if self.user.user_key:
                headers['X-User-Key'] = self.user.user_key

            resp = requests.get(CONFIG_URL, headers=headers, timeout=10)

            if resp.status_code == 401:
                self.error = "Invalid or expired user key"
                return False
            elif resp.status_code != 200:
                self.error = f"Server error: {resp.status_code}"
                return False

            self.config = resp.json()
            self.programs = self.config.get('programs', [])
            self.last_sync = datetime.now()
            self.error = None
            return True

        except requests.exceptions.ConnectionError:
            self.error = "Cannot connect to server. Check your internet."
            return False
        except requests.exceptions.Timeout:
            self.error = "Connection timeout. Please try again."
            return False
        except json.JSONDecodeError:
            self.error = "Server returned invalid data"
            return False
        except Exception as e:
            self.error = f"Error: {str(e)}"
            return False

    def validate_key(self, key):
        """ตรวจสอบ key กับ server config"""
        if not key or not key.startswith("DDOT-"):
            return False, "Invalid format. Must start with DDOT-"
        if len(key) < 16:
            return False, "Key too short"

        # ถ้ามี valid_keys ใน config ให้เช็ค
        if self.config and 'valid_keys' in self.config:
            if key not in self.config['valid_keys']:
                return False, "Key not recognized. Please contact support."

        return True, "Valid"

    def is_maintenance(self):
        if not self.config:
            return False
        return self.config.get('maintenance', False)

    def get_program_by_id(self, pid):
        for p in self.programs:
            if p['id'] == pid:
                return p
        return None


# ============================================================
# LOGIN SCREEN
# ============================================================
class LoginScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("www.ddot - Login")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG)

        self.user = UserManager()
        self.server = ServerManager(self.user)
        self.success = False

        self._build_ui()

        # ถ้ามี key เก่า ให้ลอง validate เลย
        if self.user.user_key:
            self.key_entry.insert(0, self.user.user_key)
            self.after(500, self.try_auto_login)

    def _build_ui(self):
        # Logo area
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(50, 20))

        ctk.CTkLabel(logo_frame, text="www.ddot",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color=Theme.ACCENT).pack()

        ctk.CTkLabel(logo_frame, text="Universal Program Launcher",
                    font=ctk.CTkFont(size=12),
                    text_color=Theme.TEXT2).pack(pady=(5, 0))

        # Status
        self.status_label = ctk.CTkLabel(self, text="Connecting to server...",
                                        text_color=Theme.TEXT3,
                                        font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(0, 20))

        # Key input
        input_frame = ctk.CTkFrame(self, fg_color=Theme.BG2, corner_radius=12)
        input_frame.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(input_frame, text="User Key",
                    text_color=Theme.TEXT2,
                    font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(15, 5))

        self.key_entry = ctk.CTkEntry(input_frame, height=44,
                                     placeholder_text="DDOT-XXXX-XXXX-XXXX",
                                     font=ctk.CTkFont(size=14, family="Consolas"))
        self.key_entry.pack(fill="x", padx=20, pady=(0, 15))
        self.key_entry.bind("<Return>", lambda e: self.do_login())

        # Error label
        self.error_label = ctk.CTkLabel(self, text="",
                                       text_color=Theme.DANGER,
                                       font=ctk.CTkFont(size=11))
        self.error_label.pack(pady=5)

        # Login button
        self.login_btn = ctk.CTkButton(self, text="LOGIN",
                                      height=44, width=200,
                                      fg_color=Theme.ACCENT,
                                      hover_color=Theme.ACCENT_HOVER,
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      command=self.do_login)
        self.login_btn.pack(pady=15)

        # Footer
        ctk.CTkLabel(self, text=f"Launcher v{LAUNCHER_VERSION}",
                    text_color=Theme.TEXT3,
                    font=ctk.CTkFont(size=9)).pack(side="bottom", pady=15)

        # เริ่มดึง config
        threading.Thread(target=self._fetch_config, daemon=True).start()

    def _fetch_config(self):
        ok = self.server.fetch_config()
        if ok:
            self.after(0, lambda: self.status_label.configure(
                text=f"✓ Connected • {len(self.server.programs)} programs available",
                text_color=Theme.SUCCESS))
        else:
            self.after(0, lambda: self.status_label.configure(
                text=f"✗ {self.server.error}",
                text_color=Theme.DANGER))

    def try_auto_login(self):
        """ลอง login อัตโนมัติถ้ามี key เก่า"""
        self.do_login()

    def do_login(self):
        key = self.key_entry.get().strip()
        if not key:
            self.error_label.configure(text="Please enter your user key")
            return

        self.login_btn.configure(state="disabled", text="Verifying...")
        self.error_label.configure(text="")

        def verify():
            # ดึง config ใหม่เสมอ (real-time)
            ok = self.server.fetch_config()
            if not ok:
                self.after(0, lambda: self._login_failed(self.server.error))
                return

            # เช็ค maintenance
            if self.server.is_maintenance():
                msg = self.server.config.get('maintenance_message', 'System under maintenance')
                self.after(0, lambda: self._login_failed(f"⚠ {msg}"))
                return

            # Validate key
            valid, msg = self.server.validate_key(key)
            if not valid:
                self.after(0, lambda: self._login_failed(msg))
                return

            # Success
            self.user.user_key = key
            self.user.username = f"User_{key[-6:]}"
            self.user.login_time = datetime.now().isoformat()
            self.user.save()
            self.after(0, self._login_success)

        threading.Thread(target=verify, daemon=True).start()

    def _login_failed(self, msg):
        self.error_label.configure(text=f"✗ {msg}")
        self.login_btn.configure(state="normal", text="LOGIN")

    def _login_success(self):
        self.success = True
        self.destroy()


# ============================================================
# MAIN LAUNCHER
# ============================================================
class MainLauncher(ctk.CTk):
    def __init__(self, user, server):
        super().__init__()
        self.user = user
        self.server = server
        self.title(f"www.ddot Launcher - {user.username}")
        self.geometry("900x650")
        self.configure(fg_color=Theme.BG)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.installed_programs = self._load_installed()
        self._build_ui()
        self.refresh_programs()

    def _load_installed(self):
        """โหลดข้อมูลโปรแกรมที่ติดตั้งแล้ว"""
        meta_file = PROGRAMS_DIR / "installed.json"
        if meta_file.exists():
            try:
                return json.loads(meta_file.read_text(encoding='utf-8'))
            except:
                pass
        return {}

    def _save_installed(self):
        PROGRAMS_DIR.mkdir(exist_ok=True)
        meta_file = PROGRAMS_DIR / "installed.json"
        meta_file.write_text(json.dumps(self.installed_programs, indent=2), encoding='utf-8')

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=60, fg_color=Theme.BG2)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        ctk.CTkLabel(header, text="www.ddot",
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color=Theme.ACCENT).place(x=20, y=15)

        ctk.CTkLabel(header, text="Program Launcher",
                    font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT2).place(x=20, y=38)

        # User info
        ctk.CTkLabel(header, text=f"👤 {self.user.username}",
                    text_color=Theme.TEXT,
                    font=ctk.CTkFont(size=11)).place(x=600, y=20)

        ctk.CTkLabel(header, text=f"Key: {self.user.user_key[:12]}...",
                    text_color=Theme.TEXT3,
                    font=ctk.CTkFont(size=9)).place(x=600, y=38)

        # Refresh button
        self.refresh_btn = ctk.CTkButton(header, text="🔄 Refresh",
                                        width=100, height=30,
                                        fg_color=Theme.BG3,
                                        hover_color=Theme.BG4,
                                        command=self.refresh_programs)
        self.refresh_btn.place(x=780, y=15)

        # Logout
        ctk.CTkButton(header, text="Logout",
                     width=80, height=30,
                     fg_color="transparent",
                     text_color=Theme.DANGER,
                     hover_color=Theme.BG3,
                     command=self.do_logout).place(x=780, y=50)

        # Status bar
        self.sync_status = ctk.CTkLabel(header, text="",
                                       text_color=Theme.TEXT3,
                                       font=ctk.CTkFont(size=9))
        self.sync_status.place(x=200, y=20)

        # Content area
        self.content = ctk.CTkScrollableFrame(self, fg_color=Theme.BG)
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

    def refresh_programs(self):
        """รีเฟรชรายการจาก server (real-time)"""
        self.refresh_btn.configure(state="disabled", text="Syncing...")
        self.sync_status.configure(text="Connecting to server...", text_color=Theme.TEXT3)

        def worker():
            ok = self.server.fetch_config()
            if ok:
                self.after(0, self._render_programs)
                time_str = self.server.last_sync.strftime("%H:%M:%S")
                self.after(0, lambda: self.sync_status.configure(
                    text=f"✓ Synced at {time_str} • {len(self.server.programs)} programs",
                    text_color=Theme.SUCCESS))
            else:
                self.after(0, lambda: self.sync_status.configure(
                    text=f"✗ {self.server.error}",
                    text_color=Theme.DANGER))
            self.after(0, lambda: self.refresh_btn.configure(state="normal", text="🔄 Refresh"))

        threading.Thread(target=worker, daemon=True).start()

    def _render_programs(self):
        """แสดงรายการโปรแกรม"""
        # ล้าง content เก่า
        for widget in self.content.winfo_children():
            widget.destroy()

        if not self.server.programs:
            ctk.CTkLabel(self.content, text="No programs available",
                        text_color=Theme.TEXT2).pack(pady=50)
            return

        # Group by category
        categories = {}
        for prog in self.server.programs:
            cat = prog.get('category', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(prog)

        for cat, programs in categories.items():
            # Category header
            cat_frame = ctk.CTkFrame(self.content, fg_color="transparent")
            cat_frame.pack(fill="x", pady=(15, 5))

            ctk.CTkLabel(cat_frame, text=f"■ {cat}",
                        font=ctk.CTkFont(size=14, weight="bold"),
                        text_color=Theme.ACCENT).pack(anchor="w")

            ctk.CTkFrame(self.content, height=1, fg_color=Theme.BG3).pack(fill="x", pady=(0, 10))

            # Program cards
            for prog in programs:
                self._create_program_card(prog)

    def _create_program_card(self, prog):
        """สร้าง card สำหรับแต่ละโปรแกรม"""
        pid = prog['id']
        installed = self.installed_programs.get(pid, {})
        installed_ver = installed.get('version')
        server_ver = prog.get('version', '0.0.0')

        # Determine status
        if not installed_ver:
            status = "not_installed"
            status_text = "Not Installed"
            status_color = Theme.TEXT3
        elif self._compare_version(server_ver, installed_ver) > 0:
            status = "update_available"
            status_text = f"Update: {installed_ver} → {server_ver}"
            status_color = Theme.WARNING
        else:
            status = "up_to_date"
            status_text = f"Installed v{installed_ver}"
            status_color = Theme.SUCCESS

        # Card
        card = ctk.CTkFrame(self.content, fg_color=Theme.BG2, corner_radius=10)
        card.pack(fill="x", pady=5)

        # Left: Icon + Info
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=15, pady=12)

        info_row = ctk.CTkFrame(left, fg_color="transparent")
        info_row.pack(fill="x")

        icon = prog.get('icon', '📦')
        ctk.CTkLabel(info_row, text=f"{icon}  ",
                    font=ctk.CTkFont(size=20)).pack(side="left")

        ctk.CTkLabel(info_row, text=prog.get('name', 'Unknown'),
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=Theme.TEXT).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(info_row, text=f"v{server_ver}",
                    font=ctk.CTkFont(size=10),
                    text_color=Theme.TEXT3).pack(side="left")

        ctk.CTkLabel(info_row, text=f"• {prog.get('size_mb', 0)} MB",
                    font=ctk.CTkFont(size=10),
                    text_color=Theme.TEXT3).pack(side="left", padx=(5, 0))

        # Description
        ctk.CTkLabel(left, text=prog.get('description', ''),
                    font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT2,
                    wraplength=500).pack(anchor="w", pady=(5, 0))

        # Status
        ctk.CTkLabel(left, text=status_text,
                    font=ctk.CTkFont(size=10),
                    text_color=status_color).pack(anchor="w", pady=(3, 0))

        # Right: Action button
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=15, pady=12)

        if status == "not_installed":
            btn = ctk.CTkButton(btn_frame, text="Install",
                               width=100, height=32,
                               fg_color=Theme.ACCENT,
                               hover_color=Theme.ACCENT_HOVER,
                               command=lambda p=prog: self.install_program(p))
        elif status == "update_available":
            btn = ctk.CTkButton(btn_frame, text="Update",
                               width=100, height=32,
                               fg_color=Theme.WARNING,
                               hover_color="#d97706",
                               command=lambda p=prog: self.install_program(p))
        else:
            btn = ctk.CTkButton(btn_frame, text="Launch",
                               width=100, height=32,
                               fg_color=Theme.SUCCESS,
                               hover_color="#059669",
                               command=lambda p=prog: self.launch_program(p))

        btn.pack()

        # Changelog button
        if prog.get('changelog'):
            ctk.CTkButton(btn_frame, text="Notes",
                         width=100, height=26,
                         fg_color="transparent",
                         text_color=Theme.TEXT3,
                         hover_color=Theme.BG3,
                         font=ctk.CTkFont(size=9),
                         command=lambda p=prog: self.show_changelog(p)).pack(pady=(5, 0))

    def _compare_version(self, v1, v2):
        """เปรียบเทียบ version: return 1 if v1>v2, 0 if equal, -1 if v1<v2"""
        def parse(v):
            try:
                return [int(x) for x in v.split('.')]
            except:
                return [0]
        p1, p2 = parse(v1), parse(v2)
        if p1 > p2: return 1
        if p1 < p2: return -1
        return 0

    def install_program(self, prog):
        """ดาวน์โหลดและติดตั้งโปรแกรม"""
        pid = prog['id']
        name = prog.get('name', 'Unknown')
        url = prog.get('download_url')
        version = prog.get('version', '0.0.0')

        if not url:
            messagebox.showerror("Error", "No download URL available", parent=self)
            return

        if not messagebox.askyesno("Confirm", f"Install/Update {name} v{version}?", parent=self):
            return

        # สร้าง dialog แสดงความคืบหน้า
        dialog = InstallDialog(self, prog)
        dialog.transient(self)
        dialog.grab_set()

    def launch_program(self, prog):
        """เปิดโปรแกรมที่ติดตั้งแล้ว"""
        pid = prog['id']
        installed = self.installed_programs.get(pid, {})
        exe_path = installed.get('path')

        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror("Error", f"Program file not found.\nPlease reinstall.", parent=self)
            return

        try:
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            messagebox.showinfo("Launched", f"{prog['name']} started successfully!", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch:\n{e}", parent=self)

    def show_changelog(self, prog):
        changelog = prog.get('changelog', 'No changelog available')
        messagebox.showinfo(f"Changelog - {prog['name']}", changelog, parent=self)

    def do_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?", parent=self):
            self.user.logout()
            self.destroy()
            sys.exit(0)


# ============================================================
# INSTALL DIALOG
# ============================================================
class InstallDialog(ctk.CTkToplevel):
    def __init__(self, parent, prog):
        super().__init__(parent)
        self.parent_app = parent
        self.prog = prog
        self.title(f"Installing {prog['name']}")
        self.geometry("500x300")
        self.resizable(False, False)

        self._build_ui()
        self.after(100, self.start_install)

    def _build_ui(self):
        ctk.CTkLabel(self, text=f"Installing {self.prog['name']}",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=Theme.TEXT).pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Preparing...",
                                        text_color=Theme.TEXT2)
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, width=400, height=10)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.detail_label = ctk.CTkLabel(self, text="",
                                        text_color=Theme.TEXT3,
                                        font=ctk.CTkFont(size=10, family="Consolas"))
        self.detail_label.pack(pady=5)

        self.close_btn = ctk.CTkButton(self, text="Close",
                                      state="disabled",
                                      command=self.destroy)
        self.close_btn.pack(pady=15)

    def start_install(self):
        def worker():
            pid = self.prog['id']
            url = self.prog['download_url']
            version = self.prog['version']
            name = self.prog['name']

            try:
                # สร้างโฟลเดอร์
                prog_dir = PROGRAMS_DIR / pid
                prog_dir.mkdir(parents=True, exist_ok=True)

                # หาชื่อไฟล์จาก URL
                filename = url.split('/')[-1]
                if not filename.endswith('.exe'):
                    filename = f"{pid}.exe"
                filepath = prog_dir / filename

                self.after(0, lambda: self.status_label.configure(text="Downloading..."))

                # ดาวน์โหลด
                headers = {}
                if self.parent_app.user.user_key:
                    headers['X-User-Key'] = self.parent_app.user.user_key

                resp = requests.get(url, headers=headers, stream=True, timeout=60)
                if resp.status_code != 200:
                    self.after(0, lambda: self._fail(f"Download failed: HTTP {resp.status_code}"))
                    return

                total = int(resp.headers.get('content-length', 0))
                downloaded = 0

                with open(filepath, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = downloaded / total
                                self.after(0, lambda p=pct: self.progress.set(p))
                                mb_d = downloaded / 1048576
                                mb_t = total / 1048576
                                self.after(0, lambda d=mb_d, t=mb_t: self.detail_label.configure(
                                    text=f"{d:.1f} MB / {t:.1f} MB"))

                # บันทึกข้อมูลการติดตั้ง
                self.parent_app.installed_programs[pid] = {
                    'version': version,
                    'path': str(filepath),
                    'installed_at': datetime.now().isoformat(),
                    'filename': filename
                }
                self.parent_app._save_installed()

                self.after(0, lambda: self._success(name, version))

            except Exception as e:
                self.after(0, lambda: self._fail(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _success(self, name, version):
        self.status_label.configure(text="✓ Installation complete!", text_color=Theme.SUCCESS)
        self.progress.set(1.0)
        self.detail_label.configure(text=f"{name} v{version} ready to launch")
        self.close_btn.configure(state="normal")

        # รีเฟรช launcher
        self.parent_app.refresh_programs()

    def _fail(self, msg):
        self.status_label.configure(text="✗ Installation failed", text_color=Theme.DANGER)
        self.detail_label.configure(text=msg)
        self.close_btn.configure(state="normal", text="Close")


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    if os.name != 'nt':
        print("Windows only")
        sys.exit(1)

    # หน้า Login
    login = LoginScreen()
    login.mainloop()

    if not login.success:
        sys.exit(0)

    # หน้า Launcher หลัก
    app = MainLauncher(login.user, login.server)
    app.mainloop()


if __name__ == "__main__":
    main()
