from client.network.remote_game_engine import RemoteGameEngine
from shared.config import (
    AIRBORNE_KEY,
    BLACK_USERNAME_KEY,
    CLOCK_KEY,
    LOCKED_KEY,
    PENDING_MOVES_KEY,
    RESTING_KEY,
    SETTLED_MOVES_KEY,
    WHITE,
    WHITE_USERNAME_KEY,
)


def _initial_payload():
    return {
        "board": [["." for _ in range(8)] for _ in range(8)],
        WHITE_USERNAME_KEY: "alice",
        BLACK_USERNAME_KEY: "bob",
        CLOCK_KEY: 0,
        LOCKED_KEY: [],
        PENDING_MOVES_KEY: [],
        RESTING_KEY: [],
        AIRBORNE_KEY: [],
        SETTLED_MOVES_KEY: [],
    }


def _make_engine() -> RemoteGameEngine:
    return RemoteGameEngine(WHITE, _initial_payload(), send_move=lambda *a: None, send_jump=lambda *a: None)


def test_mark_game_over_stores_new_ratings_from_payload():
    engine = _make_engine()

    engine.mark_game_over({"new_ratings": {"alice": 1272, "bob": 1170}})

    assert engine.is_over is True
    assert engine.new_ratings == {"alice": 1272, "bob": 1170}


def test_mark_game_over_defaults_to_empty_ratings_when_absent():
    engine = _make_engine()

    engine.mark_game_over({})

    assert engine.is_over is True
    assert engine.new_ratings == {}
