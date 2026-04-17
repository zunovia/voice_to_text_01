import json
import os
import sys
import logging

log = logging.getLogger("VoiceToText")


def _get_app_dir() -> str:
    """Get the directory where config/log files should be stored.
    For exe (frozen): %APPDATA%/VoiceToText/ (persists across reinstalls).
    For script: directory containing this .py file.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", os.path.expanduser("~")))
        data_dir = os.path.join(appdata, "VoiceToText")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _get_app_dir()
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

# Log paths at startup for debugging
log.info(f"APP_DIR={APP_DIR}, CONFIG_PATH={CONFIG_PATH}, frozen={getattr(sys, 'frozen', False)}")


DEFAULT_CONFIG = {
    "api_key": "",
    "gemini_api_key": "",
    "use_gemini_cleanup": False,
    "hotkey": "f2",
    "mode": "toggle",
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
        "鉤括弧": "「",
        "鉤括弧閉じ": "」",
        "カギカッコ": "「",
        "カギカッコトジ": "」",
        "すみかっこ": "【",
        "すみかっことじ": "】",
        "タブ": "\t",
        "スペース": " ",
        "とうてん": "、",
        "くてん": "。",
    },
}


def load_config() -> dict:
    log.debug(f"Loading config from: {CONFIG_PATH}")
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            merged = {**DEFAULT_CONFIG, **config}
            merged["voice_commands"] = {
                **DEFAULT_CONFIG["voice_commands"],
                **config.get("voice_commands", {}),
            }
            return merged
        except Exception as e:
            log.error(f"Failed to load config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(CONFIG_PATH)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # Verify save was successful
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("api_key") == config.get("api_key"):
                log.info(f"Config saved and verified: {CONFIG_PATH}")
                return True
            else:
                log.error(f"Config verification failed! Saved key doesn't match.")
                return False
        else:
            log.error(f"Config file not found after save: {CONFIG_PATH}")
            return False
    except Exception as e:
        log.error(f"Failed to save config to {CONFIG_PATH}: {e}")
        return False


def get_api_key() -> str:
    return load_config().get("api_key", "")


def set_api_key(key: str):
    config = load_config()
    config["api_key"] = key
    save_config(config)
