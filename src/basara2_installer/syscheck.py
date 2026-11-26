"""Cek sistem: apakah PC ini bisa membangun port Basara 2 Heroes (Wii).

Syarat (dari README port PotatoRecomp/B2HWii-Android + kebutuhan build):
  - Windows 10 atau Windows 11 64-bit (build dari source hanya di Windows)
  - CPU x86-64 (AVX2 TIDAK disyaratkan README port — hanya dilaporkan)
  - RAM: tidak ada batas minimum di README; 8 GB direkomendasikan
    (hanya laporan + rekomendasi, tidak pernah gagal karena angka)
  - GPU yang mendukung Vulkan (hanya dilaporkan)
  - Ruang disk kosong minimal 15 GB (source + toolchain + deps + build)
  - .NET 8 SDK terpasang (translator C# butuh .NET 8) — GAGAL bila tidak ada
  - PowerShell tersedia (semua script build repo port memakai PowerShell)

Setiap cek mengembalikan dict:
  {"id", "name", "status", "detail", "tip"}
dengan status "ok" | "gagal" | "tidak diketahui".

Semua cek dirancang gagal dengan anggun di Linux/Wine — tidak pernah crash,
melainkan melaporkan "tidak dapat diperiksa di sini".
"""

import ctypes
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import (
    DOTNET_DOWNLOAD_PAGE,
    DOTNET_MAJOR_REQUIRED,
    MIN_DISK_GB,
    MIN_WINDOWS_BUILD,
    RECOMMENDED_RAM_GB,
)

# Status
OK = "ok"
FAIL = "gagal"
UNKNOWN = "tidak diketahui"


def _check(check_id: str, name: str, status: str, detail: str, tip: str = "") -> dict:
    return {
        "id": check_id,
        "name": name,
        "status": status,
        "detail": detail,
        "tip": tip,
    }


# ---------------------------------------------------------------------------
# OS
# ---------------------------------------------------------------------------

def _os_check() -> dict:
    if platform.system() != "Windows":
        return _check(
            "os",
            "Sistem operasi",
            UNKNOWN,
            f"Tidak dapat diperiksa di sini ({platform.system()} — bukan Windows).",
            "Build dari source hanya didukung di Windows 10 atau Windows 11 "
            "64-bit (lihat README port).",
        )
    try:
        ver = sys.getwindowsversion()
        build = ver.build
        edition = "Windows 11" if build >= 22000 else "Windows 10"
        is_64bit = platform.machine().lower() in ("amd64", "x86_64", "arm64")
        if build >= MIN_WINDOWS_BUILD and is_64bit:
            return _check(
                "os",
                "Sistem operasi",
                OK,
                f"{edition} build {build} 64-bit.",
            )
        if build < MIN_WINDOWS_BUILD:
            return _check(
                "os",
                "Sistem operasi",
                FAIL,
                f"{edition} build {build} — terlalu lama.",
                "Butuh Windows 10 versi 1903 (build 18362) atau lebih baru.",
            )
        return _check(
            "os",
            "Sistem operasi",
            FAIL,
            "Windows 32-bit terdeteksi.",
            "Build dari source butuh Windows 64-bit.",
        )
    except (OSError, AttributeError):
        return _check(
            "os",
            "Sistem operasi",
            UNKNOWN,
            "Versi Windows tidak dapat dibaca.",
            "Pastikan memakai Windows 10 atau Windows 11 64-bit.",
        )


# ---------------------------------------------------------------------------
# CPU (hanya laporan — README port tidak menetapkan syarat instruksi)
# ---------------------------------------------------------------------------

def _cpu_name() -> str:
    if platform.system() == "Linux":
        try:
            text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
            match = re.search(r"model name\s*:\s*(.+)", text)
            if match:
                return match.group(1).strip()
        except OSError:
            pass
    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=15,
            )
            lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
            if len(lines) > 1:
                return lines[1]
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.processor() or "Tidak diketahui"


