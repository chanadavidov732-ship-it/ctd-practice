import numpy as np
import pytest

from client.ui.img import Img
from client.ui.screens.matchmaking_screen import MatchmakingScreen
from client.ui.screens.room_screen import RoomScreen


def _blank_canvas(width=640, height=480) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


@pytest.mark.parametrize("screen_class", [MatchmakingScreen, RoomScreen])
def test_on_enter_stores_username_and_rating(screen_class):
    screen = screen_class(bridge=None)
    screen.on_enter({"username": "alice", "rating": 1310})
    assert screen.username == "alice"
    assert screen.rating == 1310


@pytest.mark.parametrize("screen_class", [MatchmakingScreen, RoomScreen])
def test_on_enter_defaults_when_payload_is_missing_fields(screen_class):
    screen = screen_class(bridge=None)
    screen.on_enter({})
    assert screen.username == "?"
    assert screen.rating is None


@pytest.mark.parametrize("screen_class", [MatchmakingScreen, RoomScreen])
def test_render_does_not_raise(screen_class):
    screen = screen_class(bridge=None)
    screen.on_enter({"username": "alice", "rating": 1200})
    screen.render(_blank_canvas())
