import asyncio

import server.logic.rating as rating_module
from server.logic.game_session import GameSession, PlayerSlot
from server.logic.rating import apply_match_result, capture_bonus
from shared.config import AIR_CAPTURE_KEY, BLACK, CAPTURED_TOKEN_KEY, EMPTY_CELL, MOVE_TOKEN_KEY, WHITE


def make_session():
    players = [
        PlayerSlot(client_id="a", username="alice", rating=1200, websocket=None, color=WHITE),
        PlayerSlot(client_id="b", username="bob", rating=1200, websocket=None, color=BLACK),
    ]
    return GameSession(session_id="s1", players=players)


def test_capture_bonus_scales_with_capture_count():
    assert capture_bonus(0) == 0
    assert capture_bonus(3) == 6


def test_apply_match_result_awards_fixed_win_and_loss_points_plus_capture_bonus(monkeypatch):
    saved = {}
    monkeypatch.setattr(rating_module, "update_rating", lambda username, value: saved.__setitem__(username, value))

    updated_winner, updated_loser = asyncio.run(
        apply_match_result("alice", 1200, "bob", 1200, captures_winner=3, captures_loser=1)
    )

    assert updated_winner == 1200 + 100 + 6
    assert updated_loser == 1200 - 30 + 2
    assert saved == {"alice": updated_winner, "bob": updated_loser}


def test_record_captures_credits_the_mover_for_a_regular_capture():
    session = make_session()
    session._record_captures([{MOVE_TOKEN_KEY: "wQ", CAPTURED_TOKEN_KEY: "bR"}])
    assert session.captures == {WHITE: 1, BLACK: 0}


def test_record_captures_credits_the_defender_for_an_air_capture():
    session = make_session()
    session._record_captures([{MOVE_TOKEN_KEY: "wQ", CAPTURED_TOKEN_KEY: "wQ", AIR_CAPTURE_KEY: True}])
    assert session.captures == {WHITE: 0, BLACK: 1}


def test_record_captures_ignores_non_captures():
    session = make_session()
    session._record_captures([{MOVE_TOKEN_KEY: "wQ", CAPTURED_TOKEN_KEY: EMPTY_CELL}])
    assert session.captures == {WHITE: 0, BLACK: 0}
