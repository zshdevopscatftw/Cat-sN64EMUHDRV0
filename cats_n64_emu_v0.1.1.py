#!/usr/bin/env python3
"""
Cat's N64 EMU v0.1.1
Auto-detects OS and installs RetroArch to standard system locations.
"""

import os
import platform
import requests
import zipfile
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import shutil
from pathlib import Path

# =============================================================================
# OS DETECTION & PATH CONFIGURATION
# =============================================================================

SYS_OS = platform.system().lower()
MACHINE = platform.machine().lower()
HOME = Path.home()

print(f"[Setup] Detected: {platform.system()} {platform.release()} ({MACHINE})")


def get_platform_paths():
    """
    Returns platform-specific paths for RetroArch installation.
    
    Returns dict with:
        - retroarch_dir: Where RetroArch binary/app lives
        - config_dir: Where configs/settings go
        - cores_dir: Where libretro cores go
        - ra_exe: Path to RetroArch executable
        - ra_url: Download URL for RetroArch
        - ra_file: Downloaded archive filename
        - core_url: Download URL for parallel_n64 core
        - core_ext: Core file extension
    """
    ra_version = "1.22.1"
    base_url = f"https://buildbot.libretro.com/stable/{ra_version}/"
    
    if SYS_OS == "windows":
        # Windows: AppData/Roaming/RetroArch (user-writable, no admin needed)
        appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
        retroarch_dir = appdata / "RetroArch"
        config_dir = retroarch_dir
        cores_dir = retroarch_dir / "cores"
        ra_exe = retroarch_dir / "retroarch.exe"
        
        # Detect architecture
        if "64" in MACHINE or "amd64" in MACHINE.lower():
            ra_url = f"{base_url}windows/x86_64/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/windows/x86_64/latest/parallel_n64_libretro.dll.zip"
        else:
            ra_url = f"{base_url}windows/x86/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/windows/x86/latest/parallel_n64_libretro.dll.zip"
        
        ra_file = retroarch_dir / "RetroArch.7z"
        core_ext = ".dll"
        
    elif SYS_OS == "darwin":
        # macOS: /Applications for app, ~/Library/Application Support for data
        retroarch_dir = Path("/Applications")
        config_dir = HOME / "Library" / "Application Support" / "RetroArch"
        # Cores go inside app bundle OR in Application Support
        cores_dir = config_dir / "cores"
        ra_exe = retroarch_dir / "RetroArch.app" / "Contents" / "MacOS" / "RetroArch"
        
        # Universal binary works for both Intel and Apple Silicon
        ra_url = f"{base_url}apple/osx/universal/RetroArch_Metal.dmg"
        ra_file = config_dir / "downloads" / "RetroArch_Metal.dmg"
        
        # But cores are architecture-specific
        arch = "arm64" if "arm" in MACHINE else "x86_64"
        core_url = f"https://buildbot.libretro.com/nightly/apple/osx/{arch}/latest/parallel_n64_libretro.dylib.zip"
        core_ext = ".dylib"
        
    elif SYS_OS == "linux":
        # Linux: ~/.config/retroarch for configs, ~/.local/share/retroarch for data
        # Or use ~/.retroarch for simpler portable setup
        config_dir = HOME / ".config" / "retroarch"
        retroarch_dir = HOME / ".local" / "share" / "retroarch"
        cores_dir = retroarch_dir / "cores"
        ra_exe = retroarch_dir / "retroarch"
        
        # Detect architecture
        if "x86_64" in MACHINE or "amd64" in MACHINE:
            ra_url = f"{base_url}linux/x86_64/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/parallel_n64_libretro.so.zip"
        elif "aarch64" in MACHINE or "arm64" in MACHINE:
            ra_url = f"{base_url}linux/aarch64/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/linux/aarch64/latest/parallel_n64_libretro.so.zip"
        elif "arm" in MACHINE:
            ra_url = f"{base_url}linux/armhf/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/linux/armhf/latest/parallel_n64_libretro.so.zip"
        else:
            # Fallback to x86_64
            ra_url = f"{base_url}linux/x86_64/RetroArch.7z"
            core_url = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/parallel_n64_libretro.so.zip"
        
        ra_file = retroarch_dir / "RetroArch.7z"
        core_ext = ".so"
        
    else:
        raise ValueError(f"Unsupported OS: {SYS_OS}")
    
    return {
        "retroarch_dir": retroarch_dir,
        "config_dir": config_dir,
        "cores_dir": cores_dir,
        "ra_exe": ra_exe,
        "ra_url": ra_url,
        "ra_file": ra_file,
        "core_url": core_url,
        "core_ext": core_ext,
    }


