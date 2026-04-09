import tkinter as tk
from tkinter import ttk, messagebox
from settings_manager import load_config, save_config


class SettingsGUI:
    def __init__(self, on_save=None):
        self.on_save = on_save or (lambda cfg: None)

    def show(self):
        config = load_config()

        root = tk.Tk()
        root.title("Voice-to-Text - 設定")
        root.geometry("480x450")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        # Center on screen
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 480) // 2
        y = (root.winfo_screenheight() - 450) // 2
        root.geometry(f"480x450+{x}+{y}")
        root.lift()
        root.focus_force()

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(frame, text="Voice-to-Text 設定", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 15)
        )

        # API Key
        ttk.Label(frame, text="Gemini API Key:").grid(row=1, column=0, sticky="w", pady=(0, 5))
        api_key_var = tk.StringVar(value=config.get("api_key", ""))
        api_entry = ttk.Entry(frame, textvariable=api_key_var, width=50, show="*")
        api_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="キーを表示", variable=show_key,
            command=lambda: api_entry.config(show="" if show_key.get() else "*"),
        ).grid(row=3, column=0, sticky="w", pady=(0, 15))

        # Hotkey
        ttk.Label(frame, text="ホットキー:").grid(row=4, column=0, sticky="w", pady=(0, 5))
        hotkey_var = tk.StringVar(value=config.get("hotkey", "ctrl+shift+space"))
        ttk.Entry(frame, textvariable=hotkey_var, width=30).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(0, 15)
        )

        # Mode
        ttk.Label(frame, text="録音モード:").grid(row=6, column=0, sticky="w", pady=(0, 5))
        mode_var = tk.StringVar(value=config.get("mode", "push_to_talk"))
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 15))
        ttk.Radiobutton(
            mode_frame, text="Push-to-Talk (キーを押している間だけ録音)", variable=mode_var, value="push_to_talk"
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame, text="Toggle (1回押して録音開始、もう1回で停止)", variable=mode_var, value="toggle"
        ).pack(anchor="w")

        # Language
        ttk.Label(frame, text="言語:").grid(row=8, column=0, sticky="w", pady=(0, 5))
        lang_var = tk.StringVar(value=config.get("language", "ja"))
        ttk.Combobox(
            frame, textvariable=lang_var, values=["ja", "en", "zh", "ko"], width=10, state="readonly"
        ).grid(row=9, column=0, sticky="w", pady=(0, 20))

        # Status
        status_var = tk.StringVar(value="")
        status_label = ttk.Label(frame, textvariable=status_var, foreground="green")
        status_label.grid(row=10, column=0, columnspan=2, pady=(0, 5))

        # Save button
        def on_save():
            config["api_key"] = api_key_var.get().strip()
            config["hotkey"] = hotkey_var.get().strip()
            config["mode"] = mode_var.get()
            config["language"] = lang_var.get()

            if not config["api_key"]:
                messagebox.showwarning("Warning", "API Key を入力してください!", parent=root)
                return

            save_config(config)
            self.on_save(config)
            status_var.set("保存しました! アプリを再起動してください。")

        ttk.Button(frame, text="保存", command=on_save).grid(
            row=11, column=0, columnspan=2, pady=(5, 0)
        )

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()


# Allow running settings_gui.py directly as a standalone process
if __name__ == "__main__":
    gui = SettingsGUI()
    gui.show()
