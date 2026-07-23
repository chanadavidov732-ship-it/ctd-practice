"""Generic Img/cv2-based UI widgets, shared by every graphical wrapper screen
(Login/Home/Room/Matchmaking/...). Built once here (iteration 11), reused by
each screen added from iteration 12 onward -- no per-screen duplication of
button/text-field/keyboard-handling logic.
"""

from dataclasses import dataclass

import cv2

from client.ui.img import Img

ENTER_KEYS = (13, 10)
BACKSPACE_KEY = 8
PRINTABLE_KEY_MIN = 32
PRINTABLE_KEY_MAX = 126
MASK_CHAR = "*"

BUTTON_BG_COLOR = (70, 70, 70, 255)
BUTTON_BORDER_COLOR = (150, 150, 150, 255)
BUTTON_TEXT_COLOR = (255, 255, 255, 255)
BUTTON_FONT_SIZE = 0.6
BUTTON_BORDER_THICKNESS = 2
BUTTON_TEXT_THICKNESS = 2

TEXT_INPUT_BG_COLOR = (30, 30, 30, 255)
TEXT_INPUT_BORDER_COLOR = (100, 100, 100, 255)
TEXT_INPUT_FOCUS_BORDER_COLOR = (0, 255, 255, 255)
TEXT_INPUT_TEXT_COLOR = (255, 255, 255, 255)
TEXT_INPUT_FONT_SIZE = 0.6
TEXT_INPUT_BORDER_THICKNESS = 2
TEXT_INPUT_TEXT_THICKNESS = 2
TEXT_INPUT_PADDING_X = 10

LABEL_TEXT_COLOR = (255, 255, 255, 255)
LABEL_FONT_SIZE = 0.6
LABEL_TEXT_THICKNESS = 2
ERROR_TEXT_COLOR = (0, 0, 255, 255)


@dataclass
class Button:
    x: int
    y: int
    width: int
    height: int
    text: str
    font_size: float = BUTTON_FONT_SIZE

    def hit_test(self, x: int, y: int) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def render(self, canvas: Img) -> None:
        top_left = (self.x, self.y)
        bottom_right = (self.x + self.width, self.y + self.height)
        cv2.rectangle(canvas.img, top_left, bottom_right, BUTTON_BG_COLOR, -1)
        cv2.rectangle(canvas.img, top_left, bottom_right, BUTTON_BORDER_COLOR, BUTTON_BORDER_THICKNESS)

        (text_width, text_height), _ = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, self.font_size, BUTTON_TEXT_THICKNESS)
        text_x = self.x + (self.width - text_width) // 2
        text_y = self.y + (self.height + text_height) // 2
        canvas.put_text(self.text, text_x, text_y, self.font_size, BUTTON_TEXT_COLOR, thickness=BUTTON_TEXT_THICKNESS)


@dataclass
class TextInput:
    x: int
    y: int
    width: int
    height: int
    masked: bool = False
    focused: bool = False
    value: str = ""

    def hit_test(self, x: int, y: int) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def handle_key(self, key: int) -> bool:
        """Applies one keypress to the field's value. Returns True if Enter was
        pressed -- the field itself doesn't decide what Enter means (submit the
        form, move to the next field, ...); that's up to the owning screen."""
        if key in ENTER_KEYS:
            return True
        if key == BACKSPACE_KEY:
            self.value = self.value[:-1]
        elif PRINTABLE_KEY_MIN <= key <= PRINTABLE_KEY_MAX:
            self.value += chr(key)
        return False

    def render(self, canvas: Img) -> None:
        top_left = (self.x, self.y)
        bottom_right = (self.x + self.width, self.y + self.height)
        border_color = TEXT_INPUT_FOCUS_BORDER_COLOR if self.focused else TEXT_INPUT_BORDER_COLOR

        cv2.rectangle(canvas.img, top_left, bottom_right, TEXT_INPUT_BG_COLOR, -1)
        cv2.rectangle(canvas.img, top_left, bottom_right, border_color, TEXT_INPUT_BORDER_THICKNESS)

        displayed = MASK_CHAR * len(self.value) if self.masked else self.value
        if self.focused:
            displayed += "_"
        text_y = self.y + self.height // 2 + 6
        canvas.put_text(
            displayed,
            self.x + TEXT_INPUT_PADDING_X,
            text_y,
            TEXT_INPUT_FONT_SIZE,
            TEXT_INPUT_TEXT_COLOR,
            thickness=TEXT_INPUT_TEXT_THICKNESS,
        )


@dataclass
class Label:
    x: int
    y: int
    text: str
    color: tuple[int, int, int, int] = LABEL_TEXT_COLOR
    font_size: float = LABEL_FONT_SIZE

    def render(self, canvas: Img) -> None:
        canvas.put_text(self.text, self.x, self.y, self.font_size, self.color, thickness=LABEL_TEXT_THICKNESS)


@dataclass
class ErrorText(Label):
    color: tuple[int, int, int, int] = ERROR_TEXT_COLOR
