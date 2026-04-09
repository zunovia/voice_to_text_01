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
        self.overlay = RecordingOverlay()
        self.overlay.start()

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
        )
        self.tray.set_mode(self.config.get("mode", "push_to_talk"))

        hotkey = self.config.get("hotkey", "ctrl+shift+space")
        mode = self.config.get("mode", "push_to_talk")
        log.info(f"Voice-to-Text started! Hotkey: {hotkey}, Mode: {mode}")

        self.tray.start()  # This blocks until quit

    def _prompt_api_key(self) -> bool:
        """Show a dialog to enter API key on first run."""
        result = {"key": ""}

        root = tk.Tk()
        root.title("Voice-to-Text - Initial Setup")
        root.geometry("500x250")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        # Center on screen
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 500) // 2
        y = (root.winfo_screenheight() - 250) // 2
        root.geometry(f"500x250+{x}+{y}")

        # Force to foreground
        root.lift()
        root.focus_force()

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Voice-to-Text へようこそ!\n\nGemini API Key を入力してください。\nhttps://aistudio.google.com/apikey から取得できます。",
            justify="center",
            wraplength=400,
        ).pack(pady=(0, 15))

        key_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=key_var, width=55)
        entry.pack(pady=(0, 15))
        entry.focus_set()

        def on_save():
            key = key_var.get().strip()
            if key:
                result["key"] = key
                root.destroy()
            else:
                messagebox.showwarning("Warning", "API Key を入力してください!", parent=root)

        def on_cancel():
            root.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Save", command=on_save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)

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
