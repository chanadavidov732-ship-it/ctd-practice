import numpy as np

from client.network.app_bridge import AppEvent, CONNECTION_LOST, RESPONSE
from client.ui.img import Img
from client.ui.screens.home_screen import STATUS_DISCONNECTED, STATUS_IDLE, STATUS_WAITING_ACK, HomeScreen
from client.ui.screens.login_screen import LoginScreen
from client.ui.screens.matchmaking_screen import MatchmakingScreen
from client.ui.screens.room_screen import RoomScreen
from shared.protocol import Envelope


class FakeBridge:
    def __init__(self):
        self.sent_requests: list[Envelope] = []
        self._events: list[AppEvent] = []

    def send_request(self, envelope: Envelope) -> None:
        self.sent_requests.append(envelope)

    def poll_events(self) -> list[AppEvent]:
        events, self._events = self._events, []
        return events

    def push(self, event: AppEvent) -> None:
        self._events.append(event)


def _blank_canvas(width=640, height=480) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


def _make_screen() -> tuple[HomeScreen, FakeBridge]:
    bridge = FakeBridge()
    screen = HomeScreen(bridge)
    screen.on_enter({"username": "alice", "rating": 1310})
    return screen, bridge


def test_on_enter_stores_username_and_rating():
    screen, _ = _make_screen()
    assert screen.username == "alice"
    assert screen.rating == 1310
    assert screen.status == STATUS_IDLE


def test_on_enter_defaults_when_payload_is_missing_fields():
    screen = HomeScreen(bridge=FakeBridge())
    screen.on_enter({})
    assert screen.username == "?"
    assert screen.rating is None


def test_play_click_sends_menu_select_and_waits():
    screen, bridge = _make_screen()

    screen.handle_click(screen.play_button.x + 5, screen.play_button.y + 5)

    assert screen.status == STATUS_WAITING_ACK
    assert len(bridge.sent_requests) == 1
    sent = bridge.sent_requests[0]
    assert sent.type == "menu_select"
    assert sent.payload == {"choice": "play"}


def test_room_click_sends_menu_select_and_waits():
    screen, bridge = _make_screen()

    screen.handle_click(screen.room_button.x + 5, screen.room_button.y + 5)

    assert screen.status == STATUS_WAITING_ACK
    assert bridge.sent_requests[0].payload == {"choice": "room"}


def test_ack_after_play_transitions_to_matchmaking_with_payload():
    screen, bridge = _make_screen()
    screen.handle_click(screen.play_button.x + 5, screen.play_button.y + 5)

    bridge.push(AppEvent(kind=RESPONSE, envelope=Envelope(type="menu_ack", payload={"received": True, "choice": "play"})))
    screen.update()

    assert screen.next_screen is not None
    screen_class, payload = screen.next_screen
    assert screen_class is MatchmakingScreen
    assert payload == {"username": "alice", "rating": 1310}


def test_ack_after_room_transitions_to_room_screen():
    screen, bridge = _make_screen()
    screen.handle_click(screen.room_button.x + 5, screen.room_button.y + 5)

    bridge.push(AppEvent(kind=RESPONSE, envelope=Envelope(type="menu_ack", payload={"received": True, "choice": "room"})))
    screen.update()

    screen_class, _ = screen.next_screen
    assert screen_class is RoomScreen


def test_clicks_are_ignored_while_waiting_for_ack():
    screen, bridge = _make_screen()
    screen.handle_click(screen.play_button.x + 5, screen.play_button.y + 5)

    screen.handle_click(screen.room_button.x + 5, screen.room_button.y + 5)

    assert len(bridge.sent_requests) == 1  # the second click was ignored


def test_connection_lost_shows_disconnected_state():
    screen, bridge = _make_screen()

    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()

    assert screen.status == STATUS_DISCONNECTED


def test_back_to_login_click_transitions_to_login_screen():
    screen, bridge = _make_screen()
    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()

    screen.handle_click(screen.back_button.x + 5, screen.back_button.y + 5)

    assert screen.next_screen is not None
    screen_class, payload = screen.next_screen
    assert screen_class is LoginScreen
    assert payload == {}


def test_render_does_not_raise_in_every_status():
    screen, bridge = _make_screen()
    screen.render(_blank_canvas())  # idle

    screen.handle_click(screen.play_button.x + 5, screen.play_button.y + 5)
    screen.render(_blank_canvas())  # waiting_ack

    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()
    screen.render(_blank_canvas())  # disconnected
