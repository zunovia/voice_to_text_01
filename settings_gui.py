import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
from settings_manager import load_config, save_config


BG_COLOR = "#1a1a2e"
CARD_COLOR = "#16213e"
ACCENT_COLOR = "#0f3460"
TEXT_COLOR = "#e0e0e0"
HIGHLIGHT = "#4FC3F7"
GREEN = "#4CAF50"


class SettingsGUI:
    def __init__(self, on_save=None):
        self.on_save = on_save or (lambda cfg: None)

    def show(self):
        config = load_config()

        root = tk.Tk()
        root.title("Voice to Text - Settings")
        root.geometry("520x750")
        root.resizable(False, True)
        root.attributes("-topmost", True)
        root.configure(bg=BG_COLOR)

        # Center on screen
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 520) // 2
        y = (root.winfo_screenheight() - 750) // 2
        root.geometry(f"520x750+{x}+{y}")
        root.lift()
        root.focus_force()

        # Try to set icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass

        # Custom style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("Card.TFrame", background=CARD_COLOR)
        style.configure("Dark.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG_COLOR, foreground="#FFFFFF", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", background=CARD_COLOR, foreground=HIGHLIGHT, font=("Segoe UI", 11, "bold"))
        style.configure("Link.TLabel", background=CARD_COLOR, foreground=HIGHLIGHT, font=("Segoe UI", 9, "underline"), cursor="hand2")
        style.configure("Dark.TEntry", fieldbackground="#2a2a4a", foreground="#FFFFFF")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Dark.TRadiobutton", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Dark.TCheckbutton", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Dark.TCombobox", fieldbackground="#2a2a4a", foreground="#000000")

        # Scrollable main frame
        main = tk.Frame(root, bg=BG_COLOR, padx=20, pady=15)
        main.pack(fill="both", expand=True)

        # Title
        tk.Label(main, text="Voice to Text", font=("Segoe UI", 18, "bold"),
                 fg="#FFFFFF", bg=BG_COLOR).pack(anchor="w")
        tk.Label(main, text="Settings", font=("Segoe UI", 11),
                 fg="#888888", bg=BG_COLOR).pack(anchor="w", pady=(0, 12))

        # === API Section ===
        api_card = tk.Frame(main, bg=CARD_COLOR, padx=15, pady=12)
        api_card.pack(fill="x", pady=(0, 10))

        tk.Label(api_card, text="API Keys", font=("Segoe UI", 12, "bold"),
                 fg=HIGHLIGHT, bg=CARD_COLOR).pack(anchor="w", pady=(0, 8))

        # Groq API Key
        groq_frame = tk.Frame(api_card, bg=CARD_COLOR)
        groq_frame.pack(fill="x", pady=(0, 6))
        tk.Label(groq_frame, text="Groq API Key (STT - 無料)", font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        groq_link = tk.Label(groq_frame, text="取得する", font=("Segoe UI", 9, "underline"),
                             fg=HIGHLIGHT, bg=CARD_COLOR, cursor="hand2")
        groq_link.pack(side="right")
        groq_link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        groq_var = tk.StringVar(value=config.get("api_key", ""))
        groq_entry = tk.Entry(api_card, textvariable=groq_var, width=55, show="*",
                              bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                              relief="flat", font=("Consolas", 10))
        groq_entry.pack(fill="x", pady=(0, 10))

        # Gemini API Key
        gemini_frame = tk.Frame(api_card, bg=CARD_COLOR)
        gemini_frame.pack(fill="x", pady=(0, 6))
        tk.Label(gemini_frame, text="Gemini API Key (文章整形 - オプション)", font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        gemini_link = tk.Label(gemini_frame, text="取得する", font=("Segoe UI", 9, "underline"),
                               fg=HIGHLIGHT, bg=CARD_COLOR, cursor="hand2")
        gemini_link.pack(side="right")
        gemini_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey"))

        gemini_var = tk.StringVar(value=config.get("gemini_api_key", ""))
        gemini_entry = tk.Entry(api_card, textvariable=gemini_var, width=55, show="*",
                                bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                                relief="flat", font=("Consolas", 10))
        gemini_entry.pack(fill="x", pady=(0, 8))

        # Gemini cleanup toggle
        gemini_cleanup_var = tk.BooleanVar(value=config.get("use_gemini_cleanup", False))
        gemini_check = tk.Checkbutton(
            api_card, text="Gemini文章整形を有効にする（高精度・やや遅い）",
            variable=gemini_cleanup_var, font=("Segoe UI", 9),
            fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
            activebackground=CARD_COLOR, activeforeground=TEXT_COLOR,
        )
        gemini_check.pack(anchor="w")

        # Show/hide keys
        def toggle_show_keys():
            show = "*" if groq_entry.cget("show") == "" else ""
            groq_entry.config(show=show)
            gemini_entry.config(show=show)

        show_btn = tk.Label(api_card, text="キーを表示/非表示", font=("Segoe UI", 8, "underline"),
                            fg="#888888", bg=CARD_COLOR, cursor="hand2")
        show_btn.pack(anchor="e", pady=(4, 0))
        show_btn.bind("<Button-1>", lambda e: toggle_show_keys())

        # === Controls Section ===
        ctrl_card = tk.Frame(main, bg=CARD_COLOR, padx=15, pady=12)
        ctrl_card.pack(fill="x", pady=(0, 10))

        tk.Label(ctrl_card, text="操作設定", font=("Segoe UI", 12, "bold"),
                 fg=HIGHLIGHT, bg=CARD_COLOR).pack(anchor="w", pady=(0, 8))

        # Hotkey + Language row
        row1 = tk.Frame(ctrl_card, bg=CARD_COLOR)
        row1.pack(fill="x", pady=(0, 8))

        tk.Label(row1, text="ホットキー:", font=("Segoe UI", 10),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        hotkey_var = tk.StringVar(value=config.get("hotkey", "f2"))
        hotkey_entry = tk.Entry(row1, textvariable=hotkey_var, width=15,
                                bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                                relief="flat", font=("Consolas", 10))
        hotkey_entry.pack(side="left", padx=(5, 20))

        tk.Label(row1, text="言語:", font=("Segoe UI", 10),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        lang_var = tk.StringVar(value=config.get("language", "ja"))
        lang_combo = ttk.Combobox(row1, textvariable=lang_var,
                                   values=["ja", "en", "zh", "ko"], width=5, state="readonly",
                                   style="Dark.TCombobox")
        lang_combo.pack(side="left", padx=(5, 0))

        # Mode
        mode_var = tk.StringVar(value=config.get("mode", "toggle"))
        tk.Radiobutton(ctrl_card, text="Toggle（1回押して開始、もう1回で停止）",
                       variable=mode_var, value="toggle",
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 9)).pack(anchor="w")
        tk.Radiobutton(ctrl_card, text="Push-to-Talk（キーを押している間だけ録音）",
                       variable=mode_var, value="push_to_talk",
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 9)).pack(anchor="w")

        # === Save Button ===
        status_var = tk.StringVar(value="")
        status_label = tk.Label(main, textvariable=status_var, font=("Segoe UI", 10),
                                fg=GREEN, bg=BG_COLOR)
        status_label.pack(pady=(5, 0))

        def on_save():
            api_key = groq_var.get().strip()
            if not api_key:
                messagebox.showwarning("Warning", "Groq API Key を入力してください!", parent=root)
                return

            config["api_key"] = api_key
            config["gemini_api_key"] = gemini_var.get().strip()
            config["use_gemini_cleanup"] = gemini_cleanup_var.get()
            config["hotkey"] = hotkey_var.get().strip()
            config["mode"] = mode_var.get()
            config["language"] = lang_var.get()

            save_config(config)
            self.on_save(config)
            status_var.set("保存しました! アプリを再起動してください。")

        save_btn = tk.Button(main, text="保存", font=("Segoe UI", 12, "bold"),
                             fg="#FFFFFF", bg=GREEN, activebackground="#388E3C",
                             relief="flat", padx=40, pady=6, cursor="hand2",
                             command=on_save)
        save_btn.pack(pady=(8, 0))

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()


# Allow running settings_gui.py directly as a standalone process
if __name__ == "__main__":
    gui = SettingsGUI()
    gui.show()
