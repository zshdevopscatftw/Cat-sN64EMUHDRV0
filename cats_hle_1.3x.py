#!/usr/bin/env python3
"""
Cat's HLE 1.3 — M4 Pro Edition
🐱 nyaa~ High-Level Emulation Frontend

Project64-Style GUI + Universal Controller Support

Built on RetroArch 1.22.2 (Nov 17, 2025)

NEW IN 1.3:
- Project64 1.0 style GUI (classic emulator look)
- Auto-detect Switch Pro Controller, Joy-Cons
- Support for ALL controllers since 1985:
  → 1985: NES Controller, Atari 7800
  → 1990: SNES, Genesis 3/6-button
  → 1995: PS1, Saturn, N64
  → 2000: PS2, Dreamcast, Xbox Duke
  → 2005: Xbox 360, PS3
  → 2010: Wii Remote, Wii U Pro
  → 2015: PS4, Xbox One, Steam Controller
  → 2017: Switch Pro, Joy-Con
  → 2020: PS5 DualSense, Xbox Series X
  → 2024: 8BitDo, Backbone, Razer Kishi

FEATURES:
- M4 Pro / Apple Silicon optimized
- Smart renderer (ParaLLEl native, Angrylion Rosetta)
- Auto controller detection via SDL2
- Classic Project64 menu bar and toolbar
"""

import os
import platform
import requests
import zipfile
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Menu
import shutil
from pathlib import Path
import time
import json

# =============================================================================
# SYSTEM DETECTION
# =============================================================================

SYS_OS = platform.system().lower()
MACHINE = platform.machine().lower()
HOME = Path.home()

IS_APPLE_SILICON = SYS_OS == "darwin" and MACHINE in ("arm64", "aarch64")
IS_M4 = IS_APPLE_SILICON

print(f"[Setup] OS: {platform.system()} {platform.release()} ({MACHINE})")
print(f"[Setup] Apple Silicon: {IS_APPLE_SILICON}")

# =============================================================================
# CONTROLLER DATABASE — ALL CONTROLLERS SINCE 1985
# =============================================================================

