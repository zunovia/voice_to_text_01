import os
import sys
import logging

log = logging.getLogger("VoiceToText")

STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
)
SHORTCUT_NAME = "VoiceToText.vbs"


def _get_app_path() -> str:
    """Get the path to the launcher script or exe."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    # If running as exe
    if getattr(sys, "frozen", False):
        return os.path.join(app_dir, "VoiceToText.exe")
    # If running as script, use VoiceToText.vbs
    vbs = os.path.join(app_dir, "VoiceToText.vbs")
    if os.path.exists(vbs):
        return vbs
    return ""


def is_autostart_enabled() -> bool:
    shortcut_path = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)
    return os.path.exists(shortcut_path)


def enable_autostart():
    app_path = _get_app_path()
    if not app_path:
        log.warning("Cannot find app path for autostart")
        return False

    shortcut_path = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)

    # Create a VBS launcher in startup folder
    vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\n'
    vbs_content += f'WshShell.CurrentDirectory = "{os.path.dirname(app_path)}"\n'

    if app_path.endswith(".exe"):
        vbs_content += f'WshShell.Run """{app_path}""", 0, False\n'
    else:
        vbs_content += f'WshShell.Run "wscript ""{app_path}""", 0, False\n'

    with open(shortcut_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    log.info(f"Autostart enabled: {shortcut_path}")
    return True


def disable_autostart():
    shortcut_path = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
        log.info("Autostart disabled")
    return True
