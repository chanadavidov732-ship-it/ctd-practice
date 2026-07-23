import pytest

from client.ui.screens.base_screen import Screen


class _DummyScreen(Screen):
    def render(self, canvas):
        pass


def test_screen_starts_with_no_pending_transition():
    screen = _DummyScreen(bridge=None)
    assert screen.next_screen is None


def test_screen_default_hooks_are_no_ops():
    screen = _DummyScreen(bridge=None)
    screen.on_enter({})
    screen.update()
    screen.handle_click(1, 2)
    screen.handle_key(13)


def test_screen_can_signal_a_transition():
    screen = _DummyScreen(bridge=None)
    screen.next_screen = (_DummyScreen, {"username": "alice"})
    screen_class, payload = screen.next_screen
    assert screen_class is _DummyScreen
    assert payload == {"username": "alice"}


def test_screen_render_is_abstract():
    class _Bare(Screen):
        pass

    with pytest.raises(NotImplementedError):
        _Bare(bridge=None).render(canvas=None)
