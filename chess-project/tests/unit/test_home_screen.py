import numpy as np

from client.ui.img import Img
from client.ui.screens.home_screen import HomeScreen


def _blank_canvas(width=640, height=480) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


def test_on_enter_stores_username_and_rating():
    screen = HomeScreen(bridge=None)
    screen.on_enter({"username": "alice", "rating": 1310})
    assert screen.username == "alice"
    assert screen.rating == 1310


def test_on_enter_defaults_when_payload_is_missing_fields():
    screen = HomeScreen(bridge=None)
    screen.on_enter({})
    assert screen.username == "?"
    assert screen.rating is None


def test_render_does_not_raise():
    screen = HomeScreen(bridge=None)
    screen.on_enter({"username": "alice", "rating": 1200})
    screen.render(_blank_canvas())
