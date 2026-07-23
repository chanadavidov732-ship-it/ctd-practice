"""Room screen -- Create/Join/wait, mirroring client/cli/room.py's run_room_menu
+ _wait_in_room (one continuous flow across sub-states on the same screen).
"""

from client.network.app_bridge import CONNECTION_LOST
from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.widgets import Button, ErrorText, Label, TextInput
from shared.protocol import Envelope

STATE_CHOICE = "choice"
STATE_JOIN_FORM = "join_form"
STATE_WAITING_ACK = "waiting_ack"
STATE_WAITING = "waiting"
STATE_CANCELLING = "cancelling"
STATE_DISCONNECTED = "disconnected"

DISCONNECTED_MESSAGE = "Disconnected from server."
ROOM_ID_REQUIRED_MESSAGE = "Room ID is required."

TITLE_X = 40
TITLE_Y = 50

CHOICE_BUTTON_WIDTH = 150
CHOICE_BUTTON_HEIGHT = 42
CREATE_BUTTON_X = 40
CREATE_BUTTON_Y = 120
JOIN_BUTTON_X = 40
JOIN_BUTTON_Y = 180

FIELD_LABEL_X = 40
FIELD_LABEL_Y = 120
FIELD_X = 40
FIELD_Y = 140
FIELD_WIDTH = 240
FIELD_HEIGHT = 36
JOIN_CONFIRM_X = 40
JOIN_CONFIRM_Y = 190
JOIN_CONFIRM_WIDTH = 150
JOIN_CONFIRM_HEIGHT = 42

STATUS_LINE_X = 40
ROOM_ID_Y = 90
COUNTS_Y = 130
ROLE_Y = 160
CANCEL_BUTTON_X = 40
CANCEL_BUTTON_Y = 190
CANCEL_BUTTON_WIDTH = 150
CANCEL_BUTTON_HEIGHT = 42

BACK_BUTTON_X = 40
BACK_BUTTON_Y = 140
BACK_BUTTON_WIDTH = 180
BACK_BUTTON_HEIGHT = 42

MESSAGE_X = 40
MESSAGE_Y = 270


