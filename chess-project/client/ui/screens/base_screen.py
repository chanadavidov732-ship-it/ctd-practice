from client.network.app_bridge import AppBridge
from client.ui.img import Img


class Screen:
    def __init__(self, bridge: AppBridge):
        self.bridge = bridge
        self.next_screen: tuple[type["Screen"], dict] | None = None
        self.should_quit = False

    def on_enter(self, payload: dict) -> None:
        pass

    def update(self) -> None:
        pass

    def render(self, canvas: Img) -> None:
        raise NotImplementedError

    def handle_click(self, x: int, y: int) -> None:
        pass

    def handle_key(self, key: int) -> None:
        pass
