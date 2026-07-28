"""Forces the process's active keyboard layout to English (US) while a text-
entry window is open.

cv2.waitKey() has no Unicode/IME awareness: on Windows it returns whatever
character Windows' WM_CHAR translation produces for the *currently active
OS input language*. TextInput.handle_key only accepts plain printable ASCII
(32-126), so under a non-Latin layout (e.g. Hebrew) the same physical letter
keys produce codes outside that range and are silently dropped -- digits and
most symbols are unaffected because they sit on the same physical keys across
layouts. There is no way to fix this from cv2's side (it never sees the raw,
layout-independent key code) -- the reliable fix is to make Windows itself
translate as English while our window has input focus.
"""

import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes

    _user32 = ctypes.windll.user32
    _ENGLISH_US_KLID = "00000409"
    _KLF_ACTIVATE = 0x00000001


def force_english_layout():
    """Switches the current thread's keyboard layout to English (US).
    Returns the previous layout handle (or None off Windows / on failure) to
    pass to restore_layout() later; safe to ignore the return value."""
    if not _IS_WINDOWS:
        return None
    previous = _user32.GetKeyboardLayout(0)
    activated = _user32.LoadKeyboardLayoutW(_ENGLISH_US_KLID, _KLF_ACTIVATE)
    return previous if activated else None


def restore_layout(previous_layout) -> None:
    """Restores a layout handle returned by force_english_layout(). No-op if
    that call returned None (off Windows, or it failed)."""
    if not _IS_WINDOWS or not previous_layout:
        return
    _user32.ActivateKeyboardLayout(previous_layout, 0)
