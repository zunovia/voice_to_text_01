import tkinter as tk
import threading
import collections
import ctypes
from i18n import t


class FloatingButton:
    """Always-visible floating buttons: mic toggle + Enter key."""

    # Unified vertical capsule: mic (top) + Enter (bottom). Teal / cyan theme.
    W = 64            # capsule width
    MIC_H = 58        # mic section height
    ENTER_H = 32      # enter section height
    MARGIN = 5        # space for shadow / ring glow
    RADIUS = 20       # corner radius
    ACCENT = "#2DD4BF"         # teal accent (idle ring)
    ACCENT_SOFT = "#1C7E73"    # dim teal (idle mic inner ring)
    ACCENT_BRIGHT = "#5EEAD4"  # pressed (idle)
    REC = "#FB7185"            # coral/pink (recording)
    REC_BRIGHT = "#FDA4AF"     # pressed (recording)
    BODY = "#1B232B"           # dark slate (mic section)
    ENTER_FILL = "#33424E"     # lighter slate bar (Enter section) — clearly distinct
    ENTER_HOVER = "#3E4F5C"
    ENTER_PRESS = "#4A5D6B"
    ENTER_TEXT = "#FFFFFF"
    DIVIDER = "#33414A"
    SHADOW = "#0E1318"
    TEXT = "#D7F5EF"
    TEXT_DIM = "#8FA6A1"
    DRAG_THRESHOLD = 4
    MIC_ICON = "\U0001F3A4"

    def __init__(self, root, on_click=None, hotkey_label="F2"):
        self._root = root
        self._on_click = on_click
        self._recording = False
        self._hover = None
        self._hotkey_label = hotkey_label

        cw = self.W + 2 * self.MARGIN
        ch = self.MIC_H + self.ENTER_H + 2 * self.MARGIN

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.95)

        # Prevent focus stealing on click (Windows WS_EX_NOACTIVATE)
        self._win.update_idletasks()
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self._win.winfo_id())
        self._hwnd = hwnd
        self._user32 = user32
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_APPWINDOW = 0x00040000
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        # Use pointer-sized args so HWND_TOPMOST (-1) isn't truncated on 64-bit.
        try:
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = ctypes.c_bool
        except Exception:
            pass

        self._win.configure(bg="#010101")
        self._win.attributes("-transparentcolor", "#010101")

        # Single canvas holds the whole capsule (mic on top, Enter on bottom)
        self._canvas = tk.Canvas(
            self._win, width=cw, height=ch,
            bg="#010101", highlightthickness=0, cursor="hand2",
        )
        self._canvas.pack()
        self._draw()

        # Position: bottom-right, above overlay area
        self._win.update_idletasks()
        screen_w = self._win.winfo_screenwidth()
        screen_h = self._win.winfo_screenheight()
        x = screen_w - cw - 16
        y = screen_h - ch - 180
        self._win.geometry(f"{cw}x{ch}+{x}+{y}")

        # Drag support
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0
        self._dragged = False

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", self._on_leave)

        # Windows can let a newer topmost / fullscreen window slip above ours,
        # so re-pin to the top of the z-order periodically (without stealing focus).
        self._win.after(1500, self._keep_on_top)

    def _keep_on_top(self):
        """Re-assert HWND_TOPMOST without activating/stealing focus."""
        try:
            HWND_TOPMOST = ctypes.c_void_p(-1)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            self._user32.SetWindowPos(
                self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception:
            pass
        try:
            self._win.after(1500, self._keep_on_top)
        except (RuntimeError, tk.TclError):
            pass

    # --- Drawing ---

    def _section_at(self, y):
        """Which half of the capsule a y-coordinate falls in."""
        return "mic" if y < self.MARGIN + self.MIC_H else "enter"

    def _draw(self, pressed=None):
        c = self._canvas
        c.delete("all")
        m = self.MARGIN
        x0, y0 = m, m
        x1 = m + self.W
        y1 = m + self.MIC_H + self.ENTER_H
        r = self.RADIUS
        dy = y0 + self.MIC_H  # boundary between mic (top) and Enter (bottom)
        rec = self._recording
        ring = self.REC if rec else self.ACCENT
        if pressed == "mic":
            ring = self.REC_BRIGHT if rec else self.ACCENT_BRIGHT

        if pressed == "enter":
            enter_fill = self.ENTER_PRESS
        elif self._hover == "enter":
            enter_fill = self.ENTER_HOVER
        else:
            enter_fill = self.ENTER_FILL

        # Soft drop shadow
        self._rounded_rect(c, x0 + 1, y0 + 2, x1 + 1, y1 + 2, r, fill=self.SHADOW)
        # Fill the whole capsule with the Enter (lighter) color first...
        self._rounded_rect(c, x0, y0, x1, y1, r, fill=enter_fill)
        # ...then lay the dark mic section over the top half (rounded top, square bottom)
        self._rounded_rect(c, x0, y0, x1, dy, r, fill=self.BODY)
        c.create_rectangle(x0, dy - r, x1, dy, fill=self.BODY, outline="")
        # Outer accent ring + a crisp teal divider so the two halves read separately
        self._rounded_rect(c, x0, y0, x1, y1, r, outline=ring, width=2)
        c.create_line(x0 + 1, dy, x1 - 1, dy, fill=self.ACCENT, width=1)

        # Mic section (dark + teal)
        mcx = (x0 + x1) // 2
        mcy = y0 + self.MIC_H // 2
        rad = 18
        if rec:
            c.create_oval(mcx - rad, mcy - rad, mcx + rad, mcy + rad,
                          fill=self.REC, outline="")
        else:
            inner = self.ACCENT if self._hover == "mic" else self.ACCENT_SOFT
            c.create_oval(mcx - rad, mcy - rad, mcx + rad, mcy + rad,
                          fill="", outline=inner, width=2)
        c.create_text(mcx, mcy - 4, text=self.MIC_ICON,
                      font=("Segoe UI Emoji", 17), fill="#FFFFFF")
        c.create_text(mcx, mcy + 14, text=self._hotkey_label,
                      font=("Segoe UI", 7, "bold"),
                      fill="#FFFFFF" if rec else self.TEXT)

        # Enter section (lighter bar + white label)
        ecx = (x0 + x1) // 2
        ecy = dy + self.ENTER_H // 2
        c.create_text(ecx, ecy, text="Enter \u21B5",
                      font=("Segoe UI", 9, "bold"), fill=self.ENTER_TEXT)

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
        self._draw()

    def update_label(self, text: str):
        self._hotkey_label = text
        self._draw()

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

    # --- Unified events (section chosen by click y) ---

    def _on_press(self, event):
        self._start_drag(event)
        self._draw(pressed=self._section_at(event.y))

    def _on_release(self, event):
        section = self._section_at(event.y)
        was_dragged = self._dragged
        self._draw()
        if was_dragged:
            return
        if section == "mic":
            if self._on_click:
                self._on_click()
        else:
            threading.Thread(target=self._send_enter, daemon=True).start()

    def _on_hover(self, event):
        sec = self._section_at(event.y)
        if sec != self._hover:
            self._hover = sec
            self._draw()

    def _on_leave(self, event):
        if self._hover is not None:
            self._hover = None
            self._draw()

    @staticmethod
    def _send_enter():
        import pyautogui
        pyautogui.press("enter")


class RecordingOverlay:
    """Overlay window with real-time waveform visualization and LLM cleanup toggle."""

    WIDTH = 320
    HEIGHT = 110
    WAVE_COLOR = "#4FC3F7"
    WAVE_COLOR_LOUD = "#FF7043"
    BG_COLOR = "#1E1E1E"
    BAR_COUNT = 40
    # Single status dot color per pipeline state (SuperWhisper/Aqua-style cue).
    STATE_COLORS = {
        "idle": "#9E9E9E",
        "listening": "#EF5350",   # red — recording
        "processing": "#42A5F5",  # blue — transcribing / cleaning
        "done": "#66BB6A",        # green — inserted
        "empty": "#FFA726",       # orange — nothing captured
        "error": "#FF7043",       # deep orange — failed
    }

    def __init__(self, on_gemini_toggle=None, on_llm_toggle=None, lang="ja", on_button_click=None, hotkey_label="F2"):
        self._root = None
        self._canvas = None
        self._label = None
        self._dot = None
        self._state = "idle"
        self._gemini_btn = None
        self._float_btn = None
        self._visible = False
        self._thread = None
        self._ready = threading.Event()
        self._levels = collections.deque([0.0] * self.BAR_COUNT, maxlen=self.BAR_COUNT)
        self._waveform = [0.0] * self.BAR_COUNT
        self._animating = False
        self._gemini_on = False
        self._llm_on = False
        self._llm_provider = "groq"
        # on_llm_toggle takes priority; on_gemini_toggle kept for backward compat
        self._on_llm_toggle = on_llm_toggle or on_gemini_toggle
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

    def set_state(self, state: str):
        """Set the status-dot color by pipeline state (thread-safe)."""
        self._state = state
        if self._root and self._dot:
            try:
                self._root.after(0, self._apply_state)
            except RuntimeError:
                pass  # mainloop not running yet; applied on next show()

    def _apply_state(self):
        if not self._dot:
            return
        color = self.STATE_COLORS.get(self._state, self.STATE_COLORS["idle"])
        self._dot.delete("all")
        self._dot.create_oval(2, 2, 12, 12, fill=color, outline="")

    def update_audio(self, level: float, waveform: list):
        self._levels.append(level)
        if waveform:
            if len(waveform) >= self.BAR_COUNT:
                self._waveform = waveform[:self.BAR_COUNT]
            else:
                self._waveform = waveform + [0.0] * (self.BAR_COUNT - len(waveform))

    def set_gemini_state(self, enabled: bool):
        """Backward-compatible alias for set_llm_state."""
        self._gemini_on = enabled
        self._llm_on = enabled
        if self._root and self._gemini_btn:
            try:
                self._root.after(0, self._update_gemini_btn)
            except RuntimeError:
                pass  # mainloop not yet running; state will be applied on next show()

    def set_llm_state(self, enabled: bool, provider: str = "groq"):
        self._llm_on = enabled
        self._gemini_on = enabled
        self._llm_provider = provider
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

        # Top row: status dot + label + Gemini button
        top_frame = tk.Frame(main_frame, bg=self.BG_COLOR)
        top_frame.pack(fill="x")

        self._dot = tk.Canvas(top_frame, width=14, height=14, bg=self.BG_COLOR,
                              highlightthickness=0)
        self._dot.pack(side="left", padx=(0, 6))
        self._dot.create_oval(2, 2, 12, 12,
                              fill=self.STATE_COLORS.get(self._state, "#9E9E9E"), outline="")

        self._label = tk.Label(
            top_frame,
            text="Recording...",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.BG_COLOR,
        )
        self._label.pack(side="left")

        # LLM cleanup toggle button
        self._gemini_btn = tk.Label(
            top_frame,
            text=t("llm_off", self._lang),
            font=("Segoe UI", 8),
            fg="#999999",
            bg="#333333",
            padx=6,
            pady=1,
            cursor="hand2",
        )
        self._gemini_btn.pack(side="right")
        self._gemini_btn.bind("<Button-1>", self._on_llm_click)

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
            if self._llm_on:
                if self._llm_provider == "gemini":
                    label = t("llm_on_gemini", self._lang)
                else:
                    label = t("llm_on_groq", self._lang)
                self._gemini_btn.config(
                    text=label,
                    fg="#FFFFFF",
                    bg="#4CAF50",
                )
            else:
                self._gemini_btn.config(
                    text=t("llm_off", self._lang),
                    fg="#999999",
                    bg="#333333",
                )

    def _on_float_btn_click(self):
        if self._on_button_click:
            threading.Thread(target=self._on_button_click, daemon=True).start()

    def _on_llm_click(self, event):
        if self._on_llm_toggle:
            self._on_llm_toggle()

    def _on_gemini_click(self, event):
        """Backward-compatible alias."""
        self._on_llm_click(event)

    def _do_show(self, text: str):
        if self._label:
            self._label.config(text=text)
        self._update_gemini_btn()
        self._apply_state()
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