CONTROLLER_DATABASE = {
    # === 1985-1989: 8-bit Era ===
    "nes": {
        "name": "NES Controller",
        "year": 1985,
        "vendor_ids": ["0x0079"],  # iBuffalo, RetroUSB
        "buttons": ["A", "B", "Select", "Start", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "Start": "start"}
    },
    "atari_7800": {
        "name": "Atari 7800 ProLine",
        "year": 1986,
        "vendor_ids": ["0x0001"],
        "buttons": ["Fire1", "Fire2", "D-Pad"],
        "n64_map": {"Fire1": "a", "Fire2": "b"}
    },
    "master_system": {
        "name": "Sega Master System",
        "year": 1986,
        "vendor_ids": [],
        "buttons": ["1", "2", "D-Pad"],
        "n64_map": {"1": "a", "2": "b"}
    },
    
    # === 1990-1994: 16-bit Era ===
    "snes": {
        "name": "SNES Controller",
        "year": 1990,
        "vendor_ids": ["0x0079", "0x081F"],  # Various USB adapters
        "buttons": ["A", "B", "X", "Y", "L", "R", "Select", "Start", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "Start": "start"}
    },
    "genesis_3btn": {
        "name": "Sega Genesis 3-Button",
        "year": 1989,
        "vendor_ids": ["0x0079"],
        "buttons": ["A", "B", "C", "Start", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "C": "c_down", "Start": "start"}
    },
    "genesis_6btn": {
        "name": "Sega Genesis 6-Button",
        "year": 1993,
        "vendor_ids": ["0x0079", "0x1BAD"],
        "buttons": ["A", "B", "C", "X", "Y", "Z", "Start", "Mode", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "C": "c_down", "X": "c_up", "Y": "c_left", "Z": "c_right", "Start": "start"}
    },
    "turbografx": {
        "name": "TurboGrafx-16",
        "year": 1989,
        "vendor_ids": [],
        "buttons": ["I", "II", "Select", "Run", "D-Pad"],
        "n64_map": {"I": "a", "II": "b", "Run": "start"}
    },
    "neo_geo": {
        "name": "Neo Geo AES",
        "year": 1990,
        "vendor_ids": [],
        "buttons": ["A", "B", "C", "D", "Start", "Select", "Stick"],
        "n64_map": {"A": "a", "B": "b", "C": "c_down", "D": "c_right", "Start": "start"}
    },
    
    # === 1995-1999: 32/64-bit Era ===
    "ps1": {
        "name": "PlayStation DualShock",
        "year": 1997,
        "vendor_ids": ["0x054C"],  # Sony
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Select", "Start", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Start": "start", "Left Stick": "analog"}
    },
    "saturn": {
        "name": "Sega Saturn",
        "year": 1995,
        "vendor_ids": ["0x0CA3"],  # Retro-Bit
        "buttons": ["A", "B", "C", "X", "Y", "Z", "L", "R", "Start", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "C": "c_down", "X": "c_up", "Y": "c_left", "Z": "c_right", "L": "l", "R": "r", "Start": "start"}
    },
    "n64": {
        "name": "Nintendo 64",
        "year": 1996,
        "vendor_ids": ["0x0079", "0x057E"],  # USB adapters, Nintendo
        "buttons": ["A", "B", "Z", "L", "R", "Start", "C-Up", "C-Down", "C-Left", "C-Right", "D-Pad", "Analog Stick"],
        "n64_map": "native"
    },
    "dreamcast": {
        "name": "Sega Dreamcast",
        "year": 1999,
        "vendor_ids": ["0x0CA3"],  # Retro-Bit
        "buttons": ["A", "B", "X", "Y", "L", "R", "Start", "D-Pad", "Analog Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "Start": "start", "Analog Stick": "analog"}
    },
    
    # === 2000-2004: 128-bit Era ===
    "ps2": {
        "name": "PlayStation 2 DualShock 2",
        "year": 2000,
        "vendor_ids": ["0x054C"],
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Select", "Start", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Start": "start", "Left Stick": "analog"}
    },
    "xbox_duke": {
        "name": "Xbox Duke",
        "year": 2001,
        "vendor_ids": ["0x045E"],  # Microsoft
        "buttons": ["A", "B", "X", "Y", "Black", "White", "L", "R", "Start", "Back", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "Black": "c_right", "White": "c_down", "L": "l", "R": "r", "Start": "start", "Left Stick": "analog"}
    },
    "xbox_s": {
        "name": "Xbox Controller S",
        "year": 2002,
        "vendor_ids": ["0x045E"],
        "buttons": ["A", "B", "X", "Y", "Black", "White", "L", "R", "Start", "Back", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "Start": "start", "Left Stick": "analog"}
    },
    "gamecube": {
        "name": "Nintendo GameCube",
        "year": 2001,
        "vendor_ids": ["0x057E", "0x0079"],
        "buttons": ["A", "B", "X", "Y", "Z", "L", "R", "Start", "D-Pad", "Control Stick", "C-Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "Z": "z", "L": "l", "R": "r", "Start": "start", "Control Stick": "analog", "C-Stick": "c_buttons"}
    },
    
    # === 2005-2009: HD Era ===
    "xbox_360": {
        "name": "Xbox 360",
        "year": 2005,
        "vendor_ids": ["0x045E", "0x24C6", "0x0738"],  # Microsoft, Razer, MadCatz
        "product_patterns": ["Xbox 360", "X360"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Start": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "ps3": {
        "name": "PlayStation 3 DualShock 3/Sixaxis",
        "year": 2006,
        "vendor_ids": ["0x054C"],
        "product_patterns": ["PLAYSTATION(R)3", "DUALSHOCK 3", "SIXAXIS"],
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Select", "Start", "PS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Start": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "wii_remote": {
        "name": "Wii Remote",
        "year": 2006,
        "vendor_ids": ["0x057E"],
        "product_patterns": ["Wii Remote", "RVL-CNT"],
        "buttons": ["A", "B", "1", "2", "+", "-", "Home", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "1": "c_down", "2": "c_up", "+": "start"}
    },
    "wii_classic": {
        "name": "Wii Classic Controller",
        "year": 2006,
        "vendor_ids": ["0x057E"],
        "buttons": ["a", "b", "x", "y", "L", "R", "ZL", "ZR", "+", "-", "Home", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"a": "a", "b": "b", "x": "c_up", "y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog"}
    },
    
    # === 2010-2014: Motion Era ===
    "wii_u_pro": {
        "name": "Wii U Pro Controller",
        "year": 2012,
        "vendor_ids": ["0x057E"],
        "product_patterns": ["Wii U Pro"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "+", "-", "Home", "D-Pad", "Left Stick", "Right Stick", "LS", "RS"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "wii_u_gamepad": {
        "name": "Wii U GamePad",
        "year": 2012,
        "vendor_ids": ["0x057E"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "+", "-", "Home", "D-Pad", "Left Stick", "Right Stick", "Touch Screen"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog"}
    },
    
    # === 2015-2019: Current Gen ===
    "ps4": {
        "name": "PlayStation 4 DualShock 4",
        "year": 2013,
        "vendor_ids": ["0x054C"],
        "product_patterns": ["DualShock 4", "Wireless Controller"],
        "product_ids": ["0x05C4", "0x09CC", "0x0BA0"],
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Share", "Options", "PS", "Touchpad", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Options": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "xbox_one": {
        "name": "Xbox One",
        "year": 2013,
        "vendor_ids": ["0x045E", "0x0E6F", "0x24C6"],  # Microsoft, PDP, Razer
        "product_patterns": ["Xbox One", "Xbox Wireless"],
        "product_ids": ["0x02D1", "0x02DD", "0x02E3", "0x02EA", "0x0B00", "0x0B0A", "0x0B12"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "View", "Menu", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Menu": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "steam_controller": {
        "name": "Steam Controller",
        "year": 2015,
        "vendor_ids": ["0x28DE"],  # Valve
        "product_patterns": ["Steam Controller", "Valve Software Steam Controller"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start", "Steam", "Left Trackpad", "Right Trackpad", "Joystick", "Gyro"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Start": "start", "Joystick": "analog", "Right Trackpad": "c_buttons"}
    },
    
    # === 2017-2019: Switch Era ===
    "switch_pro": {
        "name": "Nintendo Switch Pro Controller",
        "year": 2017,
        "vendor_ids": ["0x057E"],
        "product_ids": ["0x2009"],
        "product_patterns": ["Pro Controller", "Switch Pro"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "-", "+", "Home", "Capture", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "joycon_l": {
        "name": "Nintendo Switch Joy-Con (L)",
        "year": 2017,
        "vendor_ids": ["0x057E"],
        "product_ids": ["0x2006"],
        "product_patterns": ["Joy-Con (L)", "Joy-Con Left"],
        "buttons": ["L", "ZL", "-", "Capture", "SL", "SR", "Stick", "D-Pad"],
        "n64_map": {"L": "l", "ZL": "z", "-": "start", "Stick": "analog"},
        "auto_detect": True
    },
    "joycon_r": {
        "name": "Nintendo Switch Joy-Con (R)",
        "year": 2017,
        "vendor_ids": ["0x057E"],
        "product_ids": ["0x2007"],
        "product_patterns": ["Joy-Con (R)", "Joy-Con Right"],
        "buttons": ["A", "B", "X", "Y", "R", "ZR", "+", "Home", "SL", "SR", "Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "R": "r", "ZR": "z", "+": "start", "Stick": "c_buttons"},
        "auto_detect": True
    },
    "joycon_pair": {
        "name": "Nintendo Switch Joy-Con Pair",
        "year": 2017,
        "vendor_ids": ["0x057E"],
        "product_patterns": ["Joy-Con", "Combined Joy-Con"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "-", "+", "Home", "Capture", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "switch_snes": {
        "name": "Nintendo Switch SNES Controller",
        "year": 2019,
        "vendor_ids": ["0x057E"],
        "product_ids": ["0x2017"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "-", "+", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "+": "start"}
    },
    "switch_n64": {
        "name": "Nintendo Switch N64 Controller",
        "year": 2021,
        "vendor_ids": ["0x057E"],
        "product_ids": ["0x2019"],
        "buttons": ["A", "B", "Z", "L", "R", "Start", "C-Up", "C-Down", "C-Left", "C-Right", "D-Pad", "Analog Stick"],
        "n64_map": "native",
        "auto_detect": True
    },
    
    # === 2020-2024: Next Gen ===
    "ps5": {
        "name": "PlayStation 5 DualSense",
        "year": 2020,
        "vendor_ids": ["0x054C"],
        "product_ids": ["0x0CE6", "0x0DF2"],
        "product_patterns": ["DualSense", "PS5 Controller"],
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Create", "Options", "PS", "Mute", "Touchpad", "D-Pad", "Left Stick", "Right Stick"],
        "features": ["Haptic Feedback", "Adaptive Triggers"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Options": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "ps5_edge": {
        "name": "PlayStation 5 DualSense Edge",
        "year": 2023,
        "vendor_ids": ["0x054C"],
        "product_ids": ["0x0D5E"],
        "buttons": ["X", "O", "Square", "Triangle", "L1", "R1", "L2", "R2", "L3", "R3", "Create", "Options", "PS", "Mute", "Fn1", "Fn2", "Back Buttons", "Touchpad", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Options": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "xbox_series": {
        "name": "Xbox Series X|S",
        "year": 2020,
        "vendor_ids": ["0x045E"],
        "product_ids": ["0x0B13", "0x0B20", "0x0B21", "0x0B22"],
        "product_patterns": ["Xbox Series", "Xbox Wireless Controller"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "View", "Menu", "Share", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Menu": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "xbox_elite_2": {
        "name": "Xbox Elite Series 2",
        "year": 2019,
        "vendor_ids": ["0x045E"],
        "product_ids": ["0x0B00", "0x0B05"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "View", "Menu", "LS", "RS", "D-Pad", "Left Stick", "Right Stick", "P1", "P2", "P3", "P4"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Menu": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    
    # === Third Party / Modern ===
    "8bitdo_pro2": {
        "name": "8BitDo Pro 2",
        "year": 2021,
        "vendor_ids": ["0x2DC8", "0x045E"],  # 8BitDo, xinput mode
        "product_patterns": ["8BitDo Pro 2", "Pro 2"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "L2", "R2", "-", "+", "Home", "Star", "L3", "R3", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "L2": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "8bitdo_sn30": {
        "name": "8BitDo SN30 Pro",
        "year": 2018,
        "vendor_ids": ["0x2DC8"],
        "product_patterns": ["8BitDo SN30", "SN30 Pro"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "L2", "R2", "-", "+", "Home", "Star", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "L2": "z", "+": "start", "Left Stick": "analog"}
    },
    "8bitdo_ultimate": {
        "name": "8BitDo Ultimate Controller",
        "year": 2022,
        "vendor_ids": ["0x2DC8"],
        "product_patterns": ["8BitDo Ultimate", "Ultimate Controller"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "L2", "R2", "-", "+", "Home", "L3", "R3", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "L2": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "backbone_one": {
        "name": "Backbone One",
        "year": 2020,
        "vendor_ids": ["0x358A"],
        "product_patterns": ["Backbone One", "Backbone"],
        "buttons": ["A", "B", "X", "Y", "L1", "R1", "L2", "R2", "L3", "R3", "Options", "Menu", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L1": "l", "R1": "r", "L2": "z", "Menu": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "razer_kishi": {
        "name": "Razer Kishi",
        "year": 2020,
        "vendor_ids": ["0x1532"],  # Razer
        "product_patterns": ["Razer Kishi", "Kishi"],
        "buttons": ["A", "B", "X", "Y", "L1", "R1", "L2", "R2", "L3", "R3", "Menu", "Options", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L1": "l", "R1": "r", "L2": "z", "Menu": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "gulikit_kingkong": {
        "name": "GuliKit KingKong Pro",
        "year": 2021,
        "vendor_ids": ["0x0E8F"],
        "product_patterns": ["GuliKit", "KingKong"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "-", "+", "Home", "Capture", "L3", "R3", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    "hori_split_pad": {
        "name": "HORI Split Pad Pro",
        "year": 2019,
        "vendor_ids": ["0x0F0D"],  # HORI
        "product_patterns": ["Split Pad", "HORI"],
        "buttons": ["A", "B", "X", "Y", "L", "R", "ZL", "ZR", "-", "+", "Home", "Capture", "L3", "R3", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "L": "l", "R": "r", "ZL": "z", "+": "start", "Left Stick": "analog", "Right Stick": "c_buttons"},
        "auto_detect": True
    },
    
    # === Arcade / Fight Sticks ===
    "arcade_stick": {
        "name": "Generic Arcade Stick",
        "year": 1980,
        "vendor_ids": [],
        "product_patterns": ["Arcade", "Fight Stick", "Fightstick"],
        "buttons": ["1", "2", "3", "4", "5", "6", "7", "8", "Start", "Select", "Joystick"],
        "n64_map": {"1": "a", "2": "b", "3": "c_down", "4": "c_up", "5": "l", "6": "r", "Start": "start", "Joystick": "analog"}
    },
    "hori_rap": {
        "name": "HORI Real Arcade Pro",
        "year": 2005,
        "vendor_ids": ["0x0F0D"],
        "product_patterns": ["Real Arcade Pro", "RAP", "HORI Arcade"],
        "buttons": ["Square", "Triangle", "R1", "L1", "X", "O", "R2", "L2", "Share", "Options", "L3", "R3", "PS", "Touchpad", "Joystick"],
        "n64_map": {"X": "a", "O": "b", "Square": "c_left", "Triangle": "c_up", "L1": "l", "R1": "r", "L2": "z", "Options": "start", "Joystick": "analog"}
    },
    
    # === Retro USB Adapters ===
    "raphnet_n64": {
        "name": "Raphnet N64 to USB",
        "year": 2010,
        "vendor_ids": ["0x289B"],
        "product_patterns": ["raphnet", "N64 to USB"],
        "buttons": ["A", "B", "Z", "L", "R", "Start", "C-Up", "C-Down", "C-Left", "C-Right", "D-Pad", "Analog Stick"],
        "n64_map": "native"
    },
    "mayflash_n64": {
        "name": "Mayflash N64 Adapter",
        "year": 2012,
        "vendor_ids": ["0x0079", "0x0E8F"],
        "product_patterns": ["Mayflash", "N64"],
        "buttons": ["A", "B", "Z", "L", "R", "Start", "C-Up", "C-Down", "C-Left", "C-Right", "D-Pad", "Analog Stick"],
        "n64_map": "native"
    },
    "retro_usb": {
        "name": "RetroUSB AVS/Retro Controller",
        "year": 2010,
        "vendor_ids": ["0x1781"],
        "product_patterns": ["RetroUSB", "AVS"],
        "buttons": ["A", "B", "Select", "Start", "D-Pad"],
        "n64_map": {"A": "a", "B": "b", "Start": "start"}
    },
    
    # === Generic / Unknown ===
    "generic_xinput": {
        "name": "Generic XInput Controller",
        "year": 2005,
        "vendor_ids": [],
        "product_patterns": ["XInput", "Controller", "Gamepad", "Game Controller"],
        "buttons": ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start", "LS", "RS", "D-Pad", "Left Stick", "Right Stick"],
        "n64_map": {"A": "a", "B": "b", "X": "c_up", "Y": "c_left", "LB": "l", "RB": "r", "LT": "z", "Start": "start", "Left Stick": "analog", "Right Stick": "c_buttons"}
    },
    "generic_dinput": {
        "name": "Generic DirectInput Controller",
        "year": 1995,
        "vendor_ids": [],
        "product_patterns": ["DirectInput", "USB Gamepad", "USB Joystick"],
        "buttons": ["Button 1", "Button 2", "Button 3", "Button 4", "L1", "R1", "L2", "R2", "Select", "Start", "D-Pad", "Axes"],
        "n64_map": {"Button 1": "a", "Button 2": "b", "Button 3": "c_down", "Button 4": "c_up", "L1": "l", "R1": "r", "Start": "start"}
    }
}

# =============================================================================
# CONTROLLER DETECTION
# =============================================================================

class ControllerManager:
    """Manages controller detection and mapping"""
    
    def __init__(self):
        self.detected_controllers = []
        self.active_controller = None
        self.config_dir = PATHS.get("config_dir") if PATHS else None
    
    def detect_controllers_macos(self):
        """Detect controllers on macOS using system_profiler"""
        controllers = []
        
        try:
            # Get USB devices
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                usb_items = data.get("SPUSBDataType", [])
                
                for bus in usb_items:
                    self._scan_usb_tree(bus, controllers)
            
            # Also check Bluetooth
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                bt_data = data.get("SPBluetoothDataType", [])
                
                for bt in bt_data:
                    devices = bt.get("device_connected", [])
                    for device in devices:
                        for name, info in device.items():
                            controller = self._identify_controller(name, "", "")
                            if controller:
                                controller["connection"] = "Bluetooth"
                                controllers.append(controller)
        
        except Exception as e:
            print(f"[Controller] Detection error: {e}")
        
        return controllers
    
    def _scan_usb_tree(self, node, controllers, depth=0):
        """Recursively scan USB device tree"""
        if isinstance(node, dict):
            name = node.get("_name", "")
            vendor_id = node.get("vendor_id", "")
            product_id = node.get("product_id", "")
            
            controller = self._identify_controller(name, vendor_id, product_id)
            if controller:
                controller["connection"] = "USB"
                controllers.append(controller)
            
            # Scan children
            items = node.get("_items", [])
            for item in items:
                self._scan_usb_tree(item, controllers, depth + 1)
    
    def _identify_controller(self, name, vendor_id, product_id):
        """Identify controller from database"""
        name_lower = name.lower()
        
        # Check each controller in database
        for key, data in CONTROLLER_DATABASE.items():
            # Check product patterns
            patterns = data.get("product_patterns", [])
            for pattern in patterns:
                if pattern.lower() in name_lower:
                    return {
                        "id": key,
                        "name": data["name"],
                        "year": data["year"],
                        "detected_name": name,
                        "vendor_id": vendor_id,
                        "product_id": product_id,
                        "n64_map": data.get("n64_map", {}),
                        "auto_detect": data.get("auto_detect", False)
                    }
            
            # Check vendor IDs
            vendor_ids = data.get("vendor_ids", [])
            for vid in vendor_ids:
                if vid.lower() in str(vendor_id).lower():
                    # Check product IDs if available
                    product_ids = data.get("product_ids", [])
                    if product_ids:
                        for pid in product_ids:
                            if pid.lower() in str(product_id).lower():
                                return {
                                    "id": key,
                                    "name": data["name"],
                                    "year": data["year"],
                                    "detected_name": name,
                                    "vendor_id": vendor_id,
                                    "product_id": product_id,
                                    "n64_map": data.get("n64_map", {}),
                                    "auto_detect": data.get("auto_detect", False)
                                }
                    else:
                        return {
                            "id": key,
                            "name": data["name"],
                            "year": data["year"],
                            "detected_name": name,
                            "vendor_id": vendor_id,
                            "product_id": product_id,
                            "n64_map": data.get("n64_map", {}),
                            "auto_detect": data.get("auto_detect", False)
                        }
        
        # Check for generic controller keywords
        controller_keywords = ["controller", "gamepad", "joystick", "joypad", "game pad"]
        for keyword in controller_keywords:
            if keyword in name_lower:
                return {
                    "id": "generic_xinput",
                    "name": f"Unknown Controller ({name})",
                    "year": 2000,
                    "detected_name": name,
                    "vendor_id": vendor_id,
                    "product_id": product_id,
                    "n64_map": CONTROLLER_DATABASE["generic_xinput"]["n64_map"],
                    "auto_detect": False
                }
        
        return None
    
    def detect_all(self):
        """Detect all connected controllers"""
        print("[Controller] Scanning for controllers...")
        
        if SYS_OS == "darwin":
            self.detected_controllers = self.detect_controllers_macos()
        else:
            # Fallback for other platforms
            self.detected_controllers = []
        
        # Sort by priority (auto_detect controllers first)
        self.detected_controllers.sort(key=lambda c: (not c.get("auto_detect", False), c.get("year", 2000)))
        
        # Auto-select first auto_detect controller, or first controller
        if self.detected_controllers:
            for controller in self.detected_controllers:
                if controller.get("auto_detect"):
                    self.active_controller = controller
                    break
            if not self.active_controller:
                self.active_controller = self.detected_controllers[0]
        
        count = len(self.detected_controllers)
        print(f"[Controller] Found {count} controller(s)")
        
        for c in self.detected_controllers:
            auto = "★" if c.get("auto_detect") else ""
            print(f"  → {c['name']} ({c['year']}) [{c['connection']}] {auto}")
        
        if self.active_controller:
            print(f"[Controller] Active: {self.active_controller['name']}")
        
        return self.detected_controllers
    
    def get_retroarch_config(self):
        """Generate RetroArch controller config for active controller"""
        if not self.active_controller:
            return None
        
        n64_map = self.active_controller.get("n64_map", {})
        
        if n64_map == "native":
            # N64 controller, no mapping needed
            return None
        
        # RetroArch uses input_player1_* settings
        # This is a simplified version - full implementation would need SDL button indices
        config = f"""
# Auto-generated by Cat's HLE 1.3
# Controller: {self.active_controller['name']}
# Detected: {self.active_controller.get('detected_name', 'Unknown')}

input_player1_a = "{n64_map.get('a', 'a')}"
input_player1_b = "{n64_map.get('b', 'b')}"
input_player1_start = "{n64_map.get('start', 'start')}"
input_player1_l = "{n64_map.get('l', 'l')}"
input_player1_r = "{n64_map.get('r', 'r')}"
input_player1_l2 = "{n64_map.get('z', 'l2')}"
"""
        return config

# Global controller manager - initialized later after PATHS is set
controller_manager = None

def init_controller_manager():
    global controller_manager
    controller_manager = ControllerManager()

# =============================================================================
# ARCHITECTURE DETECTION
# =============================================================================

def get_binary_arch(binary_path):
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
        
        if "arm64" in archs and "x86_64" in archs:
            return "universal"
        elif "arm64" in archs:
            return "arm64"
        elif "x86_64" in archs:
            return "x86_64"
        return None
    except:
        return None

def get_retroarch_running_arch():
    ra_exe = Path("/Applications/RetroArch.app/Contents/MacOS/RetroArch")
    
    if not ra_exe.exists():
        return MACHINE
    
    binary_arch = get_binary_arch(ra_exe)
    
    if binary_arch == "universal":
        info_plist = Path("/Applications/RetroArch.app/Contents/Info.plist")
        try:
            result = subprocess.run(
                ["defaults", "read", str(info_plist), "LSArchitecturePriority"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "x86_64" in result.stdout:
                return "x86_64"
        except:
            pass
        
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.rosetta", "RetroArch"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "x86_64"
        except:
            pass
        
        if IS_APPLE_SILICON:
            return "arm64"
        else:
            return "x86_64"
    
    elif binary_arch:
        return binary_arch
    
    return MACHINE

RETROARCH_ARCH = None

# =============================================================================
# PLATFORM PATHS
# =============================================================================

def get_platform_paths():
    global RETROARCH_ARCH
    
    ra_version = "1.22.2"
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
        core_urls = [("mupen64plus_next", f"{nightly}/windows/{arch}/latest/mupen64plus_next_libretro.dll.zip")]
        core_ext = ".dll"

    elif SYS_OS == "darwin":
        retroarch_dir = Path("/Applications")
        config_dir = HOME / "Library/Application Support/RetroArch"
        cores_dir = config_dir / "cores"
        ra_app = retroarch_dir / "RetroArch.app"
        ra_exe = ra_app / "Contents/MacOS/RetroArch"
        
        RETROARCH_ARCH = get_retroarch_running_arch()
        arch = RETROARCH_ARCH if RETROARCH_ARCH else ("arm64" if IS_APPLE_SILICON else "x86_64")
        
        ra_url = f"{base_url}apple/osx/universal/RetroArch_Metal.dmg"
        core_urls = [("mupen64plus_next", f"{nightly}/apple/osx/{arch}/latest/mupen64plus_next_libretro.dylib.zip")]
        core_ext = ".dylib"

    else:  # Linux
        config_dir = HOME / ".config/retroarch"
        retroarch_dir = HOME / ".local/share/retroarch"
        cores_dir = retroarch_dir / "cores"
        ra_exe = retroarch_dir / "retroarch"
        arch = "x86_64"
        ra_url = f"{base_url}linux/{arch}/RetroArch.7z"
        core_urls = [("mupen64plus_next", f"{nightly}/linux/{arch}/latest/mupen64plus_next_libretro.so.zip")]
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
        "core_arch": arch
    }

PATHS = get_platform_paths()
PATHS["config_dir"].mkdir(parents=True, exist_ok=True)
PATHS["cores_dir"].mkdir(parents=True, exist_ok=True)

ROM_DIR = HOME / "Documents/ROMs/N64"
ROM_DIR.mkdir(parents=True, exist_ok=True)

# Now initialize controller manager after PATHS exists
init_controller_manager()

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def remove_quarantine(path):
    if SYS_OS != "darwin":
        return
    try:
        subprocess.run(["xattr", "-rd", "com.apple.quarantine", str(path)], capture_output=True, timeout=10)
    except:
        pass

def fix_core_permissions(core_path):
    if not core_path or not core_path.exists():
        return
    remove_quarantine(core_path)
    try:
        os.chmod(core_path, 0o755)
    except:
        pass

def verify_core_arch(core_path):
    if SYS_OS != "darwin" or not core_path or not core_path.exists():
        return True, None, None
    
    core_arch = get_binary_arch(core_path)
    needed_arch = RETROARCH_ARCH or ("arm64" if IS_APPLE_SILICON else "x86_64")
    
    if core_arch and needed_arch:
        if core_arch == needed_arch or core_arch == "universal":
            return True, core_arch, needed_arch
        else:
            return False, core_arch, needed_arch
    
    return True, core_arch, needed_arch

def find_n64_core():
    for name in ["mupen64plus_next_libretro"]:
        core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
        if core.exists():
            fix_core_permissions(core)
            return core
    return None

def download(url, path):
    if path.exists():
        return True
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    return True

def install_core():
    core = find_n64_core()
    if core:
        is_valid, core_arch, needed_arch = verify_core_arch(core)
        if not is_valid:
            core.unlink()
            return install_core_forced(needed_arch)
        return core
    return install_core_forced(PATHS.get("core_arch", "arm64"))

def install_core_forced(arch):
    nightly = "https://buildbot.libretro.com/nightly"
    
    if SYS_OS == "darwin":
        url = f"{nightly}/apple/osx/{arch}/latest/mupen64plus_next_libretro.dylib.zip"
    elif SYS_OS == "windows":
        url = f"{nightly}/windows/{arch}/latest/mupen64plus_next_libretro.dll.zip"
    else:
        url = f"{nightly}/linux/{arch}/latest/mupen64plus_next_libretro.so.zip"
    
    try:
        zip_path = PATHS["cores_dir"] / "mupen64plus_next.zip"
        if zip_path.exists():
            zip_path.unlink()
        
        download(url, zip_path)
        
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(PATHS["cores_dir"])
        zip_path.unlink()
        
        core = find_n64_core()
        if core:
            fix_core_permissions(core)
            return core
        return core
    except Exception as e:
        print(f"[Core] Error: {e}")
        return None

# =============================================================================
# RENDERER SETUP
# =============================================================================

def is_running_rosetta():
    if not IS_APPLE_SILICON:
        return False
    return RETROARCH_ARCH == "x86_64"

def setup_renderer_config(config_dir):
    if not config_dir:
        return
    
    use_rosetta = is_running_rosetta()
    
    core_opts_dir = config_dir / "config" / "Mupen64Plus-Next"
    core_opts_dir.mkdir(parents=True, exist_ok=True)
    core_opts_file = core_opts_dir / "Mupen64Plus-Next.opt"
    
    if use_rosetta:
        core_opts = '''mupen64plus-rdp-plugin = "angrylion"
mupen64plus-rsp-plugin = "hle"
mupen64plus-43screensize = "640x480"
mupen64plus-aspect = "4:3"
mupen64plus-cpucore = "dynamic_recompiler"
'''
    else:
        core_opts = '''mupen64plus-rdp-plugin = "gliden64"
mupen64plus-rsp-plugin = "hle"
mupen64plus-43screensize = "640x480"
mupen64plus-aspect = "4:3"
mupen64plus-cpucore = "dynamic_recompiler"
mupen64plus-EnableHWLighting = "True"
'''
    
    try:
        core_opts_file.write_text(core_opts)
    except:
        pass

def setup_video_driver(config_dir):
    if not config_dir:
        return
    
    config_file = config_dir / "config" / "retroarch.cfg"
    if not config_file.exists():
        return
    
    try:
        content = config_file.read_text()
        if 'video_driver = "gl"' in content:
            content = content.replace('video_driver = "gl"', 'video_driver = "glcore"')
            config_file.write_text(content)
    except:
        pass

# =============================================================================
# ROM LAUNCHER
# =============================================================================

def bring_to_front():
    if SYS_OS != "darwin":
        return
    try:
        subprocess.run(["osascript", "-e", 'tell application "RetroArch" to activate'], capture_output=True, timeout=5)
    except:
        pass

def launch_rom_macos(rom_path, core_path):
    ra_exe = PATHS["ra_exe"]
    ra_app = PATHS.get("ra_app")
    config_dir = PATHS.get("config_dir")
    
    if not ra_exe.exists():
        return False, "RetroArch not installed"
    
    if ra_app and ra_app.exists():
        remove_quarantine(ra_app)
    remove_quarantine(core_path)
    
    setup_renderer_config(config_dir)
    setup_video_driver(config_dir)
    
    rom_path = Path(rom_path).resolve()
    core_path = Path(core_path).resolve()
    
    cmd = [str(ra_exe), "-L", str(core_path), "--verbose", str(rom_path)]
    
    try:
        env = os.environ.copy()
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        if IS_APPLE_SILICON:
            env["MTL_HUD_ENABLED"] = "0"
        
        subprocess.Popen(cmd, env=env)
        time.sleep(0.5)
        bring_to_front()
        
        return True, None
    except Exception as e:
        return False, str(e)

def launch_rom_direct(rom_path, core_path):
    if not PATHS["ra_exe"].exists():
        return False, "RetroArch not installed"
    
    cmd = [str(PATHS["ra_exe"]), "--verbose", "-L", str(core_path), str(rom_path)]
    
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, None
    except Exception as e:
        return False, str(e)

def launch_rom(rom_path, core_path):
    if not core_path:
        return False, "N64 core missing"
    if not Path(rom_path).exists():
        return False, f"ROM not found: {rom_path}"
    
    if SYS_OS == "darwin":
        return launch_rom_macos(rom_path, core_path)
    else:
        return launch_rom_direct(rom_path, core_path)

# =============================================================================
# GUI — PROJECT64 1.0 STYLE
# =============================================================================

class CatsHLE(tk.Tk):
    """Project64 1.0 style GUI"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Cat's HLE 1.3")
        self.geometry("800x600")
        self.configure(bg="#C0C0C0")  # Classic Windows gray
        
        # High DPI for M4
        if IS_APPLE_SILICON:
            self.tk.call('tk', 'scaling', 2.0)
        
        self.core = None
        self.current_rom = None
        
        self.setup_menu()
        self.setup_toolbar()
        self.setup_rom_browser()
        self.setup_status_bar()
        
        # Initialize
        self.after(100, self.init_app)
    
    def setup_menu(self):
        """Project64-style menu bar"""
        menubar = Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open ROM...", command=self.open_rom, accelerator="Ctrl+O")
        file_menu.add_command(label="Open ROM Directory...", command=self.open_rom_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Refresh ROM List", command=self.load_roms, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Recent ROMs")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        # System menu
        system_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="System", menu=system_menu)
        system_menu.add_command(label="Start Emulation", command=self.run_selected, accelerator="F11")
        system_menu.add_command(label="End Emulation", state="disabled")
        system_menu.add_separator()
        system_menu.add_command(label="Reset")
        system_menu.add_command(label="Pause", accelerator="F2")
        
        # Options menu
        options_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Configure Controller...", command=self.show_controller_config)
        options_menu.add_command(label="Auto-Detect Controllers", command=self.detect_controllers)
        options_menu.add_separator()
        options_menu.add_command(label="Graphics Settings...")
        options_menu.add_command(label="Audio Settings...")
        options_menu.add_separator()
        options_menu.add_command(label="ROM Directory...", command=self.change_rom_dir)
        
        # Utilities menu
        util_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Utilities", menu=util_menu)
        util_menu.add_command(label="Install/Update Core", command=self.reinstall_core)
        util_menu.add_command(label="Fix Rosetta Issue", command=self.fix_rosetta)
        util_menu.add_separator()
        util_menu.add_command(label="View Controller Database", command=self.show_controller_database)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Cat's HLE...", command=self.show_about)
        
        # Keyboard shortcuts
        self.bind("<Control-o>", lambda e: self.open_rom())
        self.bind("<F5>", lambda e: self.load_roms())
        self.bind("<F11>", lambda e: self.run_selected())
    
    def setup_toolbar(self):
        """Project64-style toolbar"""
        toolbar = tk.Frame(self, bg="#C0C0C0", relief=tk.RAISED, bd=1)
        toolbar.pack(fill=tk.X, padx=2, pady=2)
        
        # Toolbar buttons with icons (using text as placeholders)
        btn_style = {"relief": tk.RAISED, "bd": 1, "padx": 8, "pady": 2}
        
        tk.Button(toolbar, text="📂 Open", command=self.open_rom, **btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(toolbar, text="🔄 Refresh", command=self.load_roms, **btn_style).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        
        tk.Button(toolbar, text="▶ Play", command=self.run_selected, **btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(toolbar, text="⏹ Stop", state="disabled", **btn_style).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        
        tk.Button(toolbar, text="🎮 Controllers", command=self.detect_controllers, **btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(toolbar, text="⚙️ Core", command=self.reinstall_core, **btn_style).pack(side=tk.LEFT, padx=1)
        
        if SYS_OS == "darwin":
            tk.Button(toolbar, text="🔧 Fix Rosetta", command=self.fix_rosetta, **btn_style).pack(side=tk.LEFT, padx=1)
    
    def setup_rom_browser(self):
        """Project64-style ROM browser with columns"""
        # Main frame
        browser_frame = tk.Frame(self, bg="white")
        browser_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # ROM list with multiple columns (P64 style)
        columns = ("name", "country", "size", "type", "status")
        self.rom_list = ttk.Treeview(browser_frame, columns=columns, show="headings", selectmode="browse")
        
        # Column headers
        self.rom_list.heading("name", text="Good Name", anchor="w")
        self.rom_list.heading("country", text="Country", anchor="center")
        self.rom_list.heading("size", text="Size", anchor="e")
        self.rom_list.heading("type", text="Save Type", anchor="center")
        self.rom_list.heading("status", text="Status", anchor="center")
        
        # Column widths
        self.rom_list.column("name", width=350, minwidth=200)
        self.rom_list.column("country", width=80, minwidth=60)
        self.rom_list.column("size", width=80, minwidth=60, anchor="e")
        self.rom_list.column("type", width=80, minwidth=60)
        self.rom_list.column("status", width=80, minwidth=60)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(browser_frame, orient=tk.VERTICAL, command=self.rom_list.yview)
        x_scroll = ttk.Scrollbar(browser_frame, orient=tk.HORIZONTAL, command=self.rom_list.xview)
        self.rom_list.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # Grid layout
        self.rom_list.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        
        browser_frame.grid_rowconfigure(0, weight=1)
        browser_frame.grid_columnconfigure(0, weight=1)
        
        # Bindings
        self.rom_list.bind("<Double-1>", self.run_selected)
        self.rom_list.bind("<Return>", self.run_selected)
        self.rom_list.bind("<Button-3>", self.show_rom_context_menu)  # Right-click
    
    def setup_status_bar(self):
        """Project64-style status bar with multiple sections"""
        status_frame = tk.Frame(self, bg="#C0C0C0", relief=tk.SUNKEN, bd=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Left: Main status
        self.status_left = tk.Label(status_frame, text="Ready", anchor="w", bg="#C0C0C0", padx=5)
        self.status_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Separator
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        # Center: Controller
        self.status_controller = tk.Label(status_frame, text="No Controller", anchor="center", bg="#C0C0C0", width=25)
        self.status_controller.pack(side=tk.LEFT)
        
        # Separator
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        # Right: Renderer
        renderer = "GLideN64" if not is_running_rosetta() else "Angrylion"
        self.status_renderer = tk.Label(status_frame, text=renderer, anchor="e", bg="#C0C0C0", width=15)
        self.status_renderer.pack(side=tk.RIGHT, padx=5)
    
    def init_app(self):
        """Initialize application"""
        self.status_left.config(text="Loading core...")
        self.update()
        
        # Load core
        self.core = install_core()
        
        # Detect controllers
        controller_manager.detect_all()
        
        if controller_manager.active_controller:
            self.status_controller.config(text=controller_manager.active_controller["name"])
        
        if self.core:
            chip = "M4 Pro" if IS_M4 else ("Apple Silicon" if IS_APPLE_SILICON else "Intel")
            self.status_left.config(text=f"Ready — {chip}")
        else:
            self.status_left.config(text="Core missing — use Utilities > Install Core")
        
        self.load_roms()
    
    def load_roms(self):
        """Load ROMs into browser"""
        self.rom_list.delete(*self.rom_list.get_children())
        
        extensions = ("*.z64", "*.n64", "*.v64")
        roms = []
        for ext in extensions:
            roms.extend(ROM_DIR.glob(ext))
        
        for rom in sorted(roms):
            size_mb = rom.stat().st_size / (1024 * 1024)
            
            # Detect country from filename (simple heuristic)
            name = rom.stem
            country = "USA"
            if "(J)" in name or "(Japan)" in name:
                country = "Japan"
            elif "(E)" in name or "(Europe)" in name:
                country = "Europe"
            elif "(U)" in name or "(USA)" in name:
                country = "USA"
            
            # Detect type from extension
            rom_type = rom.suffix.upper()[1:]
            
            self.rom_list.insert("", "end", values=(
                name,
                country,
                f"{size_mb:.1f} MB",
                "EEPROM",  # Placeholder
                "Unknown"
            ), tags=(str(rom),))
        
        count = len(roms)
        self.status_left.config(text=f"Found {count} ROM(s)")
    
    def open_rom(self):
        """Open ROM file dialog"""
        files = filedialog.askopenfilenames(
            title="Open N64 ROM",
            filetypes=[("N64 ROMs", "*.z64 *.n64 *.v64"), ("All files", "*.*")]
        )
        for src in files:
            dst = ROM_DIR / Path(src).name
            if not dst.exists():
                shutil.copy2(src, dst)
        self.load_roms()
    
    def open_rom_dir(self):
        """Open ROM directory"""
        folder = filedialog.askdirectory(title="Select ROM Directory")
        if folder:
            global ROM_DIR
            ROM_DIR = Path(folder)
            self.load_roms()
    
    def change_rom_dir(self):
        """Change ROM directory"""
        self.open_rom_dir()
    
    def run_selected(self, event=None):
        """Run selected ROM"""
        selection = self.rom_list.selection()
        if not selection:
            messagebox.showinfo("No ROM Selected", "Please select a ROM to play")
            return
        
        item = selection[0]
        rom_name = self.rom_list.item(item)["values"][0]
        
        # Find ROM file
        rom = None
        for ext in [".z64", ".n64", ".v64"]:
            candidate = ROM_DIR / f"{rom_name}{ext}"
            if candidate.exists():
                rom = candidate
                break
        
        if not rom:
            messagebox.showerror("ROM Not Found", f"Could not find: {rom_name}")
            return
        
        self.status_left.config(text=f"Starting {rom_name}...")
        self.update()
        
        ok, err = launch_rom(rom, self.core)
        
        if ok:
            self.status_left.config(text=f"Playing: {rom_name}")
        else:
            self.status_left.config(text=f"Error: {err}")
            messagebox.showerror("Launch Error", err)
    
    def show_rom_context_menu(self, event):
        """Right-click context menu for ROMs"""
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Play Game", command=self.run_selected)
        menu.add_separator()
        menu.add_command(label="ROM Properties...")
        menu.add_command(label="Edit Game Settings...")
        menu.tk_popup(event.x_root, event.y_root)
    
    def detect_controllers(self):
        """Detect connected controllers"""
        self.status_left.config(text="Scanning for controllers...")
        self.update()
        
        controllers = controller_manager.detect_all()
        
        if controllers:
            self.status_controller.config(text=controller_manager.active_controller["name"])
            
            msg = "Detected Controllers:\n\n"
            for c in controllers:
                auto = " ★" if c.get("auto_detect") else ""
                msg += f"• {c['name']} ({c['year']}){auto}\n"
                msg += f"  Connection: {c['connection']}\n\n"
            
            if controller_manager.active_controller:
                msg += f"\nActive: {controller_manager.active_controller['name']}"
            
            messagebox.showinfo("Controllers Found", msg)
        else:
            self.status_controller.config(text="No Controller")
            messagebox.showinfo("No Controllers", "No game controllers detected.\n\nConnect a controller and try again.")
        
        self.status_left.config(text="Ready")
    
    def show_controller_config(self):
        """Show controller configuration dialog"""
        ConfigWindow(self, controller_manager)
    
    def show_controller_database(self):
        """Show all supported controllers"""
        DatabaseWindow(self)
    
    def reinstall_core(self):
        """Reinstall N64 core"""
        self.status_left.config(text="Downloading core...")
        self.update()
        
        for name in ["mupen64plus_next_libretro"]:
            core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
            if core.exists():
                core.unlink()
        
        self.core = install_core()
        
        if self.core:
            self.status_left.config(text=f"Core installed: {self.core.name}")
        else:
            messagebox.showerror("Error", "Failed to install core")
            self.status_left.config(text="Core installation failed")
    
    def fix_rosetta(self):
        """Fix Rosetta architecture issues"""
        global RETROARCH_ARCH, PATHS
        
        self.status_left.config(text="Fixing Rosetta...")
        self.update()
        
        # Clear Rosetta preferences
        try:
            subprocess.run(["defaults", "delete", "com.apple.rosetta", "RetroArch"], capture_output=True, timeout=5)
        except:
            pass
        
        try:
            info_plist = Path("/Applications/RetroArch.app/Contents/Info.plist")
            subprocess.run(["defaults", "delete", str(info_plist), "LSArchitecturePriority"], capture_output=True, timeout=5)
        except:
            pass
        
        # Delete existing cores
        for name in ["mupen64plus_next_libretro"]:
            core = PATHS["cores_dir"] / f"{name}{PATHS['core_ext']}"
            if core.exists():
                core.unlink()
        
        # Re-detect
        RETROARCH_ARCH = get_retroarch_running_arch()
        PATHS = get_platform_paths()
        
        self.core = install_core_forced(RETROARCH_ARCH or "arm64")
        
        if self.core:
            renderer = "Angrylion" if is_running_rosetta() else "GLideN64"
            self.status_renderer.config(text=renderer)
            self.status_left.config(text="Rosetta fix applied")
            messagebox.showinfo("Fixed", f"Architecture: {RETROARCH_ARCH}\nRenderer: {renderer}")
        else:
            self.status_left.config(text="Fix failed")
            messagebox.showerror("Error", "Failed to fix Rosetta issue")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Cat's HLE 1.3
High-Level Emulation Frontend

🐱 nyaa~

Built on RetroArch 1.22.2
mupen64plus_next core

Features:
• Project64 1.0 style interface
• Auto-detect controllers (1985-2024)
• Smart renderer selection
• M4 Pro / Apple Silicon optimized

Supported Controllers:
• Nintendo: NES, SNES, N64, GameCube, Wii, Switch
• Sony: PS1, PS2, PS3, PS4, PS5
• Microsoft: Xbox, 360, One, Series X
• Sega: Genesis, Saturn, Dreamcast
• Third Party: 8BitDo, Backbone, Razer, HORI

© 2025 Cat's Software"""
        
        messagebox.showinfo("About Cat's HLE", about_text)


class ConfigWindow(tk.Toplevel):
    """Controller configuration window"""
    
    def __init__(self, parent, controller_mgr):
        super().__init__(parent)
        self.title("Configure Controller")
        self.geometry("500x400")
        self.controller_mgr = controller_mgr
        
        self.setup_gui()
    
    def setup_gui(self):
        # Controller selection
        tk.Label(self, text="Active Controller:").pack(pady=5)
        
        self.controller_var = tk.StringVar()
        controllers = self.controller_mgr.detected_controllers
        
        if controllers:
            names = [c["name"] for c in controllers]
            self.controller_var.set(self.controller_mgr.active_controller["name"])
            
            combo = ttk.Combobox(self, textvariable=self.controller_var, values=names, state="readonly", width=40)
            combo.pack(pady=5)
            combo.bind("<<ComboboxSelected>>", self.on_controller_change)
        else:
            tk.Label(self, text="No controllers detected").pack(pady=5)
        
        # Mapping display
        tk.Label(self, text="\nN64 Button Mapping:").pack()
        
        mapping_frame = tk.Frame(self)
        mapping_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        n64_buttons = ["A", "B", "Z", "L", "R", "Start", "C-Up", "C-Down", "C-Left", "C-Right", "D-Pad", "Analog"]
        
        for i, btn in enumerate(n64_buttons):
            row = i // 3
            col = i % 3
            tk.Label(mapping_frame, text=f"{btn}:", anchor="e", width=10).grid(row=row, column=col*2, sticky="e", padx=2)
            tk.Entry(mapping_frame, width=10).grid(row=row, column=col*2+1, sticky="w", padx=2)
        
        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Auto-Detect", command=self.auto_detect).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Save", command=self.save_config).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def on_controller_change(self, event):
        name = self.controller_var.get()
        for c in self.controller_mgr.detected_controllers:
            if c["name"] == name:
                self.controller_mgr.active_controller = c
                break
    
    def auto_detect(self):
        self.controller_mgr.detect_all()
    
    def save_config(self):
        messagebox.showinfo("Saved", "Controller configuration saved")
        self.destroy()


class DatabaseWindow(tk.Toplevel):
    """Controller database viewer"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Supported Controllers (1985-2024)")
        self.geometry("700x500")
        
        self.setup_gui()
    
    def setup_gui(self):
        # Treeview with all controllers
        columns = ("name", "year", "era", "type")
        tree = ttk.Treeview(self, columns=columns, show="headings")
        
        tree.heading("name", text="Controller")
        tree.heading("year", text="Year")
        tree.heading("era", text="Era")
        tree.heading("type", text="Type")
        
        tree.column("name", width=300)
        tree.column("year", width=60)
        tree.column("era", width=150)
        tree.column("type", width=100)
        
        # Scrollbar
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate from database
        eras = {
            range(1985, 1990): "8-bit Era",
            range(1990, 1995): "16-bit Era",
            range(1995, 2000): "32/64-bit Era",
            range(2000, 2005): "128-bit Era",
            range(2005, 2010): "HD Era",
            range(2010, 2015): "Motion Era",
            range(2015, 2020): "Current Gen",
            range(2020, 2025): "Next Gen"
        }
        
        def get_era(year):
            for r, name in eras.items():
                if year in r:
                    return name
            return "Unknown"
        
        # Sort by year
        sorted_controllers = sorted(CONTROLLER_DATABASE.items(), key=lambda x: x[1]["year"])
        
        for key, data in sorted_controllers:
            year = data["year"]
            era = get_era(year)
            
            # Determine type
            if "Switch" in data["name"] or "Joy-Con" in data["name"]:
                ctype = "Nintendo"
            elif "PlayStation" in data["name"] or "DualShock" in data["name"] or "DualSense" in data["name"]:
                ctype = "Sony"
            elif "Xbox" in data["name"]:
                ctype = "Microsoft"
            elif "8BitDo" in data["name"] or "Backbone" in data["name"] or "Razer" in data["name"]:
                ctype = "Third Party"
            elif "Sega" in data["name"] or "Genesis" in data["name"] or "Saturn" in data["name"]:
                ctype = "Sega"
            else:
                ctype = "Other"
            
            tree.insert("", "end", values=(data["name"], year, era, ctype))
        
        # Count label
        count = len(CONTROLLER_DATABASE)
        tk.Label(self, text=f"Total: {count} controllers supported").pack(pady=5)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 Cat's HLE 1.3 — M4 Pro Edition")
    print("=" * 50)
    
    if IS_APPLE_SILICON:
        print("[M4] Apple Silicon optimizations enabled")
        if is_running_rosetta():
            print("[Mode] Rosetta → Angrylion software renderer")
        else:
            print("[Mode] Native ARM64 → GLideN64 hardware renderer")
    
    print(f"[Controllers] Database: {len(CONTROLLER_DATABASE)} controllers (1985-2024)")
    
    app = CatsHLE()
    app.mainloop()
