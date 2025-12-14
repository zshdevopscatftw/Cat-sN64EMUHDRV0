import os
import platform
import requests
import zipfile
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sys
import shutil
from pathlib import Path

# Debug: OS detection
sys_os = platform.system().lower()
machine = platform.machine().lower()
print(f"Debug: Detected OS: {sys_os}, Machine: {machine}")

# Documents path
documents = Path(os.path.expanduser("~/Documents"))
retroarch_dir = documents / "RetroArch"
cores_dir = retroarch_dir / "cores"
retroarch_dir.mkdir(parents=True, exist_ok=True)
print(f"Debug: Target dir: {retroarch_dir}")

# RetroArch version and links (stable where possible, nightly for mac cores)
ra_version = "1.22.1"
base_url = "https://buildbot.libretro.com/stable/1.22.1/"

# OS-specific RetroArch download
if sys_os == "windows":
    ra_url = f"{base_url}windows/x86_64/RetroArch.7z"
    ra_file = retroarch_dir / "RetroArch.7z"
    core_url = "https://buildbot.libretro.com/nightly/windows/x86_64/latest/parallel_n64_libretro.dll.zip"
    core_ext = ".dll"
elif sys_os == "linux":
    ra_url = f"{base_url}linux/x86_64/RetroArch.7z"
    ra_file = retroarch_dir / "RetroArch.7z"
    core_url = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/parallel_n64_libretro.so.zip"
    core_ext = ".so"
elif sys_os == "darwin":  # macOS
    if "arm" in machine:
        ra_url = f"{base_url}apple/osx/universal/RetroArch_Metal.dmg"  # Universal for M1+
    else:
        ra_url = f"{base_url}apple/osx/universal/RetroArch_Metal.dmg"  # Same universal
    ra_file = retroarch_dir / "RetroArch_Metal.dmg"
    core_url = f"https://buildbot.libretro.com/nightly/apple/osx/{'arm64' if 'arm' in machine else 'x86_64'}/latest/parallel_n64_libretro.dylib.zip"
    core_ext = ".dylib"
else:
    raise ValueError("Unsupported OS")

# Download function
def download(url, path):
    if path.exists():
        print(f"Debug: {path} already exists, skipping download")
        return
    print(f"Debug: Downloading {url} to {path}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# Download RetroArch
download(ra_url, ra_file)

# Extract/Install RetroArch
if sys_os in ["windows", "linux"]:
    print(f"Debug: Extracting 7z for {sys_os}")
    import py7zr  # Assume installed, or use subprocess 7z
    try:
        with py7zr.SevenZipFile(ra_file, mode='r') as z:
            z.extractall(retroarch_dir)
    except ImportError:
        # Fallback to subprocess if py7zr not available
        subprocess.call(['7z', 'x', str(ra_file), f"-o{retroarch_dir}"])
elif sys_os == "darwin":
    print("Debug: Mounting DMG on macOS")
    mount_point = retroarch_dir / "mount"
    mount_point.mkdir(exist_ok=True)
    subprocess.call(['hdiutil', 'attach', str(ra_file), '-mountpoint', str(mount_point)])
    app_path = mount_point / "RetroArch.app"
    target_app = retroarch_dir / "RetroArch.app"
    if app_path.exists():
        shutil.copytree(app_path, target_app, dirs_exist_ok=True)
    subprocess.call(['hdiutil', 'detach', str(mount_point)])
    cores_dir = target_app / "Contents" / "Resources" / "cores"  # mac app bundle cores path
    cores_dir.mkdir(parents=True, exist_ok=True)

# Download parallel_n64 core
core_file = retroarch_dir / f"parallel_n64_libretro{core_ext}.zip"
download(core_url, core_file)

# Extract core
print("Debug: Extracting core")
with zipfile.ZipFile(core_file, 'r') as z:
    z.extractall(cores_dir)

# RetroArch executable path
if sys_os == "windows":
    ra_exe = retroarch_dir / "retroarch.exe"
elif sys_os == "linux":
    ra_exe = retroarch_dir / "retroarch"
    os.chmod(ra_exe, 0o755)  # Make executable
elif sys_os == "darwin":
    ra_exe = retroarch_dir / "RetroArch.app" / "Contents" / "MacOS" / "RetroArch"
    os.chmod(ra_exe, 0o755)

print(f"Debug: RetroArch exe: {ra_exe}")

# Tkinter GUI - Clone Project64 1.6 legacy style: Menu, ROM list, basic buttons
class PJ64Revamped(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Samsoft's Parallel Launcher PJ64 Revamped 0.1")
        self.geometry("800x600")
        self.rom_dir = documents / "ROMs"  # Assume ROMs in Documents/ROMs
        self.rom_dir.mkdir(exist_ok=True)
        self.roms = []

        # Menu bar
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open ROM...", command=self.open_rom)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        systemmenu = tk.Menu(menubar, tearoff=0)
        systemmenu.add_command(label="Reset", state="disabled")  # Placeholder
        systemmenu.add_command(label="Pause", state="disabled")
        systemmenu.add_command(label="Resume", state="disabled")
        menubar.add_cascade(label="System", menu=systemmenu)

        optionsmenu = tk.Menu(menubar, tearoff=0)
        optionsmenu.add_command(label="Settings...", command=self.settings)
        menubar.add_cascade(label="Options", menu=optionsmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.config(menu=menubar)

        # Toolbar (simplified)
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X)
        tk.Button(toolbar, text="Refresh ROMs", command=self.load_roms).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Settings", command=self.settings).pack(side=tk.LEFT)

        # ROM list
        columns = ("Good Name", "File Name", "Size")
        self.rom_list = ttk.Treeview(self, columns=columns, show="headings")
        self.rom_list.heading("Good Name", text="Good Name")
        self.rom_list.heading("File Name", text="File Name")
        self.rom_list.heading("Size", text="Size")
        self.rom_list.pack(fill=tk.BOTH, expand=True)

        # Load ROMs
        self.load_roms()

        # Double-click to run
        self.rom_list.bind("<Double-1>", self.run_rom)

    def load_roms(self):
        self.rom_list.delete(*self.rom_list.get_children())
        self.roms = list(self.rom_dir.glob("*.[nNzZ]64"))  # .n64, .z64 etc.
        for rom in self.roms:
            size = os.path.getsize(rom) / (1024 * 1024)  # MB
            self.rom_list.insert("", "end", values=(rom.stem, rom.name, f"{size:.2f} MB"))
        print(f"Debug: Loaded {len(self.roms)} ROMs")

    def open_rom(self):
        rom_path = filedialog.askopenfilename(filetypes=[("N64 ROMs", "*.n64 *.z64")])
        if rom_path:
            self.run_rom_path(rom_path)

    def run_rom(self, event):
        selected = self.rom_list.selection()
        if selected:
            index = self.rom_list.index(selected[0])
            rom_path = str(self.roms[index])
            self.run_rom_path(rom_path)

    def run_rom_path(self, rom_path):
        print(f"Debug: Launching {rom_path}")
        core_path = str(cores_dir / f"parallel_n64_libretro{core_ext}")
        cmd = [str(ra_exe), "-L", core_path, rom_path]
        subprocess.Popen(cmd)

    def settings(self):
        messagebox.showinfo("Settings", "Settings placeholder - configure in RetroArch directly.")

    def about(self):
        messagebox.showinfo("About", "Samsoft's Parallel Launcher PJ64 Revamped 0.1\nBackend: RetroArch + parallel_n64\nUnrestricted N64 emulation wrapper.")

if __name__ == "__main__":
    app = PJ64Revamped()
    app.mainloop()
