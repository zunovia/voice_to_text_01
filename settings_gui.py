import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
import sys
import logging
from settings_manager import load_config, save_config, CONFIG_PATH
from i18n import t

log = logging.getLogger("VoiceToText")

BG_COLOR = "#1a1a2e"
CARD_COLOR = "#16213e"
ACCENT_COLOR = "#0f3460"
TEXT_COLOR = "#e0e0e0"
HIGHLIGHT = "#4FC3F7"
GREEN = "#4CAF50"


def _get_resource_dir():
    """Get the directory containing bundled assets (icons, etc.)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


class SettingsGUI:
    def __init__(self, on_save=None):
        self.on_save = on_save or (lambda cfg: None)

    def show(self):
        config = load_config()
        L = config.get("language", "ja")
        log.info(f"Settings GUI opening. CONFIG_PATH={CONFIG_PATH}, api_key={'set' if config.get('api_key') else 'empty'}")

        root = tk.Tk()
        root.title("Voice to Text - Settings")
        root.attributes("-topmost", True)
        root.configure(bg=BG_COLOR)

        # Size to fit the screen; content scrolls so nothing is ever cut off,
        # and the window stays resizable for the user.
        win_w = 540
        root.update_idletasks()
        screen_h = root.winfo_screenheight()
        win_h = min(760, screen_h - 80)
        x = (root.winfo_screenwidth() - win_w) // 2
        y = max(0, (screen_h - win_h) // 2)
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        root.minsize(460, 400)
        root.lift()
        root.focus_force()

        icon_path = os.path.join(_get_resource_dir(), "icon.ico")
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox", fieldbackground="#2a2a4a", foreground="#000000")

        # === Top bar with save button ===
        top_bar = tk.Frame(root, bg="#111122", pady=8)
        top_bar.pack(side="top", fill="x")

        tk.Label(top_bar, text=t("settings_title", L), font=("Segoe UI", 14, "bold"),
                 fg="#FFFFFF", bg="#111122").pack(side="left", padx=(15, 0))

        def on_save():
            api_key = groq_var.get().strip()
            if not api_key:
                messagebox.showwarning("Warning", t("settings_groq_required", L), parent=root)
                return

            # Update config (Groq only)
            config["api_key"] = api_key
            use_llm = llm_cleanup_var.get()
            config["use_llm_cleanup"] = use_llm
            config["llm_provider"] = "groq"
            # Model: extract model ID from display string
            model_display = groq_model_var.get()
            model_id = model_display.split(" ")[0] if model_display else "openai/gpt-oss-20b"
            config["groq_llm_model"] = model_id
            config["hotkey"] = hotkey_var.get().strip()
            config["mode"] = mode_var.get()
            config["language"] = lang_var.get()
            # Accuracy settings
            stt_display = stt_model_var.get()
            config["stt_model"] = stt_display.split(" ")[0] if stt_display else "whisper-large-v3-turbo"
            config["vocabulary"] = vocab_text.get("1.0", "end").strip()
            config["sounds_enabled"] = sounds_var.get()

            log.info(f"Saving config: api_key={'set' if api_key else 'empty'}, path={CONFIG_PATH}")

            success = save_config(config)
            if success:
                log.info("Settings saved successfully")
                self.on_save(config)
                root.destroy()
            else:
                log.error("Settings save FAILED")
                messagebox.showerror("Error", f"{t('settings_save_failed', L)}\n{CONFIG_PATH}", parent=root)

        save_btn = tk.Button(top_bar, text=t("settings_save", L), font=("Segoe UI", 11, "bold"),
                             fg="#FFFFFF", bg=GREEN, activebackground="#388E3C",
                             relief="flat", padx=15, pady=3, cursor="hand2",
                             command=on_save)
        save_btn.pack(side="right", padx=(0, 15))

        # === Scrollable content area (so nothing gets cut off) ===
        body = tk.Frame(root, bg=BG_COLOR)
        body.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(body, bg=BG_COLOR, highlightthickness=0)
        vsb = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Inner frame keeps the original variable name `main`, so all the layout
        # code below is unchanged — it just lives inside the scrollable canvas.
        main = tk.Frame(canvas, bg=BG_COLOR, padx=20, pady=10)
        main_window = canvas.create_window((0, 0), window=main, anchor="nw")

        def _sync_scrollregion(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main.bind("<Configure>", _sync_scrollregion)

        def _stretch_inner(e):
            canvas.itemconfigure(main_window, width=e.width)
        canvas.bind("<Configure>", _stretch_inner)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-e.delta / 120), "units")
        # bind_all is scoped to this settings window's own Tk interpreter and is
        # released when the window closes; only active while the pointer is over it.
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # === API Section ===
        api_card = tk.Frame(main, bg=CARD_COLOR, padx=15, pady=10)
        api_card.pack(fill="x", pady=(0, 8))

        tk.Label(api_card, text=t("settings_api_keys", L), font=("Segoe UI", 12, "bold"),
                 fg=HIGHLIGHT, bg=CARD_COLOR).pack(anchor="w", pady=(0, 6))

        # Groq
        groq_frame = tk.Frame(api_card, bg=CARD_COLOR)
        groq_frame.pack(fill="x", pady=(0, 4))
        tk.Label(groq_frame, text=t("settings_groq_label", L), font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        groq_link = tk.Label(groq_frame, text=t("settings_get_key", L), font=("Segoe UI", 9, "underline"),
                             fg=HIGHLIGHT, bg=CARD_COLOR, cursor="hand2")
        groq_link.pack(side="right")
        groq_link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        groq_current = config.get("api_key", "")
        groq_has_key = bool(groq_current and not groq_current.startswith("YOUR_") and len(groq_current) > 10)
        groq_var = tk.StringVar(value=groq_current if groq_has_key else "")
        groq_entry = tk.Entry(api_card, textvariable=groq_var, width=55, show="*",
                              bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                              relief="flat", font=("Consolas", 10))
        groq_entry.pack(fill="x", pady=(0, 2))
        groq_status = tk.Label(api_card,
                               text="API Key 設定済み" if groq_has_key else "未設定",
                               font=("Segoe UI", 8),
                               fg=GREEN if groq_has_key else "#FF5252",
                               bg=CARD_COLOR)
        groq_status.pack(anchor="w", pady=(0, 6))

        # LLM cleanup section
        use_llm_init = config.get("use_llm_cleanup", config.get("use_gemini_cleanup", False))
        llm_cleanup_var = tk.BooleanVar(value=use_llm_init)
        tk.Checkbutton(api_card, text=t("settings_llm_check", L),
                       variable=llm_cleanup_var, font=("Segoe UI", 9),
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR).pack(anchor="w")

        # Groq cleanup model dropdown
        groq_model_frame = tk.Frame(api_card, bg=CARD_COLOR)
        groq_model_frame.pack(fill="x", pady=(4, 2))
        tk.Label(groq_model_frame, text=t("settings_groq_model", L), font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")

        groq_model_options = [
            "openai/gpt-oss-20b (推奨・キャッシュ対応)" if L == "ja" else "openai/gpt-oss-20b (Recommended, cached)",
            "llama-3.1-8b-instant (最速)" if L == "ja" else "llama-3.1-8b-instant (Fastest)",
            "qwen/qwen3-32b (高品質)" if L == "ja" else "qwen/qwen3-32b (High quality)",
            "llama-3.3-70b-versatile (バランス)" if L == "ja" else "llama-3.3-70b-versatile (Balanced)",
        ]
        current_model = config.get("groq_llm_model", "openai/gpt-oss-20b")
        # Find matching display option
        model_init = groq_model_options[0]
        for opt in groq_model_options:
            if opt.startswith(current_model):
                model_init = opt
                break
        groq_model_var = tk.StringVar(value=model_init)
        groq_model_combo = ttk.Combobox(groq_model_frame, textvariable=groq_model_var,
                                         values=groq_model_options, width=38, state="readonly",
                                         style="Dark.TCombobox")
        groq_model_combo.pack(side="left", padx=(5, 0))

        # === Accuracy Section ===
        acc_card = tk.Frame(main, bg=CARD_COLOR, padx=15, pady=10)
        acc_card.pack(fill="x", pady=(0, 8))

        tk.Label(acc_card, text=t("settings_accuracy", L), font=("Segoe UI", 12, "bold"),
                 fg=HIGHLIGHT, bg=CARD_COLOR).pack(anchor="w", pady=(0, 6))

        # STT model
        stt_frame = tk.Frame(acc_card, bg=CARD_COLOR)
        stt_frame.pack(fill="x", pady=(0, 6))
        tk.Label(stt_frame, text=t("settings_stt_model", L), font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        stt_model_options = [
            "whisper-large-v3-turbo (高速)" if L == "ja" else "whisper-large-v3-turbo (Fast)",
            "whisper-large-v3 (高精度)" if L == "ja" else "whisper-large-v3 (Accurate)",
        ]
        current_stt = config.get("stt_model", "whisper-large-v3-turbo")
        stt_init = stt_model_options[0]
        for opt in stt_model_options:
            if opt.startswith(current_stt):
                stt_init = opt
                break
        stt_model_var = tk.StringVar(value=stt_init)
        ttk.Combobox(stt_frame, textvariable=stt_model_var, values=stt_model_options,
                     width=30, state="readonly", style="Dark.TCombobox").pack(side="left", padx=(5, 0))

        # Custom vocabulary (Whisper prompt bias)
        tk.Label(acc_card, text=t("settings_vocabulary", L), font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(anchor="w")
        vocab_text = tk.Text(acc_card, height=3, width=55, bg="#2a2a4a", fg="#FFFFFF",
                             insertbackground="#FFFFFF", relief="flat", font=("Consolas", 10),
                             wrap="word")
        vocab_text.pack(fill="x", pady=(2, 2))
        vocab_text.insert("1.0", config.get("vocabulary", ""))
        tk.Label(acc_card, text=t("settings_vocabulary_note", L), font=("Segoe UI", 8),
                 fg="#888888", bg=CARD_COLOR, wraplength=460, justify="left").pack(anchor="w")

        # === Controls Section ===
        ctrl_card = tk.Frame(main, bg=CARD_COLOR, padx=15, pady=10)
        ctrl_card.pack(fill="x", pady=(0, 8))

        tk.Label(ctrl_card, text=t("settings_controls", L), font=("Segoe UI", 12, "bold"),
                 fg=HIGHLIGHT, bg=CARD_COLOR).pack(anchor="w", pady=(0, 2))
        tk.Label(ctrl_card, text=t("settings_hotkey_note", L),
                 font=("Segoe UI", 8), fg="#888888", bg=CARD_COLOR, wraplength=450,
                 justify="left").pack(anchor="w", pady=(0, 6))

        row1 = tk.Frame(ctrl_card, bg=CARD_COLOR)
        row1.pack(fill="x", pady=(0, 6))

        tk.Label(row1, text=t("settings_hotkey", L), font=("Segoe UI", 10),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        hotkey_var = tk.StringVar(value=config.get("hotkey", "f2"))
        tk.Entry(row1, textvariable=hotkey_var, width=12,
                 bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                 relief="flat", font=("Consolas", 10)).pack(side="left", padx=(5, 20))

        tk.Label(row1, text=t("settings_language", L), font=("Segoe UI", 10),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        lang_var = tk.StringVar(value=config.get("language", "ja"))
        lang_combo = ttk.Combobox(row1, textvariable=lang_var,
                                   values=["ja", "en", "zh", "ko"], width=5, state="readonly",
                                   style="Dark.TCombobox")
        lang_combo.pack(side="left", padx=(5, 0))

        mode_var = tk.StringVar(value=config.get("mode", "toggle"))
        tk.Radiobutton(ctrl_card, text=t("settings_mode_toggle", L),
                       variable=mode_var, value="toggle",
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 9)).pack(anchor="w")
        tk.Radiobutton(ctrl_card, text=t("settings_mode_ptt", L),
                       variable=mode_var, value="push_to_talk",
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 9)).pack(anchor="w")

        sounds_var = tk.BooleanVar(value=config.get("sounds_enabled", True))
        tk.Checkbutton(ctrl_card, text=t("settings_sounds", L),
                       variable=sounds_var, font=("Segoe UI", 9),
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR).pack(anchor="w", pady=(4, 0))

        # === Info bar ===
        info = tk.Frame(main, bg=BG_COLOR)
        info.pack(fill="x", pady=(5, 0))
        tk.Label(info, text=f"Config: {CONFIG_PATH}", font=("Segoe UI", 7),
                 fg="#555555", bg=BG_COLOR).pack(anchor="w")

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()


if __name__ == "__main__":
    gui = SettingsGUI()
    gui.show()
