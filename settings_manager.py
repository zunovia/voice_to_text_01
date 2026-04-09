import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "f2",
    "mode": "toggle",  # "push_to_talk" or "toggle"
    "language": "ja",
    "sample_rate": 16000,
    "voice_commands": {
        "エンター": "\n",
        "改行": "\n",
        "ピリオド": "。",
        "句点": "。",
        "読点": "、",
        "カンマ": "、",
        "まる": "。",
        "てん": "、",
        "かっこ": "（",
        "かっことじ": "）",
        "かぎかっこ": "「",
        "かぎかっことじ": "」",
        "タブ": "\t",
        "スペース": " ",
    },
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Merge with defaults for any missing keys
        merged = {**DEFAULT_CONFIG, **config}
        merged["voice_commands"] = {
            **DEFAULT_CONFIG["voice_commands"],
            **config.get("voice_commands", {}),
        }
        return merged
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_api_key() -> str:
    return load_config().get("api_key", "")


def set_api_key(key: str):
    config = load_config()
    config["api_key"] = key
    save_config(config)
