"""Main graphical loop for the wrapper-screen flow (Login/Home/Room/...),
running on the main thread. Reuses the single OS window the in-game
client/ui/renderer.py's Renderer already opens (same WINDOW_NAME) so the
handoff into an active game (iteration 14/15) and back out of it
(iteration 16) never closes/reopens a window.
"""

import cv2
import numpy as np

from client.network.app_bridge import AppBridge
from client.ui.img import Img
from client.ui.renderer import WINDOW_NAME
from client.ui.screens.base_screen import Screen

FRAME_DELAY_MS = 30
# Esc only (unlike renderer.py's QUIT_KEYS, which also includes "q"): wrapper
# screens keep a text field focused at all times, so "q" has to reach it as a
# normal character instead of being swallowed as a quit shortcut.
QUIT_KEYS = (27,)
DEFAULT_CANVAS_WIDTH = 640
DEFAULT_CANVAS_HEIGHT = 480
BACKGROUND_COLOR = (30, 30, 30, 255)


class ScreenManager:
    def __init__(
        self,
        bridge: AppBridge,
        start_screen: type[Screen],
        start_payload: dict | None = None,
        canvas_size: tuple[int, int] = (DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT),
    ):
        self.bridge = bridge
        self.canvas_width, self.canvas_height = canvas_size
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

        self.active_screen: Screen = start_screen(bridge)
        self.active_screen.on_enter(start_payload or {})

    def _on_mouse(self, event, x, y, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self.active_screen.handle_click(x, y)

    def run(self) -> None:
        """Blocks the main thread, driving the active screen frame by frame
        until the window is closed. Returns normally on quit (mirrors
        Renderer.render()'s own quit handling, so the caller can decide what
        "done" means -- e.g. iteration 16 doesn't tear the process down)."""
        while True:
            self.active_screen.update()

            if self.active_screen.should_quit:
                cv2.destroyAllWindows()
                return

            canvas = self._blank_canvas()
            self.active_screen.render(canvas)
            cv2.imshow(WINDOW_NAME, canvas.img)

            key = cv2.waitKey(FRAME_DELAY_MS)
            if key != -1:
                # On Windows, waitKey()'s raw return value carries extra bits
                # above the actual key code for some keys; masking to the low
                # byte is the standard OpenCV fix (must skip -1 == "no key",
                # since -1 & 0xFF would wrongly become 255).
                key &= 0xFF
            closed_by_user = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1
            if key in QUIT_KEYS or closed_by_user:
                cv2.destroyAllWindows()
                return
            if key != -1:
                self.active_screen.handle_key(key)

            if self.active_screen.next_screen is not None:
                screen_class, payload = self.active_screen.next_screen
                self.active_screen = screen_class(self.bridge)
                self.active_screen.on_enter(payload)
                # A screen that just ran the legacy game loop (client.ui.
                # game_runner.run_graphical_game) left the window destroyed
                # behind it -- Renderer always calls cv2.destroyAllWindows()
                # on exit, quit or "Back to Menu" alike. Recreating both here
                # unconditionally is cheap and correct on every transition,
                # game-loop-driven or not.
                cv2.namedWindow(WINDOW_NAME)
                cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    def _blank_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.full((self.canvas_height, self.canvas_width, 4), BACKGROUND_COLOR, dtype=np.uint8)
        return canvas