def _cpu_check() -> dict:
    name = _cpu_name()
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return _check(
            "cpu",
            "CPU",
            OK,
            f"CPU x86-64: {name}.",
            "README port tidak menetapkan syarat instruksi CPU (AVX2 tidak "
            "diwajibkan); CPU modern apa pun umumnya cukup.",
        )
    if machine in ("arm64", "aarch64"):
        return _check(
            "cpu",
            "CPU",
            FAIL,
            f"CPU ARM terdeteksi ({name}).",
            "Build Windows port ini memakai compiler x86-64 (llvm-mingw); "
            "butuh PC Windows x86-64.",
        )
    return _check(
        "cpu",
        "CPU",
        UNKNOWN,
        f"Arsitektur CPU tidak dapat dipastikan ({machine or '?'}). CPU: {name}.",
        "Pastikan memakai PC Windows x86-64.",
    )


# ---------------------------------------------------------------------------
# RAM (hanya laporan + rekomendasi 8 GB)
# ---------------------------------------------------------------------------

def _ram_gb() -> float | None:
    if platform.system() == "Windows":
        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024 ** 3
        except (OSError, AttributeError):
            return None
    if platform.system() == "Linux":
        try:
            text = Path("/proc/meminfo").read_text(encoding="utf-8")
            match = re.search(r"MemTotal:\s*(\d+)\s*kB", text)
            if match:
                return int(match.group(1)) / 1024 / 1024
        except OSError:
            return None
    if platform.system() == "Darwin":
        try:
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=10,
            )
            return int(out.stdout.strip()) / 1024 ** 3
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    return None


def _ram_check() -> dict:
    ram = _ram_gb()
    if ram is None:
        return _check(
            "ram",
            "RAM",
            UNKNOWN,
            "RAM tidak dapat diperiksa di sini.",
            f"Disarankan RAM {RECOMMENDED_RAM_GB:.0f} GB atau lebih — build "
            "C++ penuh (terjemahan + kompilasi) memakai banyak memori.",
        )
    if ram >= RECOMMENDED_RAM_GB:
        return _check(
            "ram",
            "RAM",
            OK,
            f"{ram:.1f} GB terpasang.",
        )
    return _check(
        "ram",
        "RAM",
        OK,
        f"{ram:.1f} GB terpasang (di bawah rekomendasi "
        f"{RECOMMENDED_RAM_GB:.0f} GB).",
        "Build tetap bisa jalan, tetapi mungkin lebih lambat. "
        "Tutup aplikasi lain saat build.",
    )


# ---------------------------------------------------------------------------
# GPU + Vulkan (hanya laporan)
# ---------------------------------------------------------------------------

def _gpu_info() -> tuple[str, float | None]:
    """(nama GPU, VRAM dalam GB atau None bila tidak diketahui)."""
    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController",
                 "get", "name,AdapterRAM"],
                capture_output=True, text=True, timeout=20,
            )
            best_name, best_vram = "", None
            for line in out.stdout.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("adapterram"):
                    continue
                parts = line.split(None, 1)
                try:
                    vram_bytes = int(parts[0])
                    vram_gb = vram_bytes / 1024 ** 3
                except (ValueError, IndexError):
                    vram_gb = None
                name = parts[1].strip() if len(parts) > 1 else ""
                if best_name == "" or (vram_gb or 0) > (best_vram or 0):
                    best_name, best_vram = name, vram_gb
            if best_name:
                return best_name, best_vram
        except (OSError, subprocess.SubprocessError):
            pass
        return "Tidak diketahui", None
    if platform.system() == "Linux":
        try:
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=20)
            for line in out.stdout.splitlines():
                if "VGA" in line or "3D controller" in line:
                    return line.split(":", 2)[-1].strip(), None
        except (OSError, subprocess.SubprocessError):
            pass
        return "Tidak diketahui", None
    return "Tidak diketahui", None


