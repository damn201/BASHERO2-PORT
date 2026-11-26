"""Manajemen port Basara 2 Heroes (Wii) — PotatoRecomp/B2HWii-Android:
unduh source, siapkan toolchain, validasi & ekstrak disc, terjemahkan,
bangun Windows, dan jalankan game.

v1.1.0 — perbaikan dari laporan pengguna (v1.0.0 tidak bisa menginstall):
  1. .rvz TIDAK LAGI jalan buntu: installer mengonversi .rvz ke .iso
     SENDIRI dengan DolphinTool.exe (dari paket Windows Dolphin resmi)
     — perintah resmi Dolphin: dolphin-tool convert -i <rvz> -o <iso>
     -f iso. Bila konversi gagal, error jelas + instruksi manual.
  2. .NET 8 SDK TIDAK LAGI penghalang: bila PC tidak punya SDK 8.x,
     installer mengunduh SDK zip otomatis ke third_party/dotnet-sdk
     dan memakai dotnet.exe dari sana untuk `dotnet build`.
  3. Folder generated/ + generated/b/ dibuat dulu sebelum script repo
     (b-translate.ps1 / b-win.ps1) menulis log ke sana.
  4. setup_toolchain memperbaiki tiap bagian yang hilang satu per satu
     (cmake / ninja / deps / llvm-mingw / dotnet) — tidak berhenti hanya
     karena setup-android.ps1 gagal di tengah; NDK tetap ditolerir.
  5. Alur MAIN satu tombol, resumable: tiap langkah dilewati bila hasil
     sebelumnya sudah ada (source, toolchain, main.dol, WiiCompiled.exe).

Port yang dipakai: PotatoRecomp/B2HWii-Android v1.2.1-hotfix (GPLv3).
TIDAK ADA build Windows jadi di rilis port (hanya APK Android 82,5 MB),
jadi installer ini mengotomasi build dari source di PC pengguna, mengikuti
README + script repo port:
  1. Unduh source zip, ekstrak ke folder install.
  2. tools/setup-android.ps1 — CMake 4.3.3, Ninja 1.13.2, Gradle 8.7,
     Dawn prebuilt, aurora dependencies (Prepare-Dependencies.ps1).
     Langkah NDK-nya butuh Android SDK; bila gagal, installer tetap
     lanjut selama bagian Windows (cmake/ninja/deps) sudah ada.
  3. llvm-mingw — TIDAK diunduh script repo mana pun; installer
     mengunduhnya sendiri (20261117, ucrt x64) ke third_party/llvm-mingw.
  4. .NET 8 runtime lokal — b-translate.ps1 mengatur DOTNET_ROOT ke
     third_party/dotnet; installer mengunduh runtime 8.0.34 ke sana bila
     belum ada. .NET 8 SDK (untuk `dotnet build`) diunduh otomatis bila
     sistem tidak punya SDK 8.x.
  5. Translator C# dibangun dulu (dotnet build) karena tidak ada script
     repo yang membangun Translator.Cli.dll yang dipakai b-translate.ps1.
  6. Disc .rvz dikonversi ke .iso (DolphinTool), lalu diekstrak dengan
     wit ke assets/basara-heroes/sys/main.dol.
  7. tools/b-translate.ps1 — PowerPC -> C++ (generated/).
  8. tools/b-win.ps1 -Mode configure (sekali) lalu -Mode build —
     menghasilkan generated/win-build/WiiCompiled.exe.
  9. tools/b-win.ps1 -Mode run -Seconds 0 — main (junction game ->
     assets/basara-heroes, log di UserData).

Modul ini TIDAK menyertakan file game apa pun — pengguna wajib memakai
dump Wii Sengoku Basara 2 Heroes NTSC-J (RBSJ08) miliknya sendiri
(.iso atau .rvz). Versi PS2 (SLPM-66848) TIDAK bisa dipakai di sini.
"""

import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from .config import (
    BUILT_EXE_PARTS,
    CMAKE_URL,
    DOLPHIN_SIZE,
    DOLPHIN_TOOL_PARTS,
    DOLPHIN_TOP_FOLDER,
    DOLPHIN_URL,
    DOLPHIN_ZIP,
    DOTNET_MAJOR_REQUIRED,
    DOTNET_RUNTIME_SIZE,
    DOTNET_RUNTIME_URL,
    DOTNET_RUNTIME_ZIP,
    DOTNET_SDK_SIZE,
    DOTNET_SDK_URL,
    DOTNET_SDK_VERSION,
    DOTNET_SDK_ZIP,
    GAME_DOL_PARTS,
    GAME_ID,
    LLVM_CLANG_PARTS,
    LLVM_MINGW_URL,
    LLVM_MINGW_ZIP,
    NINJA_URL,
    PORT_ANDROID_ASSET,
    PORT_RELEASE_API,
    PORT_TAG,
    RVZ_MAGIC,
    SOURCE_ZIP_ROOT,
    SOURCE_ZIP_URL,
    USER_AGENT,
    VC_REDIST_URL,
    WIT_EXE_PARTS,
    WIT_URL,
    WIT_ZIP,
    downloads_dir,
    load_settings,
    save_settings,
    tools_dir,
)
from .syscheck import dotnet_version as _system_dotnet_version


def _github_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def release_info(timeout: int = 30) -> dict:
    """Ambil info rilis port dari GitHub API.

    Mengembalikan {"tag", "asset_names": [...]}. Dipakai self-test untuk
    memastikan rilis v1.2.1-hotfix masih ada dan berisi APK Android
    (bukti tidak ada build Windows jadi di rilis).
    """
    data = _github_json(PORT_RELEASE_API, timeout=timeout)
    names = [a.get("name", "") for a in data.get("assets", [])]
    return {"tag": data.get("tag_name", ""), "asset_names": names}


