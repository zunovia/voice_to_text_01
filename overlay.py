import tkinter as tk
import threading
import collections


class RecordingOverlay:
    """Overlay window with real-time waveform visualization and Gemini toggle."""

    WIDTH = 320
    HEIGHT = 110
    WAVE_COLOR = "#4FC3F7"
    WAVE_COLOR_LOUD = "#FF7043"
    BG_COLOR = "#1E1E1E"
    BAR_COUNT = 40

    def __init__(self, on_gemini_toggle=None):
        self._root = None
        self._canvas = None
        self._label = None
        self._gemini_btn = None
        self._visible = False
        self._thread = None
        self._ready = threading.Event()
        self._levels = collections.deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._waveform = [0.0] * self.BAR_COUNT
        self._animating = False
        self._gemini_on = False
        self._on_gemini_toggle = on_gemini_toggle

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def show(self, text="Recording..."):
        if self._root:
            self._root.after(0, lambda: self._do_show(text))

    def hide(self):
        if self._root:
            self._root.after(0, self._do_hide)

    def update_text(self, text: str):
        if self._root and self._label:
            self._root.after(0, lambda: self._label.config(text=text))

    def update_audio(self, level: float, waveform: list):
        self._levels.append(level)
        if waveform:
            if len(waveform) >= self.BAR_COUNT:
                self._waveform = waveform[:self.BAR_COUNT]
            else:
                self._waveform = waveform + [0.0] * (self.BAR_COUNT - len(waveform))

    def set_gemini_state(self, enabled: bool):
        self._gemini_on = enabled
        if self._root and self._gemini_btn:
            self._root.after(0, self._update_gemini_btn)

    def destroy(self):
        if self._root:
            self._root.after(0, self._root.destroy)

    def _run(self):
        self._root = tk.Tk()
        self._root.title("")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.configure(bg=self.BG_COLOR)

        # Main frame
        main_frame = tk.Frame(self._root, bg=self.BG_COLOR, padx=10, pady=6)
        main_frame.pack(fill="both", expand=True)

        # Top row: status label + Gemini button
        top_frame = tk.Frame(main_frame, bg=self.BG_COLOR)
        top_frame.pack(fill="x")

        self._label = tk.Label(
            top_frame,
            text="Recording...",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.BG_COLOR,
        )
        self._label.pack(side="left")

        # Gemini toggle button
        self._gemini_btn = tk.Label(
            top_frame,
            text="Gemini OFF",
            font=("Segoe UI", 8),
            fg="#999999",
            bg="#333333",
            padx=6,
            pady=1,
            cursor="hand2",
        )
        self._gemini_btn.pack(side="right")
        self._gemini_btn.bind("<Button-1>", self._on_gemini_click)

        # Waveform canvas
        self._canvas = tk.Canvas(
            main_frame,
            width=self.WIDTH - 20,
            height=60,
            bg=self.BG_COLOR,
            highlightthickness=0,
        )
        self._canvas.pack(pady=(4, 2))

        # Position at bottom-right
        self._root.update_idletasks()
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = screen_w - self.WIDTH - 20
        y = screen_h - self.HEIGHT - 60
        self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        self._root.withdraw()
        self._ready.set()
        self._root.mainloop()

    def _update_gemini_btn(self):
        if self._gemini_btn:
            if self._gemini_on:
                self._gemini_btn.config(
                    text="Gemini ON",
                    fg="#FFFFFF",
                    bg="#4CAF50",
                )
            else:
                self._gemini_btn.config(
                    text="Gemini OFF",
                    fg="#999999",
                    bg="#333333",
                )

    def _on_gemini_click(self, event):
        if self._on_gemini_toggle:
            self._on_gemini_toggle()

    def _do_show(self, text: str):
        if self._label:
            self._label.config(text=text)
        self._update_gemini_btn()
        if self._root:
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            x = screen_w - self.WIDTH - 20
            y = screen_h - self.HEIGHT - 60
            self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
            self._root.deiconify()
        self._visible = True
        self._animating = True
        self._levels = collections.deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._animate()

    def _do_hide(self):
        self._animating = False
        self._visible = False
        if self._root:
            self._root.withdraw()

    def _animate(self):
        if not self._animating or not self._canvas:
            return

        canvas = self._canvas
        canvas.delete("all")

        w = canvas.winfo_width() or (self.WIDTH - 20)
        h = canvas.winfo_height() or 60
        mid_y = h / 2
        bar_w = max(2, (w - self.BAR_COUNT) / self.BAR_COUNT)
        gap = 1

        for i in range(self.BAR_COUNT):
            val = abs(self._waveform[i]) if i < len(self._waveform) else 0.0
            bar_h = max(2, val * h * 0.9)

            x0 = i * (bar_w + gap)
            x1 = x0 + bar_w
            y0 = mid_y - bar_h / 2
            y1 = mid_y + bar_h / 2

            if val > 0.3:
                color = self.WAVE_COLOR_LOUD
            elif val > 0.05:
                color = self.WAVE_COLOR
            else:
                color = "#455A64"

            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

        if self._animating:
            self._root.after(33, self._animate)