def _gpu_check() -> dict:
    name, vram = _gpu_info()
    if name == "Tidak diketahui":
        return _check(
            "gpu",
            "GPU / VRAM",
            UNKNOWN,
            "GPU tidak dapat diperiksa di sini.",
            "Pastikan GPU mendukung Vulkan dan drivernya terbaru.",
        )
    if vram is None:
        return _check(
            "gpu",
            "GPU / VRAM",
            OK,
            f"GPU: {name} (VRAM tidak dapat dibaca).",
            "Pastikan GPU mendukung Vulkan dan drivernya terbaru.",
        )
    return _check(
        "gpu",
        "GPU / VRAM",
        OK,
        f"{name} — VRAM {vram:.1f} GB.",
    )


def _vulkan_check() -> dict:
    if platform.system() == "Windows":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        dll = system_root / "System32" / "vulkan-1.dll"
        if dll.is_file():
            return _check(
                "vulkan",
                "Vulkan",
                OK,
                "vulkan-1.dll ditemukan di System32.",
            )
        return _check(
            "vulkan",
            "Vulkan",
            FAIL,
            "vulkan-1.dll tidak ditemukan di System32.",
            "Pasang driver GPU terbaru dari situs resmi NVIDIA / AMD / Intel — "
            "driver terbaru sudah menyertakan Vulkan.",
        )
    return _check(
        "vulkan",
        "Vulkan",
        UNKNOWN,
        "Tidak dapat diperiksa di sini (bukan Windows).",
        "Di Windows, pastikan driver GPU terbaru terpasang (Vulkan).",
    )


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

def _disk_check(path: str | Path | None) -> dict:
    target = Path(path) if path else Path.home()
    if not target.exists():
        target = Path.home()
    try:
        free_gb = shutil.disk_usage(target).free / 1024 ** 3
    except OSError:
        return _check(
            "disk",
            "Ruang disk kosong",
            UNKNOWN,
            f"Tidak dapat memeriksa disk di {target}.",
            f"Siapkan minimal {MIN_DISK_GB} GB kosong (source + toolchain "
            "+ dependency + build C++ bisa memakan > 10 GB).",
        )
    if free_gb >= MIN_DISK_GB:
        return _check(
            "disk",
            "Ruang disk kosong",
            OK,
            f"{free_gb:.1f} GB kosong di {target}.",
        )
    return _check(
        "disk",
        "Ruang disk kosong",
        FAIL,
        f"Hanya {free_gb:.1f} GB kosong di {target}.",
        f"Siapkan minimal {MIN_DISK_GB} GB kosong — source + toolchain + "
        "dependency + build C++ bisa memakan > 10 GB. Kosongkan disk atau "
        "pilih drive lain untuk folder install.",
    )


# ---------------------------------------------------------------------------
# .NET 8 SDK (WAJIB — translator C# butuh .NET 8)
# ---------------------------------------------------------------------------

def parse_dotnet_version(text: str) -> tuple[int, ...] | None:
    """Ubah output `dotnet --version` menjadi tuple versi, atau None.

    Fungsi murni (tanpa Windows) agar bisa diuji unit test:
    "8.0.428" -> (8, 0, 428); "9.0.100" -> (9, 0, 100);
    teks kosong / tanpa angka -> None.
    """
    if not text:
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text.strip())
    if not match:
        return None
    return tuple(int(g) for g in match.groups())


def dotnet_version() -> tuple[int, ...] | None:
    """Versi `dotnet` di PATH sebagai tuple, atau None bila tidak ada."""
    try:
        out = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return parse_dotnet_version(out.stdout)