def download_file(
    url: str,
    dest: Path,
    progress_cb=None,
    expected_size: int = 0,
    timeout: int = 1800,
) -> Path:
    """Unduh file dengan laporan progres (downloaded_bytes, total_bytes).

    Memverifikasi ukuran file bila expected_size > 0.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)
    if expected_size and dest.stat().st_size != expected_size:
        raise RuntimeError(
            f"Ukuran file tidak cocok: {dest.stat().st_size} byte, "
            f"diharapkan {expected_size} byte. Unduhan mungkin rusak — coba lagi."
        )
    return dest


def _extract_zip_flatten(zip_path: Path, dest: Path) -> Path:
    """Ekstrak zip ke dest; bila zip hanya berisi satu folder teratas,
    isi folder itu yang dipindah ke dest (bukan foldernya sendiri)."""
    dest = Path(dest)
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(f"File bukan zip yang valid: {zip_path}")
    tmp = dest.parent / (dest.name + ".extract")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(path=tmp)
    children = [p for p in tmp.iterdir()]
    dest.mkdir(parents=True, exist_ok=True)
    if len(children) == 1 and children[0].is_dir():
        for item in children[0].iterdir():
            shutil.move(str(item), str(dest / item.name))
    else:
        for item in children:
            shutil.move(str(item), str(dest / item.name))
    shutil.rmtree(tmp, ignore_errors=True)
    return dest


def _extract_7z_flatten(archive_path: Path, dest: Path) -> Path:
    """Ekstrak arsip .7z ke dest; bila arsip hanya berisi satu folder
    teratas, isi folder itu yang dipindah ke dest (seperti
    _extract_zip_flatten, tetapi untuk .7z).

    Pakai py7zr yang terbundel di installer (pure Python + ekstensi C
    untuk dekompresi). Bila py7zr tidak tersedia, coba tar.exe bawaan
    Windows (bsdtar/libarchive bisa membaca .7z). Bila keduanya gagal,
    beri error jelas + instruksi manual.
    """
    archive_path = Path(archive_path)
    dest = Path(dest)
    if not archive_path.is_file():
        raise RuntimeError(f"File arsip tidak ditemukan: {archive_path}")
    tmp = dest.parent / (dest.name + ".extract7z")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    extracted = False
    last_error: Exception | None = None
    try:
        import py7zr  # type: ignore

        with py7zr.SevenZipFile(archive_path, "r") as zf:
            zf.extractall(path=tmp)
        extracted = True
    except ImportError as exc:
        last_error = exc
    except Exception as exc:  # noqa: BLE001 - coba fallback tar.exe
        last_error = exc
    if not extracted:
        # Fallback: tar.exe bawaan Windows 10/11 (libarchive membaca .7z).
        tar = shutil.which("tar")
        if tar:
            code = subprocess.run(
                [tar, "-xf", str(archive_path), "-C", str(tmp)],
                capture_output=True, text=True, timeout=600,
            ).returncode
            if code == 0 and any(tmp.iterdir()):
                extracted = True
            else:
                last_error = RuntimeError(
                    f"tar.exe gagal mengekstrak {archive_path.name} "
                    f"(exit {code})."
                )
    if not extracted:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(
            f"Tidak bisa mengekstrak {archive_path.name}. "
            f"Penyebab: {last_error}. Coba ekstrak manual dengan 7-Zip "
            "(https://www.7-zip.org) lalu letakkan isinya di folder "
            f"{dest}."
        )
    children = [p for p in tmp.iterdir()]
    dest.mkdir(parents=True, exist_ok=True)
    if len(children) == 1 and children[0].is_dir():
        for item in children[0].iterdir():
            shutil.move(str(item), str(dest / item.name))
    else:
        for item in children:
            shutil.move(str(item), str(dest / item.name))
    shutil.rmtree(tmp, ignore_errors=True)
    return dest


def ensure_generated_dirs(source_root: Path | str) -> tuple[Path, Path]:
    """Buat folder generated/ dan generated/b/ di folder source.

    Source port TIDAK berisi folder generated/ (0 entri di git tree),
    tetapi b-translate.ps1 dan b-win.ps1 menulis log ke generated/b/...
    via Out-File — tanpa folder ini script gagal menulis log. Dipanggil
    sebelum translate / configure / build.
    """
    source_root = Path(source_root)
    generated = source_root / "generated"
    logs = generated / "b"
    logs.mkdir(parents=True, exist_ok=True)
    return generated, logs


# ---------------------------------------------------------------------------
# Source port
# ---------------------------------------------------------------------------

def download_source_zip(
    dest: Path | None = None,
    progress_cb=None,
) -> Path:
    """Unduh source zip port v1.2.1-hotfix."""
    dest = dest or (downloads_dir() / f"B2HWii-Android-{PORT_TAG}.zip")
    return download_file(SOURCE_ZIP_URL, dest, progress_cb=progress_cb)


def extract_source_zip(zip_path: Path, install_dir: Path) -> Path:
    """Ekstrak source zip ke folder install. Mengembalikan folder install."""
    zip_path = Path(zip_path)
    install_dir = Path(install_dir)
    if not zip_path.is_file():
        raise RuntimeError(f"File zip tidak ditemukan: {zip_path}")
    _extract_zip_flatten(zip_path, install_dir)
    return install_dir


def find_source_root(install_dir: Path | str) -> Path | None:
    """Folder source port bila sudah terpasang (tools/b-win.ps1 ada)."""
    root = Path(install_dir)
    if not root.is_dir():
        return None
    # Source zip diekstrak langsung ke install_dir (flatten), jadi script
    # ada di <install_dir>/tools/. Bila pengguna mengekstrak manual tanpa
    # flatten, cek juga satu level lebih dalam.
    if (root / "tools" / "b-win.ps1").is_file():
        return root
    nested = root / SOURCE_ZIP_ROOT
    if (nested / "tools" / "b-win.ps1").is_file():
        return nested
    return None


def install_source(
    install_dir: Path | str,
    progress_cb=None,
) -> Path:
    """Unduh + ekstrak source port ke folder install.

    Menyimpan install_dir dan versi port ke settings.
    """
    install_dir = Path(install_dir)
    zip_path = download_source_zip(progress_cb=progress_cb)
    extract_source_zip(zip_path, install_dir)
    root = find_source_root(install_dir)
    if root is None:
        raise RuntimeError(
            "Source berhasil diunduh dan diekstrak, tetapi "
            "tools/b-win.ps1 tidak ditemukan di folder install."
        )
    settings = load_settings()
    settings["install_dir"] = str(install_dir)
    settings["port_version"] = PORT_TAG
    save_settings(settings)
    return root


# ---------------------------------------------------------------------------
# Menjalankan perintah eksternal dengan log live
# ---------------------------------------------------------------------------

def run_streaming(
    cmd: list[str],
    log_cb=None,
    cwd: Path | str | None = None,
    timeout: int | None = None,
) -> int:
    """Jalankan perintah, kirim tiap baris output ke log_cb, kembalikan
    exit code. Melempar RuntimeError bila perintah tidak bisa dijalankan."""
    try:
        proc = subprocess.Popen(
            [str(c) for c in cmd],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        raise RuntimeError(f"Tidak bisa menjalankan {' '.join(cmd)}: {exc}")
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if log_cb:
                log_cb(line.rstrip("\r\n"))
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(
            f"Perintah kehabisan waktu ({timeout} detik): {' '.join(cmd)}"
        )
    return proc.returncode


def run_powershell(
    script: Path | str,
    args: list[str] | None = None,
    log_cb=None,
    cwd: Path | str | None = None,
) -> int:
    """Jalankan script .ps1 repo port via PowerShell (hanya Windows)."""
    import platform

    if platform.system() != "Windows":
        raise RuntimeError(
            "Script build port hanya bisa dijalankan di Windows "
            "(memakai PowerShell)."
        )
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
    ] + [str(a) for a in (args or [])]
    return run_streaming(cmd, log_cb=log_cb, cwd=cwd)


def _powershell_available() -> bool:
    return shutil.which("powershell") is not None


# ---------------------------------------------------------------------------
# Toolchain
# ---------------------------------------------------------------------------

def _check_toolchain_pieces(source_root: Path) -> dict:
    """Bagian toolchain Windows yang sudah ada (True/False per bagian)."""
    tp = source_root / "third_party"
    return {
        "cmake": (tp / "cmake" / "bin" / "cmake.exe").is_file(),
        "ninja": (tp / "ninja" / "ninja.exe").is_file(),
        "deps": (tp / "deps").is_dir()
        and any((tp / "deps").iterdir()),
        "llvm-mingw": (tp / "llvm-mingw").joinpath(*LLVM_CLANG_PARTS).is_file(),
        "dotnet": (tp / "dotnet" / "dotnet.exe").is_file(),
    }


def _repair_cmake(source_root: Path, log_cb=None, progress_cb=None) -> None:
    """Unduh + pasang CMake bila third_party/cmake belum lengkap."""
    target = source_root / "third_party" / "cmake"
    if (target / "bin" / "cmake.exe").is_file():
        return
    dest = downloads_dir() / "cmake-4.3.3-windows-x86_64.zip"
    if log_cb:
        log_cb("CMake belum ada — mengunduh langsung...")
    download_file(CMAKE_URL, dest, progress_cb=progress_cb)
    _extract_zip_flatten(dest, target)
    if not (target / "bin" / "cmake.exe").is_file():
        raise RuntimeError("CMake gagal dipasang — cmake.exe tidak ditemukan.")


def _repair_ninja(source_root: Path, log_cb=None, progress_cb=None) -> None:
    """Unduh + pasang Ninja bila third_party/ninja belum lengkap."""
    target = source_root / "third_party" / "ninja"
    if (target / "ninja.exe").is_file():
        return
    dest = downloads_dir() / "ninja-win.zip"
    if log_cb:
        log_cb("Ninja belum ada — mengunduh langsung...")
    download_file(NINJA_URL, dest, progress_cb=progress_cb)
    _extract_zip_flatten(dest, target)
    if not (target / "ninja.exe").is_file():
        raise RuntimeError("Ninja gagal dipasang — ninja.exe tidak ditemukan.")


def _repair_deps(source_root: Path, log_cb=None) -> None:
    """Jalankan Prepare-Dependencies.ps1 langsung bila third_party/deps
    belum lengkap (script ini yang mengunduh SDL/Dawn/fmt/dll. ke deps).

    Langkah ini memang bisa gagal di sebagian PC (mis. langkah cppwinrt
    khusus Windows); bila tetap gagal, beri error jelas — build Windows
    tidak bisa jalan tanpa deps.
    """
    tp = source_root / "third_party"
    deps = tp / "deps"
    if deps.is_dir() and any(deps.iterdir()):
        return
    script = source_root / "tools" / "build" / "Prepare-Dependencies.ps1"
    if not script.is_file():
        raise RuntimeError(
            f"Script dependency tidak ditemukan: {script}. Toolchain "
            "tidak bisa dilengkapi."
        )
    if log_cb:
        log_cb("Dependency (deps) belum ada — menjalankan "
               "Prepare-Dependencies.ps1 langsung...")
    code = run_powershell(
        script, ["-Destination", str(deps)], log_cb=log_cb, cwd=source_root
    )
    if code != 0 or not (deps.is_dir() and any(deps.iterdir())):
        raise RuntimeError(
            "Prepare-Dependencies.ps1 gagal "
            f"(exit {code}) dan folder third_party/deps masih kosong. "
            "Build Windows butuh dependency ini (SDL, Dawn, fmt). "
            "Periksa log di atas; kemungkinan jaringan terputus saat "
            "mengunduh dari github.com."
        )
    if log_cb:
        log_cb("Dependency (deps) terpasang.")


def setup_toolchain(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> dict:
    """Siapkan toolchain Windows untuk build port.

    1. Jalankan tools/setup-android.ps1 (CMake, Ninja, Gradle, Dawn,
       aurora deps). Langkah NDK-nya butuh Android SDK; bila script gagal
       di langkah itu tetapi bagian Windows sudah lengkap, dianggap
       berhasil dengan peringatan.
    2. PERBAIKAN v1.1.0: bila script gagal di tengah (unduhan CMake /
       Ninja / Dawn gagal), periksa tiap bagian satu per satu dan unduh
       langsung bagian yang hilang (cmake, ninja, deps). Hanya gagal bila
       setelah perbaikan pun bagian Windows (cmake/ninja/deps) belum
       lengkap.
    3. Unduh + pasang llvm-mingw (tidak disediakan script repo).
    4. Unduh + pasang .NET 8 runtime lokal ke third_party/dotnet
       (dibutuhkan b-translate.ps1 via DOTNET_ROOT).

    Mengembalikan dict hasil cek bagian toolchain.
    """
    source_root = Path(source_root)
    if log_cb:
        log_cb("Menyiapkan toolchain (setup-android.ps1)...")
    script = source_root / "tools" / "setup-android.ps1"
    if not script.is_file():
        raise RuntimeError(f"Script tidak ditemukan: {script}")
    code = run_powershell(script, log_cb=log_cb, cwd=source_root)
    pieces = _check_toolchain_pieces(source_root)
    windows_ready = pieces["cmake"] and pieces["ninja"] and pieces["deps"]
    if code != 0:
        if log_cb:
            log_cb(
                f"setup-android.ps1 berakhir dengan error (exit {code}). "
                "Memeriksa tiap bagian toolchain satu per satu dan "
                "memperbaiki yang hilang..."
            )
        # Perbaiki tiap bagian yang hilang, satu per satu.
        try:
            _repair_cmake(source_root, log_cb=log_cb, progress_cb=progress_cb)
            _repair_ninja(source_root, log_cb=log_cb, progress_cb=progress_cb)
            _repair_deps(source_root, log_cb=log_cb)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Toolchain gagal dilengkapi setelah setup-android.ps1 "
                f"gagal (exit {code}). {exc}"
            )
        pieces = _check_toolchain_pieces(source_root)
        windows_ready = pieces["cmake"] and pieces["ninja"] and pieces["deps"]
        if not windows_ready:
            raise RuntimeError(
                "setup-android.ps1 gagal dan perbaikan otomatis belum "
                "melengkapi toolchain Windows (cmake/ninja/deps). "
                "Periksa log di atas — kemungkinan jaringan terputus."
            )
        if log_cb:
            log_cb(
                "Toolchain Windows berhasil dilengkapi setelah perbaikan "
                "otomatis (kemungkinan kegagalan tadi di langkah NDK "
                "Android yang tidak dibutuhkan untuk build Windows)."
            )
    if log_cb:
        log_cb("setup-android.ps1 selesai. Memasang llvm-mingw...")
    ensure_llvm_mingw(source_root, log_cb=log_cb, progress_cb=progress_cb)
    if log_cb:
        log_cb("Memasang .NET 8 runtime lokal (third_party/dotnet)...")
    ensure_dotnet_local(source_root, log_cb=log_cb, progress_cb=progress_cb)
    pieces = _check_toolchain_pieces(source_root)
    settings = load_settings()
    settings["toolchain_ready"] = all(pieces.values())
    save_settings(settings)
    return pieces


def ensure_llvm_mingw(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Pastikan llvm-mingw ada di third_party/llvm-mingw (unduh bila belum)."""
    source_root = Path(source_root)
    target = source_root / "third_party" / "llvm-mingw"
    clang = target.joinpath(*LLVM_CLANG_PARTS)
    if clang.is_file():
        if log_cb:
            log_cb(f"llvm-mingw sudah ada: {clang}")
        return target
    dest = downloads_dir() / LLVM_MINGW_ZIP
    if log_cb:
        log_cb(f"Mengunduh llvm-mingw {LLVM_MINGW_URL} ...")
    download_file(LLVM_MINGW_URL, dest, progress_cb=progress_cb)
    if log_cb:
        log_cb("Mengekstrak llvm-mingw (182 MB, mohon tunggu)...")
    _extract_zip_flatten(dest, target)
    if not clang.is_file():
        raise RuntimeError(
            "llvm-mingw berhasil diunduh dan diekstrak, tetapi compiler "
            f"{'/'.join(LLVM_CLANG_PARTS)} tidak ditemukan di {target}."
        )
    if log_cb:
        log_cb(f"llvm-mingw terpasang: {clang}")
    return target


