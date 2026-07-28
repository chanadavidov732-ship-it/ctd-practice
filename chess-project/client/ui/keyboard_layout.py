import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes

    _user32 = ctypes.windll.user32
    _ENGLISH_US_KLID = "00000409"
    _KLF_ACTIVATE = 0x00000001


def force_english_layout():
    if not _IS_WINDOWS:
        return None
    previous = _user32.GetKeyboardLayout(0)
    activated = _user32.LoadKeyboardLayoutW(_ENGLISH_US_KLID, _KLF_ACTIVATE)
    return previous if activated else None


def restore_layout(previous_layout) -> None:
    if not _IS_WINDOWS or not previous_layout:
        return
    _user32.ActivateKeyboardLayout(previous_layout, 0)
