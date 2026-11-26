"""Unit test pre-flight v1.1.2 (cek drive file game + VC++ Redistributable).

Jalankan dari root proyek:
  python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from basara2_installer.config import RVZ_CONVERT_FREE_BYTES  # noqa: E402
from basara2_installer.port import (  # noqa: E402
    check_game_drive_space,
    free_space_bytes,
    vcpp_redist_installed,
)


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_free_space_tmp_terbaca(self):
        free = free_space_bytes(self.root)
        self.assertIsInstance(free, int)
        self.assertGreater(free, 0)

    def test_free_space_path_tidak_ada_none(self):
        self.assertIsNone(free_space_bytes(self.root / "tidak-ada"))

    def test_vcpp_bukan_windows_none(self):
        # Di Linux (mesin build ini) registry Windows tidak ada —
        # hasilnya harus None (tidak dapat diperiksa), bukan False.
        if sys.platform != "win32":
            self.assertIsNone(vcpp_redist_installed())

    def test_rvz_butuh_5gb_di_drive_game(self):
        rvz = self.root / "basara2heroes.rvz"
        rvz.write_bytes(b"RVZ\x01" + b"\x00" * 1024)
        hasil = check_game_drive_space(rvz)
        self.assertEqual(
            hasil["needed_bytes"], RVZ_CONVERT_FREE_BYTES
        )
        self.assertEqual(hasil["needed_bytes"], 5 * 1024 ** 3)
        # Ruang kosong di mesin ini bisa di bawah 5 GB (mis. /tmp VM
        # yang kecil) — yang diuji adalah konsistensi hasilnya, bukan
        # asumsi ruang kosong mesin build.
        self.assertEqual(hasil["ok"], hasil["free_bytes"] >= RVZ_CONVERT_FREE_BYTES)
        self.assertIsInstance(hasil["free_bytes"], int)
        self.assertIn("GB", hasil["detail"])

    def test_iso_tidak_butuh_ruang_di_drive_game(self):
        iso = self.root / "basara2heroes.iso"
        iso.write_bytes(b"RBSJ08" + b"\x00" * 1024)
        hasil = check_game_drive_space(iso)
        self.assertEqual(hasil["needed_bytes"], 0)
        self.assertTrue(hasil["ok"])

    def test_folder_tidak_butuh_ruang_di_drive_game(self):
        folder = self.root / "basara-heroes"
        (folder / "sys").mkdir(parents=True)
        (folder / "sys" / "main.dol").write_bytes(b"\x00" * 64)
        hasil = check_game_drive_space(folder)
        self.assertEqual(hasil["needed_bytes"], 0)
        self.assertTrue(hasil["ok"])


if __name__ == "__main__":
    unittest.main()
