import os
import sys
import platform
from pathlib import Path

try:
    import win32com.client
except ImportError:
    win32com = None


APP_SHORTCUT_NAME = "AnchorPass.lnk"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _get_startup_folder() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"


def _get_shortcut_path() -> Path | None:
    folder = _get_startup_folder()
    if folder is None:
        return None
    return folder / APP_SHORTCUT_NAME


def _get_target_and_args() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return sys.executable, ""

    python_exe = sys.executable
    script = os.path.abspath(sys.argv[0])
    return python_exe, f'"{script}"'


def set_startup_enabled(enabled: bool) -> None:
    if not _is_windows():
        return

    shortcut_path = _get_shortcut_path()
    if shortcut_path is None:
        return

    if not enabled:
        try:
            if shortcut_path.exists():
                shortcut_path.unlink()
        except OSError:
            pass
        return

    if win32com is None:
        return

    startup_folder = shortcut_path.parent
    startup_folder.mkdir(parents=True, exist_ok=True)

    target, args = _get_target_and_args()

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = target
        shortcut.Arguments = args
        shortcut.WorkingDirectory = os.path.dirname(target)
        shortcut.IconLocation = target
        shortcut.save()
    except Exception:
        pass


def is_startup_enabled() -> bool:
    if not _is_windows():
        return False

    shortcut_path = _get_shortcut_path()
    if shortcut_path is None:
        return False

    return shortcut_path.exists()
