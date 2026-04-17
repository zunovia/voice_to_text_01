import tkinter as tk
import threading
import collections
import ctypes
from i18n import t


class FloatingButton:
    """Always-visible floating buttons: mic toggle + Enter key."""

    BTN_SIZE = 60
    ENTER_H = 34
    GAP = 5
    # Soft pastel-dark palette
    COLOR_IDLE = "#3E3B5C"
    COLOR_IDLE_HOVER = "#524E75"
    COLOR_IDLE_RING = "#6C63FF"
    COLOR_RECORDING = "#C62828"
    COLOR_RECORDING_HOVER = "#E53935"
    COLOR_RECORDING_RING = "#FF8A80"
    COLOR_ENTER = "#2E4A3E"
    COLOR_ENTER_HOVER = "#3E5F50"
    COLOR_ENTER_PRESS = "#4E7562"
    COLOR_ENTER_RING = "#66BB6A"
    DRAG_THRESHOLD = 4
    MIC_ICON = "\U0001F3A4"

    def __init__(self, root, on_click=None, hotkey_label="F2"):
        self._root = root
        self._on_click = on_click
        self._recording = False

        win_w = self.BTN_SIZE + 8  # extra space for glow ring
        win_h = self.BTN_SIZE + 8 + self.GAP + self.ENTER_H

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.95)

        # Prevent focus stealing on click (Windows WS_EX_NOACTIVATE)
        self._win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_APPWINDOW = 0x00040000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

        self._win.configure(bg="#010101")
        self._win.attributes("-transparentcolor", "#010101")

        # Mic button canvas (top) — bigger for glow ring
        mic_canvas_size = self.BTN_SIZE + 8
        self._canvas = tk.Canvas(
            self._win, width=mic_canvas_size, height=mic_canvas_size,
            bg="#010101", highlightthickness=0, cursor="hand2",
        )
        self._canvas.pack()

        # Enter button canvas (bottom)
        self._enter_canvas = tk.Canvas(
            self._win, width=win_w, height=self.ENTER_H,
            bg="#010101", highlightthickness=0, cursor="hand2",
        )
        self._enter_canvas.pack(pady=(self.GAP, 0))

        self._hotkey_label = hotkey_label
        self._draw_mic_button()
        self._draw_enter_button()

        # Position: bottom-right, above overlay area
        self._win.update_idletasks()
        screen_w = self._win.winfo_screenwidth()
        screen_h = self._win.winfo_screenheight()
        x = screen_w - win_w - 16
        y = screen_h - win_h - 180
        self._win.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Drag support (shared for whole window)
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0
        self._dragged = False

        # Mic button events
        self._canvas.bind("<ButtonPress-1>", self._on_mic_press)
        self._canvas.bind("<B1-Motion>", self._on_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_mic_release)
        self._canvas.bind("<Enter>", self._on_mic_enter)
        self._canvas.bind("<Leave>", self._on_mic_leave)

        # Enter button events
        self._enter_canvas.bind("<ButtonPress-1>", self._on_enter_press)
        self._enter_canvas.bind("<B1-Motion>", self._on_motion)
        self._enter_canvas.bind("<ButtonRelease-1>", self._on_enter_release)
        self._enter_canvas.bind("<Enter>", self._on_enter_hover_in)
        self._enter_canvas.bind("<Leave>", self._on_enter_hover_out)

    # --- Drawing ---

    def _draw_mic_button(self, color=None):
        if color is None:
            color = self.COLOR_RECORDING if self._recording else self.COLOR_IDLE
        ring = self.COLOR_RECORDING_RING if self._recording else self.COLOR_IDLE_RING
        c = self._canvas
        s = self.BTN_SIZE + 8  # canvas size
        c.delete("all")
        # Outer glow ring — visible on any background
        c.create_oval(0, 0, s, s, fill="", outline=ring, width=3)
        # Inner shadow
        pad = 4
        c.create_oval(pad + 1, pad + 1, s - pad + 1, s - pad + 1,
                       fill="#1A1A2E", outline="")
        # Main circle
        c.create_oval(pad, pad, s - pad, s - pad,
                       fill=color, outline="")
        # Inner highlight (top-left shine)
        c.create_arc(pad + 4, pad + 4, s - pad - 12, s - pad - 12,
                      start=100, extent=60, fill="", outline="#FFFFFF",
                      width=1, style="arc")
        # Mic icon
        cx, cy = s // 2, s // 2
        c.create_text(cx, cy - 4,
                       text=self.MIC_ICON, font=("Segoe UI Emoji", 16),
                       fill="#FFFFFF")
        # Hotkey label
        c.create_text(cx, cy + 19,
                       text=self._hotkey_label, font=("Segoe UI", 7, "bold"),
                       fill="#DDDDDD")

    def _draw_enter_button(self, color=None):
        if color is None:
            color = self.COLOR_ENTER
        c = self._enter_canvas
        c.delete("all")
        w = self.BTN_SIZE + 8
        h = self.ENTER_H
        r = 12
        # Outer glow rounded rect
        self._rounded_rect(c, 0, 0, w, h, r, fill="", outline=self.COLOR_ENTER_RING, width=2)
        # Shadow
        self._rounded_rect(c, 2, 2, w - 2, h - 1, r - 1, fill="#1A2E1A", outline="")
        # Main body
        self._rounded_rect(c, 1, 1, w - 1, h - 2, r - 1, fill=color, outline="")
        # Enter label with arrow
        c.create_text(w // 2, h // 2, text="Enter \u21B5",
                       font=("Segoe UI", 9, "bold"), fill="#E0E0E0")

    @staticmethod
    def _rounded_rect(canvas, x0, y0, x1, y1, r, **kwargs):
        """Draw a rounded rectangle on canvas."""
        fill = kwargs.get("fill", "")
        outline = kwargs.get("outline", "")
        width = kwargs.get("width", 1)
        points = [
            x0 + r, y0, x1 - r, y0,
            x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1,
            x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r,
            x0, y0 + r, x0, y0,
        ]
        canvas.create_polygon(points, smooth=True,
                              fill=fill, outline=outline, width=width)

    # --- Public API ---

    def set_recording(self, recording: bool):
        self._recording = recording
        self._draw_mic_button()

    def update_label(self, text: str):
        self._hotkey_label = text
        self._draw_mic_button()

    def destroy(self):
        self._win.destroy()

    # --- Drag (shared) ---

    def _start_drag(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._win_start_x = self._win.winfo_x()
        self._win_start_y = self._win.winfo_y()
        self._dragged = False

    def _on_motion(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        if abs(dx) > self.DRAG_THRESHOLD or abs(dy) > self.DRAG_THRESHOLD:
            self._dragged = True
        if self._dragged:
            new_x = self._win_start_x + dx
            new_y = self._win_start_y + dy
            self._win.geometry(f"+{new_x}+{new_y}")

    # --- Mic button events ---

    def _on_mic_enter(self, event):
        color = self.COLOR_RECORDING_HOVER if self._recording else self.COLOR_IDLE_HOVER
        self._draw_mic_button(color)

    def _on_mic_leave(self, event):
        self._draw_mic_button()

    def _on_mic_press(self, event):
        self._start_drag(event)
        bright = "#FF5252" if self._recording else "#6860A0"
        self._draw_mic_button(bright)

    def _on_mic_release(self, event):
        if not self._dragged and self._on_click:
            self._on_click()
        self._draw_mic_button()

    # --- Enter button events ---

    def _on_enter_hover_in(self, event):
        self._draw_enter_button(self.COLOR_ENTER_HOVER)

    def _on_enter_hover_out(self, event):
        self._draw_enter_button()

    def _on_enter_press(self, event):
        self._start_drag(event)
        self._draw_enter_button(self.COLOR_ENTER_PRESS)

    def _on_enter_release(self, event):
        if not self._dragged:
            self._draw_enter_button()
            threading.Thread(target=self._send_enter, daemon=True).start()
        else:
            self._draw_enter_button()

    @staticmethod
    def _send_enter():
        import pyautogui
        pyautogui.press("enter")


class RecordingOverlay:
    """Overlay window with real-time waveform visualization and Gemini toggle."""

    WIDTH = 320
    HEIGHT = 110
    WAVE_COLOR = "#4FC3F7"
    WAVE_COLOR_LOUD = "#FF7043"
    BG_COLOR = "#1E1E1E"
    BAR_COUNT = 40

    def __init__(self, on_gemini_toggle=None, lang="ja", on_button_click=None, hotkey_label="F2"):
        self._root = None
        self._canvas = None
        self._label = None
        self._gemini_btn = None
        self._float_btn = None
        self._visible = False
        self._thread = None
        self._ready = threading.Event()
        self._levels = collections.deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._waveform = [0.0] * self.BAR_COUNT
        self._animating = False
        self._gemini_on = False
        self._on_gemini_toggle = on_gemini_toggle
        self._on_button_click = on_button_click
        self._hotkey_label = hotkey_label
        self._lang = lang

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def show(self, text="Recording..."):
        if self._root:
            try:
                self._root.after(0, lambda: self._do_show(text))
            except RuntimeError:
                pass

    def hide(self):
        if self._root:
            try:
                self._root.after(0, self._do_hide)
            except RuntimeError:
                pass

    def update_text(self, text: str):
        if self._root and self._label:
            try:
                self._root.after(0, lambda: self._label.config(text=text))
            except RuntimeError:
                pass

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
            try:
                self._root.after(0, self._update_gemini_btn)
            except RuntimeError:
                pass  # mainloop not yet running; state will be applied on next show()

    def update_button_label(self, text: str):
        if self._root and self._float_btn:
            try:
                self._root.after(0, lambda: self._float_btn.update_label(text))
            except RuntimeError:
                pass

    def set_button_recording(self, recording: bool):
        if self._root and self._float_btn:
            try:
                self._root.after(0, lambda: self._float_btn.set_recording(recording))
            except RuntimeError:
                pass

    def destroy(self):
        if self._root:
            def _destroy():
                if self._float_btn:
                    self._float_btn.destroy()
                self._root.destroy()
            try:
                self._root.after(0, _destroy)
            except RuntimeError:
                pass

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

        # Create floating button
        self._float_btn = FloatingButton(
            self._root,
            on_click=self._on_float_btn_click,
            hotkey_label=self._hotkey_label,
        )

        # Signal readiness AFTER mainloop starts processing events,
        # so that self._root.after() calls from other threads are safe.
        self._root.after(0, self._ready.set)
        self._root.mainloop()

    def _update_gemini_btn(self):
        if self._gemini_btn:
            if self._gemini_on:
                self._gemini_btn.config(
                    text=t("gemini_on", self._lang),
                    fg="#FFFFFF",
                    bg="#4CAF50",
                )
            else:
                self._gemini_btn.config(
                    text=t("gemini_off", self._lang),
                    fg="#999999",
                    bg="#333333",
                )

    def _on_float_btn_click(self):
        if self._on_button_click:
            threading.Thread(target=self._on_button_click, daemon=True).start()

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
        if self._float_btn:
            self._float_btn.set_recording(True)
        self._animate()

    def _do_hide(self):
        self._animating = False
        self._visible = False
        if self._root:
            self._root.withdraw()
        if self._float_btn:
            self._float_btn.set_recording(False)

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
