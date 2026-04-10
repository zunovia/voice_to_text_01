import sys
import os
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Setup logging to file (essential for pythonw where there's no console)
def _get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = _get_app_dir()
LOG_PATH = os.path.join(APP_DIR, "voicetotext.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("VoiceToText")

# Redirect stderr to log file for pythonw
if sys.executable.endswith("pythonw.exe"):
    sys.stderr = open(LOG_PATH, "a", encoding="utf-8")
    sys.stdout = open(LOG_PATH, "a", encoding="utf-8")


def show_error(title, message):
    """Show error dialog even if no Tk root exists yet."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror(title, message, parent=root)
        root.destroy()
    except Exception:
        pass


try:
    from settings_manager import load_config, save_config, CONFIG_PATH
    from i18n import t
    from recorder import AudioRecorder
    from transcriber import Transcriber
    from text_inserter import TextInserter
    from hotkey_manager import HotkeyManager
    from tray_app import TrayApp
    from overlay import RecordingOverlay
    from settings_gui import SettingsGUI
except ImportError as e:
    log.error(f"Import error: {e}")
    show_error("Voice-to-Text Error", f"Missing dependency:\n{e}\n\nRun: pip install -r requirements.txt")
    sys.exit(1)


class VoiceToTextApp:
    def __init__(self):
        self.config = load_config()
        self.recorder = AudioRecorder(sample_rate=self.config.get("sample_rate", 16000))
        self.transcriber = None
        self.inserter = TextInserter(self.config.get("voice_commands", {}))
        self.hotkey_manager = None
        self.tray = None
        self.overlay = None
        self.settings_gui = None
        self._tk_root = None

    def run(self):
        # Check for API key first - show GUI prompt
        api_key = self.config.get("api_key", "")
        if not api_key or api_key.startswith("YOUR_") or len(api_key) < 10:
            if not self._prompt_api_key():
                show_error("Voice-to-Text", "API Key is required to use this app.\nPlease restart and enter your Gemini API Key.")
                sys.exit(1)

        # Initialize transcriber
        try:
            gemini_key = ""
            if self.config.get("use_gemini_cleanup", False):
                gemini_key = self.config.get("gemini_api_key", "")
            self.transcriber = Transcriber(
                self.config["api_key"],
                gemini_api_key=gemini_key,
            )
        except Exception as e:
            log.error(f"Failed to init transcriber: {e}")
            show_error("Voice-to-Text Error", f"Failed to initialize:\n{e}")
            sys.exit(1)

        # Pre-load Silero VAD in background (avoids 1s delay on first recording)
        import threading
        threading.Thread(target=self._preload_vad, daemon=True).start()

        lang = self.config.get("language", "ja")

        # Initialize overlay
        self.overlay = RecordingOverlay(on_gemini_toggle=self._toggle_gemini_cleanup, lang=lang)
        self.overlay.start()
        self.overlay.set_gemini_state(self.config.get("use_gemini_cleanup", False))

        # Connect recorder audio levels to overlay waveform
        self.recorder.set_level_callback(
            lambda level, waveform: self.overlay.update_audio(level, waveform)
        )

        # Initialize settings GUI
        self.settings_gui = SettingsGUI(on_save=self._on_settings_saved)

        # Setup hotkey manager
        self._setup_hotkey()

        # Setup and run system tray (blocks main thread)
        self.tray = TrayApp(
            on_settings=self._show_settings,
            on_quit=self._quit,
            on_mode_toggle=self._toggle_mode,
            on_gemini_toggle=self._toggle_gemini_cleanup,
            lang=lang,
        )
        self.tray.set_mode(self.config.get("mode", "push_to_talk"))
        self.tray.set_gemini_cleanup(self.config.get("use_gemini_cleanup", False))

        hotkey = self.config.get("hotkey", "ctrl+shift+space")
        mode = self.config.get("mode", "push_to_talk")
        log.info(f"Voice-to-Text started! Hotkey: {hotkey}, Mode: {mode}")

        self.tray.start()  # This blocks until quit

    def _prompt_api_key(self) -> bool:
        """Show a welcome dialog to enter API keys on first run."""
        import webbrowser
        import locale

        # Detect system language for initial UI
        sys_lang = locale.getdefaultlocale()[0] or ""
        current_lang = "ja" if sys_lang.startswith("ja") else "en"

        while True:
            result_data = self._show_setup_dialog(current_lang)
            if result_data is None:
                # Language switched, retry with new language
                current_lang = "en" if current_lang == "ja" else "ja"
                continue
            if result_data.get("groq_key"):
                self.config["api_key"] = result_data["groq_key"]
                self.config["language"] = current_lang
                if result_data.get("gemini_key"):
                    self.config["gemini_api_key"] = result_data["gemini_key"]
                    self.config["use_gemini_cleanup"] = True
                success = save_config(self.config)
                if success:
                    log.info(f"API Keys saved to {CONFIG_PATH}")
                else:
                    log.error(f"FAILED to save API Keys to {CONFIG_PATH}")
                return success
            return False

    def _show_setup_dialog(self, L) -> dict | None:
        """Show setup dialog. Returns dict with keys, or None if language switched."""
        import webbrowser
        result = {"groq_key": "", "gemini_key": "", "lang_switched": False}

        BG = "#1a1a2e"
        CARD = "#16213e"
        HIGHLIGHT = "#4FC3F7"
        GREEN = "#4CAF50"

        root = tk.Tk()
        root.title("Voice to Text")
        root.geometry("520x560")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=BG)

        icon_path = os.path.join(APP_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass

        root.update_idletasks()
        x = (root.winfo_screenwidth() - 520) // 2
        y = (root.winfo_screenheight() - 560) // 2
        root.geometry(f"520x560+{x}+{y}")
        root.lift()
        root.focus_force()

        main = tk.Frame(root, bg=BG, padx=30, pady=15)
        main.pack(fill="both", expand=True)

        # Language switch + Title
        title_row = tk.Frame(main, bg=BG)
        title_row.pack(fill="x", pady=(0, 3))

        tk.Label(title_row, text=t("setup_title", L), font=("Segoe UI", 22, "bold"),
                 fg="#FFFFFF", bg=BG).pack(side="left")

        # Language toggle button
        lang_state = {"lang": L}

        def toggle_lang():
            result["lang_switched"] = True
            root.destroy()

        lang_btn = tk.Button(title_row, text="EN" if L == "ja" else "日本語",
                             font=("Segoe UI", 9), fg="#FFFFFF", bg="#333333",
                             activebackground="#444444", relief="flat",
                             padx=8, pady=2, cursor="hand2",
                             command=toggle_lang)
        lang_btn.pack(side="right")

        tk.Label(main, text=t("setup_subtitle", L), font=("Segoe UI", 10),
                 fg="#888888", bg=BG).pack(anchor="w", pady=(0, 15))

        # === Groq Card ===
        groq_card = tk.Frame(main, bg=CARD, padx=15, pady=12)
        groq_card.pack(fill="x", pady=(0, 10))

        groq_header = tk.Frame(groq_card, bg=CARD)
        groq_header.pack(fill="x", pady=(0, 5))
        tk.Label(groq_header, text=t("setup_groq_title", L), font=("Segoe UI", 11, "bold"),
                 fg=HIGHLIGHT, bg=CARD).pack(side="left")
        groq_link = tk.Label(groq_header, text=t("setup_groq_link", L), font=("Segoe UI", 9, "underline"),
                             fg=HIGHLIGHT, bg=CARD, cursor="hand2")
        groq_link.pack(side="right")
        groq_link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        tk.Label(groq_card, text=t("setup_groq_desc", L), font=("Segoe UI", 9),
                 fg="#888888", bg=CARD).pack(anchor="w", pady=(0, 5))

        groq_var = tk.StringVar()
        groq_entry = tk.Entry(groq_card, textvariable=groq_var, width=55,
                              bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                              relief="flat", font=("Consolas", 10))
        groq_entry.pack(fill="x", pady=(0, 5))
        groq_entry.focus_set()

        tk.Label(groq_card, text=t("setup_groq_steps", L),
                 font=("Segoe UI", 8), fg="#666666", bg=CARD).pack(anchor="w")

        # === Gemini Card ===
        gemini_card = tk.Frame(main, bg=CARD, padx=15, pady=12)
        gemini_card.pack(fill="x", pady=(0, 10))

        gemini_header = tk.Frame(gemini_card, bg=CARD)
        gemini_header.pack(fill="x", pady=(0, 5))
        tk.Label(gemini_header, text=t("setup_gemini_title", L), font=("Segoe UI", 11, "bold"),
                 fg="#FFA726", bg=CARD).pack(side="left")
        gemini_link = tk.Label(gemini_header, text=t("setup_groq_link", L), font=("Segoe UI", 9, "underline"),
                               fg=HIGHLIGHT, bg=CARD, cursor="hand2")
        gemini_link.pack(side="right")
        gemini_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey"))

        tk.Label(gemini_card, text=t("setup_gemini_desc", L), font=("Segoe UI", 9),
                 fg="#888888", bg=CARD).pack(anchor="w", pady=(0, 5))

        gemini_var = tk.StringVar()
        gemini_entry = tk.Entry(gemini_card, textvariable=gemini_var, width=55,
                                bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                                relief="flat", font=("Consolas", 10))
        gemini_entry.pack(fill="x", pady=(0, 5))

        tk.Label(gemini_card, text=t("setup_gemini_optional", L),
                 font=("Segoe UI", 8), fg="#666666", bg=CARD).pack(anchor="w")

        # === Buttons ===
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(pady=(15, 0))

        def on_save():
            key = groq_var.get().strip()
            if not key:
                messagebox.showwarning("Warning", t("setup_groq_required", L), parent=root)
                return
            result["groq_key"] = key
            result["gemini_key"] = gemini_var.get().strip()
            root.destroy()

        def on_cancel():
            root.destroy()

        save_btn = tk.Button(btn_frame, text=t("setup_start", L), font=("Segoe UI", 12, "bold"),
                             fg="#FFFFFF", bg=GREEN, activebackground="#388E3C",
                             relief="flat", padx=30, pady=5, cursor="hand2",
                             command=on_save)
        save_btn.pack(side="left", padx=5)
        cancel_btn = tk.Button(btn_frame, text=t("setup_cancel", L), font=("Segoe UI", 10),
                               fg="#888888", bg="#333333", activebackground="#444444",
                               relief="flat", padx=15, pady=5, cursor="hand2",
                               command=on_cancel)
        cancel_btn.pack(side="left", padx=5)

        root.bind("<Return>", lambda e: on_save())
        root.protocol("WM_DELETE_WINDOW", on_cancel)

        root.mainloop()

        if result.get("lang_switched"):
            return None  # Signal to retry with switched language
        if result["groq_key"]:
            return result
        return {}

    def _setup_hotkey(self):
        if self.hotkey_manager:
            self.hotkey_manager.stop()

        self.hotkey_manager = HotkeyManager(
            hotkey_str=self.config.get("hotkey", "ctrl+shift+space"),
            mode=self.config.get("mode", "push_to_talk"),
            on_start=self._on_recording_start,
            on_stop=self._on_recording_stop,
        )
        self.hotkey_manager.start()

    def _on_recording_start(self):
        log.info("Recording started...")
        L = self.config.get("language", "ja")
        self.recorder.start()
        if self.tray:
            self.tray.set_recording(True)
        if self.overlay:
            self.overlay.show(t("recording", L))

    def _on_recording_stop(self):
        log.info("Recording stopped. Processing...")
        wav_data = self.recorder.stop()
        duration = self.recorder.get_duration()

        if self.tray:
            self.tray.set_processing()
        if self.overlay:
            self.overlay.update_text(t("processing", self.config.get("language", "ja")))

        if not wav_data or duration < 0.3:
            log.info("Recording too short, skipping.")
            if self.tray:
                self.tray.set_recording(False)
            if self.overlay:
                self.overlay.hide()
            return

        try:
            text = self.transcriber.transcribe(wav_data)
            if text:
                log.info(f"Transcribed: {text}")
                self.inserter.process_and_insert(text)
            else:
                log.info("No text transcribed.")
        except Exception as e:
            log.error(f"Transcription error: {e}")
            if self.overlay:
                self.overlay.update_text(t("error", self.config.get("language", "ja")))
                import time
                time.sleep(1)
        finally:
            if self.tray:
                self.tray.set_recording(False)
            if self.overlay:
                self.overlay.hide()

    def _show_settings(self):
        def _show():
            try:
                self.settings_gui.show()
            except Exception as e:
                log.error(f"Settings GUI error: {e}")

        threading.Thread(target=_show, daemon=True).start()

    def _on_settings_saved(self, new_config):
        self.config = new_config
        if self.transcriber:
            self.transcriber.update_api_key(new_config["api_key"])
        self.inserter.update_voice_commands(new_config.get("voice_commands", {}))
        self._setup_hotkey()
        if self.tray:
            self.tray.set_mode(new_config.get("mode", "push_to_talk"))
        log.info(f"Settings updated. Hotkey: {new_config['hotkey']}, Mode: {new_config['mode']}")

    def _preload_vad(self):
        """Pre-load Silero VAD model in background to avoid delay on first recording."""
        try:
            from recorder import _get_vad_model
            _get_vad_model()
            log.info("VAD pre-loaded successfully")
        except Exception as e:
            log.warning(f"VAD pre-load failed: {e}")

    def _toggle_mode(self):
        current = self.config.get("mode", "push_to_talk")
        new_mode = "toggle" if current == "push_to_talk" else "push_to_talk"
        self.config["mode"] = new_mode
        save_config(self.config)
        if self.hotkey_manager:
            self.hotkey_manager.update_mode(new_mode)
        if self.tray:
            self.tray.set_mode(new_mode)
        log.info(f"Mode switched to: {new_mode}")

    def _toggle_gemini_cleanup(self):
        current = self.config.get("use_gemini_cleanup", False)
        new_val = not current
        self.config["use_gemini_cleanup"] = new_val
        save_config(self.config)

        # Update transcriber
        gemini_key = self.config.get("gemini_api_key", "") if new_val else ""
        self.transcriber = Transcriber(
            self.config["api_key"],
            gemini_api_key=gemini_key,
        )
        if self.tray:
            self.tray.set_gemini_cleanup(new_val)
        if self.overlay:
            self.overlay.set_gemini_state(new_val)
        log.info(f"Gemini cleanup: {'ON' if new_val else 'OFF'}")

    def _quit(self):
        log.info("Shutting down...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        if self.overlay:
            self.overlay.destroy()


def check_single_instance():
    """Prevent multiple instances using a lock file."""
    lock_path = os.path.join(APP_DIR, ".lock")
    try:
        if os.path.exists(lock_path):
            # Check if PID in lock file is still running
            with open(lock_path, "r") as f:
                old_pid = int(f.read().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, old_pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                # Process still running
                show_error("Voice to Text", "既に起動しています。\nタスクバー右下のアイコンを確認してください。")
                return False
        # Write our PID
        with open(lock_path, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


if __name__ == "__main__":
    try:
        if not check_single_instance():
            sys.exit(0)
        app = VoiceToTextApp()
        app.run()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        # Don't show error dialog for non-critical errors during shutdown
        # Only show if it's truly fatal (app never started)
        sys.exit(1)
    finally:
        # Clean up lock file
        lock_path = os.path.join(APP_DIR, ".lock")
        try:
            os.remove(lock_path)
        except Exception:
            pass
