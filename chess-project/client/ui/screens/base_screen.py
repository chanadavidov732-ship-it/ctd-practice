"""Base class for graphical wrapper screens (Login/Home/Room/Matchmaking/...),
driven by client.ui.screen_manager.ScreenManager.
"""

from client.network.app_bridge import AppBridge
from client.ui.img import Img


class Screen:
    """One frame-driven screen. ScreenManager calls, every frame while this
    screen is active: update() then render(canvas). Mouse/keyboard events are
    routed to handle_click/handle_key. A screen requests a transition by
    setting self.next_screen = (ScreenClass, payload); ScreenManager notices
    it after the frame, constructs the new screen and calls its on_enter(payload).
    """

    def __init__(self, bridge: AppBridge):
        self.bridge = bridge
        self.next_screen: tuple[type["Screen"], dict] | None = None
        # Set True by a screen that just ran the legacy game loop (client.ui.
        # game_runner.run_graphical_game) to completion -- ends the wrapper
        # loop the same way closing the window would. Returning to a menu
        # after a finished game is deliberately out of scope until iteration
        # 16, so there is no screen to hand off to here.
        self.should_quit = False

    def on_enter(self, payload: dict) -> None:
        """Called once, right after construction, with the payload handed off
        by the previous screen (or {} for the very first screen)."""

    def update(self) -> None:
        """Called once per frame before render(). Screens that react to
        server broadcasts poll self.bridge.poll_events() here."""

    def render(self, canvas: Img) -> None:
        raise NotImplementedError

    def handle_click(self, x: int, y: int) -> None:
        """x, y are raw canvas pixel coordinates (no board offset)."""

    def handle_key(self, key: int) -> None:
        """key is an OpenCV cv2.waitKey() code."""
