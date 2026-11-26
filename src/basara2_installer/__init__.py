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
unduh source -> validasi + konversi .rvz ke .iso otomatis (DolphinTool)
-> ekstrak disc (wit) -> siapkan toolchain (CMake/Ninja/deps + llvm-mingw +
.NET 8 runtime lokal) -> pastikan .NET 8 SDK (diunduh otomatis bila
tidak ada) -> terjemahkan (b-translate) -> bangun (b-win configure +
build) -> main (WiiCompiled.exe).

v1.1.0: UI SATU LAYAR — pilih file game, tekan tombol besar MAIN,
semua langkah di atas jalan otomatis dan resumable (langkah yang sudah
selesai dilewati). Perbaikan dari laporan pengguna v1.0.0: .rvz tidak
lagi jalan buntu, .NET 8 SDK diunduh otomatis, folder generated/
dibuat dulu, toolchain diperbaiki per-bagian bila script gagal.

v1.1.2: (a) alur MAIN dibalik — validasi + konversi .rvz + ekstrak
disc sekarang jalan SEBELUM toolchain (mengikuti urutan README port:
ekstrak disc dulu, baru setup toolchain), supaya file game yang
bermasalah ketahuan dalam hitungan menit dan perbaikan validasi .rvz
v1.1.1 benar-benar tercapai sebelum toolchain yang lama; (b) pre-flight
baru sebelum konversi .rvz: cek ruang kosong di drive file game
(~5 GB untuk .iso hasil konversi) dan cek Visual C++ Redistributable
yang dibutuhkan DolphinTool — keduanya gagal cepat dengan pesan jelas,
bukan di tengah konversi; (c) log kini juga disimpan otomatis ke file
basara2-installer.log di folder data aplikasi, jadi tetap bisa dikirim
walau aplikasi sudah ditutup (sebelumnya log hanya ada di layar).

Aplikasi ini TIDAK menyertakan file game apa pun. Pengguna wajib memakai
dump Wii Sengoku Basara 2 Heroes NTSC-J (RBSJ08) miliknya sendiri
(.iso atau .rvz).
"""

__version__ = "1.1.2"
__port_repo__ = "PotatoRecomp/B2HWii-Android"
__port_tag__ = "v1.2.1-hotfix"
