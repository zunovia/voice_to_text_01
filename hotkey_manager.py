import threading
from pynput import keyboard


class HotkeyManager:
    def __init__(self, hotkey_str: str, mode: str, on_start=None, on_stop=None):
        """
        hotkey_str: e.g. "ctrl+shift+space"
        mode: "push_to_talk" or "toggle"
        on_start: callback when recording should start
        on_stop: callback when recording should stop
        """
        self.mode = mode
        self.on_start = on_start or (lambda: None)
        self.on_stop = on_stop or (lambda: None)
        self._is_active = False
        self._hotkey_keys = self._parse_hotkey(hotkey_str)
        self._pressed_keys = set()
        self._listener = None
        self._running = False

    def start(self):
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    def trigger(self):
        """Toggle recording from button click (always toggle, even in push_to_talk mode)."""
        if not self._is_active:
            self._is_active = True
            threading.Thread(target=self.on_start, daemon=True).start()
        else:
            self._is_active = False
            threading.Thread(target=self.on_stop, daemon=True).start()

    def update_hotkey(self, hotkey_str: str):
        self._hotkey_keys = self._parse_hotkey(hotkey_str)

    def update_mode(self, mode: str):
        self.mode = mode

    def _on_press(self, key):
        if not self._running:
            return
        normalized = self._normalize_key(key)
        if normalized:
            self._pressed_keys.add(normalized)

        if self._is_hotkey_pressed():
            if self.mode == "push_to_talk":
                if not self._is_active:
                    self._is_active = True
                    threading.Thread(target=self.on_start, daemon=True).start()
            elif self.mode == "toggle":
                if not self._is_active:
                    self._is_active = True
                    threading.Thread(target=self.on_start, daemon=True).start()
                else:
                    self._is_active = False
                    threading.Thread(target=self.on_stop, daemon=True).start()

    def _on_release(self, key):
        if not self._running:
            return
        normalized = self._normalize_key(key)
        if normalized:
            self._pressed_keys.discard(normalized)

        if self.mode == "push_to_talk" and self._is_active:
            if not self._is_hotkey_pressed():
                self._is_active = False
                threading.Thread(target=self.on_stop, daemon=True).start()

    def _is_hotkey_pressed(self) -> bool:
        return self._hotkey_keys.issubset(self._pressed_keys)

    def _normalize_key(self, key) -> str | None:
        try:
            if hasattr(key, "char") and key.char:
                return key.char.lower()
        except AttributeError:
            pass
        key_map = {
            keyboard.Key.ctrl_l: "ctrl",
            keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.shift_l: "shift",
            keyboard.Key.shift_r: "shift",
            keyboard.Key.alt_l: "alt",
            keyboard.Key.alt_r: "alt",
            keyboard.Key.cmd: "cmd",
            keyboard.Key.cmd_l: "cmd",
            keyboard.Key.cmd_r: "cmd",
            keyboard.Key.space: "space",
            keyboard.Key.enter: "enter",
            keyboard.Key.tab: "tab",
            keyboard.Key.esc: "esc",
            keyboard.Key.f1: "f1",
            keyboard.Key.f2: "f2",
            keyboard.Key.f3: "f3",
            keyboard.Key.f4: "f4",
            keyboard.Key.f5: "f5",
            keyboard.Key.f6: "f6",
            keyboard.Key.f7: "f7",
            keyboard.Key.f8: "f8",
            keyboard.Key.f9: "f9",
            keyboard.Key.f10: "f10",
            keyboard.Key.f11: "f11",
            keyboard.Key.f12: "f12",
        }
        return key_map.get(key)

    @staticmethod
    def _parse_hotkey(hotkey_str: str) -> set:
        parts = hotkey_str.lower().replace(" ", "").split("+")
        return set(parts)
