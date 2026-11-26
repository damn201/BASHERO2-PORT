"""Konstanta dan pengaturan Basara 2 Heroes PC Installer (stdlib saja)."""

import json
import os
import platform
from pathlib import Path

APP_DIR_NAME = "Basara2HeroesPCInstaller"

# --- Port native yang dipakai (PotatoRecomp/B2HWii-Android) ---
PORT_REPO = "PotatoRecomp/B2HWii-Android"
PORT_TAG = "v1.2.1-hotfix"
PORT_LICENSE = "GPLv3"
PORT_RELEASE_API = (
    f"https://api.github.com/repos/{PORT_REPO}/releases/tags/{PORT_TAG}"
)
# Aset Android di rilis ini (satu-satunya aset; tidak ada build Windows jadi).
# Ukuran dari API GitHub (pembulatan): 82,5 MB — tidak dipakai untuk
# verifikasi ukuran karena bukan angka byte persis.
PORT_ANDROID_ASSET = "basara2heroes-1.2.1-hotfix-android-arm64.apk"
PORT_ANDROID_ASSET_MB = 82.5
SOURCE_ZIP_URL = (
    f"https://github.com/{PORT_REPO}/archive/refs/tags/{PORT_TAG}.zip"
)
# Folder hasil ekstrak source zip (nama folder di dalam zip).
SOURCE_ZIP_ROOT = f"B2HWii-Android-{PORT_TAG}"

# --- File game (milik pengguna sendiri) ---
GAME_ID = "RBSJ08"  # Wii NTSC-J Sengoku Basara 2 Heroes
# Magic format RVZ Dolphin: "RVZ" + byte versi 0x01 (BUKAN ASCII "RVZ1"!
# v1.1.1: RVZ_MAGIC sempat b"RVZ1" sehingga semua file .rvz ASLI ditolak.
# Terverifikasi: RomM rvz_hasher.py (_RVZ_MAGIC = b"RVZ\x01") dan
# bodgit/rvz reader.go (rvzMagic 0x52565a01); file asli diawali
# 52 56 5A 01 01 00 00 00 ... (version u32 LE = 1 di byte 4-7).
RVZ_MAGIC = b"RVZ\x01"
# Game hasil build Windows (relatif terhadap folder install/source).
BUILT_EXE_PARTS = ("generated", "win-build", "WiiCompiled.exe")
BUILT_EXE_REL = "\\".join(BUILT_EXE_PARTS)
# Disc hasil ekstrak harus berisi file ini:
GAME_DOL_PARTS = ("assets", "basara-heroes", "sys", "main.dol")
GAME_DOL_REL = "\\".join(GAME_DOL_PARTS)

# --- Toolchain (semua URL terverifikasi 26 Nov 2026) ---
# llvm-mingw: TIDAK diunduh script repo mana pun — installer mengunduhnya
# sendiri ke third_party/llvm-mingw. Versi terbaru saat verifikasi:
# 20261117 (18 Nov 2026). Dipilih varian UCRT (default modern;
# varian msvcrt adalah alternatif lawas).
LLVM_MINGW_VERSION = "20261117"
LLVM_MINGW_ZIP = f"llvm-mingw-{LLVM_MINGW_VERSION}-ucrt-x86_64.zip"
LLVM_MINGW_URL = (
    "https://github.com/mstorsjo/llvm-mingw/releases/download/"
    f"{LLVM_MINGW_VERSION}/{LLVM_MINGW_ZIP}"
)
LLVM_MINGW_SIZE = 0  # tidak diverifikasi persis (API hanya memberi MB bulat)
LLVM_MINGW_MB = 182.2  # dari API GitHub (pembulatan), terverifikasi 26 Nov 2026
LLVM_CLANG_PARTS = ("bin", "x86_64-w64-mingw32-clang.exe")

# .NET 8 runtime lokal: b-translate.ps1 mengatur DOTNET_ROOT ke
# third_party/dotnet, jadi folder itu harus berisi dotnet.exe + runtime.
# Dipakai runtime (bukan SDK) karena b-translate hanya MENJALANKAN dll
# translator; membangun translator (dotnet build) memakai .NET 8 SDK
# yang diperiksa di syscheck — BILA TIDAK ADA, installer v1.1.0
# mengunduh SDK zip otomatis ke third_party/dotnet-sdk (bukan gagal).
DOTNET_RUNTIME_VERSION = "8.0.34"
DOTNET_RUNTIME_ZIP = f"dotnet-runtime-{DOTNET_RUNTIME_VERSION}-win-x64.zip"
DOTNET_RUNTIME_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/Runtime/"
    f"{DOTNET_RUNTIME_VERSION}/{DOTNET_RUNTIME_ZIP}"
)
DOTNET_RUNTIME_SIZE = 33343771  # 31,8 MB (terverifikasi 26 Nov 2026)
# .NET 8 SDK (diunduh otomatis bila sistem tidak punya SDK 8.x):
# 8.0.428, terverifikasi 26 Nov 2026: HEAD 200, 285.304.526 byte.
DOTNET_SDK_VERSION = "8.0.428"
DOTNET_SDK_ZIP = f"dotnet-sdk-{DOTNET_SDK_VERSION}-win-x64.zip"
DOTNET_SDK_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/"
    f"{DOTNET_SDK_VERSION}/{DOTNET_SDK_ZIP}"
)
DOTNET_SDK_SIZE = 285304526  # ~272 MB (terverifikasi 26 Nov 2026)
DOTNET_DOWNLOAD_PAGE = "https://dotnet.microsoft.com/download/dotnet/8.0"