def ensure_dotnet_local(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Pastikan .NET 8 runtime lokal ada di third_party/dotnet.

    b-translate.ps1 mengatur DOTNET_ROOT ke folder ini, jadi folder ini
    harus berisi dotnet.exe + runtime agar translator bisa dijalankan.
    """
    source_root = Path(source_root)
    target = source_root / "third_party" / "dotnet"
    exe = target / "dotnet.exe"
    if exe.is_file():
        if log_cb:
            log_cb(f".NET runtime lokal sudah ada: {exe}")
        return target
    dest = downloads_dir() / DOTNET_RUNTIME_ZIP
    if log_cb:
        log_cb(f"Mengunduh .NET 8 runtime {DOTNET_RUNTIME_URL} ...")
    download_file(
        DOTNET_RUNTIME_URL, dest,
        progress_cb=progress_cb, expected_size=DOTNET_RUNTIME_SIZE,
    )
    if log_cb:
        log_cb("Mengekstrak .NET 8 runtime...")
    _extract_zip_flatten(dest, target)
    if not exe.is_file():
        raise RuntimeError(
            ".NET 8 runtime berhasil diunduh dan diekstrak, tetapi "
            f"dotnet.exe tidak ditemukan di {target}."
        )
    if log_cb:
        log_cb(f".NET 8 runtime lokal terpasang: {exe}")
    return target


def sdk_dotnet_exe(source_root: Path | str) -> Path | None:
    """dotnet.exe dari SDK lokal (third_party/dotnet-sdk) bila sudah ada."""
    exe = Path(source_root) / "third_party" / "dotnet-sdk" / "dotnet.exe"
    return exe if exe.is_file() else None


def system_dotnet_sdk_version() -> tuple[int, ...] | None:
    """Versi SDK .NET sistem (PATH), atau None bila tidak ada."""
    return _system_dotnet_version()


def ensure_dotnet_sdk(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> str:
    """Pastikan ada dotnet SDK 8.x untuk `dotnet build` translator.

    Urutan: (1) SDK sistem di PATH bila versinya 8.x (atau lebih baru);
    (2) SDK lokal di third_party/dotnet-sdk bila sudah diunduh;
    (3) unduh SDK zip otomatis (~272 MB) ke third_party/dotnet-sdk dan
    pakai dotnet.exe dari sana. Mengembalikan perintah dotnet yang
    dipakai untuk build (path exe atau "dotnet").
    """
    source_root = Path(source_root)
    version = system_dotnet_sdk_version()
    if version is not None and version[0] >= DOTNET_MAJOR_REQUIRED:
        if log_cb:
            log_cb(
                ".NET SDK sistem ditemukan: "
                f"{'.'.join(str(v) for v in version)} — dipakai untuk build."
            )
        return "dotnet"
    local = sdk_dotnet_exe(source_root)
    if local is not None:
        if log_cb:
            log_cb(f".NET 8 SDK lokal sudah ada: {local}")
        return str(local)
    target = source_root / "third_party" / "dotnet-sdk"
    dest = downloads_dir() / DOTNET_SDK_ZIP
    if log_cb:
        log_cb(
            ".NET 8 SDK tidak ditemukan di PC — mengunduh otomatis "
            f"({DOTNET_SDK_VERSION}, ~272 MB, mohon tunggu)..."
        )
    try:
        download_file(
            DOTNET_SDK_URL, dest,
            progress_cb=progress_cb, expected_size=DOTNET_SDK_SIZE,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Gagal mengunduh .NET 8 SDK "
            f"({exc}). Coba pasang manual dari "
            "https://dotnet.microsoft.com/download/dotnet/8.0 "
            "(pilih SDK x64 untuk Windows), lalu tekan MAIN lagi."
        )
    if log_cb:
        log_cb("Mengekstrak .NET 8 SDK...")
    _extract_zip_flatten(dest, target)
    exe = sdk_dotnet_exe(source_root)
    if exe is None:
        raise RuntimeError(
            ".NET 8 SDK berhasil diunduh dan diekstrak, tetapi dotnet.exe "
            f"tidak ditemukan di {target}."
        )
    if log_cb:
        log_cb(f".NET 8 SDK lokal terpasang: {exe}")
    return str(exe)


def dotnet_exe(source_root: Path | str | None = None) -> str:
    """Perintah dotnet untuk membangun translator: SDK sistem (PATH)
    bila ada, sonst SDK lokal di third_party/dotnet-sdk, sonst runtime
    lokal di third_party/dotnet (hanya bisa menjalankan, bukan build)."""
    if shutil.which("dotnet"):
        return "dotnet"
    if source_root is not None:
        local_sdk = sdk_dotnet_exe(source_root)
        if local_sdk is not None:
            return str(local_sdk)
        local = Path(source_root) / "third_party" / "dotnet" / "dotnet.exe"
        if local.is_file():
            return str(local)
    return "dotnet"


def translator_dll(source_root: Path | str) -> Path:
    """Path dll translator hasil build (Release, net8.0)."""
    return (
        Path(source_root) / "translator" / "src" / "Translator.Cli"
        / "bin" / "Release" / "net8.0" / "Translator.Cli.dll"
    )


def build_translator(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Bangun translator C# (dotnet build). Tidak ada script repo yang
    melakukan ini — b-translate.ps1 mengharapkan dll-nya sudah ada.

    v1.1.0: bila PC tidak punya .NET 8 SDK, SDK diunduh otomatis dulu
    (ensure_dotnet_sdk) — bukan lagi kegagalan.
    """
    source_root = Path(source_root)
    dll = translator_dll(source_root)
    if dll.is_file():
        if log_cb:
            log_cb(f"Translator sudah dibangun: {dll}")
        return dll
    csproj = (
        source_root / "translator" / "src" / "Translator.Cli"
        / "Translator.Cli.csproj"
    )
    if not csproj.is_file():
        raise RuntimeError(f"Project translator tidak ditemukan: {csproj}")
    exe = ensure_dotnet_sdk(
        source_root, log_cb=log_cb, progress_cb=progress_cb
    )
    if log_cb:
        log_cb("Membangun translator (dotnet build, Release)...")
    code = run_streaming(
        [exe, "build", str(csproj), "-c", "Release"],
        log_cb=log_cb,
        cwd=source_root,
    )
    if code != 0:
        raise RuntimeError(
            f"dotnet build translator gagal (exit {code}). Periksa log di "
            "atas — kemungkinan file project rusak atau disk penuh. "
            "Tekan MAIN lagi untuk mencoba dari langkah ini."
        )
    if not dll.is_file():
        raise RuntimeError(
            "dotnet build selesai tanpa error, tetapi "
            f"{dll.name} tidak ditemukan di {dll.parent}."
        )
    if log_cb:
        log_cb(f"Translator berhasil dibangun: {dll}")
    return dll


# ---------------------------------------------------------------------------
# Validasi file game
# ---------------------------------------------------------------------------

def _read_magic(path: Path, size: int = 4) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(size)


def _printable_id(raw: bytes) -> str:
    text = "".join(chr(b) if 32 <= b < 127 else "?" for b in raw)
    return text.strip() or "(tidak terbaca)"


def validate_game_file(path: Path | str) -> dict:
    """Validasi satu file/folder game.

    - .iso: 6 byte pertama harus "RBSJ08" (Wii NTSC-J Basara 2 Heroes).
    - .rvz: 4 byte pertama harus "RVZ" + byte 0x01 (magic RVZ Dolphin;
      v1.1.0: dikonversi otomatis ke .iso dengan DolphinTool — tidak
      lagi jalan buntu).
    - folder: harus berisi sys/main.dol (folder hasil ekstraksi disc).

    Mengembalikan:
      {"valid": bool, "kind": "iso"|"rvz"|"folder"|"",
       "issues": [...], "warnings": [...], "detail": str,
       "game_id": str}
    """
    issues: list[str] = []
    warnings: list[str] = []
    kind = ""
    game_id = ""

    raw = Path(path) if str(path).strip() else Path("")
    if not str(path).strip():
        issues.append("File/folder game belum dipilih.")
    elif not raw.exists():
        issues.append(f"File/folder game tidak ditemukan: {raw}")
    elif raw.is_dir():
        kind = "folder"
        dol = raw / "sys" / "main.dol"
        nested = raw / "assets" / "basara-heroes" / "sys" / "main.dol"
        if dol.is_file():
            game_id = GAME_ID
        elif nested.is_file():
            game_id = GAME_ID
        else:
            issues.append(
                f"Folder {raw} tidak berisi sys/main.dol — ini bukan "
                "folder hasil ekstraksi disc Wii Basara 2 Heroes. "
                "Pilih folder hasil ekstraksi (berisi sys/main.dol) atau "
                "ekstrak disc .iso dulu."
            )
    elif raw.is_file():
        if raw.stat().st_size == 0:
            issues.append(f"File game kosong (0 byte): {raw}")
        else:
            suffix = raw.suffix.lower()
            if suffix == ".iso":
                kind = "iso"
                try:
                    # Game ID Wii = 6 byte di offset 0 (mis. "RBSJ08").
                    magic = _read_magic(raw, size=6)
                except OSError as exc:
                    issues.append(f"Tidak bisa membaca file game: {exc}")
                    magic = b""
                if magic:
                    game_id = _printable_id(magic)
                    if magic != GAME_ID.encode("ascii"):
                        issues.append(
                            f"Game ID di file ini: {game_id} — bukan "
                            f"{GAME_ID}. Pastikan ini dump Wii Sengoku "
                            "Basara 2 Heroes NTSC-J. Versi PS2 (SLPM-66848) "
                            "TIDAK bisa dipakai — installer ini hanya untuk "
                            "versi Wii (RBSJ08)."
                        )
            elif suffix == ".rvz":
                kind = "rvz"
                try:
                    magic = _read_magic(raw)
                except OSError as exc:
                    issues.append(f"Tidak bisa membaca file game: {exc}")
                    magic = b""
                if magic:
                    if magic == RVZ_MAGIC:
                        game_id = GAME_ID
                        warnings.append(
                            "File .rvz akan dikonversi otomatis ke .iso "
                            "oleh installer (DolphinTool) sebelum "
                            "diekstrak — tidak perlu konversi manual."
                        )
                    else:
                        issues.append(
                            "File .rvz ini tidak diawali magic RVZ "
                            "(\"RVZ\" + byte 0x01) "
                            f"(terdeteksi: {_printable_id(magic)}). File "
                            "mungkin rusak atau bukan file RVZ."
                        )
            else:
                issues.append(
                    f"Format file tidak didukung: {raw.suffix or '(tanpa ekstensi)'} "
                    f"(file ini: {raw.name}). Pilih dump Wii .iso atau .rvz, "
                    "atau folder hasil ekstraksi (berisi sys/main.dol)."
                )
    else:
        issues.append(f"Path game tidak valid: {raw}")

    valid = not issues
    if valid and kind == "iso":
        detail = (
            f"File game valid: dump Wii Sengoku Basara 2 Heroes NTSC-J "
            f"({GAME_ID}), format .iso."
        )
    elif valid and kind == "rvz":
        detail = (
            "File game valid: dump Wii (RVZ). Installer akan mengonversi "
            "otomatis ke .iso (DolphinTool) sebelum diekstrak."
        )
    elif valid and kind == "folder":
        detail = (
            "Folder game valid: berisi sys/main.dol "
            "(hasil ekstraksi disc Wii)."
        )
    elif valid:
        detail = "File game valid."
    else:
        detail = "File game TIDAK valid — " + " ".join(issues)
    if valid and warnings:
        detail += " Catatan: " + " ".join(warnings)
    return {
        "valid": valid,
        "kind": kind,
        "issues": issues,
        "warnings": warnings,
        "detail": detail,
        "game_id": game_id,
    }


def validate_extracted_folder(folder: Path | str) -> Path | None:
    """Path sys/main.dol bila folder berisi hasil ekstraksi disc."""
    folder = Path(folder)
    direct = folder / "sys" / "main.dol"
    if direct.is_file():
        return direct
    nested = folder / "assets" / "basara-heroes" / "sys" / "main.dol"
    if nested.is_file():
        return nested
    return None


# ---------------------------------------------------------------------------
# Konversi .rvz -> .iso dengan DolphinTool (perbaikan bug v1.0.0)
# ---------------------------------------------------------------------------

# Exit code Windows saat program gagal jalan karena DLL hilang
# (STATUS_DLL_NOT_FOUND, 0xC0000135): DolphinTool butuh Visual C++
# Redistributable VS 2022.
_MISSING_DLL_EXIT = -1073741515  # 0xC0000135 sebagai signed int32


def dolphin_tool_command(
    tool_exe: Path | str,
    rvz_path: Path | str,
    iso_path: Path | str,
) -> list[str]:
    """Perintah konversi .rvz -> .iso (sintaks resmi README Dolphin).

    Fungsi murni (tanpa menjalankan apa pun) agar bisa diuji unit test:
    dolphin-tool convert -i <rvz> -o <iso> -f iso
    """
    return [
        str(tool_exe), "convert",
        "-i", str(rvz_path),
        "-o", str(iso_path),
        "-f", "iso",
    ]


def find_dolphin_tool() -> Path | None:
    """DolphinTool.exe bila sudah ada: di PATH, atau di folder tools
    aplikasi (hasil unduhan installer sebelumnya)."""
    found = shutil.which("DolphinTool") or shutil.which("dolphin-tool")
    if found:
        return Path(found)
    exe = tools_dir() / "dolphin" / "Dolphin-x64" / "DolphinTool.exe"
    if exe.is_file():
        return exe
    # Lokasi lama (sebelum flatten): tools/dolphin/DolphinTool.exe
    legacy = tools_dir() / "dolphin" / "DolphinTool.exe"
    if legacy.is_file():
        return legacy
    return None


def ensure_dolphin(log_cb=None, progress_cb=None) -> Path:
    """Pastikan DolphinTool.exe tersedia (unduh paket Windows Dolphin
    resmi bila belum ada).

    Paket Windows Dolphin (2609b, .7z, ~19 MB) diunduh dari
    dl.dolphin-emu.org dan diekstrak ke folder tools aplikasi; di
    dalamnya ada Dolphin-x64/DolphinTool.exe. Dolphin di sini HANYA
    dipakai untuk mengonversi .rvz ke .iso — gamenya tetap dimainkan
    lewat port native hasil build, bukan lewat emulator.
    """
    existing = find_dolphin_tool()
    if existing is not None:
        if log_cb:
            log_cb(f"DolphinTool sudah ada: {existing}")
        return existing
    dest = downloads_dir() / DOLPHIN_ZIP
    if log_cb:
        log_cb(
            "Mengunduh Dolphin (untuk konversi .rvz ke .iso) — "
            f"~19 MB dari {DOLPHIN_URL} ..."
        )
    try:
        download_file(
            DOLPHIN_URL, dest,
            progress_cb=progress_cb, expected_size=DOLPHIN_SIZE,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Gagal mengunduh Dolphin "
            f"({exc}). Konversi .rvz tidak bisa jalan otomatis. "
            "Yang bisa dilakukan: unduh Dolphin manual dari "
            "https://dolphin-emu.org/download/ , buka Dolphin, lalu "
            "Tools > Convert File — pilih file .rvz, ubah format ke ISO, "
            "simpan, lalu pilih file .iso hasil konversi di installer ini."
        )
    dolphin_root = tools_dir() / "dolphin"
    if log_cb:
        log_cb("Mengekstrak Dolphin...")
    _extract_7z_flatten(dest, dolphin_root)
    exe = dolphin_root.joinpath(DOLPHIN_TOP_FOLDER, *DOLPHIN_TOOL_PARTS)
    if not exe.is_file():
        # Coba cari DolphinTool.exe di mana pun di dalam folder hasil ekstrak.
        found = [
            p for p in dolphin_root.rglob("*.exe")
            if p.name.lower() == "dolphintool.exe"
        ]
        if found:
            exe = found[0]
    if not exe.is_file():
        raise RuntimeError(
            "Dolphin berhasil diunduh dan diekstrak, tetapi "
            "DolphinTool.exe tidak ditemukan. Konversi .rvz tidak bisa "
            "jalan otomatis. Yang bisa dilakukan: buka Dolphin manual "
            "(https://dolphin-emu.org/download/), Tools > Convert File, "
            "pilih file .rvz, ubah format ke ISO, lalu pilih file .iso "
            "hasil konversi di installer ini."
        )
    if log_cb:
        log_cb(f"DolphinTool terpasang: {exe}")
    return exe


def convert_rvz_to_iso(
    rvz_path: Path | str,
    iso_path: Path | str | None = None,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Konversi dump .rvz ke .iso dengan DolphinTool.

    Mengembalikan path .iso hasil konversi (divalidasi game ID-nya
    RBSJ08). Bila .iso tujuan sudah ada dan valid, dipakai langsung
    (resumable — tidak mengonversi ulang).
    """
    rvz_path = Path(rvz_path)
    result = validate_game_file(rvz_path)
    if not result["valid"] or result["kind"] != "rvz":
        raise RuntimeError(
            "Konversi dibatalkan: file bukan .rvz Wii yang valid. "
            + result["detail"]
        )
    iso_path = (
        Path(iso_path) if iso_path
        else rvz_path.with_suffix(".iso")
    )
    if iso_path.is_file():
        check = validate_game_file(iso_path)
        if check["valid"] and check["kind"] == "iso":
            if log_cb:
                log_cb(
                    f"File .iso hasil konversi sudah ada: {iso_path} "
                    "(dipakai langsung, tidak mengonversi ulang)."
                )
            return iso_path
        iso_path.unlink(missing_ok=True)
    tool = ensure_dolphin(log_cb=log_cb, progress_cb=progress_cb)
    if log_cb:
        log_cb(
            f"Mengonversi {rvz_path.name} ke .iso dengan DolphinTool "
            "(bisa memakan waktu beberapa menit untuk file besar)..."
        )
    code = run_streaming(
        dolphin_tool_command(tool, rvz_path, iso_path),
        log_cb=log_cb,
    )
    if code != 0:
        if code == _MISSING_DLL_EXIT:
            raise RuntimeError(
                "DolphinTool gagal jalan: file DLL Visual C++ tidak "
                "ditemukan di PC ini. Yang harus dilakukan: pasang "
                "Visual C++ Redistributable (x64) dari "
                f"{VC_REDIST_URL} , lalu tekan MAIN lagi."
            )
        raise RuntimeError(
            f"Konversi .rvz gagal (exit {code}). Periksa log di atas. "
            "Yang bisa dilakukan: buka Dolphin manual "
            "(https://dolphin-emu.org/download/), Tools > Convert File, "
            "pilih file .rvz, ubah format ke ISO, lalu pilih file .iso "
            "hasil konversi di installer ini dan tekan MAIN lagi."
        )
    if not iso_path.is_file():
        raise RuntimeError(
            "DolphinTool selesai tanpa error, tetapi file .iso hasil "
            f"konversi tidak ditemukan di {iso_path}."
        )
    check = validate_game_file(iso_path)
    if not check["valid"] or check["kind"] != "iso":
        raise RuntimeError(
            "File .iso hasil konversi tidak valid: " + check["detail"]
        )
    if log_cb:
        log_cb(f"Konversi selesai: {iso_path}")
    return iso_path


# ---------------------------------------------------------------------------
# Ekstraksi disc dengan wit
# ---------------------------------------------------------------------------

def ensure_wit(log_cb=None, progress_cb=None) -> Path:
    """Pastikan wit.exe tersedia (unduh + ekstrak bila belum ada).

    wit dipakai tanpa instalasi: bin/wit.exe di dalam zip Cygwin.
    """
    wit_root = tools_dir() / "wit"
    exe = wit_root.joinpath(*WIT_EXE_PARTS)
    if exe.is_file():
        if log_cb:
            log_cb(f"wit sudah ada: {exe}")
        return exe
    dest = downloads_dir() / WIT_ZIP
    if log_cb:
        log_cb(f"Mengunduh wit {WIT_URL} ...")
    try:
        download_file(WIT_URL, dest, progress_cb=progress_cb)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Gagal mengunduh wit dari wit.wiimm.de "
            f"({exc}). Coba unduh manual dari "
            "https://wit.wiimm.de/download.html "
            f"({WIT_ZIP}), ekstrak, lalu letakkan wit.exe di {wit_root}."
        )
    if log_cb:
        log_cb("Mengekstrak wit...")
    _extract_zip_flatten(dest, wit_root)
    if not exe.is_file():
        raise RuntimeError(
            "wit berhasil diunduh dan diekstrak, tetapi "
            f"{'/'.join(WIT_EXE_PARTS)} tidak ditemukan di {wit_root}."
        )
    if log_cb:
        log_cb(f"wit terpasang: {exe}")
    return exe


def extract_disc(
    iso_path: Path | str,
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Ekstrak disc .iso ke assets/basara-heroes dengan wit.

    Resumable: bila sys/main.dol sudah ada di assets/basara-heroes,
    ekstraksi dilewati dan main.dol yang ada dipakai langsung.
    Mengembalikan path sys/main.dol hasil ekstraksi.
    """
    iso_path = Path(iso_path)
    source_root = Path(source_root)
    dest = source_root / "assets" / "basara-heroes"
    existing = validate_extracted_folder(dest)
    if existing is not None:
        if log_cb:
            log_cb(
                f"Disc sudah diekstrak sebelumnya: {existing} "
                "(dilewati, tidak mengekstrak ulang)."
            )
        return existing
    result = validate_game_file(iso_path)
    if not result["valid"] or result["kind"] != "iso":
        raise RuntimeError(
            "Ekstraksi dibatalkan: file game tidak valid untuk diekstrak. "
            + result["detail"]
        )
    wit = ensure_wit(log_cb=log_cb, progress_cb=progress_cb)
    if dest.exists():
        if log_cb:
            log_cb(f"Menghapus hasil ekstraksi lama: {dest}")
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if log_cb:
        log_cb(f"Mengekstrak {iso_path.name} ke {dest} (wit, mohon tunggu)...")
    code = run_streaming(
        [str(wit), "extract", str(iso_path), f"--dest={dest}"],
        log_cb=log_cb,
        cwd=source_root,
    )
    if code != 0:
        raise RuntimeError(
            f"wit extract gagal (exit {code}). Periksa log di atas — "
            "pastikan file .iso tidak rusak dan disk masih cukup."
        )
    dol = validate_extracted_folder(dest)
    if dol is None:
        raise RuntimeError(
            "wit selesai tanpa error, tetapi sys/main.dol tidak ditemukan "
            f"di {dest}. File .iso mungkin bukan dump Wii yang lengkap."
        )
    if log_cb:
        log_cb(f"Ekstraksi selesai: {dol}")
    settings = load_settings()
    settings["game_dir"] = str(dest)
    save_settings(settings)
    return dol


def use_extracted_folder(folder: Path | str, source_root: Path | str) -> Path:
    """Pakai folder hasil ekstraksi manual sebagai assets/basara-heroes.

    Menyalin (bila beda lokasi) atau menandai langsung bila foldernya
    memang sudah <source>/assets/basara-heroes. Mengembalikan main.dol.
    """
    folder = Path(folder)
    source_root = Path(source_root)
    dol = validate_extracted_folder(folder)
    if dol is None:
        raise RuntimeError(
            f"Folder {folder} tidak berisi sys/main.dol."
        )
    dest = source_root / "assets" / "basara-heroes"
    if dol.parent.parent.resolve() == dest.resolve():
        return dol
    if dest.exists():
        shutil.rmtree(dest)
    # Folder yang dipilih pengguna adalah folder hasil ekstraksi itu
    # sendiri (berisi sys/main.dol) — salin isinya ke assets/basara-heroes.
    src = dol.parent.parent
    if (folder / "assets" / "basara-heroes").is_dir():
        src = folder / "assets" / "basara-heroes"
    shutil.copytree(src, dest)
    dol = validate_extracted_folder(dest)
    if dol is None:
        raise RuntimeError(
            "Penyalinan folder hasil ekstraksi gagal — sys/main.dol "
            f"tidak ditemukan di {dest}."
        )
    settings = load_settings()
    settings["game_dir"] = str(dest)
    save_settings(settings)
    return dol


def prepare_game_file(
    game_path: Path | str,
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> Path:
    """Siapkan file game untuk build: validasi, lalu jadikan
    assets/basara-heroes/sys/main.dol tersedia.

    - folder hasil ekstraksi -> dipakai langsung (use_extracted_folder).
    - .iso -> diekstrak dengan wit (dilewati bila main.dol sudah ada).
    - .rvz -> dikonversi otomatis ke .iso (DolphinTool), lalu diekstrak.

    Mengembalikan path sys/main.dol.
    """
    game_path = Path(game_path)
    source_root = Path(source_root)
    result = validate_game_file(game_path)
    if not result["valid"]:
        raise RuntimeError(
            "File game tidak valid — " + " ".join(result["issues"])
        )
    kind = result["kind"]
    if kind == "folder":
        if log_cb:
            log_cb("Memakai folder hasil ekstraksi disc...")
        return use_extracted_folder(game_path, source_root)
    if kind == "rvz":
        if log_cb:
            log_cb("File game .rvz — dikonversi dulu ke .iso...")
        iso_path = convert_rvz_to_iso(
            game_path, log_cb=log_cb, progress_cb=progress_cb
        )
        return extract_disc(
            iso_path, source_root, log_cb=log_cb, progress_cb=progress_cb
        )
    if kind == "iso":
        return extract_disc(
            game_path, source_root, log_cb=log_cb, progress_cb=progress_cb
        )
    raise RuntimeError(f"Jenis file game tidak dikenal: {kind}.")


# ---------------------------------------------------------------------------
# Terjemah + build Windows
# ---------------------------------------------------------------------------

def translate(
    source_root: Path | str,
    log_cb=None,
    progress_cb=None,
) -> None:
    """Jalankan tools/b-translate.ps1 (PowerPC -> C++, ke generated/).

    Membangun translator dulu bila dll-nya belum ada. Membuat folder
    generated/ + generated/b/ dulu (script menulis log ke sana).
    """
    source_root = Path(source_root)
    ensure_generated_dirs(source_root)
    build_translator(source_root, log_cb=log_cb, progress_cb=progress_cb)
    script = source_root / "tools" / "b-translate.ps1"
    if not script.is_file():
        raise RuntimeError(f"Script tidak ditemukan: {script}")
    if log_cb:
        log_cb("Menerjemahkan kode PowerPC ke C++ (b-translate.ps1)...")
        log_cb("Langkah ini bisa memakan waktu beberapa menit.")
    code = run_powershell(script, log_cb=log_cb, cwd=source_root)
    if code != 0:
        raise RuntimeError(
            f"b-translate.ps1 gagal (exit {code}). Periksa log di atas — "
            "biasanya karena main.dol belum diekstrak atau .NET 8 bermasalah. "
            "Tekan MAIN lagi untuk mencoba dari langkah ini."
        )
    settings = load_settings()
    settings["translated"] = True
    save_settings(settings)
    if log_cb:
        log_cb("Terjemahan selesai.")


def configure_windows(source_root: Path | str, log_cb=None) -> None:
    """Jalankan tools/b-win.ps1 -Mode configure (sekali saja)."""
    source_root = Path(source_root)
    ensure_generated_dirs(source_root)
    script = source_root / "tools" / "b-win.ps1"
    if not script.is_file():
        raise RuntimeError(f"Script tidak ditemukan: {script}")
    if log_cb:
        log_cb("Mengonfigurasi build Windows (b-win.ps1 -Mode configure)...")
    code = run_powershell(
        script, ["-Mode", "configure"], log_cb=log_cb, cwd=source_root
    )
    if code != 0:
        raise RuntimeError(
            f"b-win.ps1 -Mode configure gagal (exit {code}). Periksa "
            "generated/b/win-configure.log di folder source. Tekan MAIN "
            "lagi untuk mencoba dari langkah ini."
        )
    if log_cb:
        log_cb("Konfigurasi build Windows selesai.")


def build_windows(source_root: Path | str, log_cb=None) -> Path:
    """Jalankan tools/b-win.ps1 -Mode build. Mengembalikan WiiCompiled.exe."""
    source_root = Path(source_root)
    ensure_generated_dirs(source_root)
    script = source_root / "tools" / "b-win.ps1"
    if not script.is_file():
        raise RuntimeError(f"Script tidak ditemukan: {script}")
    build_dir = source_root / "generated" / "win-build"
    if not (build_dir / "build.ninja").is_file():
        configure_windows(source_root, log_cb=log_cb)
    if log_cb:
        log_cb("Membangun game untuk Windows (b-win.ps1 -Mode build)...")
        log_cb(
            "Build C++ penuh — bisa memakan waktu PULUHAN MENIT tergantung "
            "PC. Jangan tutup aplikasi; progres muncul di log di bawah."
        )
    code = run_powershell(
        script, ["-Mode", "build"], log_cb=log_cb, cwd=source_root
    )
    if code != 0:
        raise RuntimeError(
            f"b-win.ps1 -Mode build gagal (exit {code}). Periksa "
            "generated/b/win-build.log di folder source. Tekan MAIN lagi "
            "untuk mencoba dari langkah ini."
        )
    exe = find_built_exe(source_root)
    if exe is None:
        raise RuntimeError(
            "Build selesai tanpa error, tetapi WiiCompiled.exe tidak "
            f"ditemukan di {build_dir}."
        )
    settings = load_settings()
    settings["built_exe"] = str(exe)
    save_settings(settings)
    if log_cb:
        log_cb(f"Build Windows selesai: {exe}")
    return exe


def find_built_exe(source_root: Path | str) -> Path | None:
    """Cari WiiCompiled.exe hasil build Windows."""
    root = Path(source_root)
    if not root.is_dir():
        return None
    candidate = root.joinpath(*BUILT_EXE_PARTS)
    if candidate.is_file():
        return candidate
    target = BUILT_EXE_PARTS[-1].lower()
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == target:
            return path
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def launch_game(source_root: Path | str) -> tuple[bool, str]:
    """Jalankan game hasil build (b-win.ps1 -Mode run -Seconds 0).

    -Seconds 0 = jalan sampai jendela game ditutup (bukan 30 detik).
    Dijalankan lepas (detached) agar installer tetap responsif.
    """
    source_root = Path(source_root)
    exe = find_built_exe(source_root)
    if exe is None:
        return False, (
            "Game hasil build belum ada (WiiCompiled.exe tidak ditemukan). "
            "Tekan tombol MAIN — installer akan membangun gamenya dulu."
        )
    script = source_root / "tools" / "b-win.ps1"
    if not script.is_file():
        return False, f"Script tidak ditemukan: {script}"
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(script), "-Mode", "run", "-Seconds", "0"],
            cwd=str(source_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"Tidak bisa menjalankan game: {exc}"
    return True, (
        "Sengoku Basara 2 Heroes dibuka. Menu dalam game mendukung Bahasa "
        "Inggris dan Bahasa Indonesia. Log game tersimpan di UserData di "
        "folder build."
    )


def open_folder(path: Path | str) -> tuple[bool, str]:
    """Buka folder di File Explorer (Windows) / file manager lainnya."""
    import platform

    target = Path(path)
    if not target.is_dir():
        return False, f"Folder tidak ditemukan: {target}"
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["explorer", str(target)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as exc:
        return False, f"Tidak bisa membuka folder: {exc}"
    return True, f"Membuka folder: {target}"
