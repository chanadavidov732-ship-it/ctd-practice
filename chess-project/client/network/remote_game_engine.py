import threading

from shared.config import (
    AIRBORNE_KEY,
    BLACK_USERNAME_KEY,
    CAPTURED_KEY,
    CAPTURED_TOKEN_KEY,
    CLOCK_KEY,
    LOCKED_KEY,
    MOVE_COMPLETION_TIME_KEY,
    MOVE_DURATION_KEY,
    MOVE_FROM_KEY,
    MOVE_TOKEN_KEY,
    MOVE_TO_KEY,
    PENDING_MOVES_KEY,
    POS_KEY,
    RESTING_DURATION_KEY,
    RESTING_KEY,
    RESTING_UNTIL_KEY,
    SETTLED_MOVES_KEY,
    WHITE_USERNAME_KEY,
)
from shared.model.board import Board
from shared.model.game_state import GameState
from shared.rules import rule_engine
from shared.rules.move_validator import validate_jump, validate_move


class RemoteGameEngine:
    def __init__(self, my_color: str, initial_payload: dict, send_move, send_jump):
        self.my_color = my_color
        self.white_username = initial_payload[WHITE_USERNAME_KEY]
        self.black_username = initial_payload[BLACK_USERNAME_KEY]
        self._send_move = send_move
        self._send_jump = send_jump
        self._lock = threading.Lock()
        self._pending_settled: list[dict] = []

        self.board = Board([row[:] for row in initial_payload["board"]])
        self.game_state = GameState()
        self.is_over = False
        self.disconnect_countdown: dict | None = None

        self.apply_snapshot(initial_payload)

    def apply_snapshot(self, payload: dict) -> None:
        with self._lock:
            self.board.load_grid([row[:] for row in payload["board"]])

            gs = GameState()
            gs.clock = payload[CLOCK_KEY]
            gs.locked = {tuple(pos) for pos in payload[LOCKED_KEY]}
            gs.pending_moves = [
                {
                    MOVE_FROM_KEY: tuple(m[MOVE_FROM_KEY]),
                    MOVE_TO_KEY: tuple(m[MOVE_TO_KEY]),
                    MOVE_TOKEN_KEY: m[MOVE_TOKEN_KEY],
                    MOVE_COMPLETION_TIME_KEY: m[MOVE_COMPLETION_TIME_KEY],
                    MOVE_DURATION_KEY: m[MOVE_DURATION_KEY],
                }
                for m in payload[PENDING_MOVES_KEY]
            ]
            gs.resting = {tuple(r[POS_KEY]): r[RESTING_UNTIL_KEY] for r in payload[RESTING_KEY]}
            gs.resting_duration = {tuple(r[POS_KEY]): r[RESTING_DURATION_KEY] for r in payload[RESTING_KEY]}
            gs.airborne = {tuple(a[POS_KEY]): a[RESTING_UNTIL_KEY] for a in payload[AIRBORNE_KEY]}
            self.game_state = gs

            self._pending_settled.extend(
                {
                    MOVE_FROM_KEY: tuple(m[MOVE_FROM_KEY]),
                    MOVE_TO_KEY: tuple(m[MOVE_TO_KEY]),
                    MOVE_TOKEN_KEY: m[MOVE_TOKEN_KEY],
                    CAPTURED_TOKEN_KEY: m[CAPTURED_KEY],
                }
                for m in payload[SETTLED_MOVES_KEY]
            )

    def pop_newly_settled(self) -> list[dict]:
        with self._lock:
            batch, self._pending_settled = self._pending_settled, []
            return batch

    def advance_time(self, ms) -> list:
        with self._lock:
            self.game_state.clock += ms
        return []

    def mark_game_over(self, payload: dict) -> None:
        with self._lock:
            self.is_over = True

    def set_disconnect_countdown(self, payload: dict | None) -> None:
        with self._lock:
            self.disconnect_countdown = payload

    def is_locked(self, pos) -> bool:
        return pos in self.game_state.locked or pos in self.game_state.resting

    def request_move(self, from_pos, to_pos) -> None:
        if self.is_over:
            return
        if validate_move(self.board, self.my_color, from_pos, to_pos) == rule_engine.OK:
            self._send_move(from_pos, to_pos)

    def request_jump(self, pos) -> None:
        if self.is_over:
            return
        if validate_jump(self.board, self.my_color, pos) == rule_engine.OK:
            self._send_jump(pos)