# Dolphin (emulator) — dipakai HANYA untuk mengonversi .rvz ke .iso
# dengan DolphinTool.exe (bukan untuk memainkan game; gamenya dimainkan
# lewat port native hasil build). Rilis stabil terbaru saat verifikasi:
# 2609b (hotfix kedua 2609, Sep 2026; tercantum di halaman unduh resmi
# 13 Nov 2026). URL terverifikasi 26 Nov 2026: HEAD 200,
# 20.028.240 byte. Pola URL resmi (dari winget-pkgs + EmuDeck):
#   https://dl.dolphin-emu.org/releases/<versi>/dolphin-<versi>-x64.7z
# Formatnya .7z (bukan .zip) — diekstrak dengan py7zr yang terbundel di
# installer. Isi paket terverifikasi 26 Nov 2026 (diunduh + dibuka di
# sini): folder teratas "Dolphin-x64" berisi Dolphin.exe,
# DolphinTool.exe, Updater.exe. Di Windows nama tool-nya DolphinTool.exe
# (di Linux "dolphin-tool"). DolphinTool butuh Visual C++ Redistributable
# VS 2022 — bila gagal jalan, installer memberi tahu pengguna memasangnya.
DOLPHIN_VERSION = "2609b"
DOLPHIN_ZIP = f"dolphin-{DOLPHIN_VERSION}-x64.7z"
DOLPHIN_URL = (
    "https://dl.dolphin-emu.org/releases/"
    f"{DOLPHIN_VERSION}/{DOLPHIN_ZIP}"
)
DOLPHIN_SIZE = 20028240  # ~19,1 MB (terverifikasi 26 Nov 2026)
DOLPHIN_TOP_FOLDER = "Dolphin-x64"
DOLPHIN_TOOL_PARTS = ("DolphinTool.exe",)
VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

# Wiimms ISO Tools (wit) v3.05a r8638 (27 Agu 2022) — Windows 64-bit
# (Cygwin). wit TIDAK mendukung .rvz; .rvz harus dikonversi ke .iso
# dulu dengan Dolphin. URL dari daftar resmi wit.wiimm.de/download.html
# (diperiksa 26 Nov 2026; HEAD langsung dari VM ini diblokir situsnya,
# installer melaporkan jelas bila unduhan gagal).
WIT_VERSION = "3.05a-r8638"
WIT_ZIP = "wit-v3.05a-r8638-cygwin64.zip"
WIT_URL = f"https://wit.wiimm.de/download/{WIT_ZIP}"
WIT_MB = 14.9  # dari daftar unduh resmi wit.wiimm.de/download.html
WIT_EXE_PARTS = ("bin", "wit.exe")

# URL lain yang dipakai script repo port (dari tools/setup-android.ps1
# dan tools/build/Prepare-Dependencies.ps1 — dicatat untuk transparansi):
CMAKE_URL = (
    "https://github.com/Kitware/CMake/releases/download/v4.3.3/"
    "cmake-4.3.3-windows-x86_64.zip"
)
NINJA_URL = (
    "https://github.com/ninja-build/ninja/releases/download/v1.13.2/"
    "ninja-win.zip"
)

# --- Syarat minimum PC (dari README port + kebutuhan build) ---
MIN_WINDOWS_BUILD = 18362  # Windows 10 versi 1903 (lantai wajar; README: Windows)
MIN_DISK_GB = 15  # source + toolchain + deps + build bisa > 10 GB
RECOMMENDED_RAM_GB = 8.0  # hanya rekomendasi, bukan syarat gagal
DOTNET_MAJOR_REQUIRED = 8  # translator butuh .NET 8

USER_AGENT = "Basara2HeroesPCInstaller/1.1 (+https://github.com/PotatoRecomp/B2HWii-Android)"


def platform_id() -> str:
    """'windows' | 'macos' | 'linux' | 'unknown'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return "unknown"


def is_frozen() -> bool:
    """True saat berjalan sebagai binary hasil PyInstaller."""
    import sys

    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Folder data Basara 2 Heroes PC Installer milik pengguna."""
    pid = platform_id()
    if pid == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif pid == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / APP_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def downloads_dir() -> Path:
    folder = app_dir() / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def tools_dir() -> Path:
    folder = app_dir() / "tools"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def settings_path() -> Path:
    return app_dir() / "settings.json"


def default_install_dir() -> str:
    """Folder install bawaan source port: path pendek (disarankan)."""
    if platform_id() == "windows":
        return r"C:\Games\Basara2Heroes"
    return str(Path.home() / "Basara2Heroes")


def default_settings() -> dict:
    return {
        "install_dir": "",
        "game_file": "",
        "game_dir": "",
        "game_validated": False,
        "port_version": "",
        "built_exe": "",
        "toolchain_ready": False,
        "translated": False,
    }


def load_settings() -> dict:
    settings = default_settings()
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            settings.update(data)
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    settings_path().write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
