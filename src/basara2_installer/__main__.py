"""Entry point Basara 2 Heroes PC Installer.

Penggunaan:
  python -m basara2_installer            # buka GUI
  python -m basara2_installer --version  # tampilkan versi
  python -m basara2_installer --self-test  # cek non-GUI (untuk pengujian)
"""

import argparse
import sys
import tempfile
from pathlib import Path


def self_test() -> int:
    """Tes mandiri tanpa GUI; kembalikan 0 bila semua lolos."""
    from basara2_installer import __version__
    from basara2_installer.config import (
        GAME_ID,
        PORT_ANDROID_ASSET,
        PORT_TAG,
        app_dir,
        platform_id,
    )
    from basara2_installer.port import (
        release_info,
        validate_extracted_folder,
        validate_game_file,
    )
    from basara2_installer.syscheck import run_checks, summarize

    failures = []

    print(f"Basara 2 Heroes PC Installer v{__version__} — self-test")
    print(f"platform: {platform_id()} | python: {sys.version.split()[0]}")

    try:
        folder = app_dir()
        print(f"app_dir: {folder} (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"app_dir: {exc}")

    try:
        info = release_info()
        assert info["tag"] == PORT_TAG, info
        assert PORT_ANDROID_ASSET in info["asset_names"], info
        assert not any(
            name.lower().endswith((".exe", ".zip"))
            for name in info["asset_names"]
        ), info
        print(
            f"rilis port: {info['tag']} | aset: {info['asset_names']} "
            f"(hanya APK Android — tidak ada build Windows jadi) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        # GitHub API sering rate-limit 403 untuk request tanpa login
        # (terutama dari IP egress bersama) — itu BUKAN kegagalan
        # installer: alur normal v1.1.0 tidak pernah memakai API ini
        # (unduhan memakai URL hardcoded di config).
        import urllib.error

        if isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
            print(
                "rilis port: tidak dapat diperiksa (GitHub API rate-limit "
                "403) — bukan kegagalan; alur normal tidak memakai API "
                "GitHub (ok)"
            )
        else:
            failures.append(f"rilis port (GitHub API): {exc}")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            iso = root / "basara2heroes.iso"
            iso.write_bytes(GAME_ID.encode("ascii") + b"\x00" * 1024)
            hasil = validate_game_file(iso)
            assert hasil["valid"] is True, hasil
            assert hasil["kind"] == "iso", hasil
            assert hasil["game_id"] == GAME_ID, hasil
            print("validasi file game: .iso dengan header RBSJ08 lolos (ok)")

            iso_salah = root / "game-lain.iso"
            iso_salah.write_bytes(b"RBXJ01" + b"\x00" * 1024)
            hasil = validate_game_file(iso_salah)
            assert hasil["valid"] is False, hasil
            assert "RBSJ08" in " ".join(hasil["issues"]), hasil
            print("validasi file game: .iso dengan game ID lain gagal (ok)")

            hasil = validate_game_file(root / "tidak-ada.iso")
            assert hasil["valid"] is False, hasil
            print("validasi file game: file tidak ada gagal (ok)")

            rvz = root / "basara2heroes.rvz"
            rvz.write_bytes(b"RVZ\x01" + b"\x00" * 1024)
            hasil = validate_game_file(rvz)
            assert hasil["valid"] is True, hasil
            assert hasil["kind"] == "rvz", hasil
            assert hasil["warnings"], hasil
            print("validasi file game: .rvz dengan magic RVZ lolos (ok)")

            rvz_rusak = root / "rusak.rvz"
            rvz_rusak.write_bytes(b"XXXX" + b"\x00" * 1024)
            hasil = validate_game_file(rvz_rusak)
            assert hasil["valid"] is False, hasil
            print("validasi file game: .rvz tanpa magic RVZ gagal (ok)")

            folder = root / "basara-heroes"
            (folder / "sys").mkdir(parents=True)
            (folder / "sys" / "main.dol").write_bytes(b"\x00" * 64)
            hasil = validate_game_file(folder)
            assert hasil["valid"] is True, hasil
            assert hasil["kind"] == "folder", hasil
            assert validate_extracted_folder(folder) is not None
            print("validasi file game: folder dengan sys/main.dol lolos (ok)")

            folder_kosong = root / "kosong"
            folder_kosong.mkdir()
            hasil = validate_game_file(folder_kosong)
            assert hasil["valid"] is False, hasil
            assert validate_extracted_folder(folder_kosong) is None
            print("validasi file game: folder tanpa main.dol gagal (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"validasi file game: {exc}")

    try:
        from basara2_installer.port import (
            dolphin_tool_command,
            ensure_generated_dirs,
        )
        from basara2_installer.syscheck import parse_dotnet_version

        assert parse_dotnet_version("8.0.428") == (8, 0, 428)
        assert parse_dotnet_version("9.0.100") == (9, 0, 100)
        assert parse_dotnet_version("") is None
        assert parse_dotnet_version("bukan versi") is None
        print("helper baru: parse_dotnet_version (8.0.428 / 9.0.100 / "
              "kosong / tanpa angka) (ok)")

        cmd = dolphin_tool_command("DolphinTool.exe", "game.rvz", "game.iso")
        assert cmd == [
            "DolphinTool.exe", "convert",
            "-i", "game.rvz", "-o", "game.iso", "-f", "iso",
        ], cmd
        print("helper baru: dolphin_tool_command (convert -i/-o/-f iso) (ok)")

        with tempfile.TemporaryDirectory() as tmp:
            gen, logs = ensure_generated_dirs(Path(tmp))
            assert gen.is_dir() and logs.is_dir()
            assert gen.name == "generated" and logs.name == "b"
        print("helper baru: ensure_generated_dirs (generated/ + "
              "generated/b/) (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"helper baru v1.1.0: {exc}")

    try:
        # py7zr dipakai untuk mengekstrak paket Dolphin (.7z memakai
        # filter BCJ + LZMA2, jadi modul "bcj" WAJIB ikut terbundel).
        # Di Windows (termasuk .exe hasil build) ini dicek ketat; di
        # Linux hanya peringatan, karena jalur ekstraksi Dolphin hanya
        # berjalan di Windows dan modulnya belum tentu terpasang di
        # mesin Linux ini.
        import bcj  # noqa: F401
        import py7zr

        print(f"ekstraksi .7z: py7zr {py7zr.__version__} + bcj "
              "tersedia (ok)")
    except Exception as exc:  # noqa: BLE001
        if sys.platform == "win32":
            failures.append(f"ekstraksi .7z (py7zr/bcj): {exc}")
        else:
            print(f"ekstraksi .7z: tidak dapat diperiksa di sini "
                  f"({exc}) — bukan kegagalan; dicek ketat di Windows (ok)")

    try:
        checks = run_checks()
        ok, gagal, tidak_diketahui = summarize(checks)
        for check in checks:
            print(f"  syscheck [{check['status']}] {check['name']}: {check['detail']}")
        print(
            f"syscheck: {len(checks)} cek jalan tanpa crash "
            f"({ok} lolos, {gagal} gagal, {tidak_diketahui} tidak diketahui) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"syscheck: {exc}")

    try:
        import tkinter  # noqa: F401
        print("tkinter: ok")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"tkinter: {exc}")

    if failures:
        print("\nSELF-TEST GAGAL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nSELF-TEST OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="basara2_installer",
        description="Basara 2 Heroes PC Installer — port native Sengoku "
                    "Basara 2 Heroes (Wii) untuk Windows",
    )
    parser.add_argument("--version", action="store_true", help="tampilkan versi")
    parser.add_argument("--self-test", action="store_true", help="tes mandiri tanpa GUI")
    args = parser.parse_args(argv)
    if args.version:
        from basara2_installer import __version__
        print(f"Basara 2 Heroes PC Installer {__version__}")
        return 0
    if args.self_test:
        return self_test()
    from basara2_installer.app import run
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
