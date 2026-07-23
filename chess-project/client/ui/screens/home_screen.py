"""Home screen -- placeholder for iteration 12 (just proves the Login ->
Home handoff works end to end); iteration 13 fills this in with the real
Play/Room menu.
"""

from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Label

TITLE_X = 40
TITLE_Y = 50
STATUS_X = 40
STATUS_Y = 90


class HomeScreen(Screen):
    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Home", font_size=1.0).render(canvas)
        rating_text = self.rating if self.rating is not None else "N/A"
        Label(x=STATUS_X, y=STATUS_Y, text=f"Logged in as {self.username} (rating {rating_text})").render(canvas)
