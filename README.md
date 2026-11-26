# Basara 2 Heroes PC Installer — v1.1.2

Installer/launcher Windows untuk memainkan **Sengoku Basara 2 Heroes
(versi Wii) secara native di PC** — **BUKAN emulator**.

Aplikasi ini membangun port native open-source **PotatoRecomp/B2HWii-Android**
([PotatoRecomp/B2HWii-Android](https://github.com/PotatoRecomp/B2HWii-Android),
v1.2.1-hotfix, lisensi GPLv3) dari source di PC kamu. Caranya SIMPLE:
**pilih file game, tekan tombol besar ▶ MAIN, lalu main.** Semua langkah
(cek PC, unduh source, konversi .rvz, ekstrak disc, siapkan toolchain,
terjemahkan, bangun Windows) jalan otomatis dan berurutan — dan bila ada
langkah gagal, tekan MAIN lagi untuk melanjutkan dari langkah itu
(langkah yang sudah selesai tidak diulang).

## Yang diperbaiki di v1.1.2

v1.1.1 memperbaiki validasi .rvz, tetapi v1.1.1 masih gagal di PC pengguna
tanpa log yang bisa dibaca. v1.1.2 memperbaiki tiga hal yang ditemukan
dari pemeriksaan kode setelah laporan itu:

1. **Urutan MAIN dibalik** — validasi + konversi .rvz + ekstrak disc
   sekarang jalan SEBELUM toolchain (~500 MB), mengikuti urutan README
   port (ekstrak disc dulu, baru setup toolchain). File game yang
   bermasalah ketahuan dalam hitungan menit, dan perbaikan .rvz v1.1.1
   benar-benar tercapai sebelum toolchain yang lama.
2. **Pre-flight sebelum konversi .rvz** — installer memeriksa ruang
   kosong di drive file game (~5 GB untuk .iso hasil konversi, yang
   ditulis di folder yang sama dengan file .rvz) dan Visual C++
   Redistributable yang dibutuhkan DolphinTool. Keduanya gagal cepat
   dengan pesan jelas, bukan di tengah konversi.
3. **Log disimpan otomatis ke file**
   `%APPDATA%\Basara2HeroesPCInstaller\basara2-installer.log`, jadi
   tetap bisa dikirim walau aplikasi sudah ditutup (sebelumnya log
   hanya ada di layar). Tombol **Buka Folder Log** membuka folder itu.

## Yang diperbaiki di v1.1.1

v1.1.1 memperbaiki cek RVZ sehingga file RVZ asli diterima: installer
sempat memeriksa magic ASCII `RVZ1`, padahal magic format RVZ Dolphin
yang sebenarnya adalah `RVZ` + byte versi `0x01` (file asli diawali
`52 56 5A 01`). Akibatnya semua file `.rvz` asli ditolak sebagai "bukan
file game" — sekarang sudah diterima dan dikonversi otomatis ke `.iso`
seperti biasa.

## Yang diperbaiki di v1.1.0

v1.0.0 dilaporkan tidak bisa menginstall game (mencoba .iso maupun .rvz
tetap gagal). Penyebabnya sudah diperbaiki:

1. **.rvz jalan buntu** — v1.0.0 menerima .rvz di validasi tetapi
   menolaknya saat ekstraksi. v1.1.0 mengonversi .rvz ke .iso SENDIRI
   dengan DolphinTool.exe (dari paket Windows Dolphin resmi) sebelum
   diekstrak. Bila konversi gagal, log menulis error persisnya +
   instruksi manual (Dolphin > Tools > Convert File).
2. **.NET 8 SDK jadi penghalang** — v1.0.0 butuh SDK terpasang di PC
   tetapi hanya mengunduh runtime. v1.1.0 mengunduh .NET 8 SDK
   otomatis (~272 MB) ke `third_party/dotnet-sdk` bila PC tidak punya
   SDK 8.x, lalu memakai dotnet.exe dari sana untuk `dotnet build`.
3. **Folder log belum tentu ada** — source port tidak berisi folder
   `generated/`, tetapi script repo menulis log ke `generated/b/`.
   v1.1.0 membuat folder `generated/` dan `generated/b/` dulu sebelum
   menjalankan script build.
4. **Toolchain rapuh** — v1.0.0 berhenti bila setup-android.ps1 gagal
   di tengah. v1.1.0 memeriksa tiap bagian (cmake, ninja, deps,
   llvm-mingw, dotnet) satu per satu dan mengunduh langsung bagian
   yang hilang; kegagalan langkah NDK (Android) tetap ditolerir.
5. **UI 6 tab terlalu rumit** — v1.1.0 hanya SATU LAYAR: pilih file
   game, pilih folder install, tekan MAIN. Tidak ada lagi tab Cek
   Sistem / Unduh Source / Game / Build yang terpisah.

## Penjelasan jujur: kenapa ini bisa native?

Kode game **Wii tidak bisa jalan native di PC begitu saja**. Wii memakai
CPU PowerPC yang arsitekturnya berbeda total dari PC x86-64, sehingga
game Wii biasanya hanya bisa dimainkan lewat emulator (mis. Dolphin).

Yang dilakukan port ini adalah **static recompilation** (WiiCompiled):
kode PowerPC di `main.dol` diterjemahkan ke C++ di depan (ahead of time)
lalu dikompilasi menjadi aplikasi Windows native, bersama runtime yang
menggantikan system software Wii dan renderer GX di Vulkan. Tidak ada
yang diemulasi saat game berjalan.

Catatan: Dolphin di sini HANYA dipakai sebagai alat konversi .rvz ke
.iso (DolphinTool) — gamenya sendiri dimainkan lewat port native hasil
build, bukan lewat emulator.

## PENTING: versi Wii, bukan PS2

Port ini **hanya untuk versi Wii (NTSC-J, game ID `RBSJ08`)**.
Gamenya sama dengan versi PS2 (Capcom, rilis 29 November 2007 di PS2 dan
Wii), tetapi **versi PS2 (SLPM-66848) TIDAK punya port native** — hanya
bisa lewat emulator (PCSX2), yang tidak dipakai di sini. Installer ini
menolak file yang game ID-nya bukan `RBSJ08`.

## Kenapa build dari source (bukan unduh jadi)?

Rilis port ini **tidak menyediakan build Windows jadi** — keempat rilis
(v1.0, v1.1, v1.2, v1.2.1-hotfix) hanya berisi APK Android (82,5 MB).
Repo port juga tidak punya GitHub Actions. Jadi satu-satunya cara
memainkan versi Windows adalah mengompilasi dari source di PC sendiri —
dan itulah yang diotomasi aplikasi ini. Build penuh bisa memakan waktu
**puluhan menit** tergantung PC, dan mengunduh toolchain ~500 MB.

## Syarat PC

(Dari README port + kebutuhan build.)

- Windows 10 atau Windows 11 64-bit (build dari source hanya di Windows)
- CPU x86-64 (README port tidak menetapkan syarat instruksi seperti AVX2)
- RAM 8 GB direkomendasikan (build C++ penuh memakai banyak memori)
- GPU yang mendukung **Vulkan**
- Ruang disk kosong minimal **15 GB** (source + toolchain + dependency + build)
- PowerShell (bawaan Windows 10/11)
- **.NET 8 SDK — TIDAK PERLU dipasang manual**: bila tidak ada di PC,
  installer mengunduhnya otomatis saat MAIN ditekan. Bila ingin memasang
  sendiri: https://dotnet.microsoft.com/download/dotnet/8.0
- **Visual C++ Redistributable (x64)** — hanya dibutuhkan bila file
  game-mu .rvz (DolphinTool butuh runtime ini). Bila belum ada,
  installer memberi tahu saat konversi gagal; pasang dari
  https://aka.ms/vs/17/release/vc_redist.x64.exe

Cek sistem di awal alur MAIN hanya bersifat info — kekurangan TIDAK
pernah memblokir MAIN; yang bisa diperbaiki otomatis akan diperbaiki.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
file berikut **milikmu sendiri**:

- Dump Wii Sengoku Basara 2 Heroes **NTSC-J (`RBSJ08`)** — `.iso`
  atau `.rvz`

Hanya versi Wii NTSC-J `RBSJ08` yang didukung port ini. Installer
memvalidasi file yang kamu pilih (game ID di 6 byte pertama `.iso`
harus `RBSJ08`; `.rvz` harus diawali magic RVZ — `RVZ` + byte `0x01`).

### Tentang .rvz

Wiimms ISO Tools (wit) **tidak mendukung .rvz**. v1.1.0 mengonversi
`.rvz` ke `.iso` otomatis dengan DolphinTool
(`dolphin-tool convert -i <rvz> -o <iso> -f iso`, sintaks resmi README
Dolphin), lalu mengekstrak .iso hasilnya. Bila konversi otomatis gagal,
log menulis cara manualnya: buka Dolphin
(https://dolphin-emu.org/download/), Tools > Convert File, pilih file
.rvz, ubah format ke ISO — lalu pilih file .iso hasilnya di installer
dan tekan MAIN lagi. Alternatif lain: pilih folder yang sudah diekstrak
(berisi `sys/main.dol`).

## Cara pakai (v1.1.2 — satu layar)

1. Jalankan `Basara2HeroesPCInstaller.exe`.
2. **1. File Game** — pilih dump `.iso`/`.rvz` milikmu (atau folder
   hasil ekstraksi disc).
3. **2. Folder Install** — biarkan bawaan (`C:\Games\Basara2Heroes`)
   atau pilih folder lain dengan path pendek.
4. Tekan tombol besar **▶ MAIN**. Semua langkah di bawah jalan otomatis,
   dan progresnya muncul di log:
   1. Cek sistem (info saja — tidak memblokir).
   2. Unduh + ekstrak source port (dilewati bila sudah ada).
   3. Validasi file game; bila .rvz, konversi otomatis ke .iso;
      ekstrak disc ke `assets/basara-heroes/sys/main.dol` (dilewati
      bila sudah ada). Sejak v1.1.2 langkah ini jalan SEBELUM
      toolchain, supaya file game yang bermasalah ketahuan cepat.
      Sebelum konversi .rvz, installer memeriksa ruang kosong di
      drive file game (~5 GB untuk .iso hasil konversi) dan Visual
      C++ Redistributable yang dibutuhkan DolphinTool.
   4. Siapkan toolchain (CMake, Ninja, dependency, llvm-mingw,
      .NET 8 runtime lokal; ~500 MB).
   5. Pastikan .NET 8 SDK (diunduh otomatis bila tidak ada).
   6. Buat folder `generated/` + `generated/b/`.
   7. Terjemahkan (PowerPC -> C++, beberapa menit) lalu bangun Windows
      (kompilasi C++ penuh, bisa puluhan menit; dilewati bila
      `WiiCompiled.exe` sudah ada).
   8. Buka game. Menu dalam game mendukung Bahasa Inggris dan Bahasa
      Indonesia.

Bila ada langkah gagal: baca log — di sana tertulis error persisnya +
"yang harus dilakukan" dalam Bahasa Indonesia yang sederhana. Tekan
MAIN lagi untuk melanjutkan dari langkah yang gagal. Tombol **Salin
Log** menyalin seluruh log ke clipboard agar bisa dikirim bila butuh
bantuan. Sejak v1.1.2 log juga tersimpan otomatis di file
`%APPDATA%\Basara2HeroesPCInstaller\basara2-installer.log`, jadi tetap
bisa dikirim walau aplikasi sudah ditutup — tombol **Buka Folder Log**
membuka folder itu.

Catatan:

- Build pertama adalah yang paling lama; build berikutnya hanya
  mengompilasi yang berubah.
- Log game tersimpan di `generated/win-build/UserData` di folder source.
- Save game tersimpan di dalam aplikasi hasil build (UserData).

## Alur build (untuk yang ingin tahu)

Mengikuti README + script repo port:

```
dump Wii (.iso/.rvz)
  └─ .rvz dikonversi (DolphinTool) ──> .iso
  └─ diekstrak (wit) ──> assets/basara-heroes/sys/main.dol
                            │
translator/ (C#/.NET 8) + config/basara/{recomp.yml, MAP.txt}
                            │  PowerPC -> C++
                            ▼
generated/  (kode game hasil terjemahan)
                            │
runtime/ (C++, HLE) + aurora/ (GX -> WebGPU/Dawn)
                            │
                            ▼
              Windows .exe (WiiCompiled.exe)
              tools/b-win.ps1 configure + build
```

Hal-hal yang **tidak** disediakan script repo port (dan ditangani
installer ini):

- **llvm-mingw** — tidak diunduh script repo mana pun; installer
  mengunduhnya sendiri ke `third_party/llvm-mingw`.
- **Translator** — `b-translate.ps1` mengharapkan
  `Translator.Cli.dll` sudah ada, tetapi tidak ada script repo yang
  membangunnya; installer menjalankan `dotnet build` dulu (dengan SDK
  sistem atau SDK lokal yang diunduh otomatis). Selain itu
  `b-translate.ps1` mengatur `DOTNET_ROOT` ke `third_party/dotnet`,
  jadi installer mengunduh .NET 8 runtime ke sana bila belum ada.
- **Folder generated/** — tidak ada di git tree repo port; installer
  membuatnya dulu sebelum script menulis log ke `generated/b/`.

Langkah NDK di `setup-android.ps1` butuh Android SDK; bila gagal di
langkah itu tetapi bagian Windows (cmake/ninja/deps) sudah lengkap,
installer tetap melanjutkan — NDK hanya dibutuhkan untuk build Android.

## URL toolchain (semua terverifikasi 26 November 2026)

| Kebutuhan | URL |
|---|---|
| Source port v1.2.1-hotfix | https://github.com/PotatoRecomp/B2HWii-Android/archive/refs/tags/v1.2.1-hotfix.zip |
| Rilis port (API, hanya untuk self-test) | https://api.github.com/repos/PotatoRecomp/B2HWii-Android/releases/tags/v1.2.1-hotfix |
| llvm-mingw 20261117 (ucrt, x64, 182,2 MB) | https://github.com/mstorsjo/llvm-mingw/releases/download/20261117/llvm-mingw-20261117-ucrt-x86_64.zip |
| .NET 8 runtime 8.0.34 (win-x64, 31,8 MB) | https://builds.dotnet.microsoft.com/dotnet/Runtime/8.0.34/dotnet-runtime-8.0.34-win-x64.zip |
| .NET 8 SDK 8.0.428 (win-x64, ~272 MB, diunduh otomatis bila perlu) | https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.428/dotnet-sdk-8.0.428-win-x64.zip |
| Dolphin 2609b (win-x64, .7z, 19,1 MB — untuk konversi .rvz) | https://dl.dolphin-emu.org/releases/2609b/dolphin-2609b-x64.7z |
| Visual C++ Redistributable x64 (bila DolphinTool gagal jalan) | https://aka.ms/vs/17/release/vc_redist.x64.exe |
| Wiimms ISO Tools v3.05a r8638 (cygwin64, 14,9 MB) | https://wit.wiimm.de/download/wit-v3.05a-r8638-cygwin64.zip |
| CMake 4.3.3 (dipakai setup-android.ps1) | https://github.com/Kitware/CMake/releases/download/v4.3.3/cmake-4.3.3-windows-x86_64.zip |
| Ninja 1.13.2 (dipakai setup-android.ps1) | https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip |
| Dawn Windows prebuilt v20260603.191052 | https://github.com/theofficialgman/dawn-build/releases/download/v20260603.191052/dawn-windows-amd64.tar.gz |

Catatan: llvm-mingw dipilih varian **UCRT** (default modern; varian
MSVCRT adalah alternatif lawas). Paket Windows Dolphin adalah arsip
.7z (bukan .zip) — installer mengekstraknya dengan py7zr yang
terbundel; isi paket terverifikasi di sini (folder `Dolphin-x64`
berisi `Dolphin.exe`, `DolphinTool.exe`, `Updater.exe`). Unduhan wit
dari situs wiimm.de terkadang memblokir klien tertentu — bila unduhan
wit gagal, installer menampilkan pesan jelas dan kamu bisa mengunduh
manual dari https://wit.wiimm.de/download.html lalu meletakkan
`wit.exe` di folder tools aplikasi.

## Port / proyek terkait

Selain port utama (B2HWii-Android v1.2.1-hotfix untuk versi Wii),
ada proyek terkait lain yang bisa dicoba sendiri:

- **Basara 4 Sumeragi native PC port** (razzconnect/basara4-native-pc)
  — port native untuk game Basara 4, proyek terpisah.
- **Patch Bahasa Indonesia untuk PS2** (DeZer04/sengoku-basara-2-heroes-id)
  — patch bahasa untuk versi PS2; memainkannya tetap butuh emulator
  (PCSX2), bukan port native.

Installer ini hanya memakai B2HWii-Android; keduanya dicantumkan di
sini sebagai alternatif untuk dicoba sendiri.

## Build sendiri (installer ini)

### Windows (hasil: `dist\Basara2HeroesPCInstaller.exe`)

```bat
build\build-windows.bat
```

Syarat: Python 3.12 terpasang dan ada di PATH. Semua DLL runtime (Tk/Tcl)
terbundel di dalam exe. Dependensi runtime: py-cpuinfo, py7zr (untuk
ekstrak .7z Dolphin; wheel Windows py7zr + pybcj + pyppmd + pyzstd +
multivolumefile harus tersedia saat build).

### GitHub Actions

Push tag `v*` (mis. `v1.1.0`) atau jalankan manual via tab Actions.
Runner `windows-latest` membangun exe dan mengunggah artifact bernama
**Basara2HeroesPCInstaller-Windows**.

### Tes mandiri (tanpa GUI)

```sh
PYTHONPATH=src python -m basara2_installer --self-test
```

Tes ini memeriksa: rilis port di GitHub bisa dijangkau (dan hanya berisi
APK Android; bila API GitHub rate-limit 403, bagian ini dilaporkan
"tidak dapat diperiksa" — BUKAN gagal, karena alur normal tidak memakai
API GitHub), validasi file game pada file tiruan (.iso RBSJ08, .rvz
RVZ, folder sys/main.dol), helper baru v1.1.0 (parse_dotnet_version,
dolphin_tool_command, ensure_generated_dirs), dan cek sistem tidak
crash. Unit test:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Lisensi

- **Basara 2 Heroes PC Installer** (aplikasi ini): kode installer/launcher
  di sini bebas dipakai untuk keperluan pribadi.
- **Port B2HWii-Android** (PotatoRecomp/B2HWii-Android): GPLv3.
- **Sengoku Basara 2 Heroes dan aset game** adalah milik Capcom.
  Aplikasi ini tidak menyertakan, mendistribusikan, atau menyediakan
  file game, key, atau konten berhak cipta apa pun — gunakan hanya dump
  Wii `RBSJ08` milikmu sendiri.
