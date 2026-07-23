import numpy as np

from client.ui.img import Img
from client.ui.widgets import Button, ErrorText, Label, TextInput


def _blank_canvas(width=200, height=100) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


def test_button_hit_test_inside_and_outside():
    button = Button(x=10, y=10, width=100, height=40, text="Login")
    assert button.hit_test(50, 20) is True
    assert button.hit_test(5, 5) is False
    assert button.hit_test(200, 200) is False


def test_button_hit_test_edges_are_inclusive():
    button = Button(x=0, y=0, width=100, height=40, text="Login")
    assert button.hit_test(0, 0) is True
    assert button.hit_test(100, 40) is True


def test_button_render_does_not_raise():
    Button(x=10, y=10, width=100, height=40, text="Login").render(_blank_canvas())


def test_text_input_appends_printable_characters():
    field = TextInput(x=0, y=0, width=100, height=30)
    for ch in "abc":
        assert field.handle_key(ord(ch)) is False
    assert field.value == "abc"


def test_text_input_backspace_removes_last_character():
    field = TextInput(x=0, y=0, width=100, height=30, value="abc")
    field.handle_key(8)
    assert field.value == "ab"


def test_text_input_backspace_on_empty_value_is_a_no_op():
    field = TextInput(x=0, y=0, width=100, height=30)
    field.handle_key(8)
    assert field.value == ""


def test_text_input_enter_reports_submit_without_changing_value():
    field = TextInput(x=0, y=0, width=100, height=30, value="abc")
    assert field.handle_key(13) is True
    assert field.value == "abc"


def test_text_input_ignores_out_of_range_key_codes():
    field = TextInput(x=0, y=0, width=100, height=30)
    field.handle_key(0)
    assert field.value == ""


def test_text_input_render_masks_password_without_changing_value():
    canvas = _blank_canvas()
    field = TextInput(x=10, y=10, width=150, height=30, masked=True, value="secret")
    field.render(canvas)
    assert field.value == "secret"


def test_label_and_error_text_render_do_not_raise():
    canvas = _blank_canvas()
    Label(x=5, y=5, text="hello").render(canvas)
    ErrorText(x=5, y=20, text="bad input").render(canvas)