class RoomScreen(Screen):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.username = "?"
        self.rating: int | None = None
        self.status = STATE_CHOICE
        self.error_message: str | None = None

        self.room_id: str | None = None
        self.role: str | None = None
        self.player_count = 0
        self.viewer_count = 0

        self.create_button = Button(x=CREATE_BUTTON_X, y=CREATE_BUTTON_Y, width=CHOICE_BUTTON_WIDTH, height=CHOICE_BUTTON_HEIGHT, text="Create")
        self.join_button = Button(x=JOIN_BUTTON_X, y=JOIN_BUTTON_Y, width=CHOICE_BUTTON_WIDTH, height=CHOICE_BUTTON_HEIGHT, text="Join")
        self.room_id_field = TextInput(x=FIELD_X, y=FIELD_Y, width=FIELD_WIDTH, height=FIELD_HEIGHT)
        self.join_confirm_button = Button(x=JOIN_CONFIRM_X, y=JOIN_CONFIRM_Y, width=JOIN_CONFIRM_WIDTH, height=JOIN_CONFIRM_HEIGHT, text="Join Room")
        self.cancel_button = Button(x=CANCEL_BUTTON_X, y=CANCEL_BUTTON_Y, width=CANCEL_BUTTON_WIDTH, height=CANCEL_BUTTON_HEIGHT, text="Cancel")
        self.back_button = Button(x=BACK_BUTTON_X, y=BACK_BUTTON_Y, width=BACK_BUTTON_WIDTH, height=BACK_BUTTON_HEIGHT, text="Back to Login")

    def on_enter(self, payload: dict) -> None:
        self.username = payload.get("username", "?")
        self.rating = payload.get("rating")

    def update(self) -> None:
        for event in self.bridge.poll_events():
            if event.kind == CONNECTION_LOST:
                self.status = STATE_DISCONNECTED
                continue

            envelope = event.envelope
            if envelope is None:
                continue

            if self.status == STATE_WAITING_ACK and envelope.type in ("room_state", "join_room"):
                self._handle_room_response(envelope.payload)
            elif self.status == STATE_CANCELLING and envelope.type == "room_state":
                self._return_to_home()
            elif self.status == STATE_WAITING:
                if envelope.type == "room_state":
                    self.player_count = envelope.payload.get("player_count", self.player_count)
                    self.viewer_count = envelope.payload.get("viewer_count", self.viewer_count)
                elif envelope.type == "game_started":
                    self._enter_game(envelope.payload)

    def _handle_room_response(self, payload: dict) -> None:
        if payload.get("success") is False:
            self.status = STATE_JOIN_FORM
            self.error_message = payload.get("message", "could not join room")
            return

        self.room_id = payload["room_id"]
        self.role = payload["role"]
        self.player_count = payload.get("player_count", 0)
        self.viewer_count = payload.get("viewer_count", 0)
        self.error_message = None
        self.status = STATE_WAITING

    def _enter_game(self, payload: dict) -> None:
        # Imported lazily: only reached once a game actually starts, not by
        # every screen that merely imports RoomScreen (e.g. HomeScreen).
        from client.ui.game_runner import run_graphical_game

        engine = self.bridge.build_remote_engine(payload)
        run_graphical_game(self.bridge, engine)
        self.should_quit = True

    def _return_to_home(self) -> None:
        # Imported lazily: home_screen.py imports RoomScreen at module level,
        # so importing HomeScreen back at module level here would create a
        # circular import.
        from client.ui.screens.home_screen import HomeScreen

        self.next_screen = (HomeScreen, {"username": self.username, "rating": self.rating})

    def handle_click(self, x: int, y: int) -> None:
        if self.status == STATE_DISCONNECTED:
            if self.back_button.hit_test(x, y):
                from client.ui.screens.login_screen import LoginScreen

                self.next_screen = (LoginScreen, {})
            return

        if self.status == STATE_CHOICE:
            if self.create_button.hit_test(x, y):
                self._create()
            elif self.join_button.hit_test(x, y):
                self.status = STATE_JOIN_FORM
                self.room_id_field.focused = True
        elif self.status == STATE_JOIN_FORM:
            if self.room_id_field.hit_test(x, y):
                self.room_id_field.focused = True
            elif self.join_confirm_button.hit_test(x, y):
                self._join()
        elif self.status == STATE_WAITING:
            if self.cancel_button.hit_test(x, y):
                self._cancel()

    def handle_key(self, key: int) -> None:
        if self.status != STATE_JOIN_FORM:
            return
        if self.room_id_field.handle_key(key):
            self._join()

    def _create(self) -> None:
        self.status = STATE_WAITING_ACK
        self.error_message = None
        self.bridge.send_request(Envelope(type="create_room", payload={}))

    def _join(self) -> None:
        room_id = self.room_id_field.value.strip()
        if not room_id:
            self.error_message = ROOM_ID_REQUIRED_MESSAGE
            return
        self.error_message = None
        self.status = STATE_WAITING_ACK
        self.bridge.send_request(Envelope(type="join_room", payload={"room_id": room_id}))

    def _cancel(self) -> None:
        self.status = STATE_CANCELLING
        self.bridge.send_request(Envelope(type="cancel_room", payload={"room_id": self.room_id}))

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Room", font_size=1.0).render(canvas)

        if self.status == STATE_DISCONNECTED:
            ErrorText(x=MESSAGE_X, y=MESSAGE_Y, text=DISCONNECTED_MESSAGE).render(canvas)
            self.back_button.render(canvas)
            return

        if self.status == STATE_CHOICE:
            self.create_button.render(canvas)
            self.join_button.render(canvas)
            return

        if self.status == STATE_JOIN_FORM:
            Label(x=FIELD_LABEL_X, y=FIELD_LABEL_Y, text="Room ID:").render(canvas)
            self.room_id_field.render(canvas)
            self.join_confirm_button.render(canvas)
            if self.error_message:
                ErrorText(x=MESSAGE_X, y=MESSAGE_Y, text=self.error_message).render(canvas)
            return

        if self.status == STATE_WAITING_ACK:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Sending...").render(canvas)
            return

        # STATE_WAITING or STATE_CANCELLING
        Label(x=STATUS_LINE_X, y=ROOM_ID_Y, text=f"Room ID: {self.room_id}").render(canvas)
        Label(x=STATUS_LINE_X, y=COUNTS_Y, text=f"Players: {self.player_count}/2  Viewers: {self.viewer_count}").render(canvas)
        Label(x=STATUS_LINE_X, y=ROLE_Y, text=f"Role: {self.role}").render(canvas)
        self.cancel_button.render(canvas)
        if self.status == STATE_CANCELLING:
            Label(x=MESSAGE_X, y=MESSAGE_Y, text="Leaving...").render(canvas)
