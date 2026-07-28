import client.ui.game_runner as game_runner_module
from client.ui.screens.room_screen import RoomScreen
from shared.protocol import Envelope


class FakeEngine:
    def __init__(self, new_ratings):
        self.new_ratings = new_ratings


class FakeBridge:
    def __init__(self, engine):
        self.sent_requests: list[Envelope] = []
        self._events = []
        self._engine = engine

    def send_request(self, envelope: Envelope) -> None:
        self.sent_requests.append(envelope)

    def poll_events(self):
        events, self._events = self._events, []
        return events

    def build_remote_engine(self, payload: dict):
        return self._engine


def _make_screen(engine_new_ratings: dict) -> tuple[RoomScreen, FakeBridge]:
    bridge = FakeBridge(FakeEngine(engine_new_ratings))
    screen = RoomScreen(bridge)
    screen.on_enter({"username": "alice", "rating": 1200})
    return screen, bridge


def test_enter_game_refreshes_rating_from_game_over_payload_before_returning_home(monkeypatch):
    screen, bridge = _make_screen({"alice": 1272, "bob": 1170})
    monkeypatch.setattr(game_runner_module, "run_graphical_game", lambda bridge, engine: True)

    screen._enter_game({"your_color": "w"})

    assert screen.rating == 1272
    screen_class, payload = screen.next_screen
    assert payload == {"username": "alice", "rating": 1272}
