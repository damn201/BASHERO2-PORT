"""Unit test helper baru v1.1.0 (bisa diuji tanpa Windows).

Jalankan dari root proyek:
  python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from basara2_installer.port import (  # noqa: E402
    dolphin_tool_command,
    ensure_generated_dirs,
    find_dolphin_tool,
    sdk_dotnet_exe,
)
from basara2_installer.syscheck import parse_dotnet_version  # noqa: E402


class TestParseDotnetVersion(unittest.TestCase):
    def test_sdk_8(self):
        self.assertEqual(parse_dotnet_version("8.0.428"), (8, 0, 428))

    def test_sdk_9(self):
        self.assertEqual(parse_dotnet_version("9.0.100"), (9, 0, 100))

    def test_output_dengan_teks_lain(self):
        # `dotnet --version` kadang mencetak baris lain di sekitarnya.
        self.assertEqual(
            parse_dotnet_version("Microsoft .NET SDK\n8.0.204\n"),
            (8, 0, 204),
        )

    def test_kosong(self):
        self.assertIsNone(parse_dotnet_version(""))

    def test_tanpa_angka(self):
        self.assertIsNone(parse_dotnet_version("bukan versi"))

    def test_hanya_dua_angka(self):
        self.assertIsNone(parse_dotnet_version("8.0"))


class TestDolphinToolCommand(unittest.TestCase):
    def test_perintah_konversi(self):
        cmd = dolphin_tool_command(
            "DolphinTool.exe", "game.rvz", "game.iso"
        )
        self.assertEqual(cmd, [
            "DolphinTool.exe", "convert",
            "-i", "game.rvz", "-o", "game.iso", "-f", "iso",
        ])

    def test_path_dengan_spasi(self):
        cmd = dolphin_tool_command(
            r"C:\Tools\DolphinTool.exe",
            r"C:\Games\Basara 2.rvz",
            r"C:\Games\Basara 2.iso",
        )
        self.assertEqual(cmd[0], r"C:\Tools\DolphinTool.exe")
        self.assertIn(r"C:\Games\Basara 2.rvz", cmd)
        self.assertIn(r"C:\Games\Basara 2.iso", cmd)
        self.assertIn("-f", cmd)
        self.assertEqual(cmd[cmd.index("-f") + 1], "iso")


class TestEnsureGeneratedDirs(unittest.TestCase):
    def test_membuat_kedua_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen, logs = ensure_generated_dirs(Path(tmp))
            self.assertTrue(gen.is_dir())
            self.assertTrue(logs.is_dir())
            self.assertEqual(gen.name, "generated")
            self.assertEqual(logs.name, "b")

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_generated_dirs(Path(tmp))
            gen, logs = ensure_generated_dirs(Path(tmp))
            self.assertTrue(gen.is_dir())
            self.assertTrue(logs.is_dir())


class TestSdkDotnetExe(unittest.TestCase):
    def test_sdk_lokal_ditemukan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "third_party" / "dotnet-sdk" / "dotnet.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"fake")
            self.assertEqual(sdk_dotnet_exe(root), exe)

    def test_sdk_lokal_tidak_ada(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sdk_dotnet_exe(Path(tmp)))


class TestFindDolphinTool(unittest.TestCase):
    def test_dolphin_di_tools_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = (
                Path(tmp) / "dolphin" / "Dolphin-x64" / "DolphinTool.exe"
            )
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"fake")
            with mock.patch(
                "basara2_installer.port.tools_dir",
                return_value=Path(tmp),
            ):
                with mock.patch(
                    "basara2_installer.port.shutil.which",
                    return_value=None,
                ):
                    self.assertEqual(find_dolphin_tool(), exe)

    def test_tidak_ada(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch(
                "basara2_installer.port.tools_dir",
                return_value=Path(tmp),
            ):
                with mock.patch(
                    "basara2_installer.port.shutil.which",
                    return_value=None,
                ):
                    self.assertIsNone(find_dolphin_tool())


if __name__ == "__main__":
    unittest.main()
