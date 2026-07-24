"""Matchmaking (Play) screen -- mirrors client/cli/play.py's run_play_menu +
_wait_for_match (one continuous flow: queue -> search -> game/timeout/cancel).
"""

import time

from client.network.app_bridge import CONNECTION_LOST
from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Button, ErrorText, Label
from shared.protocol import Envelope

STATE_QUEUING = "queuing"
STATE_SEARCHING = "searching"
STATE_CANCELLING = "cancelling"
STATE_TIMEOUT = "timeout"
STATE_QUEUE_ERROR = "queue_error"
STATE_DISCONNECTED = "disconnected"

DISCONNECTED_MESSAGE = "Disconnected from server."
TIMEOUT_MESSAGE = "No opponent found within 60 seconds."

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
        self.bridge.send_request(Envelope(type="play", payload={}))

    def update(self) -> None:
        for event in self.bridge.poll_events():
            if event.kind == CONNECTION_LOST:
                self.status = STATE_DISCONNECTED
                continue

            envelope = event.envelope
            if envelope is None:
                continue

            # game_started/match_timeout always win, regardless of the current
            # sub-state: the same race client/cli/play.py's _wait_for_match
            # already resolves today (a match can be found the instant before
            # Cancel is clicked, even after cancel_play was already sent).
            if envelope.type == "game_started":
                self._enter_game(envelope.payload)
                return
            if envelope.type == "match_timeout":
                self.status = STATE_TIMEOUT
                continue

            if self.status == STATE_QUEUING and envelope.type in ("play_queued", "play"):
                self._handle_play_response(envelope.payload)
            elif self.status == STATE_SEARCHING and envelope.type == "match_found":
                self.opponent_username = envelope.payload.get("opponent_username")
                self.opponent_rating = envelope.payload.get("opponent_rating")
            elif self.status == STATE_CANCELLING and envelope.type == "play_cancelled":
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
        # Imported lazily: only reached once a game actually starts, not by
        # every screen that merely imports MatchmakingScreen (e.g. HomeScreen).
        from client.ui.game_runner import run_graphical_game

        engine = self.bridge.build_remote_engine(payload)
        wants_menu = run_graphical_game(self.bridge, engine)
        if wants_menu:
            self._return_to_home()
        else:
            self.should_quit = True

    def _return_to_home(self) -> None:
        # Imported lazily: home_screen.py imports MatchmakingScreen at module
        # level, so importing HomeScreen back at module level here would
        # create a circular import.
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
        self.bridge.send_request(Envelope(type="cancel_play", payload={}))

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

        # STATE_SEARCHING or STATE_CANCELLING
        elapsed = int(time.perf_counter() - self._search_started_at) if self._search_started_at else 0
        Label(x=STATUS_LINE_X, y=STATUS_LINE_Y, text=f"Searching for opponent... ({elapsed}s)").render(canvas)
        if self.opponent_username is not None:
            opponent_text = f"Match found: {self.opponent_username} (rating {self.opponent_rating})"
            Label(x=STATUS_LINE_X, y=OPPONENT_LINE_Y, text=opponent_text).render(canvas)

        if self.status == STATE_SEARCHING:
            self.cancel_button.render(canvas)
        else:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Leaving...").render(canvas)
