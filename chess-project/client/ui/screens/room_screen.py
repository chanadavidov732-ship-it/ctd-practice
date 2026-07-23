"""Room screen -- placeholder for iteration 13 (proves the Home -> Room
handoff); iteration 14 fills this in with the real Create/Join/wait flow.
"""

from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Label

TITLE_X = 40
TITLE_Y = 50


class RoomScreen(Screen):
    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Room", font_size=1.0).render(canvas)
