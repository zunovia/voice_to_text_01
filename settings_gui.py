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


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
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
        root.geometry("520x660")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=BG_COLOR)

        root.update_idletasks()
        x = (root.winfo_screenwidth() - 520) // 2
        y = (root.winfo_screenheight() - 660) // 2
        root.geometry(f"520x660+{x}+{y}")
        root.lift()
        root.focus_force()

        icon_path = os.path.join(_get_app_dir(), "icon.ico")
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

            # Update config
            config["api_key"] = api_key
            config["gemini_api_key"] = gemini_var.get().strip()
            config["use_gemini_cleanup"] = gemini_cleanup_var.get()
            config["hotkey"] = hotkey_var.get().strip()
            config["mode"] = mode_var.get()
            config["language"] = lang_var.get()

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

        # === Main content ===
        main = tk.Frame(root, bg=BG_COLOR, padx=20, pady=10)
        main.pack(side="top", fill="both", expand=True)

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

        # Gemini
        gemini_frame = tk.Frame(api_card, bg=CARD_COLOR)
        gemini_frame.pack(fill="x", pady=(0, 4))
        tk.Label(gemini_frame, text=t("settings_gemini_label", L), font=("Segoe UI", 9),
                 fg=TEXT_COLOR, bg=CARD_COLOR).pack(side="left")
        gemini_link = tk.Label(gemini_frame, text=t("settings_get_key", L), font=("Segoe UI", 9, "underline"),
                               fg=HIGHLIGHT, bg=CARD_COLOR, cursor="hand2")
        gemini_link.pack(side="right")
        gemini_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/apikey"))

        gemini_current = config.get("gemini_api_key", "")
        gemini_has_key = bool(gemini_current and len(gemini_current) > 10)
        gemini_var = tk.StringVar(value=gemini_current if gemini_has_key else "")
        gemini_entry = tk.Entry(api_card, textvariable=gemini_var, width=55, show="*",
                                bg="#2a2a4a", fg="#FFFFFF", insertbackground="#FFFFFF",
                                relief="flat", font=("Consolas", 10))
        gemini_entry.pack(fill="x", pady=(0, 2))
        gemini_status = tk.Label(api_card,
                                 text="API Key 設定済み (オプション)" if gemini_has_key else "未設定 (オプション)",
                                 font=("Segoe UI", 8),
                                 fg=GREEN if gemini_has_key else "#888888",
                                 bg=CARD_COLOR)
        gemini_status.pack(anchor="w", pady=(0, 4))

        gemini_cleanup_var = tk.BooleanVar(value=config.get("use_gemini_cleanup", False))
        tk.Checkbutton(api_card, text=t("settings_gemini_check", L),
                       variable=gemini_cleanup_var, font=("Segoe UI", 9),
                       fg=TEXT_COLOR, bg=CARD_COLOR, selectcolor=ACCENT_COLOR,
                       activebackground=CARD_COLOR, activeforeground=TEXT_COLOR).pack(anchor="w")

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
