import sys
import time
import pyperclip
import pyautogui

# Disable pyautogui's failsafe pause
pyautogui.PAUSE = 0.02

IS_MAC = sys.platform == "darwin"


class TextInserter:
    def __init__(self, voice_commands: dict = None):
        self.voice_commands = voice_commands or {}

    def process_and_insert(self, text: str):
        """Process voice commands in text, then insert at cursor position."""
        processed = self._process_voice_commands(text)
        if not processed:
            return

        # Split by newlines to handle "エンター" commands
        segments = processed.split("\n")

        for i, segment in enumerate(segments):
            if segment:
                self._paste_text(segment)
            if i < len(segments) - 1:
                pyautogui.press("enter")
                time.sleep(0.02)

    def insert_raw(self, text: str):
        """Insert text as-is without voice command processing."""
        if text:
            self._paste_text(text)

    def _paste_text(self, text: str):
        """Insert text via clipboard + Ctrl+V, preserving original clipboard."""
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        pyperclip.copy(text)
        time.sleep(0.02)
        if IS_MAC:
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")
        time.sleep(0.05)

        # Restore original clipboard
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

    def _process_voice_commands(self, text: str) -> str:
        """Replace voice command words with their corresponding characters."""
        result = text
        for command, replacement in self.voice_commands.items():
            result = result.replace(command, replacement)
        return result

    def update_voice_commands(self, voice_commands: dict):
        self.voice_commands = voice_commands
