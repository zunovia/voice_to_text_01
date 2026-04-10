import tkinter as tk
import threading
import os
import sys


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class SplashScreen:
    """Show a splash screen while the app is loading."""

    def __init__(self):
        self._root = None
        self._label = None
        self._ready = threading.Event()

    def show(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def update(self, text: str):
        if self._root and self._label:
            self._root.after(0, lambda: self._label.config(text=text))

    def close(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    def _run(self):
        BG = "#1a1a2e"

        self._root = tk.Tk()
        self._root.title("")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.configure(bg=BG)

        w, h = 320, 120
        self._root.geometry(f"{w}x{h}")

        # Center on screen
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 2
        self._root.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self._root, bg=BG, padx=20, pady=15)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Voice to Text", font=("Segoe UI", 16, "bold"),
                 fg="#FFFFFF", bg=BG).pack()

        self._label = tk.Label(frame, text="Loading...", font=("Segoe UI", 10),
                               fg="#888888", bg=BG)
        self._label.pack(pady=(10, 0))

        self._ready.set()
        self._root.mainloop()
