import cv2
import numpy as np

from client.config import ESC_KEY, FRAME_DELAY_MS
from client.network.app_bridge import AppBridge
from client.ui.img import Img
from client.ui.keyboard_layout import force_english_layout, restore_layout
from client.ui.renderer import WINDOW_NAME
from client.ui.screens.base_screen import Screen

QUIT_KEYS = (ESC_KEY,)
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
        self._create_window()
        self._previous_keyboard_layout = force_english_layout()

        self.active_screen: Screen = start_screen(bridge)
        self.active_screen.on_enter(start_payload or {})

    def _create_window(self) -> None:
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self.active_screen.handle_click(x, y)

    def run(self) -> None:
        while True:
            self.active_screen.update()

            if self.active_screen.should_quit:
                restore_layout(self._previous_keyboard_layout)
                cv2.destroyAllWindows()
                return

            canvas = self._blank_canvas()
            self.active_screen.render(canvas)
            cv2.imshow(WINDOW_NAME, canvas.img)

            key = cv2.waitKey(FRAME_DELAY_MS)
            if key != -1:
                key &= 0xFF
            closed_by_user = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1
            if key in QUIT_KEYS or closed_by_user:
                restore_layout(self._previous_keyboard_layout)
                cv2.destroyAllWindows()
                return
            if key != -1:
                self.active_screen.handle_key(key)

            if self.active_screen.next_screen is not None:
                screen_class, payload = self.active_screen.next_screen
                self.active_screen = screen_class(self.bridge)
                self.active_screen.on_enter(payload)
                self._create_window()

    def _blank_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.full((self.canvas_height, self.canvas_width, 4), BACKGROUND_COLOR, dtype=np.uint8)
        return canvas
