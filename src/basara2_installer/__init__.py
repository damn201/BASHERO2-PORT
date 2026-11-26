"""Basara 2 Heroes PC Installer — port native Sengoku Basara 2 Heroes
(versi Wii) untuk Windows. BUKAN emulator.

Port yang dipakai: PotatoRecomp/B2HWii-Android v1.2.1-hotfix (GPLv3).
Kode PowerPC game diterjemahkan ke C++ (static recompilation, WiiCompiled)
lalu dibangun menjadi aplikasi Windows native — tidak ada yang diemulasi.
Port ini HANYA untuk versi Wii (NTSC-J, RBSJ08). Versi PS2 (SLPM-66848)
tidak punya port native; hanya bisa lewat emulator (PCSX2), yang tidak
dipakai di sini.

Tidak ada rilis Windows jadi di repo port (hanya APK Android), jadi
installer ini mengotomasi build dari source di PC pengguna:
unduh source -> siapkan toolchain (CMake/Ninja/deps + llvm-mingw +
.NET 8 runtime lokal) -> pastikan .NET 8 SDK (diunduh otomatis bila
tidak ada) -> konversi .rvz ke .iso otomatis (DolphinTool) -> ekstrak
disc (wit) -> terjemahkan (b-translate) -> bangun (b-win configure +
build) -> main (WiiCompiled.exe).

v1.1.0: UI SATU LAYAR — pilih file game, tekan tombol besar MAIN,
semua langkah di atas jalan otomatis dan resumable (langkah yang sudah
selesai dilewati). Perbaikan dari laporan pengguna v1.0.0: .rvz tidak
lagi jalan buntu, .NET 8 SDK diunduh otomatis, folder generated/
dibuat dulu, toolchain diperbaiki per-bagian bila script gagal.

v1.1.1: perbaikan cek magic RVZ — file .rvz asli sempat ditolak karena
installer memeriksa ASCII "RVZ1", padahal magic RVZ Dolphin adalah
"RVZ" + byte 0x01. File .rvz asli sekarang diterima.

Aplikasi ini TIDAK menyertakan file game apa pun. Pengguna wajib memakai
dump Wii Sengoku Basara 2 Heroes NTSC-J (RBSJ08) miliknya sendiri
(.iso atau .rvz).
"""

__version__ = "1.1.1"
__port_repo__ = "PotatoRecomp/B2HWii-Android"
__port_tag__ = "v1.2.1-hotfix"
