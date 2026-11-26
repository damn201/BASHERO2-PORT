# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec untuk Basara 2 Heroes PC Installer.

Dijalankan dari root proyek:  pyinstaller build/basara2_installer.spec --noconfirm
Hasil:
  Windows  -> dist/Basara2HeroesPCInstaller.exe  (satu file; DLL runtime ikut terbundel)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent  # noqa: F821 - disediakan PyInstaller
ICON = str(PROJECT_ROOT / "assets" / "icon.ico") if sys.platform == "win32" else None

a = Analysis(
    [str(PROJECT_ROOT / "src" / "basara2_installer" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[(str(PROJECT_ROOT / "assets" / "icon.png"), "assets")],
    hiddenimports=[
        "cpuinfo",
        # py7zr + modul dekompresinya (diimpor dinamis di dalam py7zr):
        # NOTE: wheel-nya bernama "pybcj", tapi modul yang bisa diimpor
        # adalah "bcj" (bukan "pybcj") — salah nama di sini membuat
        # PyInstaller tidak membundelnya dan ekstraksi .7z gagal.
        "py7zr",
        "bcj",
        "pyppmd",
        "pyzstd",
        "multivolumefile",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Basara2HeroesPCInstaller",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
