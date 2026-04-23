import sys
import os
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Setup logging to file (essential for pythonw where there's no console)
def _get_app_dir():
    """Get the data directory for config/log files.
    For exe (frozen): %APPDATA%/VoiceToText/ (persists across reinstalls).
    For script: directory containing this .py file.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", os.path.expanduser("~")))
        data_dir = os.path.join(appdata, "VoiceToText")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = _get_app_dir()

def _get_resource_dir():
    """Get the directory containing bundled assets (icons, etc.).
    For frozen exe: sys._MEIPASS (PyInstaller temp extraction dir).
    For script: same as APP_DIR.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return APP_DIR

RESOURCE_DIR = _get_resource_dir()
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
        from splash import SplashScreen

        # Check for API key first - show GUI prompt
        api_key = self.config.get("api_key", "")
        if not api_key or api_key.startswith("YOUR_") or len(api_key) < 10:
            if not self._prompt_api_key():
                show_error("Voice-to-Text", "API Key is required to use this app.\nPlease restart and enter your Gemini API Key.")
                sys.exit(1)

        # Create desktop shortcut on first run (frozen exe only)
        if getattr(sys, "frozen", False):
            self._ensure_desktop_shortcut()

        # Show splash screen while loading
        splash = SplashScreen()
        splash.show()
        splash.update("Initializing...")

        # Initialize transcriber
        try:
            gemini_key = self.config.get("gemini_api_key", "")
            llm_provider = self.config.get("llm_provider", "groq")
            groq_llm_model = self.config.get("groq_llm_model", "llama-3.1-8b-instant")
            self.transcriber = Transcriber(
                self.config["api_key"],
                gemini_api_key=gemini_key,
                llm_provider=llm_provider,
                groq_llm_model=groq_llm_model,
            )
            splash.update("Loading voice detection...")
        except Exception as e:
            splash.close()
            log.error(f"Failed to init transcriber: {e}")
            show_error("Voice-to-Text Error", f"Failed to initialize:\n{e}")
            sys.exit(1)

        # Pre-load Silero VAD in background (avoids 1s delay on first recording)
        import threading
        threading.Thread(target=self._preload_vad, daemon=True).start()

        lang = self.config.get("language", "ja")

        # Initialize overlay
        hotkey_label = self._format_hotkey_label(self.config.get("hotkey", "ctrl+shift+space"))
        self.overlay = RecordingOverlay(
            on_llm_toggle=self._toggle_llm_cleanup,
            lang=lang,
            on_button_click=self._on_button_click,
            hotkey_label=hotkey_label,
        )
        self.overlay.start()
        use_llm = self.config.get("use_llm_cleanup", self.config.get("use_gemini_cleanup", False))
        llm_provider = self.config.get("llm_provider", "groq")
        self.overlay.set_llm_state(use_llm, llm_provider)

        # Connect recorder audio levels to overlay waveform
        self.recorder.set_level_callback(
            lambda level, waveform: self.overlay.update_audio(level, waveform)
        )

        # Initialize settings GUI
        self.settings_gui = SettingsGUI(on_save=self._on_settings_saved)

        # Setup hotkey manager
        self._setup_hotkey()

        splash.update("Ready!")
        import time
        time.sleep(0.5)
        splash.close()

        # Setup and run system tray (blocks main thread)
        self.tray = TrayApp(
            on_settings=self._show_settings,
            on_quit=self._quit,
            on_mode_toggle=self._toggle_mode,
            on_llm_toggle=self._toggle_llm_cleanup,
            lang=lang,
        )
        self.tray.set_mode(self.config.get("mode", "push_to_talk"))
        use_llm = self.config.get("use_llm_cleanup", self.config.get("use_gemini_cleanup", False))
        llm_provider = self.config.get("llm_provider", "groq")
        self.tray.set_llm_cleanup(use_llm, llm_provider)

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

        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
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

    def _on_button_click(self):
        if self.hotkey_manager:
            self.hotkey_manager.trigger()

    @staticmethod
    def _format_hotkey_label(hotkey_str: str) -> str:
        parts = hotkey_str.strip().split("+")
        return "+".join(p.strip().upper() for p in parts)

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
            use_cleanup = self.config.get("use_llm_cleanup", self.config.get("use_gemini_cleanup", False))
            text = self.transcriber.transcribe(wav_data, use_cleanup=use_cleanup)
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
        # Recreate transcriber with new settings
        if self.transcriber:
            self.transcriber.close()
        gemini_key = new_config.get("gemini_api_key", "")
        llm_provider = new_config.get("llm_provider", "groq")
        groq_llm_model = new_config.get("groq_llm_model", "llama-3.1-8b-instant")
        self.transcriber = Transcriber(
            new_config["api_key"],
            gemini_api_key=gemini_key,
            llm_provider=llm_provider,
            groq_llm_model=groq_llm_model,
        )
        self.inserter.update_voice_commands(new_config.get("voice_commands", {}))
        self._setup_hotkey()
        if self.tray:
            self.tray.set_mode(new_config.get("mode", "push_to_talk"))
            use_llm = new_config.get("use_llm_cleanup", new_config.get("use_gemini_cleanup", False))
            self.tray.set_llm_cleanup(use_llm, llm_provider)
        if self.overlay:
            self.overlay.update_button_label(
                self._format_hotkey_label(new_config.get("hotkey", "ctrl+shift+space"))
            )
            use_llm = new_config.get("use_llm_cleanup", new_config.get("use_gemini_cleanup", False))
            self.overlay.set_llm_state(use_llm, llm_provider)
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

    def _toggle_llm_cleanup(self):
        current = self.config.get("use_llm_cleanup", self.config.get("use_gemini_cleanup", False))
        new_val = not current
        self.config["use_llm_cleanup"] = new_val
        self.config["use_gemini_cleanup"] = new_val  # keep in sync for backward compat
        save_config(self.config)

        llm_provider = self.config.get("llm_provider", "groq")
        # Update transcriber (close old client to release connections)
        if self.transcriber:
            self.transcriber.close()
        gemini_key = self.config.get("gemini_api_key", "")
        groq_llm_model = self.config.get("groq_llm_model", "llama-3.1-8b-instant")
        self.transcriber = Transcriber(
            self.config["api_key"],
            gemini_api_key=gemini_key,
            llm_provider=llm_provider,
            groq_llm_model=groq_llm_model,
        )
        if self.tray:
            self.tray.set_llm_cleanup(new_val, llm_provider)
        if self.overlay:
            self.overlay.set_llm_state(new_val, llm_provider)
        log.info(f"LLM cleanup ({llm_provider}): {'ON' if new_val else 'OFF'}")

    def _toggle_gemini_cleanup(self):
        """Backward-compatible alias for _toggle_llm_cleanup."""
        self._toggle_llm_cleanup()

    def _ensure_desktop_shortcut(self):
        """Create a desktop shortcut if one doesn't exist (frozen exe only)."""
        try:
            desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            shortcut_path = os.path.join(desktop, "Voice to Text.lnk")
            if os.path.exists(shortcut_path):
                return  # Already exists

            exe_path = sys.executable
            icon_path = os.path.join(os.path.dirname(exe_path), "icon.ico")
            # Fall back to bundled icon if not found next to exe
            if not os.path.exists(icon_path):
                icon_path = os.path.join(RESOURCE_DIR, "icon.ico")

            # Use VBScript to create a proper .lnk shortcut
            vbs_content = (
                f'Set WshShell = CreateObject("WScript.Shell")\n'
                f'Set shortcut = WshShell.CreateShortcut("{shortcut_path}")\n'
                f'shortcut.TargetPath = "{exe_path}"\n'
                f'shortcut.WorkingDirectory = "{os.path.dirname(exe_path)}"\n'
                f'shortcut.IconLocation = "{icon_path}, 0"\n'
                f'shortcut.Description = "Voice to Text - Press F2 to speak"\n'
                f'shortcut.Save\n'
            )
            vbs_path = os.path.join(os.environ.get("TEMP", "."), "vtt_shortcut.vbs")
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)
            os.system(f'cscript //nologo "{vbs_path}"')
            try:
                os.remove(vbs_path)
            except Exception:
                pass
            log.info(f"Desktop shortcut created: {shortcut_path}")
        except Exception as e:
            log.warning(f"Failed to create desktop shortcut: {e}")

    def _quit(self):
        log.info("Shutting down...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        if self.overlay:
            self.overlay.destroy()


def check_single_instance():
    """Prevent multiple instances using a Windows named mutex.

    A named mutex is automatically released by the OS when the process exits,
    even on crash or force-kill, so stale locks and PID-recycling issues are
    eliminated.
    """
    import ctypes

    # use_last_error=True makes ctypes populate ctypes.get_last_error() reliably
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    mutex_name = "VoiceToText_SingleInstance_Mutex"
    handle = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = ctypes.get_last_error()

    if last_error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        show_error("Voice to Text", "既に起動しています。\nタスクバー右下のアイコンを確認してください。")
        return False

    # Store the handle on the function object so it stays alive for the
    # entire process lifetime.  Windows will release it automatically on exit.
    check_single_instance._mutex_handle = handle

    # Remove any stale .lock file left by an older version of this app so
    # users are not confused by the leftover artefact.
    lock_path = os.path.join(APP_DIR, ".lock")
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass

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
        pass  # mutex handle is released automatically by Windows on process exit
