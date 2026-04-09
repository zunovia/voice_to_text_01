import threading
import subprocess
import sys
import os
import pystray
from autostart import is_autostart_enabled, enable_autostart, disable_autostart
from PIL import Image, ImageDraw


def _create_icon(color: str = "green", size: int = 64) -> Image.Image:
    """Create a simple circle icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    colors = {
        "green": (76, 175, 80, 255),
        "red": (244, 67, 54, 255),
        "gray": (158, 158, 158, 255),
        "orange": (255, 152, 0, 255),
    }
    fill = colors.get(color, colors["green"])
    draw.ellipse([margin, margin, size - margin, size - margin], fill=fill)
    # Microphone symbol
    cx, cy = size // 2, size // 2
    bar_w, bar_h = size // 8, size // 3
    draw.rounded_rectangle(
        [cx - bar_w, cy - bar_h, cx + bar_w, cy + bar_h // 2],
        radius=bar_w,
        fill=(255, 255, 255, 230),
    )
    draw.arc(
        [cx - bar_w * 2, cy - bar_h // 2, cx + bar_w * 2, cy + bar_h],
        start=0,
        end=180,
        fill=(255, 255, 255, 200),
        width=2,
    )
    draw.line([cx, cy + bar_h, cx, cy + bar_h + 6], fill=(255, 255, 255, 200), width=2)
    return img


class TrayApp:
    def __init__(self, on_settings=None, on_quit=None, on_mode_toggle=None, on_gemini_toggle=None):
        self.on_settings = on_settings or (lambda: None)
        self.on_quit = on_quit or (lambda: None)
        self.on_mode_toggle = on_mode_toggle or (lambda: None)
        self.on_gemini_toggle = on_gemini_toggle or (lambda: None)
        self._gemini_cleanup = False
        self._icon_normal = _create_icon("green")
        self._icon_recording = _create_icon("red")
        self._icon_processing = _create_icon("orange")
        self._icon = None
        self._current_mode = "push_to_talk"

    def _get_mode_text(self):
        if self._current_mode == "push_to_talk":
            return "Push-to-Talk (Ctrl+Shift+Space を押しながら話す)"
        else:
            return "Toggle (Ctrl+Shift+Space で開始/停止)"

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Voice-to-Text", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"使い方: {self._get_mode_text()}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"モード切替 (現在: {'Push-to-Talk' if self._current_mode == 'push_to_talk' else 'Toggle'})",
                self._toggle_mode,
            ),
            pystray.MenuItem(
                lambda item: f"Gemini文章整形: {'ON (高精度)' if self._gemini_cleanup else 'OFF (高速)'}",
                self._toggle_gemini,
            ),
            pystray.MenuItem("設定を開く", self._open_settings),
            pystray.MenuItem(
                lambda item: f"自動起動: {'ON' if is_autostart_enabled() else 'OFF'}",
                self._toggle_autostart,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self._quit),
        )
        self._icon = pystray.Icon(
            "voice_to_text",
            self._icon_normal,
            "Voice-to-Text\nCtrl+Shift+Space で録音",
            menu,
        )
        self._icon.run()

    def set_recording(self, recording: bool):
        if self._icon:
            if recording:
                self._icon.icon = self._icon_recording
                self._icon.title = "Voice-to-Text [録音中...]"
            else:
                self._icon.icon = self._icon_normal
                self._icon.title = "Voice-to-Text\nCtrl+Shift+Space で録音"

    def set_processing(self):
        if self._icon:
            self._icon.icon = self._icon_processing
            self._icon.title = "Voice-to-Text [変換中...]"

    def set_mode(self, mode: str):
        self._current_mode = mode

    def set_gemini_cleanup(self, enabled: bool):
        self._gemini_cleanup = enabled

    def _toggle_gemini(self):
        self.on_gemini_toggle()

    def _toggle_autostart(self):
        if is_autostart_enabled():
            disable_autostart()
        else:
            enable_autostart()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _open_settings(self):
        """Open settings via callback to main app."""
        self.on_settings()

    def _toggle_mode(self):
        self.on_mode_toggle()

    def _quit(self):
        self.on_quit()
        if self._icon:
            self._icon.stop()
