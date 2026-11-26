# Basara 2 Heroes PC Installer

Installer/launcher Windows untuk memainkan **Sengoku Basara 2 Heroes
(versi Wii) secara native di PC** — **BUKAN emulator**.

Aplikasi ini membangun port native open-source **PotatoRecomp/B2HWii-Android**
([PotatoRecomp/B2HWii-Android](https://github.com/PotatoRecomp/B2HWii-Android),
v1.2.1-hotfix, lisensi GPLv3) dari source di PC kamu, lalu membantumu
memeriksa PC, menyiapkan toolchain, mengekstrak disc, menerjemahkan,
membangun, dan memainkan gamenya dengan satu klik.

## Penjelasan jujur: kenapa ini bisa native?

Kode game **Wii tidak bisa jalan native di PC begitu saja**. Wii memakai
CPU PowerPC yang arsitekturnya berbeda total dari PC x86-64, sehingga
game Wii biasanya hanya bisa dimainkan lewat emulator (mis. Dolphin).

Yang dilakukan port ini adalah **static recompilation** (WiiCompiled):
kode PowerPC di `main.dol` diterjemahkan ke C++ di depan (ahead of time)
lalu dikompilasi menjadi aplikasi Windows native, bersama runtime yang
menggantikan system software Wii dan renderer GX di Vulkan. Tidak ada
yang diemulasi saat game berjalan.

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
- **.NET 8 SDK** terpasang (translator ditulis C#/.NET 8) — pasang dari
  https://dotnet.microsoft.com/download/dotnet/8.0
- PowerShell (bawaan Windows 10/11)

Aplikasi ini punya tab **Cek Sistem** yang memeriksa semua syarat di atas
dan memberi tahu mana yang lolos, gagal, atau tidak dapat diperiksa.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
file berikut **milikmu sendiri**:

- Dump Wii Sengoku Basara 2 Heroes **NTSC-J (`RBSJ08`)** — `.iso`
  atau `.rvz`

Hanya versi Wii NTSC-J `RBSJ08` yang didukung port ini.

Tab **Game** di aplikasi akan memvalidasi file yang kamu pilih (game ID
di 6 byte pertama `.iso` harus `RBSJ08`; `.rvz` harus diawali magic
`RVZ1`) dan menampilkan masalah bila ada.

### Tentang .rvz

Wiimms ISO Tools (wit) **tidak mendukung .rvz**. Bila dump kamu
berformat `.rvz`, konversi dulu ke `.iso` dengan Dolphin (klik kanan
game > Convert File > ISO), atau pilih folder yang sudah diekstrak
(berisi `sys/main.dol`) lewat tombol "Pakai Folder Hasil Ekstraksi".

## Cara pakai

1. Jalankan `Basara2HeroesPCInstaller.exe`.
2. **Cek Sistem** — tekan "Jalankan Cek Sistem", pastikan semuanya
   lolos (terutama .NET 8 SDK).
3. **Unduh Source** — pilih folder install dengan path pendek
   (mis. `C:\Games\Basara2Heroes`), tekan "Unduh Source", lalu
   "Siapkan Toolchain". Toolchain yang disiapkan: CMake 4.3.3, Ninja
   1.13.2, Gradle 8.7, Dawn prebuilt, aurora dependencies, llvm-mingw,
   dan .NET 8 runtime lokal.
4. **Game** — pilih file dump `.iso`/`.rvz` milikmu, tekan "Validasi
   File Game", lalu "Ekstrak Disc (.iso via wit)" — hasilnya
   `assets/basara-heroes/sys/main.dol`. Bila memakai `.rvz`, konversi
   dulu ke `.iso` dengan Dolphin, atau pilih folder hasil ekstraksi.
5. **Build** — tekan **TERJEMAHKAN** (PowerPC -> C++, `b-translate.ps1`,
   beberapa menit), lalu **BANGUN WINDOWS** (`b-win.ps1` configure +
   build — kompilasi C++ penuh, bisa puluhan menit). Log live tampil
   di tab ini. Hasilnya: `generated/win-build/WiiCompiled.exe`.
6. **Main** — tekan **BUKA GAME**. Menu dalam game mendukung Bahasa
   Inggris dan Bahasa Indonesia.

Catatan:

- Build pertama adalah yang paling lama; build berikutnya hanya
  mengompilasi yang berubah.
- Log game tersimpan di `generated/win-build/UserData` di folder source.
- Save game tersimpan di dalam aplikasi hasil build (UserData).

## Alur build (untuk yang ingin tahu)

Mengikuti README + script repo port:

```
dump Wii (.iso/.rvz)
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

Dua hal yang **tidak** disediakan script repo port (dan ditangani
installer ini):

- **llvm-mingw** — tidak diunduh script repo mana pun; installer
  mengunduhnya sendiri ke `third_party/llvm-mingw`.
- **Translator** — `b-translate.ps1` mengharapkan
  `Translator.Cli.dll` sudah ada, tetapi tidak ada script repo yang
  membangunnya; installer menjalankan `dotnet build` dulu. Selain itu
  `b-translate.ps1` mengatur `DOTNET_ROOT` ke `third_party/dotnet`,
  jadi installer mengunduh .NET 8 runtime ke sana bila belum ada.

Langkah NDK di `setup-android.ps1` butuh Android SDK; bila gagal di
langkah itu tetapi bagian Windows (cmake/ninja/deps) sudah lengkap,
installer tetap melanjutkan dengan peringatan — NDK hanya dibutuhkan
untuk build Android.

## URL toolchain (semua terverifikasi 26 November 2026)

| Kebutuhan | URL |
|---|---|
| Source port v1.2.1-hotfix | https://github.com/PotatoRecomp/B2HWii-Android/archive/refs/tags/v1.2.1-hotfix.zip |
| Rilis port (API) | https://api.github.com/repos/PotatoRecomp/B2HWii-Android/releases/tags/v1.2.1-hotfix |
| llvm-mingw 20261117 (ucrt, x64, 182,2 MB) | https://github.com/mstorsjo/llvm-mingw/releases/download/20261117/llvm-mingw-20261117-ucrt-x86_64.zip |
| .NET 8 runtime 8.0.34 (win-x64, 31,8 MB) | https://builds.dotnet.microsoft.com/dotnet/Runtime/8.0.34/dotnet-runtime-8.0.34-win-x64.zip |
| .NET 8 SDK 8.0.428 (win-x64, ~272 MB) | https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.428/dotnet-sdk-8.0.428-win-x64.zip |
| Wiimms ISO Tools v3.05a r8638 (cygwin64, 14,9 MB) | https://wit.wiimm.de/download/wit-v3.05a-r8638-cygwin64.zip |
| CMake 4.3.3 (dipakai setup-android.ps1) | https://github.com/Kitware/CMake/releases/download/v4.3.3/cmake-4.3.3-windows-x86_64.zip |
| Ninja 1.13.2 (dipakai setup-android.ps1) | https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip |
| Dawn Windows prebuilt v20260603.191052 | https://github.com/theofficialgman/dawn-build/releases/download/v20260603.191052/dawn-windows-amd64.tar.gz |

Catatan: llvm-mingw dipilih varian **UCRT** (default modern; varian
MSVCRT adalah alternatif lawas). Unduhan wit dari situs wiimm.de
terkadang memblokir klien tertentu — bila unduhan wit gagal, installer
menampilkan pesan jelas dan kamu bisa mengunduh manual dari
https://wit.wiimm.de/download.html lalu meletakkan `wit.exe` di folder
tools aplikasi.

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
terbundel di dalam exe.

### GitHub Actions

Push tag `v*` (mis. `v1.0.0`) atau jalankan manual via tab Actions.
Runner `windows-latest` membangun exe dan mengunggah artifact bernama
**Basara2HeroesPCInstaller-Windows**.

### Tes mandiri (tanpa GUI)

```sh
PYTHONPATH=src python -m basara2_installer --self-test
```

Tes ini memeriksa: rilis port di GitHub bisa dijangkau (dan hanya berisi
APK Android), validasi file game pada file tiruan (.iso RBSJ08, .rvz
RVZ1, folder sys/main.dol), dan cek sistem tidak crash. Unit test:

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
