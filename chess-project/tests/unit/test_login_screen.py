import numpy as np

from client.network.app_bridge import AppEvent, CONNECTED, CONNECTION_LOST, RESPONSE
from client.ui.img import Img
from client.ui.screens.home_screen import HomeScreen
from client.ui.screens.login_screen import (
    MODE_LOGIN,
    MODE_REGISTER,
    STATUS_CONNECT_ERROR,
    STATUS_CONNECTING,
    STATUS_FORM,
    STATUS_SUBMITTING,
    LoginScreen,
)
from shared.protocol import Envelope


class FakeBridge:
    def __init__(self):
        self.connect_calls: list[str] = []
        self.sent_requests: list[Envelope] = []
        self._events: list[AppEvent] = []

    def connect(self, uri: str) -> None:
        self.connect_calls.append(uri)

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


def _make_screen() -> tuple[LoginScreen, FakeBridge]:
    bridge = FakeBridge()
    screen = LoginScreen(bridge)
    screen.on_enter({})
    return screen, bridge


def test_on_enter_triggers_a_connect_attempt():
    screen, bridge = _make_screen()
    assert bridge.connect_calls == [screen_uri(screen)]
    assert screen.status == STATUS_CONNECTING


def screen_uri(screen: LoginScreen) -> str:
    from client.cli.login import SERVER_URI

    return SERVER_URI


def test_connected_event_moves_to_form_status():
    screen, bridge = _make_screen()
    bridge.push(AppEvent(kind=CONNECTED))
    screen.update()
    assert screen.status == STATUS_FORM


def _to_form(screen: LoginScreen, bridge: FakeBridge) -> None:
    bridge.push(AppEvent(kind=CONNECTED))
    screen.update()


def test_submit_blocked_when_fields_are_empty():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)

    screen._submit()

    assert screen.status == STATUS_FORM
    assert bridge.sent_requests == []
    assert screen.error_message


def test_submit_sends_request_in_current_mode():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)
    screen.username_field.value = "alice"
    screen.password_field.value = "secret"

    screen.mode = MODE_REGISTER
    screen._submit()

    assert screen.status == STATUS_SUBMITTING
    assert len(bridge.sent_requests) == 1
    sent = bridge.sent_requests[0]
    assert sent.type == MODE_REGISTER
    assert sent.payload == {"username": "alice", "password": "secret"}


def test_tab_click_switches_mode_without_sending_a_request():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)

    screen.handle_click(screen.register_tab.x + 5, screen.register_tab.y + 5)
    assert screen.mode == MODE_REGISTER
    assert bridge.sent_requests == []

    screen.handle_click(screen.login_tab.x + 5, screen.login_tab.y + 5)
    assert screen.mode == MODE_LOGIN


def test_successful_response_transitions_to_home_with_payload():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)
    screen.username_field.value = "alice"
    screen.password_field.value = "secret"
    screen._submit()

    bridge.push(AppEvent(kind=RESPONSE, envelope=Envelope(type="login_result", payload={"success": True, "rating": 1200})))
    screen.update()

    assert screen.next_screen is not None
    screen_class, payload = screen.next_screen
    assert screen_class is HomeScreen
    assert payload == {"username": "alice", "rating": 1200}


def test_failed_response_shows_error_and_stays_on_form():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)
    screen.username_field.value = "alice"
    screen.password_field.value = "wrong"
    screen._submit()

    bridge.push(
        AppEvent(kind=RESPONSE, envelope=Envelope(type="login_result", payload={"success": False, "message": "bad password"}))
    )
    screen.update()

    assert screen.next_screen is None
    assert screen.status == STATUS_FORM
    assert screen.error_message == "bad password"


def test_connection_lost_shows_connect_error_state():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)

    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()

    assert screen.status == STATUS_CONNECT_ERROR


def test_retry_click_triggers_another_connect_attempt():
    screen, bridge = _make_screen()
    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()
    assert screen.status == STATUS_CONNECT_ERROR

    screen.handle_click(screen.retry_button.x + 5, screen.retry_button.y + 5)

    assert screen.status == STATUS_CONNECTING
    assert len(bridge.connect_calls) == 2  # initial on_enter + retry


def test_enter_key_moves_focus_from_username_to_password():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)
    screen.username_field.value = "alice"

    screen.handle_key(13)  # Enter

    assert screen.password_field.focused is True
    assert screen.username_field.focused is False
    assert bridge.sent_requests == []  # doesn't submit yet


def test_enter_key_on_password_field_submits():
    screen, bridge = _make_screen()
    _to_form(screen, bridge)
    screen.username_field.value = "alice"
    screen.password_field.value = "secret"
    screen._focus(screen.password_field)

    screen.handle_key(13)  # Enter

    assert len(bridge.sent_requests) == 1


def test_render_does_not_raise_in_every_status():
    screen, bridge = _make_screen()
    screen.render(_blank_canvas())  # connecting

    _to_form(screen, bridge)
    screen.render(_blank_canvas())  # form

    screen.username_field.value = "alice"
    screen.password_field.value = "secret"
    screen._submit()
    screen.render(_blank_canvas())  # submitting

    bridge.push(AppEvent(kind=CONNECTION_LOST))
    screen.update()
    screen.render(_blank_canvas())  # connect_error
