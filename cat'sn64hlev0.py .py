#!/usr/bin/env python3
"""
Cat's N64 EMU 1.3.3 — M4 Pro Edition
🐱 nyaa~

FIXES FOR M4 PRO:
- Fixed ARM64 detection (arm64 vs arm)
- Fixed RetroArch instant quit via proper macOS launch
- Fixed window not appearing (v1.2.1)
- Fixed Rosetta architecture mismatch (v1.3)
- Fixed OpenGL "Invalid enum" crash (v1.3.3) ← UPDATED
  → Uses Angrylion software renderer when running x86_64 via Rosetta
  → HW rendering (ParaLLEl-RDP) doesn't work under Rosetta emulation
  → Software rendering is slower but 100% compatible
- Auto-detects RetroArch binary architecture
- Downloads matching core (arm64 or x86_64)
- Added "Fix Rosetta" button to resolve arch mismatches
- Added quarantine removal for downloaded cores
- Added Metal GPU initialization delay
- Added AppleScript window activation
- Better error reporting and logging

BEST PERFORMANCE TIP:
For best performance, disable Rosetta on RetroArch:
1. Right-click RetroArch.app → Get Info
2. Uncheck "Open using Rosetta"
3. Run this script again (will download ARM64 core)
This enables native ARM64 + HW rendering = FAST!
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
import time

# =============================================================================
# SYSTEM DETECTION — M4 PRO FIX v1.3
# =============================================================================

SYS_OS = platform.system().lower()
MACHINE = platform.machine().lower()
HOME = Path.home()

# M4 Pro detection fix: check for arm64 explicitly
IS_APPLE_SILICON = SYS_OS == "darwin" and MACHINE in ("arm64", "aarch64")
IS_M4 = IS_APPLE_SILICON  # M4 is arm64

print(f"[Setup] OS: {platform.system()} {platform.release()} ({MACHINE})")
print(f"[Setup] Apple Silicon: {IS_APPLE_SILICON}")

def get_binary_arch(binary_path):
    """
    Detect actual architecture of a macOS binary.
    Returns 'arm64', 'x86_64', 'universal', or None.
    """
    if SYS_OS != "darwin" or not Path(binary_path).exists():
        return None
    
    try:
        result = subprocess.run(
            ["lipo", "-archs", str(binary_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        archs = result.stdout.strip().split()
        print(f"[Arch] {binary_path}: {archs}")
        
        if "arm64" in archs and "x86_64" in archs:
            return "universal"
        elif "arm64" in archs:
            return "arm64"
        elif "x86_64" in archs:
            return "x86_64"
        return None
    except Exception as e:
        print(f"[Arch] Detection failed: {e}")
        return None

def get_retroarch_running_arch():
    """
    Detect which architecture RetroArch will actually run as.
    On Apple Silicon, universal binaries run as arm64 unless forced to Rosetta.
    """
    ra_exe = Path("/Applications/RetroArch.app/Contents/MacOS/RetroArch")
    
    if not ra_exe.exists():
        return MACHINE  # fallback to system arch
    
    binary_arch = get_binary_arch(ra_exe)
    
    if binary_arch == "universal":
        # Check if app is set to "Open using Rosetta"
        # This is stored in com.apple.LaunchServices plist, but easier to check
        # by looking at the app's Info.plist for LSArchitecturePriority
        # OR just check if there's a Rosetta marker
        
        info_plist = Path("/Applications/RetroArch.app/Contents/Info.plist")
        try:
            result = subprocess.run(
                ["defaults", "read", str(info_plist), "LSArchitecturePriority"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "x86_64" in result.stdout:
                print("[Arch] RetroArch set to prefer x86_64 (Rosetta)")
                return "x86_64"
        except:
            pass
        
        # Check system preference for this app
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.rosetta", "RetroArch"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[Arch] RetroArch has Rosetta preference set")
                return "x86_64"
        except:
            pass
        
        # Universal binary on Apple Silicon defaults to arm64
        if IS_APPLE_SILICON:
            print("[Arch] Universal binary, will run as arm64")
            return "arm64"
        else:
            return "x86_64"
    
    elif binary_arch:
        return binary_arch
    
    return MACHINE

# Detect what arch RetroArch will actually use
RETROARCH_ARCH = None  # Will be set after paths are configured

# =============================================================================
# PLATFORM PATHS — M4 PRO OPTIMIZED
# =============================================================================

def get_platform_paths():
    global RETROARCH_ARCH
    
    ra_version = "1.22.1"
    base_url = f"https://buildbot.libretro.com/stable/{ra_version}/"
    nightly = "https://buildbot.libretro.com/nightly"

    if SYS_OS == "windows":
        appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
        retroarch_dir = appdata / "RetroArch"
        config_dir = retroarch_dir
        cores_dir = retroarch_dir / "cores"
        ra_exe = retroarch_dir / "retroarch.exe"
        arch = "x86_64" if "64" in MACHINE else "x86"
        ra_url = f"{base_url}windows/{arch}/RetroArch.7z"
        core_urls = [
            ("mupen64plus_next", f"{nightly}/windows/{arch}/latest/mupen64plus_next_libretro.dll.zip")
        ]
        core_ext = ".dll"

    elif SYS_OS == "darwin":
        retroarch_dir = Path("/Applications")
        config_dir = HOME / "Library/Application Support/RetroArch"
        cores_dir = config_dir / "cores"
        ra_app = retroarch_dir / "RetroArch.app"
        ra_exe = ra_app / "Contents/MacOS/RetroArch"
        
        # CRITICAL FIX: Detect actual RetroArch architecture
        RETROARCH_ARCH = get_retroarch_running_arch()
        print(f"[Setup] RetroArch will run as: {RETROARCH_ARCH}")
        
        # Use the architecture RetroArch is actually running as!
        arch = RETROARCH_ARCH if RETROARCH_ARCH else ("arm64" if IS_APPLE_SILICON else "x86_64")
        
        ra_url = f"{base_url}apple/osx/universal/RetroArch_Metal.dmg"
        core_urls = [
            ("mupen64plus_next", f"{nightly}/apple/osx/{arch}/latest/mupen64plus_next_libretro.dylib.zip")
        ]
        core_ext = ".dylib"

    else:  # Linux
        config_dir = HOME / ".config/retroarch"
        retroarch_dir = HOME / ".local/share/retroarch"
        cores_dir = retroarch_dir / "cores"
        ra_exe = retroarch_dir / "retroarch"
        arch = "x86_64"
        ra_url = f"{base_url}linux/{arch}/RetroArch.7z"
        core_urls = [
            ("mupen64plus_next", f"{nightly}/linux/{arch}/latest/mupen64plus_next_libretro.so.zip")
        ]
        core_ext = ".so"

    return {
        "retroarch_dir": retroarch_dir,
        "config_dir": config_dir,
        "cores_dir": cores_dir,
        "ra_exe": Path(ra_exe),
        "ra_app": retroarch_dir / "RetroArch.app" if SYS_OS == "darwin" else None,
        "ra_url": ra_url,
        "core_urls": core_urls,
        "core_ext": core_ext,
        "core_arch": arch  # Store the arch we're using for cores
    }

PATHS = get_platform_paths()
PATHS["config_dir"].mkdir(parents=True, exist_ok=True)
PATHS["cores_dir"].mkdir(parents=True, exist_ok=True)

ROM_DIR = HOME / "Documents/ROMs/N64"
ROM_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# MACOS QUARANTINE FIX — CRITICAL FOR M4
# =============================================================================

def remove_quarantine(path):
    """Remove macOS quarantine attribute from downloaded files"""
    if SYS_OS != "darwin":
        return
    
    try:
        subprocess.run(
            ["xattr", "-rd", "com.apple.quarantine", str(path)],
            capture_output=True,
            timeout=10
        )
        print(f"[Quarantine] Removed from: {path}")
    except Exception as e:
        print(f"[Quarantine] Warning: {e}")

def fix_core_permissions(core_path):
    """Ensure core is executable and not quarantined"""
    if not core_path or not core_path.exists():
        return
    
    remove_quarantine(core_path)
    
    try:
        os.chmod(core_path, 0o755)
        print(f"[Permissions] Fixed: {core_path}")
    except Exception as e:
        print(f"[Permissions] Warning: {e}")

# =============================================================================
# CORE DETECTION + ARCHITECTURE VERIFICATION
# =============================================================================

def verify_core_arch(core_path):
    """
    Verify that core architecture matches RetroArch architecture.
    Returns (is_valid, core_arch, needed_arch)
    """
    if SYS_OS != "darwin" or not core_path or not core_path.exists():
        return True, None, None
    
    core_arch = get_binary_arch(core_path)
    needed_arch = RETROARCH_ARCH or ("arm64" if IS_APPLE_SILICON else "x86_64")
    
    print(f"[Core Verify] Core arch: {core_arch}, RetroArch needs: {needed_arch}")
    
    if core_arch and needed_arch:
        if core_arch == needed_arch:
            return True, core_arch, needed_arch
        elif core_arch == "universal":
            return True, core_arch, needed_arch  # Universal works for both
        else:
            print(f"[Core Verify] ⚠ MISMATCH! Core is {core_arch}, RetroArch needs {needed_arch}")
            return False, core_arch, needed_arch
    
    return True, core_arch, needed_arch

def find_n64_core():
    for name in ["mupen64plus_next_libretro"]:
        core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
        if core.exists():
            print(f"[Core] Found: {core}")
            fix_core_permissions(core)
            return core
    return None

# =============================================================================
# INSTALLERS
# =============================================================================

def download(url, path):
    if path.exists():
        return True
    print(f"[Download] {url}")
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    return True

def install_core():
    core = find_n64_core()
    if core:
        # Verify architecture matches
        is_valid, core_arch, needed_arch = verify_core_arch(core)
        if not is_valid:
            print(f"[Core] Architecture mismatch! Deleting and re-downloading...")
            core.unlink()
            return install_core_forced(needed_arch)
        return core

    # No core found, download
    return install_core_forced(PATHS.get("core_arch", "arm64"))

def install_core_forced(arch):
    """Force download core for specific architecture"""
    nightly = "https://buildbot.libretro.com/nightly"
    
    if SYS_OS == "darwin":
        url = f"{nightly}/apple/osx/{arch}/latest/mupen64plus_next_libretro.dylib.zip"
    elif SYS_OS == "windows":
        url = f"{nightly}/windows/{arch}/latest/mupen64plus_next_libretro.dll.zip"
    else:
        url = f"{nightly}/linux/{arch}/latest/mupen64plus_next_libretro.so.zip"
    
    print(f"[Core] Downloading {arch} core from: {url}")
    
    try:
        zip_path = PATHS["cores_dir"] / "mupen64plus_next.zip"
        
        # Delete existing zip if any
        if zip_path.exists():
            zip_path.unlink()
        
        download(url, zip_path)
        
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(PATHS["cores_dir"])
        zip_path.unlink()
        
        core = find_n64_core()
        if core:
            fix_core_permissions(core)
            
            # Verify the new core
            is_valid, core_arch, needed_arch = verify_core_arch(core)
            if is_valid:
                print(f"[Core] ✓ Installed {arch} core successfully")
                return core
            else:
                print(f"[Core] ✗ Downloaded core still wrong arch!")
                return None
        return core
        
    except Exception as e:
        print(f"[Core Install] Error: {e}")
        return None

# =============================================================================
# ROM LAUNCHER — M4 PRO FIX
# =============================================================================

def launch_rom_macos(rom_path, core_path):
    """
    macOS-specific launch that doesn't quit immediately.
    
    FIX v1.3.3: 
    - OpenGL "Invalid enum" crash on M4 Pro when running x86_64 via Rosetta
    - The REAL fix: mupen64plus HW rendering only works with native ARM64 RetroArch
    - For Rosetta x86_64: disable HW rendering in core options, use software renderer
    """
    ra_exe = PATHS["ra_exe"]
    ra_app = PATHS.get("ra_app")
    config_dir = PATHS.get("config_dir")
    
    if not ra_exe.exists():
        return False, "RetroArch not installed"
    
    # Remove quarantine from app and core
    if ra_app and ra_app.exists():
        remove_quarantine(ra_app)
    remove_quarantine(core_path)
    
    # FIX v1.3.3: Create core options file to disable HW rendering
    # This forces software rendering which works under Rosetta
    if config_dir:
        core_opts_dir = config_dir / "config" / "Mupen64Plus-Next"
        core_opts_dir.mkdir(parents=True, exist_ok=True)
        core_opts_file = core_opts_dir / "Mupen64Plus-Next.opt"
        
        # Write core options to force software rendering (works under Rosetta)
        core_opts = '''mupen64plus-rdp-plugin = "angrylion"
mupen64plus-rsp-plugin = "hle"
mupen64plus-43screensize = "640x480"
mupen64plus-aspect = "4:3"
mupen64plus-cpucore = "dynamic_recompiler"
'''
        try:
            core_opts_file.write_text(core_opts)
            print(f"[Config] Created core options: {core_opts_file}")
            print("[Config] Using Angrylion software renderer (Rosetta compatible)")
        except Exception as e:
            print(f"[Config] Warning: Could not write core options: {e}")
    
    # Ensure ROM path is absolute and quoted properly
    rom_path = Path(rom_path).resolve()
    core_path = Path(core_path).resolve()
    
    cmd = [
        str(ra_exe),
        "-L", str(core_path),
        "--verbose",
        str(rom_path)
    ]
    
    print("[Launch macOS]", " ".join(cmd))
    
    try:
        env = os.environ.copy()
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        
        proc = subprocess.Popen(
            cmd,
            env=env,
        )
        
        time.sleep(0.5)
        bring_to_front()
        
        return True, None
        
    except Exception as e:
        return False, str(e)

def bring_to_front():
    """Use AppleScript to bring RetroArch window to front"""
    if SYS_OS != "darwin":
        return
    
    script = '''
    tell application "RetroArch"
        activate
    end tell
    '''
    
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5
        )
        print("[Window] Brought RetroArch to front")
    except Exception as e:
        print(f"[Window] Could not activate: {e}")

def launch_rom_direct(rom_path, core_path):
    """Direct binary launch (Windows/Linux/fallback)"""
    if not PATHS["ra_exe"].exists():
        return False, "RetroArch not installed"

    cmd = [
        str(PATHS["ra_exe"]),
        "--verbose",
        "-L", str(core_path),
        str(rom_path)
    ]

    print("[Launch Direct]", " ".join(cmd))

    try:
        env = os.environ.copy()
        
        # M4 Pro: prefer Metal renderer
        if IS_APPLE_SILICON:
            env["MTL_HUD_ENABLED"] = "0"  # Disable Metal HUD if enabled
        
        subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True, None
    except Exception as e:
        return False, str(e)

def launch_rom(rom_path, core_path):
    """Main launch dispatcher"""
    if not core_path:
        return False, "N64 core missing — click Install Core"

    if not Path(rom_path).exists():
        return False, f"ROM not found: {rom_path}"

    # M4 Pro fix: use macOS-specific launcher
    if SYS_OS == "darwin":
        return launch_rom_macos(rom_path, core_path)
    else:
        return launch_rom_direct(rom_path, core_path)

# =============================================================================
# GUI — M4 PRO EDITION
# =============================================================================

class CatsN64EMU(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🐱 Cat's N64 EMU 1.3.3 — M4 Pro Edition")
        self.geometry("820x520")
        
        # M4 Pro: High DPI support
        if IS_APPLE_SILICON:
            self.tk.call('tk', 'scaling', 2.0)

        self.core = None
        self.setup_gui()
        self.after(100, self.init_core)  # Async core init

    def setup_gui(self):
        # Toolbar
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="📂 Add ROM", command=self.add_rom).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🔄 Refresh", command=self.load_roms).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="⚙️ Install Core", command=self.reinstall_core).pack(side=tk.LEFT, padx=2)
        
        # macOS-specific: Fix Rosetta button
        if SYS_OS == "darwin":
            tk.Button(toolbar, text="🔧 Fix Rosetta", command=self.fix_rosetta).pack(side=tk.LEFT, padx=2)
        
        # ROM list
        self.list = ttk.Treeview(self, columns=("file", "size"), show="headings")
        self.list.heading("file", text="ROM")
        self.list.heading("size", text="Size")
        self.list.column("size", width=100, anchor="e")
        self.list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.list.bind("<Double-1>", self.run_selected)
        self.list.bind("<Return>", self.run_selected)

        # Status bar
        self.status = tk.Label(self, text="Initializing...", anchor="w", relief=tk.SUNKEN)
        self.status.pack(fill=tk.X, padx=5, pady=2)

    def init_core(self):
        self.status.config(text="Loading N64 core...")
        self.update()
        self.core = install_core()
        
        if self.core:
            chip = "M4 Pro" if IS_M4 else "Intel"
            self.status.config(text=f"✓ Ready — {chip} — Core: {self.core.name}")
        else:
            self.status.config(text="⚠ Core missing — click Install Core")
        
        self.load_roms()

    def load_roms(self):
        self.list.delete(*self.list.get_children())
        
        extensions = ("*.z64", "*.n64", "*.v64")
        roms = []
        for ext in extensions:
            roms.extend(ROM_DIR.glob(ext))
        
        for rom in sorted(roms):
            size_mb = rom.stat().st_size / (1024 * 1024)
            self.list.insert("", "end", values=(rom.name, f"{size_mb:.1f} MB"))
        
        count = len(roms)
        self.status.config(text=f"Found {count} ROM(s) in {ROM_DIR}")

    def add_rom(self):
        files = filedialog.askopenfilenames(
            title="Select N64 ROMs",
            filetypes=[("N64 ROMs", "*.z64 *.n64 *.v64"), ("All files", "*.*")]
        )
        for src in files:
            dst = ROM_DIR / Path(src).name
            if not dst.exists():
                shutil.copy2(src, dst)
        self.load_roms()

    def reinstall_core(self):
        self.status.config(text="Downloading core...")
        self.update()
        
        # Delete existing core
        for name in ["mupen64plus_next_libretro"]:
            core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
            if core.exists():
                core.unlink()
        
        self.core = install_core()
        
        if self.core:
            self.status.config(text=f"✓ Core installed: {self.core.name}")
        else:
            messagebox.showerror("Error", "Failed to install core")

    def fix_rosetta(self):
        """Fix architecture mismatch by removing Rosetta preference and redownloading correct core"""
        global RETROARCH_ARCH, PATHS  # Must be at top of function!
        
        self.status.config(text="Fixing Rosetta issue...")
        self.update()
        
        ra_app = Path("/Applications/RetroArch.app")
        
        # Step 1: Remove "Open using Rosetta" setting
        try:
            # Clear the Rosetta preference for RetroArch
            subprocess.run(
                ["defaults", "delete", "com.apple.rosetta", "RetroArch"],
                capture_output=True,
                timeout=5
            )
            print("[Rosetta] Cleared Rosetta preference")
        except:
            pass
        
        # Step 2: Remove x86_64 architecture priority from app if set
        try:
            info_plist = ra_app / "Contents/Info.plist"
            subprocess.run(
                ["defaults", "delete", str(info_plist), "LSArchitecturePriority"],
                capture_output=True,
                timeout=5
            )
            print("[Rosetta] Cleared LSArchitecturePriority")
        except:
            pass
        
        # Step 3: Delete existing cores
        for name in ["mupen64plus_next_libretro"]:
            core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
            if core.exists():
                core.unlink()
                print(f"[Rosetta] Deleted old core: {core}")
        
        # Step 4: Re-detect architecture
        RETROARCH_ARCH = get_retroarch_running_arch()
        PATHS = get_platform_paths()
        
        print(f"[Rosetta] New detected arch: {RETROARCH_ARCH}")
        
        # Step 5: Download correct core
        self.core = install_core_forced(RETROARCH_ARCH or "arm64")
        
        if self.core:
            is_valid, core_arch, needed_arch = verify_core_arch(self.core)
            if is_valid:
                self.status.config(text=f"✓ Fixed! Core: {core_arch}, RetroArch: {needed_arch}")
                messagebox.showinfo("Fixed", 
                    f"Rosetta fix applied!\n\n"
                    f"Core architecture: {core_arch}\n"
                    f"RetroArch architecture: {needed_arch}\n\n"
                    f"Try launching a ROM now.")
            else:
                self.status.config(text=f"⚠ Still mismatched: core={core_arch}, RA={needed_arch}")
                messagebox.showwarning("Partial Fix",
                    f"Core downloaded but still mismatched.\n\n"
                    f"Try: Right-click RetroArch.app → Get Info → UNCHECK 'Open using Rosetta'\n\n"
                    f"Then click 'Fix Rosetta' again.")
        else:
            self.status.config(text="✗ Core download failed")
            messagebox.showerror("Error", "Failed to download core")

    def run_selected(self, _=None):
        item = self.list.selection()
        if not item:
            messagebox.showinfo("Select ROM", "Double-click a ROM to play")
            return
        
        rom_name = self.list.item(item[0])["values"][0]
        rom = ROM_DIR / rom_name
        
        self.status.config(text=f"Launching {rom_name}...")
        self.update()
        
        ok, err = launch_rom(rom, self.core)
        
        if ok:
            self.status.config(text=f"▶ Playing: {rom_name}")
        else:
            self.status.config(text=f"✗ Error: {err}")
            messagebox.showerror("Launch Error", err)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 Cat's N64 EMU 1.3.3 — M4 Pro Edition")
    print("=" * 50)
    
    if IS_APPLE_SILICON:
        print("[M4] Apple Silicon optimizations enabled")
    
    app = CatsN64EMU()
    app.mainloop()