# Get paths for current platform
PATHS = get_platform_paths()

# Create directories
PATHS["config_dir"].mkdir(parents=True, exist_ok=True)
PATHS["cores_dir"].mkdir(parents=True, exist_ok=True)
if SYS_OS == "darwin":
    (PATHS["config_dir"] / "downloads").mkdir(exist_ok=True)
elif SYS_OS != "darwin":
    PATHS["retroarch_dir"].mkdir(parents=True, exist_ok=True)

print(f"[Setup] RetroArch dir: {PATHS['retroarch_dir']}")
print(f"[Setup] Config dir: {PATHS['config_dir']}")
print(f"[Setup] Cores dir: {PATHS['cores_dir']}")

# Default ROM directory
ROM_DIR = HOME / "Documents" / "ROMs" / "N64"
ROM_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DOWNLOAD & INSTALLATION FUNCTIONS
# =============================================================================

def download(url, path, label="file"):
    """Download file with progress indication and error handling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        print(f"[Download] {label} already exists, skipping")
        return True
    
    print(f"[Download] Fetching {label}...")
    temp_path = path.with_suffix(path.suffix + ".tmp")
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = (downloaded / total) * 100
                    bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
                    print(f"\r  [{bar}] {pct:5.1f}%", end="", flush=True)
        
        print()
        temp_path.rename(path)
        print(f"[Download] Saved to {path}")
        return True
        
    except requests.RequestException as e:
        print(f"\n[Error] Download failed: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def extract_7z(archive_path, dest_dir):
    """Extract 7z archive using py7zr or system 7z."""
    print(f"[Extract] Unpacking {archive_path.name}...")
    
    # Try py7zr first
    try:
        import py7zr
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            z.extractall(dest_dir)
        print(f"[Extract] Done (py7zr)")
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"[Warning] py7zr failed: {e}")
    
    # Try system 7z variants
    for cmd in ['7z', '7za', '7zr']:
        if shutil.which(cmd):
            result = subprocess.run(
                [cmd, 'x', str(archive_path), f'-o{dest_dir}', '-y'],
                capture_output=True
            )
            if result.returncode == 0:
                print(f"[Extract] Done ({cmd})")
                return True
    
    # Windows: try bundled 7z if available
    if SYS_OS == "windows":
        sz_paths = [
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "7-Zip" / "7z.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "7-Zip" / "7z.exe",
        ]
        for sz in sz_paths:
            if sz.exists():
                result = subprocess.run(
                    [str(sz), 'x', str(archive_path), f'-o{dest_dir}', '-y'],
                    capture_output=True
                )
                if result.returncode == 0:
                    print(f"[Extract] Done (7-Zip)")
                    return True
    
    print("[Error] No 7z extraction tool available!")
    print("        Install one of: py7zr (pip), 7-Zip, p7zip")
    return False


def install_retroarch_windows():
    """Install RetroArch on Windows."""
    if not download(PATHS["ra_url"], PATHS["ra_file"], "RetroArch"):
        return False
    
    if not extract_7z(PATHS["ra_file"], PATHS["retroarch_dir"]):
        return False
    
    # RetroArch 7z extracts to a subdirectory (e.g., RetroArch-Win64/)
    # Find and move contents up if needed
    if not PATHS["ra_exe"].exists():
        print("[Install] Fixing directory structure...")
        for subdir in PATHS["retroarch_dir"].iterdir():
            if subdir.is_dir() and subdir.name.startswith("RetroArch"):
                # Found the nested directory, move contents up
                nested_exe = subdir / "retroarch.exe"
                if nested_exe.exists():
                    print(f"[Install] Moving files from {subdir.name}/...")
                    for item in subdir.iterdir():
                        dest = PATHS["retroarch_dir"] / item.name
                        if dest.exists():
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        shutil.move(str(item), str(dest))
                    # Remove empty subdirectory
                    try:
                        subdir.rmdir()
                    except OSError:
                        pass
                    break
    
    return PATHS["ra_exe"].exists()


def install_retroarch_linux():
    """Install RetroArch on Linux."""
    if not download(PATHS["ra_url"], PATHS["ra_file"], "RetroArch"):
        return False
    
    if not extract_7z(PATHS["ra_file"], PATHS["retroarch_dir"]):
        return False
    
    # RetroArch 7z may extract to a subdirectory - fix if needed
    if not PATHS["ra_exe"].exists():
        print("[Install] Fixing directory structure...")
        for subdir in PATHS["retroarch_dir"].iterdir():
            if subdir.is_dir() and subdir.name.startswith("RetroArch"):
                nested_exe = subdir / "retroarch"
                if nested_exe.exists():
                    print(f"[Install] Moving files from {subdir.name}/...")
                    for item in subdir.iterdir():
                        dest = PATHS["retroarch_dir"] / item.name
                        if dest.exists():
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        shutil.move(str(item), str(dest))
                    try:
                        subdir.rmdir()
                    except OSError:
                        pass
                    break
    
    # Make executable
    if PATHS["ra_exe"].exists():
        os.chmod(PATHS["ra_exe"], 0o755)
        
    return PATHS["ra_exe"].exists()


def install_retroarch_macos():
    """Install RetroArch on macOS."""
    if not download(PATHS["ra_url"], PATHS["ra_file"], "RetroArch"):
        return False
    
    print("[Install] Mounting DMG...")
    mount_point = PATHS["config_dir"] / "downloads" / "mount"
    mount_point.mkdir(exist_ok=True)
    
    try:
        # Mount
        result = subprocess.run(
            ['hdiutil', 'attach', str(PATHS["ra_file"]), 
             '-mountpoint', str(mount_point), '-nobrowse', '-quiet'],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"[Error] Mount failed: {result.stderr.decode()}")
            return False
        
        # Find and copy app
        app_src = mount_point / "RetroArch.app"
        app_dst = PATHS["retroarch_dir"] / "RetroArch.app"
        
        if not app_src.exists():
            print("[Error] RetroArch.app not found in DMG")
            return False
        
        print(f"[Install] Copying to {app_dst}...")
        if app_dst.exists():
            shutil.rmtree(app_dst)
        shutil.copytree(app_src, app_dst)
        
        # Make executable
        if PATHS["ra_exe"].exists():
            os.chmod(PATHS["ra_exe"], 0o755)
            
    finally:
        # Always unmount
        subprocess.run(['hdiutil', 'detach', str(mount_point), '-quiet'], 
                      capture_output=True)
    
    return PATHS["ra_exe"].exists()


def install_retroarch():
    """Install RetroArch for current platform."""
    if PATHS["ra_exe"].exists():
        print(f"[Setup] RetroArch already installed at {PATHS['ra_exe']}")
        return True
    
    print("[Setup] Installing RetroArch...")
    
    if SYS_OS == "windows":
        return install_retroarch_windows()
    elif SYS_OS == "darwin":
        return install_retroarch_macos()
    elif SYS_OS == "linux":
        return install_retroarch_linux()
    
    return False


def install_core():
    """Download and extract parallel_n64 core."""
    core_path = PATHS["cores_dir"] / f"parallel_n64_libretro{PATHS['core_ext']}"
    
    if core_path.exists():
        print(f"[Setup] Core already installed at {core_path}")
        return True
    
    core_zip = PATHS["config_dir"] / f"parallel_n64{PATHS['core_ext']}.zip"
    
    if not download(PATHS["core_url"], core_zip, "parallel_n64 core"):
        return False
    
    print(f"[Install] Extracting core to {PATHS['cores_dir']}...")
    try:
        with zipfile.ZipFile(core_zip, 'r') as z:
            z.extractall(PATHS["cores_dir"])
        
        # Make executable on Unix
        if SYS_OS != "windows" and core_path.exists():
            os.chmod(core_path, 0o755)
            
        return core_path.exists()
        
    except zipfile.BadZipFile as e:
        print(f"[Error] Core extraction failed: {e}")
        return False


# =============================================================================
# GUI APPLICATION
# =============================================================================

class PJ64Revamped(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cat's N64 EMU v0.1.1")
        self.geometry("850x600")
        self.minsize(600, 400)
        
        # Theme colors
        self.colors = {
            "bg": "#1a1a2e",
            "fg": "#eaeaea",
            "accent": "#0f3460",
            "highlight": "#e94560",
            "toolbar": "#16213e",
        }
        self.configure(bg=self.colors["bg"])
        
        self.rom_dir = ROM_DIR
        self.roms = {}  # iid -> Path
        
        self._setup_styles()
        self._create_menu()
        self._create_toolbar()
        self._create_statusbar()
        self._create_rom_list()
        
        self.load_roms()
        self.update_status()
        
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Treeview",
                       background=self.colors["bg"],
                       foreground=self.colors["fg"],
                       fieldbackground=self.colors["bg"],
                       rowheight=28)
        style.configure("Treeview.Heading",
                       background=self.colors["toolbar"],
                       foreground=self.colors["fg"],
                       font=('Segoe UI', 10, 'bold'))
        style.map("Treeview",
                 background=[('selected', self.colors["accent"])])
        
    def _create_menu(self):
        menubar = tk.Menu(self, bg=self.colors["toolbar"], fg=self.colors["fg"])
        
        # File menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open ROM...", command=self.open_rom, accelerator="Ctrl+O")
        filemenu.add_command(label="Refresh ROM List", command=self.load_roms, accelerator="F5")
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Options menu
        optionsmenu = tk.Menu(menubar, tearoff=0)
        optionsmenu.add_command(label="Set ROM Directory...", command=self.set_rom_dir)
        optionsmenu.add_command(label="Open RetroArch Config...", command=self.open_config_dir)
        optionsmenu.add_separator()
        optionsmenu.add_command(label="Launch RetroArch", command=self.launch_retroarch)
        menubar.add_cascade(label="Options", menu=optionsmenu)
        
        # Help menu
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.about)
        helpmenu.add_command(label="System Info", command=self.system_info)
        menubar.add_cascade(label="Help", menu=helpmenu)
        
        self.config(menu=menubar)
        
        # Keyboard shortcuts
        self.bind("<Control-o>", lambda e: self.open_rom())
        self.bind("<F5>", lambda e: self.load_roms())
        
    def _create_toolbar(self):
        toolbar = tk.Frame(self, bg=self.colors["toolbar"], height=40)
        toolbar.pack(fill=tk.X, padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        btn_style = {"bg": self.colors["accent"], "fg": self.colors["fg"],
                    "activebackground": self.colors["highlight"],
                    "activeforeground": "white", "relief": "flat",
                    "padx": 12, "pady": 5, "font": ('Segoe UI', 9)}
        
        tk.Button(toolbar, text="📂 Open ROM", command=self.open_rom, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="🔄 Refresh", command=self.load_roms, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="📁 ROM Folder", command=self.set_rom_dir, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="⚙️ RetroArch", command=self.launch_retroarch, **btn_style).pack(side=tk.LEFT, padx=4, pady=4)
        
    def _create_statusbar(self):
        self.statusbar = tk.Label(self, text="Ready", anchor=tk.W,
                                  bg=self.colors["toolbar"], fg=self.colors["fg"],
                                  padx=10, pady=5)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _create_rom_list(self):
        container = tk.Frame(self, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        columns = ("name", "filename", "size", "format")
        self.rom_list = ttk.Treeview(container, columns=columns, show="headings")
        
        self.rom_list.heading("name", text="Game Title")
        self.rom_list.heading("filename", text="File Name")
        self.rom_list.heading("size", text="Size")
        self.rom_list.heading("format", text="Format")
        
        self.rom_list.column("name", width=350, minwidth=200)
        self.rom_list.column("filename", width=250, minwidth=150)
        self.rom_list.column("size", width=80, minwidth=60, anchor=tk.E)
        self.rom_list.column("format", width=60, minwidth=50, anchor=tk.CENTER)
        
        scrollbar_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.rom_list.yview)
        scrollbar_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.rom_list.xview)
        self.rom_list.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.rom_list.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        self.rom_list.bind("<Double-1>", self.run_selected_rom)
        self.rom_list.bind("<Return>", self.run_selected_rom)
        
    def load_roms(self):
        self.rom_list.delete(*self.rom_list.get_children())
        self.roms.clear()
        
        extensions = ['*.n64', '*.N64', '*.z64', '*.Z64', '*.v64', '*.V64']
        rom_files = []
        for ext in extensions:
            rom_files.extend(self.rom_dir.glob(ext))
        
        # Dedupe (case-insensitive filesystems)
        seen = set()
        unique = []
        for rom in rom_files:
            key = str(rom).lower()
            if key not in seen:
                seen.add(key)
                unique.append(rom)
        
        for rom in sorted(unique, key=lambda r: r.stem.lower()):
            try:
                size = rom.stat().st_size / (1024 * 1024)
                fmt = rom.suffix.upper().replace(".", "")
                iid = self.rom_list.insert("", "end",
                                           values=(rom.stem, rom.name, f"{size:.1f} MB", fmt))
                self.roms[iid] = rom
            except OSError:
                pass
        
        self.update_status()
        
    def update_status(self):
        count = len(self.roms)
        self.statusbar.config(text=f"{count} ROM{'s' if count != 1 else ''} | {self.rom_dir}")
        
    def open_rom(self):
        rom_path = filedialog.askopenfilename(
            title="Open N64 ROM",
            initialdir=self.rom_dir,
            filetypes=[("N64 ROMs", "*.n64 *.z64 *.v64"), ("All files", "*.*")]
        )
        if rom_path:
            self.run_rom_path(Path(rom_path))
            
    def run_selected_rom(self, event=None):
        selected = self.rom_list.selection()
        if not selected:
            return
        
        rom_path = self.roms.get(selected[0])
        if rom_path and rom_path.exists():
            self.run_rom_path(rom_path)
        else:
            messagebox.showerror("Error", "ROM file not found. Try refreshing.")
            
    def run_rom_path(self, rom_path):
        if not PATHS["ra_exe"].exists():
            messagebox.showerror("Error", f"RetroArch not found:\n{PATHS['ra_exe']}")
            return
        
        core_path = PATHS["cores_dir"] / f"parallel_n64_libretro{PATHS['core_ext']}"
        if not core_path.exists():
            messagebox.showerror("Error", f"Core not found:\n{core_path}")
            return
        
        print(f"[Launch] {rom_path.name}")
        cmd = [str(PATHS["ra_exe"]), "-L", str(core_path), str(rom_path)]
        
        try:
            if SYS_OS == "darwin":
                # macOS: use open command for proper app launching
                subprocess.Popen(['open', '-a', str(PATHS["retroarch_dir"] / "RetroArch.app"),
                                 '--args', '-L', str(core_path), str(rom_path)])
            else:
                subprocess.Popen(cmd)
        except OSError as e:
            messagebox.showerror("Error", f"Launch failed:\n{e}")
            
    def set_rom_dir(self):
        new_dir = filedialog.askdirectory(title="Select ROM Directory", initialdir=self.rom_dir)
        if new_dir:
            self.rom_dir = Path(new_dir)
            self.load_roms()
            
    def open_config_dir(self):
        path = PATHS["config_dir"]
        if SYS_OS == "windows":
            os.startfile(path)
        elif SYS_OS == "darwin":
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])
            
    def launch_retroarch(self):
        if not PATHS["ra_exe"].exists():
            messagebox.showerror("Error", "RetroArch not installed!")
            return
        
        if SYS_OS == "darwin":
            subprocess.Popen(['open', '-a', str(PATHS["retroarch_dir"] / "RetroArch.app")])
        else:
            subprocess.Popen([str(PATHS["ra_exe"])])
            
    def about(self):
        messagebox.showinfo("About",
            "Cat's N64 EMU v0.1.1\n\n"
            "🐱 Meow-powered N64 emulation!\n\n"
            "Backend: RetroArch + parallel_n64\n"
            "A lightweight N64 emulation frontend.\n\n"
            "© 2024 Team Flames / CatOS")
        
    def system_info(self):
        info = (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Architecture: {MACHINE}\n\n"
            f"RetroArch: {PATHS['ra_exe']}\n"
            f"Cores: {PATHS['cores_dir']}\n"
            f"Config: {PATHS['config_dir']}\n\n"
            f"ROMs: {self.rom_dir}"
        )
        messagebox.showinfo("System Info", info)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("  🐱 Cat's N64 EMU v0.1.1")
    print("=" * 60)
    print()
    
    # Install RetroArch
    if not install_retroarch():
        print("\n[Error] RetroArch installation failed!")
        print("You may need to install manually or check your internet connection.")
        input("\nPress Enter to continue anyway...")
    
    # Install core
    if not install_core():
        print("\n[Error] Core installation failed!")
        print("You can download cores manually via RetroArch's Online Updater.")
        input("\nPress Enter to continue anyway...")
    
    print("\n[Ready] Launching GUI...\n")
    
    app = PJ64Revamped()
    app.mainloop()


if __name__ == "__main__":
    main()
