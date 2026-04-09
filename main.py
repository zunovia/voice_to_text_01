import sys
import os
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Setup logging to file (essential for pythonw where there's no console)
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voicetotext.log")
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
    from settings_manager import load_config, save_config
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
        if not self.config.get("api_key"):
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

        # Initialize overlay
        self.overlay = RecordingOverlay(on_gemini_toggle=self._toggle_gemini_cleanup)
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
        )
        self.tray.set_mode(self.config.get("mode", "push_to_talk"))
        self.tray.set_gemini_cleanup(self.config.get("use_gemini_cleanup", False))

        hotkey = self.config.get("hotkey", "ctrl+shift+space")
        mode = self.config.get("mode", "push_to_talk")
        log.info(f"Voice-to-Text started! Hotkey: {hotkey}, Mode: {mode}")

        self.tray.start()  # This blocks until quit

    def _prompt_api_key(self) -> bool:
        """Show a welcome dialog to enter API key on first run."""
        import webbrowser
        result = {"key": ""}

        BG = "#1a1a2e"
        CARD = "#16213e"
        HIGHLIGHT = "#4FC3F7"
        GREEN = "#4CAF50"

        root = tk.Tk()
        root.title("Voice to Text")
        root.geometry("500x420")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=BG)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass

        root.update_idletasks()
        x = (root.winfo_screenwidth() - 500) // 2
        y = (root.winfo_screenheight() - 420) // 2
        root.geometry(f"500x420+{x}+{y}")
        root.lift()
        root.focus_force()

        main = tk.Frame(root, bg=BG, padx=30, pady=20)
        main.pack(fill="both", expand=True)

        # Title
        tk.Label(main, text="Voice to Text", font=("Segoe UI", 22, "bold"),
                 fg="#FFFFFF", bg=BG).pack(pady=(0, 3))
        tk.Label(main, text="どのアプリでも声でテキスト入力", font=("Segoe UI", 10),
                 fg="#888888", bg=BG).pack(pady=(0, 20))

        # Card
        card = tk.Frame(main, bg=CARD, padx=20, pady=15)
        card.pack(fill="x")

        tk.Label(card, text="Groq API Key を入力してください", font=("Segoe UI", 11, "bold"),
                 fg=HIGHLIGHT, bg=CARD).pack(anchor="w", pady=(0, 5))
        tk.Label(card, text="無料で取得できます（14,400回/日まで無料）", font=("Segoe UI", 9),
                 fg="#888888", bg=CARD).pack(anchor="w", pady=(0, 10))

        key_var = tk.StringVar()
        entry = tk.Entry(card, textvariable=key_var, width=50,
                         bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                         relief="flat", font=("Consolas", 11))
        entry.pack(fill="x", pady=(0, 10))
        entry.focus_set()

        # Get API key link
        link_frame = tk.Frame(card, bg=CARD)
        link_frame.pack(fill="x", pady=(0, 5))
        tk.Label(link_frame, text="APIキーを持っていない場合:", font=("Segoe UI", 9),
                 fg="#888888", bg=CARD).pack(side="left")
        link = tk.Label(link_frame, text="Groqで無料取得", font=("Segoe UI", 9, "underline"),
                        fg=HIGHLIGHT, bg=CARD, cursor="hand2")
        link.pack(side="left", padx=(5, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        # Steps
        steps = tk.Label(card, text="1. 上のリンクからGroqにサインアップ\n2. API Keys → Create API Key\n3. キーをコピーして上の欄に貼り付け",
                         font=("Segoe UI", 9), fg="#666666", bg=CARD, justify="left")
        steps.pack(anchor="w", pady=(5, 0))

        # Buttons
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(pady=(20, 0))

        def on_save():
            key = key_var.get().strip()
            if key:
                result["key"] = key
                root.destroy()
            else:
                messagebox.showwarning("Warning", "API Key を入力してください!", parent=root)

        def on_cancel():
            root.destroy()

        save_btn = tk.Button(btn_frame, text="はじめる", font=("Segoe UI", 12, "bold"),
                             fg="#FFFFFF", bg=GREEN, activebackground="#388E3C",
                             relief="flat", padx=30, pady=5, cursor="hand2",
                             command=on_save)
        save_btn.pack(side="left", padx=5)
        cancel_btn = tk.Button(btn_frame, text="キャンセル", font=("Segoe UI", 10),
                               fg="#888888", bg="#333333", activebackground="#444444",
                               relief="flat", padx=15, pady=5, cursor="hand2",
                               command=on_cancel)
        cancel_btn.pack(side="left", padx=5)

        root.bind("<Return>", lambda e: on_save())
        root.protocol("WM_DELETE_WINDOW", on_cancel)

        root.mainloop()

        if result["key"]:
            self.config["api_key"] = result["key"]
            save_config(self.config)
            log.info("API Key saved successfully.")
            return True
        return False

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
        self.recorder.start()
        if self.tray:
            self.tray.set_recording(True)
        if self.overlay:
            self.overlay.show("Recording...")

    def _on_recording_stop(self):
        log.info("Recording stopped. Processing...")
        wav_data = self.recorder.stop()
        duration = self.recorder.get_duration()

        if self.tray:
            self.tray.set_processing()
        if self.overlay:
            self.overlay.update_text("Processing...")

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
                self.overlay.update_text("Error!")
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
                if not self._tk_root:
                    self._tk_root = tk.Tk()
                    self._tk_root.withdraw()
                self.settings_gui.show()
                self._tk_root.mainloop()
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


if __name__ == "__main__":
    try:
        app = VoiceToTextApp()
        app.run()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        show_error("Voice-to-Text Error", f"Unexpected error:\n{e}")
        sys.exit(1)
