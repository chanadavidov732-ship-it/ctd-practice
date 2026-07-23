"""Matchmaking (Play) screen -- placeholder for iteration 13 (proves the
Home -> Matchmaking handoff); iteration 15 fills this in with the real
"searching for opponent" flow (match_found/match_timeout/Cancel).
"""

from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Label

TITLE_X = 40
TITLE_Y = 50


class MatchmakingScreen(Screen):
    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Matchmaking", font_size=1.0).render(canvas)