def _dotnet_check() -> dict:
    if platform.system() != "Windows":
        return _check(
            "dotnet",
            ".NET 8 SDK",
            UNKNOWN,
            "Tidak dapat diperiksa di sini (bukan Windows).",
            "Translator game ini butuh .NET 8 SDK di Windows — pasang dari "
            f"{DOTNET_DOWNLOAD_PAGE}.",
        )
    version = dotnet_version()
    if version is None:
        return _check(
            "dotnet",
            ".NET 8 SDK",
            FAIL,
            ".NET SDK tidak ditemukan (perintah 'dotnet' tidak ada).",
            "Tidak apa-apa: installer v1.1.0 mengunduh .NET 8 SDK otomatis "
            "saat tombol MAIN ditekan (tidak perlu memasang manual). "
            "Bila ingin memasang sendiri: "
            f"{DOTNET_DOWNLOAD_PAGE} (pilih SDK x64 untuk Windows).",
        )
    if version[0] == DOTNET_MAJOR_REQUIRED:
        return _check(
            "dotnet",
            ".NET 8 SDK",
            OK,
            f".NET SDK {'.'.join(str(v) for v in version)} terpasang.",
        )
    if version[0] > DOTNET_MAJOR_REQUIRED:
        return _check(
            "dotnet",
            ".NET 8 SDK",
            OK,
            f".NET SDK {'.'.join(str(v) for v in version)} terpasang "
            f"(lebih baru dari .NET {DOTNET_MAJOR_REQUIRED}).",
            "Translator menargetkan .NET 8; versi lebih baru umumnya tetap "
            "bisa, tetapi bila build translator gagal, pasang .NET 8 SDK.",
        )
    return _check(
        "dotnet",
        ".NET 8 SDK",
        FAIL,
        f".NET SDK {'.'.join(str(v) for v in version)} terpasang — "
        f"terlalu lama (butuh .NET {DOTNET_MAJOR_REQUIRED}).",
        "Installer v1.1.0 mengunduh .NET 8 SDK otomatis saat tombol MAIN "
        "ditekan, jadi tidak perlu memasang manual. Bila ingin memasang "
        "sendiri: "
        f"{DOTNET_DOWNLOAD_PAGE} (bisa dipasang berdampingan dengan "
        "versi lain).",
    )


# ---------------------------------------------------------------------------
# PowerShell (semua script build repo port memakai PowerShell)
# ---------------------------------------------------------------------------

def _powershell_check() -> dict:
    if platform.system() != "Windows":
        return _check(
            "powershell",
            "PowerShell",
            UNKNOWN,
            "Tidak dapat diperiksa di sini (bukan Windows).",
            "Semua script build repo port (setup, translate, build) "
            "memakai PowerShell di Windows.",
        )
    if shutil.which("powershell"):
        return _check(
            "powershell",
            "PowerShell",
            OK,
            "PowerShell (Windows PowerShell) tersedia.",
        )
    return _check(
        "powershell",
        "PowerShell",
        FAIL,
        "PowerShell tidak ditemukan di PATH.",
        "Script build port ini memakai PowerShell — pastikan Windows "
        "PowerShell terpasang (bawaan Windows 10/11).",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_checks(install_dir: str | Path | None = None) -> list[dict]:
    """Jalankan semua cek sistem. Tidak pernah melempar exception."""
    checks = []
    for fn in (
        _os_check,
        _cpu_check,
        _ram_check,
        _gpu_check,
        _vulkan_check,
        _dotnet_check,
        _powershell_check,
    ):
        try:
            checks.append(fn())
        except Exception as exc:  # noqa: BLE001 - satu cek gagal, lainnya tetap jalan
            checks.append(_check(
                getattr(fn, "__name__", "cek"),
                "Cek sistem",
                UNKNOWN,
                f"Tidak dapat diperiksa di sini ({exc}).",
            ))
    try:
        checks.append(_disk_check(install_dir))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check(
            "disk", "Ruang disk kosong", UNKNOWN,
            f"Tidak dapat diperiksa di sini ({exc}).",
        ))
    return checks


def summarize(checks: list[dict]) -> tuple[int, int, int]:
    """(jumlah lolos, jumlah gagal, jumlah tidak diketahui)."""
    ok = sum(1 for c in checks if c["status"] == OK)
    failed = sum(1 for c in checks if c["status"] == FAIL)
    unknown = sum(1 for c in checks if c["status"] == UNKNOWN)
    return ok, failed, unknown
