"""Graphical Login/Register screen -- the graphical flow's entry point
(wired up in client/main.py from this iteration onward).
"""

from client.cli.login import SERVER_URI
from client.network.app_bridge import BROADCAST, CONNECTED, CONNECTION_LOST, RESPONSE
from client.ui.img import Img
from client.ui.screens.base_screen import Screen
from client.ui.screens.home_screen import HomeScreen
from client.ui.widgets import Button, ErrorText, Label, TextInput
from shared.protocol import Envelope

STATUS_CONNECTING = "connecting"
STATUS_CONNECT_ERROR = "connect_error"
STATUS_FORM = "form"
STATUS_SUBMITTING = "submitting"

MODE_LOGIN = "login"
MODE_REGISTER = "register"

CONNECT_ERROR_MESSAGE = "Could not reach the server."
EMPTY_FIELDS_MESSAGE = "Username and password are required."

TITLE_X = 40
TITLE_Y = 50

TAB_Y = 90
TAB_HEIGHT = 36
LOGIN_TAB_X = 40
LOGIN_TAB_WIDTH = 110
REGISTER_TAB_X = 160
REGISTER_TAB_WIDTH = 110

FIELD_X = 40
FIELD_WIDTH = 320
FIELD_HEIGHT = 36
USERNAME_Y = 150
PASSWORD_Y = 200

SUBMIT_X = 40
SUBMIT_Y = 260
SUBMIT_WIDTH = 150
SUBMIT_HEIGHT = 42

RETRY_X = 40
RETRY_Y = 150
RETRY_WIDTH = 150
RETRY_HEIGHT = 42

STATUS_TEXT_X = 40
STATUS_TEXT_Y = 330

ACTIVE_TAB_MARKER = "> {} <"


class LoginScreen(Screen):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.mode = MODE_LOGIN
        self.status = STATUS_CONNECTING
        self.error_message: str | None = None

        self.username_field = TextInput(x=FIELD_X, y=USERNAME_Y, width=FIELD_WIDTH, height=FIELD_HEIGHT)
        self.password_field = TextInput(x=FIELD_X, y=PASSWORD_Y, width=FIELD_WIDTH, height=FIELD_HEIGHT, masked=True)
        self._focus(self.username_field)

        self.login_tab = Button(x=LOGIN_TAB_X, y=TAB_Y, width=LOGIN_TAB_WIDTH, height=TAB_HEIGHT, text="Login")
        self.register_tab = Button(x=REGISTER_TAB_X, y=TAB_Y, width=REGISTER_TAB_WIDTH, height=TAB_HEIGHT, text="Register")
        self.submit_button = Button(x=SUBMIT_X, y=SUBMIT_Y, width=SUBMIT_WIDTH, height=SUBMIT_HEIGHT, text="Submit")
        self.retry_button = Button(x=RETRY_X, y=RETRY_Y, width=RETRY_WIDTH, height=RETRY_HEIGHT, text="Try Again")

    def on_enter(self, payload: dict) -> None:
        self.bridge.connect(SERVER_URI)

    def update(self) -> None:
        for event in self.bridge.poll_events():
            if event.kind == CONNECTED:
                self.status = STATUS_FORM
            elif event.kind == CONNECTION_LOST:
                self.status = STATUS_CONNECT_ERROR
                self.error_message = None
            elif event.kind == RESPONSE:
                self._handle_auth_response(event.envelope.payload)
            elif event.kind == BROADCAST:
                pass  # not expected on this screen

    def _handle_auth_response(self, payload: dict) -> None:
        if payload.get("success"):
            home_payload = {"username": self.username_field.value.strip(), "rating": payload.get("rating")}
            self.next_screen = (HomeScreen, home_payload)
            return
        self.status = STATUS_FORM
        self.error_message = payload.get("message", "login failed")

    def handle_click(self, x: int, y: int) -> None:
        if self.status == STATUS_CONNECT_ERROR:
            if self.retry_button.hit_test(x, y):
                self.status = STATUS_CONNECTING
                self.bridge.connect(SERVER_URI)
            return

        if self.status != STATUS_FORM:
            return

        if self.login_tab.hit_test(x, y):
            self.mode = MODE_LOGIN
        elif self.register_tab.hit_test(x, y):
            self.mode = MODE_REGISTER
        elif self.username_field.hit_test(x, y):
            self._focus(self.username_field)
        elif self.password_field.hit_test(x, y):
            self._focus(self.password_field)
        elif self.submit_button.hit_test(x, y):
            self._submit()

    def handle_key(self, key: int) -> None:
        if self.status != STATUS_FORM:
            return

        if self.username_field.focused:
            if self.username_field.handle_key(key):
                self._focus(self.password_field)
        elif self.password_field.focused:
            if self.password_field.handle_key(key):
                self._submit()

    def _focus(self, field: TextInput) -> None:
        self.username_field.focused = field is self.username_field
        self.password_field.focused = field is self.password_field

    def _submit(self) -> None:
        username = self.username_field.value.strip()
        password = self.password_field.value.strip()
        if not username or not password:
            self.error_message = EMPTY_FIELDS_MESSAGE
            return

        self.error_message = None
        self.status = STATUS_SUBMITTING
        self.bridge.send_request(Envelope(type=self.mode, payload={"username": username, "password": password}))

    def render(self, canvas: Img) -> None:
        Label(x=TITLE_X, y=TITLE_Y, text="Kung Fu Chess", font_size=1.0).render(canvas)

        if self.status == STATUS_CONNECTING:
            Label(x=STATUS_TEXT_X, y=STATUS_TEXT_Y, text="Connecting to server...").render(canvas)
            return

        if self.status == STATUS_CONNECT_ERROR:
            ErrorText(x=STATUS_TEXT_X, y=STATUS_TEXT_Y, text=CONNECT_ERROR_MESSAGE).render(canvas)
            self.retry_button.render(canvas)
            return

        self._render_tab(canvas, self.login_tab, MODE_LOGIN)
        self._render_tab(canvas, self.register_tab, MODE_REGISTER)
        self.username_field.render(canvas)
        self.password_field.render(canvas)
        self.submit_button.render(canvas)

        if self.status == STATUS_SUBMITTING:
            Label(x=STATUS_TEXT_X, y=STATUS_TEXT_Y, text="Submitting...").render(canvas)
        elif self.error_message:
            ErrorText(x=STATUS_TEXT_X, y=STATUS_TEXT_Y, text=self.error_message).render(canvas)

    def _render_tab(self, canvas: Img, tab: Button, mode: str) -> None:
        original_text = tab.text
        tab.text = ACTIVE_TAB_MARKER.format(original_text) if self.mode == mode else original_text
        tab.render(canvas)
        tab.text = original_text
