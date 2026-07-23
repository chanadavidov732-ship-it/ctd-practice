"""Home (menu) screen -- shows the logged-in user and offers Play/Room,
mirroring the two options client/cli/home.py already sends today.
"""

from client.network.app_bridge import CONNECTION_LOST, RESPONSE
from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.screens.matchmaking_screen import MatchmakingScreen
from client.ui.screens.room_screen import RoomScreen
from client.ui.widgets import Button, ErrorText, Label
from shared.protocol import Envelope

STATUS_IDLE = "idle"
STATUS_WAITING_ACK = "waiting_ack"
STATUS_DISCONNECTED = "disconnected"

CHOICE_PLAY = "play"
CHOICE_ROOM = "room"

DISCONNECTED_MESSAGE = "Disconnected from server."

TITLE_X = 40
TITLE_Y = 50
STATUS_LINE_X = 40
STATUS_LINE_Y = 90

PLAY_BUTTON_X = 40
PLAY_BUTTON_Y = 140
ROOM_BUTTON_X = 40
ROOM_BUTTON_Y = 200
MENU_BUTTON_WIDTH = 150
MENU_BUTTON_HEIGHT = 42

BACK_BUTTON_X = 40
BACK_BUTTON_Y = 140
BACK_BUTTON_WIDTH = 180
BACK_BUTTON_HEIGHT = 42

MESSAGE_X = 40
MESSAGE_Y = 270


class HomeScreen(Screen):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.username = "?"
        self.rating: int | None = None
        self.status = STATUS_IDLE
        self.pending_choice: str | None = None

        self.play_button = Button(x=PLAY_BUTTON_X, y=PLAY_BUTTON_Y, width=MENU_BUTTON_WIDTH, height=MENU_BUTTON_HEIGHT, text="Play")
        self.room_button = Button(x=ROOM_BUTTON_X, y=ROOM_BUTTON_Y, width=MENU_BUTTON_WIDTH, height=MENU_BUTTON_HEIGHT, text="Room")
        self.back_button = Button(x=BACK_BUTTON_X, y=BACK_BUTTON_Y, width=BACK_BUTTON_WIDTH, height=BACK_BUTTON_HEIGHT, text="Back to Login")

    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")

    def update(self) -> None:
        for event in self.bridge.poll_events():
            if event.kind == CONNECTION_LOST:
                self.status = STATUS_DISCONNECTED
            elif event.kind == RESPONSE:
                self._advance()

    def _advance(self) -> None:
        payload = {"username": self.username, "rating": self.rating}
        if self.pending_choice == CHOICE_ROOM:
            self.next_screen = (RoomScreen, payload)
        else:
            self.next_screen = (MatchmakingScreen, payload)

    def handle_click(self, x: int, y: int) -> None:
        if self.status == STATUS_DISCONNECTED:
            if self.back_button.hit_test(x, y):
                # Imported lazily: login_screen.py imports HomeScreen at module
                # level, so importing LoginScreen back at module level here
                # would create a circular import.
                from client.ui.screens.login_screen import LoginScreen

                self.next_screen = (LoginScreen, {})
            return

        if self.status != STATUS_IDLE:
            return

        if self.play_button.hit_test(x, y):
            self._select(CHOICE_PLAY)
        elif self.room_button.hit_test(x, y):
            self._select(CHOICE_ROOM)

    def _select(self, choice: str) -> None:
        self.pending_choice = choice
        self.status = STATUS_WAITING_ACK
        self.bridge.send_request(Envelope(type="menu_select", payload={"choice": choice}))

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Home", font_size=1.0).render(canvas)
        rating_text = self.rating if self.rating is not None else "N/A"
        Label(x=STATUS_LINE_X, y=STATUS_LINE_Y, text=f"Logged in as {self.username} (rating {rating_text})").render(canvas)

        if self.status == STATUS_DISCONNECTED:
            ErrorText(x=MESSAGE_X, y=MESSAGE_Y, text=DISCONNECTED_MESSAGE).render(canvas)
            self.back_button.render(canvas)
            return

        self.play_button.render(canvas)
        self.room_button.render(canvas)

        if self.status == STATUS_WAITING_ACK:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Sending...").render(canvas)
