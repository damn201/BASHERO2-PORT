"""Antarmuka grafis Basara 2 Heroes PC Installer v1.1.0 (Tkinter, Bahasa Indonesia).

SATU LAYAR SAJA — tidak ada tab lagi. Pengguna cukup:
  1. pilih file game (.iso / .rvz / folder hasil ekstraksi),
  2. pilih folder install,
  3. tekan tombol besar ▶ MAIN.
Lalu semua langkah berjalan otomatis dan berurutan: cek sistem (info
saja, tidak pernah memblokir), unduh source, siapkan toolchain, pastikan
.NET 8 SDK (diunduh otomatis bila tidak ada), validasi + konversi .rvz
otomatis + ekstrak disc, terjemahkan, bangun Windows, lalu main.

Semua langkah RESUMABLE: langkah yang hasilnya sudah ada dilewati
(source sudah ada, main.dol sudah ada, WiiCompiled.exe sudah ada). Bila
ada langkah gagal, log menulis error persisnya + "yang harus dilakukan"
dalam Bahasa Indonesia yang sederhana, dan pengguna tinggal menekan MAIN
lagi — alur melanjutkan dari langkah yang gagal, tanpa mengulang langkah
yang sudah berhasil.

Operasi panjang berjalan di thread terpisah agar jendela tidak membeku;
progres dan log dilaporkan lewat queue + after().
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .config import default_install_dir, load_settings, save_settings
from .port import (
    build_windows,
    download_source_zip,
    ensure_dotnet_sdk,
    ensure_generated_dirs,
    extract_source_zip,
    find_built_exe,
    find_source_root,
    launch_game,
    open_folder,
    prepare_game_file,
    setup_toolchain,
    translate,
)
from .syscheck import FAIL, run_checks, summarize

MAX_LOG_LINES = 2000  # log dipangkas agar tidak membengkak saat build C++


def _asset_path(name: str) -> Path | None:
    """Cari file aset (berfungsi saat dijalankan dari source maupun frozen)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parents[2]
    candidate = base / "assets" / name
    return candidate if candidate.is_file() else None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Basara 2 Heroes PC Installer v{__version__}")
        self.geometry("860x720")
        self.minsize(720, 600)
        icon = _asset_path("icon.png")
        if icon is not None:
            try:
                self._icon_photo = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon_photo)
            except tk.TclError:
                pass

        self.settings = load_settings()
        self.queue: queue.Queue = queue.Queue()
        self._busy = False

        self._build_widgets()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Layout — satu layar
    # ------------------------------------------------------------------

    def _build_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Basara 2 Heroes PC Installer",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Port native Sengoku Basara 2 Heroes (versi Wii) untuk Windows — "
                 "BUKAN emulator. Butuh dump Wii RBSJ08 milikmu sendiri "
                 "(.iso atau .rvz); file game TIDAK disertakan.",
            wraplength=820,
        ).pack(anchor="w", pady=(2, 10))

        # 1. File game
        ttk.Label(
            main, text="1. File Game", font=("TkDefaultFont", 11, "bold")
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Pilih dump Wii Sengoku Basara 2 Heroes NTSC-J (RBSJ08) "
                 "milikmu — .iso atau .rvz — atau folder hasil ekstraksi "
                 "disc (berisi sys/main.dol). Versi PS2 tidak bisa dipakai.",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 4))
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 2))
        ttk.Button(
            row, text="Pilih File Game (.iso / .rvz)...",
            command=self._pick_game_file,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            row, text="Pilih Folder Hasil Ekstraksi...",
            command=self._pick_game_folder,
        ).pack(side="left")
        self.game_var = tk.StringVar(
            value=self.settings.get("game_file") or "Belum dipilih."
        )
        ttk.Label(
            main, textvariable=self.game_var, wraplength=820,
            foreground="#444444",
        ).pack(anchor="w", pady=(0, 10))

        # 2. Folder install
        ttk.Label(
            main, text="2. Folder Install", font=("TkDefaultFont", 11, "bold")
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Source port + toolchain + hasil build disimpan di sini. "
                 "Pakai path pendek (mis. C:\\Games\\Basara2Heroes).",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 4))
        row2 = ttk.Frame(main)
        row2.pack(fill="x", pady=(0, 10))
        self.install_entry = ttk.Entry(row2)
        self.install_entry.pack(side="left", fill="x", expand=True)
        self.install_entry.insert(
            0, self.settings.get("install_dir") or default_install_dir()
        )
        ttk.Button(row2, text="Browse...", command=self._pick_install_dir).pack(
            side="left", padx=(6, 0)
        )

        # Tombol MAIN
        style = ttk.Style(self)
        style.configure(
            "Main.TButton", font=("TkDefaultFont", 15, "bold"), padding=10
        )
        self.main_btn = ttk.Button(
            main, text="▶  MAIN", style="Main.TButton",
            command=self._start_main,
        )
        self.main_btn.pack(fill="x", pady=(0, 6))

        self.progress = ttk.Progressbar(main, length=400, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 4))
        self.status_var = tk.StringVar(value="Siap — pilih file game, lalu tekan MAIN.")
        ttk.Label(main, textvariable=self.status_var, wraplength=820).pack(
            anchor="w", pady=(0, 6)
        )

        # Log besar
        ttk.Label(main, text="Log:").pack(anchor="w")
        self.log_text = tk.Text(main, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Tombol bawah
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Salin Log", command=self._copy_log).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            bottom, text="Buka Folder Install",
            command=self._open_install_folder,
        ).pack(side="left")
        ttk.Label(
            bottom,
            text="Build pertama bisa puluhan menit (unduh toolchain ~500 MB, "
                 "terjemah, kompilasi C++). Jangan tutup aplikasi.",
            wraplength=420,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Log & queue
    # ------------------------------------------------------------------

    def _append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        # Pangkas log lama agar tidak membengkak saat build C++.
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:
            self.log_text.delete("1.0", f"{lines - MAX_LOG_LINES}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "progress_mode":
                    self.progress.configure(mode=payload)
                    if payload == "indeterminate":
                        self.progress.start(12)
                    else:
                        self.progress.stop()
                        self.progress["value"] = 0
                elif kind == "progress":
                    downloaded, total = payload
                    if total:
                        self.progress["value"] = downloaded / total * 100
                        self.status_var.set(
                            f"Mengunduh... {downloaded / 1024 / 1024:.1f} / "
                            f"{total / 1024 / 1024:.1f} MB"
                        )
                elif kind == "done":
                    self._busy = False
                    self.main_btn.configure(state="normal")
                    self.progress.configure(mode="determinate")
                    self.progress.stop()
                    self.progress["value"] = 100
                    self.status_var.set(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Pilihan pengguna
    # ------------------------------------------------------------------

    def _pick_game_file(self):
        path = filedialog.askopenfilename(
            title="Pilih dump Wii Sengoku Basara 2 Heroes (RBSJ08)",
            filetypes=[
                ("Dump Wii", "*.iso *.rvz"),
                ("Disc image", "*.iso"),
                ("RVZ (Dolphin)", "*.rvz"),
                ("Semua file", "*.*"),
            ],
        )
        if path:
            self.game_var.set(path)
            self._save_game_choice(path)

    def _pick_game_folder(self):
        folder = filedialog.askdirectory(
            title="Pilih folder hasil ekstraksi disc (berisi sys/main.dol)"
        )
        if folder:
            self.game_var.set(folder)
            self._save_game_choice(folder)

    def _save_game_choice(self, path: str):
        self.settings["game_file"] = path
        save_settings(self.settings)

    def _pick_install_dir(self):
        folder = filedialog.askdirectory(title="Pilih folder install")
        if folder:
            self.install_entry.delete(0, "end")
            self.install_entry.insert(0, folder)
            self.settings["install_dir"] = folder
            save_settings(self.settings)

    def _copy_log(self):
        text = self.log_text.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set(
            "Log disalin ke clipboard — tempelkan ke saya bila ada error."
        )

    def _open_install_folder(self):
        install_dir = self.install_entry.get().strip()
        if not install_dir:
            messagebox.showwarning(
                "Folder install", "Pilih folder install dulu."
            )
            return
        ok, message = open_folder(install_dir)
        if not ok:
            messagebox.showwarning("Buka folder", message)
        self._append_log(message)

    # ------------------------------------------------------------------
    # Alur MAIN — otomatis, berurutan, resumable
    # ------------------------------------------------------------------

    def _start_main(self):
        if self._busy:
            return
        game = self.game_var.get().strip()
        install_dir = self.install_entry.get().strip()
        if game in ("", "Belum dipilih."):
            messagebox.showwarning(
                "File game",
                "Pilih dulu file game (.iso / .rvz) atau folder hasil "
                "ekstraksi di bagian 1.",
            )
            return
        if not install_dir:
            messagebox.showwarning(
                "Folder install", "Isi folder install di bagian 2."
            )
            return
        self.settings["game_file"] = game
        self.settings["install_dir"] = install_dir
        save_settings(self.settings)
        self._busy = True
        self.main_btn.configure(state="disabled")
        self.progress["value"] = 0
        self._append_log("=" * 60)
        self._append_log("MAIN ditekan — memulai semua langkah otomatis.")
        threading.Thread(
            target=self._main_worker, args=(game, install_dir), daemon=True
        ).start()

    def _main_worker(self, game: str, install_dir: str):
        put = self.queue.put
        try:
            self._run_main_flow(game, install_dir, put)
        except Exception as exc:  # noqa: BLE001
            put(("log", ""))
            put(("log", f"GAGAL: {exc}"))
            put(("log", ""))
            put((
                "log",
                "Tekan MAIN lagi untuk melanjutkan dari langkah yang gagal "
                "— langkah yang sudah selesai tidak diulang.",
            ))
            put(("done", f"Gagal — lihat log. Tekan MAIN lagi untuk melanjutkan."))

    def _run_main_flow(self, game: str, install_dir: str, put) -> None:
        log = lambda m: put(("log", m))  # noqa: E731
        progress = lambda d, t: put(("progress", (d, t)))  # noqa: E731

        # 1. Cek sistem (info saja — tidak pernah memblokir MAIN).
        put(("status", "Langkah 1/8: memeriksa PC..."))
        log("[1/8] Memeriksa PC (info saja — kekurangan akan diperbaiki "
            "otomatis bila bisa)...")
        try:
            checks = run_checks(install_dir or None)
            ok, gagal, tidak_diketahui = summarize(checks)
            log(f"      Cek sistem: {ok} lolos, {gagal} gagal, "
                f"{tidak_diketahui} tidak dapat diperiksa.")
            for check in checks:
                if check["status"] == FAIL:
                    log(f"      Peringatan: {check['name']} — "
                        f"{check['detail']}")
        except Exception as exc:  # noqa: BLE001
            log(f"      Cek sistem tidak bisa jalan ({exc}) — tetap lanjut.")

        # 2. Unduh + ekstrak source port (lewati bila sudah ada).
        put(("status", "Langkah 2/8: menyiapkan source port..."))
        root = find_source_root(install_dir)
        if root is not None:
            log(f"[2/8] Source port sudah ada: {root} (dilewati).")
        else:
            log("[2/8] Mengunduh source port (PotatoRecomp/B2HWii-Android "
                "v1.2.1-hotfix, ~7 MB)...")
            put(("progress_mode", "determinate"))
            zip_path = download_source_zip(progress_cb=progress)
            log("      Mengekstrak source...")
            extract_source_zip(zip_path, Path(install_dir))
            root = find_source_root(install_dir)
            if root is None:
                raise RuntimeError(
                    "Source berhasil diunduh dan diekstrak, tetapi "
                    "tools/b-win.ps1 tidak ditemukan di folder install. "
                    "Yang harus dilakukan: hapus folder install lalu tekan "
                    "MAIN lagi."
                )
            self.settings["install_dir"] = install_dir
            save_settings(self.settings)
            log(f"      Source terpasang: {root}")

        # 3. Siapkan toolchain (perbaikan otomatis per-bagian).
        put(("status", "Langkah 3/8: menyiapkan toolchain..."))
        log("[3/8] Menyiapkan toolchain (CMake, Ninja, dependency, "
            "llvm-mingw, .NET runtime — unduhan ~500 MB, bisa lama)...")
        put(("progress_mode", "indeterminate"))
        pieces = setup_toolchain(
            root, log_cb=log, progress_cb=progress
        )
        siap = [k for k, v in pieces.items() if v]
        log(f"      Toolchain siap: {', '.join(siap)}.")
        put(("progress_mode", "determinate"))

        # 4. Pastikan .NET 8 SDK (diunduh otomatis bila tidak ada).
        put(("status", "Langkah 4/8: memastikan .NET 8 SDK..."))
        log("[4/8] Memastikan .NET 8 SDK (untuk membangun translator)...")
        put(("progress_mode", "indeterminate"))
        exe = ensure_dotnet_sdk(root, log_cb=log, progress_cb=progress)
        log(f"      .NET SDK dipakai: {exe}")
        put(("progress_mode", "determinate"))

        # 5. Validasi + konversi .rvz + ekstrak disc.
        put(("status", "Langkah 5/8: menyiapkan file game..."))
        log(f"[5/8] Menyiapkan file game: {Path(game).name}")
        put(("progress_mode", "indeterminate"))
        dol = prepare_game_file(
            game, root, log_cb=log, progress_cb=progress
        )
        log(f"      File game siap: {dol}")
        put(("progress_mode", "determinate"))

        # 6. Buat folder generated/ (script repo menulis log ke sana).
        put(("status", "Langkah 6/8: menyiapkan folder build..."))
        ensure_generated_dirs(root)
        log("[6/8] Folder build (generated/) siap.")

        # 7. Terjemahkan + bangun Windows (lewati bila sudah ada).
        put(("status", "Langkah 7/8: membangun game..."))
        exe_built = find_built_exe(root)
        if exe_built is not None:
            log(f"[7/8] Game sudah dibangun: {exe_built} (dilewati).")
        else:
            log("[7/8] Menerjemahkan kode PowerPC ke C++...")
            log("      (Langkah ini beberapa menit.)")
            put(("progress_mode", "indeterminate"))
            translate(root, log_cb=log, progress_cb=progress)
            log("[7/8] Membangun game untuk Windows...")
            log("      Build C++ penuh — bisa PULUHAN MENIT tergantung PC. "
                "Jangan tutup aplikasi; progres muncul di log ini.")
            exe_built = build_windows(root, log_cb=log)
            log(f"      Build selesai: {exe_built}")
            put(("progress_mode", "determinate"))

        # 8. Jalankan game.
        put(("status", "Langkah 8/8: membuka game..."))
        log("[8/8] Membuka game...")
        ok, message = launch_game(root)
        if not ok:
            raise RuntimeError(message)
        log(f"      {message}")
        log("")
        log("Selesai — selamat bermain! Menu dalam game mendukung Bahasa "
            "Inggris dan Bahasa Indonesia.")
        put(("done", "Game dibuka. Selamat bermain!"))


def run():
    app = App()
    app.mainloop()
