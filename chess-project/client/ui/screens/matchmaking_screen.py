import time

from client.network.app_bridge import CONNECTION_LOST
from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Button, ErrorText, Label
from shared.config import (
    MATCH_TIMEOUT_SECONDS,
    MSG_CANCEL_PLAY,
    MSG_GAME_STARTED,
    MSG_MATCH_FOUND,
    MSG_MATCH_TIMEOUT,
    MSG_PLAY,
    MSG_PLAY_CANCELLED,
    MSG_PLAY_QUEUED,
)
from shared.protocol import Envelope

STATE_QUEUING = "queuing"
STATE_SEARCHING = "searching"
STATE_CANCELLING = "cancelling"
STATE_TIMEOUT = "timeout"
STATE_QUEUE_ERROR = "queue_error"
STATE_DISCONNECTED = "disconnected"

DISCONNECTED_MESSAGE = "Disconnected from server."
TIMEOUT_MESSAGE = f"No opponent found within {MATCH_TIMEOUT_SECONDS} seconds."

TITLE_X = 40
TITLE_Y = 50
STATUS_LINE_X = 40
STATUS_LINE_Y = 120
OPPONENT_LINE_Y = 150

CANCEL_BUTTON_X = 40
CANCEL_BUTTON_Y = 190
CANCEL_BUTTON_WIDTH = 150
CANCEL_BUTTON_HEIGHT = 42

BACK_BUTTON_X = 40
BACK_BUTTON_Y = 140
BACK_BUTTON_WIDTH = 180
BACK_BUTTON_HEIGHT = 42
BACK_TO_LOGIN_TEXT = "Back to Login"
BACK_TO_HOME_TEXT = "Back to Home"

MESSAGE_X = 40
MESSAGE_Y = 270


class MatchmakingScreen(Screen):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.username = "?"
        self.rating: int | None = None
        self.status = STATE_QUEUING
        self.error_message: str | None = None
        self.opponent_username: str | None = None
        self.opponent_rating: int | None = None
        self._search_started_at: float | None = None

        self.cancel_button = Button(x=CANCEL_BUTTON_X, y=CANCEL_BUTTON_Y, width=CANCEL_BUTTON_WIDTH, height=CANCEL_BUTTON_HEIGHT, text="Cancel")
        self.back_button = Button(x=BACK_BUTTON_X, y=BACK_BUTTON_Y, width=BACK_BUTTON_WIDTH, height=BACK_BUTTON_HEIGHT, text=BACK_TO_HOME_TEXT)

    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")
        self.status = STATE_QUEUING
        self.bridge.send_request(Envelope(type=MSG_PLAY, payload={}))

    def update(self) -> None:
        for event in self.bridge.poll_events():
            if event.kind == CONNECTION_LOST:
                self.status = STATE_DISCONNECTED
                continue

            envelope = event.envelope
            if envelope is None:
                continue

            if envelope.type == MSG_GAME_STARTED:
                self._enter_game(envelope.payload)
                return
            if envelope.type == MSG_MATCH_TIMEOUT:
                self.status = STATE_TIMEOUT
                continue

            if self.status == STATE_QUEUING and envelope.type in (MSG_PLAY_QUEUED, MSG_PLAY):
                self._handle_play_response(envelope.payload)
            elif self.status == STATE_SEARCHING and envelope.type == MSG_MATCH_FOUND:
                self.opponent_username = envelope.payload.get("opponent_username")
                self.opponent_rating = envelope.payload.get("opponent_rating")
            elif self.status == STATE_CANCELLING and envelope.type == MSG_PLAY_CANCELLED:
                self._return_to_home()

    def _handle_play_response(self, payload: dict) -> None:
        if payload.get("success") is False:
            self.status = STATE_QUEUE_ERROR
            self.error_message = payload.get("message", "could not queue for a match")
            return

        self.rating = payload.get("rating", self.rating)
        self.status = STATE_SEARCHING
        self._search_started_at = time.perf_counter()

    def _enter_game(self, payload: dict) -> None:
        from client.ui.game_runner import run_graphical_game

        engine = self.bridge.build_remote_engine(payload)
        wants_menu = run_graphical_game(self.bridge, engine)
        self.rating = engine.new_ratings.get(self.username, self.rating)
        if wants_menu:
            self._return_to_home()
        else:
            self.should_quit = True

    def _return_to_home(self) -> None:
        from client.ui.screens.home_screen import HomeScreen

        self.next_screen = (HomeScreen, {"username": self.username, "rating": self.rating})

    def handle_click(self, x: int, y: int) -> None:
        if self.status in (STATE_DISCONNECTED, STATE_QUEUE_ERROR, STATE_TIMEOUT):
            if self.back_button.hit_test(x, y):
                self._go_back()
            return

        if self.status == STATE_SEARCHING and self.cancel_button.hit_test(x, y):
            self._cancel()

    def _go_back(self) -> None:
        if self.status == STATE_DISCONNECTED:
            from client.ui.screens.login_screen import LoginScreen

            self.next_screen = (LoginScreen, {})
        else:
            self._return_to_home()

    def _cancel(self) -> None:
        self.status = STATE_CANCELLING
        self.bridge.send_request(Envelope(type=MSG_CANCEL_PLAY, payload={}))

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Matchmaking", font_size=1.0).render(canvas)

        if self.status == STATE_DISCONNECTED:
            ErrorText(x=MESSAGE_X, y=MESSAGE_Y, text=DISCONNECTED_MESSAGE).render(canvas)
            self.back_button.text = BACK_TO_LOGIN_TEXT
            self.back_button.render(canvas)
            return

        if self.status == STATE_QUEUE_ERROR:
            ErrorText(x=MESSAGE_X, y=MESSAGE_Y, text=self.error_message).render(canvas)
            self.back_button.text = BACK_TO_HOME_TEXT
            self.back_button.render(canvas)
            return

        if self.status == STATE_TIMEOUT:
            Label(x=STATUS_LINE_X, y=STATUS_LINE_Y, text=TIMEOUT_MESSAGE).render(canvas)
            self.back_button.text = BACK_TO_HOME_TEXT
            self.back_button.render(canvas)
            return

        if self.status == STATE_QUEUING:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Queuing...").render(canvas)
            return

        elapsed = int(time.perf_counter() - self._search_started_at) if self._search_started_at else 0
        Label(x=STATUS_LINE_X, y=STATUS_LINE_Y, text=f"Searching for opponent... ({elapsed}s)").render(canvas)
        if self.opponent_username is not None:
            opponent_text = f"Match found: {self.opponent_username} (rating {self.opponent_rating})"
            Label(x=STATUS_LINE_X, y=OPPONENT_LINE_Y, text=opponent_text).render(canvas)

        if self.status == STATE_SEARCHING:
            self.cancel_button.render(canvas)
        else:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Leaving...").render(canvas)
