"""Unit test validasi file game (dump Wii Sengoku Basara 2 Heroes RBSJ08).

Jalankan dari root proyek:
  python -m unittest discover -s tests -v
"""

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from basara2_installer.port import (  # noqa: E402
    validate_extracted_folder,
    validate_game_file,
)


class TestValidateGameFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_iso(self, name, game_id=b"RBSJ08"):
        path = self.root / name
        path.write_bytes(game_id + b"\x00" * 1024)
        return path

    def test_iso_rbsj08_lolos(self):
        iso = self._fake_iso("basara2heroes.iso")
        hasil = validate_game_file(iso)
        self.assertTrue(hasil["valid"])
        self.assertEqual(hasil["kind"], "iso")
        self.assertEqual(hasil["game_id"], "RBSJ08")
        self.assertFalse(hasil["issues"])

    def test_iso_game_id_lain_gagal(self):
        iso = self._fake_iso("game-lain.iso", game_id=b"RBXJ01")
        hasil = validate_game_file(iso)
        self.assertFalse(hasil["valid"])
        self.assertEqual(hasil["kind"], "iso")
        self.assertIn("RBSJ08", " ".join(hasil["issues"]))
        self.assertIn("PS2", " ".join(hasil["issues"]))

    def test_file_tidak_ada_gagal(self):
        hasil = validate_game_file(self.root / "tidak-ada.iso")
        self.assertFalse(hasil["valid"])
        self.assertTrue(hasil["issues"])

    def test_rvz_magic_rvz_lolos(self):
        rvz = self.root / "basara2heroes.rvz"
        rvz.write_bytes(b"RVZ\x01" + b"\x00" * 1024)
        hasil = validate_game_file(rvz)
        self.assertTrue(hasil["valid"])
        self.assertEqual(hasil["kind"], "rvz")
        self.assertTrue(hasil["warnings"])
        self.assertIn("Dolphin", " ".join(hasil["warnings"]))

    def test_rvz_header_asli_ed_lolos(self):
        # Regresi v1.1.1: file .rvz asli Ed diawali 16 byte ini
        # (52 56 5A 01 01 00 00 00 00 03 00 00 00 00 00 DC) — RVZ v1
        # valid (magic "RVZ" + byte 0x01, version u32 LE = 1).
        # Dulu ditolak karena installer memeriksa ASCII "RVZ1".
        rvz = self.root / "basara2heroes.rvz"
        rvz.write_bytes(
            bytes.fromhex("52 56 5A 01 01 00 00 00 00 03 00 00 00 00 00 DC")
            + b"\x00" * 1024
        )
        hasil = validate_game_file(rvz)
        self.assertTrue(hasil["valid"])
        self.assertEqual(hasil["kind"], "rvz")

    def test_rvz_ascii_rvz1_gagal(self):
        # Regresi v1.1.1: ASCII "RVZ1" (52 56 5A 31) BUKAN magic RVZ
        # asli — file seperti ini harus DITOLAK.
        rvz = self.root / "palsu.rvz"
        rvz.write_bytes(b"RVZ1" + b"\x00" * 1024)
        hasil = validate_game_file(rvz)
        self.assertFalse(hasil["valid"])
        self.assertEqual(hasil["kind"], "rvz")

    def test_rvz_tanpa_magic_gagal(self):
        rvz = self.root / "rusak.rvz"
        rvz.write_bytes(b"XXXX" + b"\x00" * 1024)
        hasil = validate_game_file(rvz)
        self.assertFalse(hasil["valid"])
        self.assertEqual(hasil["kind"], "rvz")

    def test_folder_dengan_main_dol_lolos(self):
        folder = self.root / "basara-heroes"
        (folder / "sys").mkdir(parents=True)
        (folder / "sys" / "main.dol").write_bytes(b"\x00" * 64)
        hasil = validate_game_file(folder)
        self.assertTrue(hasil["valid"])
        self.assertEqual(hasil["kind"], "folder")
        self.assertIsNotNone(validate_extracted_folder(folder))

    def test_folder_tanpa_main_dol_gagal(self):
        folder = self.root / "kosong"
        folder.mkdir()
        hasil = validate_game_file(folder)
        self.assertFalse(hasil["valid"])
        self.assertIsNone(validate_extracted_folder(folder))

    def test_format_lain_gagal(self):
        lain = self.root / "game.wbfs"
        lain.write_bytes(b"RBSJ08" + b"\x00" * 1024)
        hasil = validate_game_file(lain)
        self.assertFalse(hasil["valid"])


if __name__ == "__main__":
    unittest.main()
