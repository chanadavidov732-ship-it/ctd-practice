import threading

from shared.model.board import Board
from shared.model.game_state import GameState
from shared.rules import rule_engine
from shared.rules.move_validator import validate_jump, validate_move


class RemoteGameEngine:
    """Renderer/Controller-compatible stand-in for the local GameEngine.

    The server is the single source of truth: request_move/request_jump only do
    a local legality pre-check (shared.rules) and hand the request off to the
    network layer, never mutating board/game_state directly. Board/game_state
    are replaced wholesale whenever a fresh snapshot arrives from the server
    (apply_snapshot); board.grid is mutated in place (not board re-assigned) so
    Renderer/Controller/BoardMapper — which each capture their own `board`
    reference at construction — keep seeing the same live object.
    """

    def __init__(self, my_color: str, initial_payload: dict, send_move, send_jump):
        self.my_color = my_color
        self.white_username = initial_payload["white_username"]
        self.black_username = initial_payload["black_username"]
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
            self.board.grid = [row[:] for row in payload["board"]]
            self.board.height = len(self.board.grid)
            self.board.width = len(self.board.grid[0]) if self.board.grid else 0

            gs = GameState()
            gs.clock = payload["clock"]
            gs.locked = {tuple(pos) for pos in payload["locked"]}
            gs.pending_moves = [
                {
                    "from": tuple(m["from"]),
                    "to": tuple(m["to"]),
                    "token": m["token"],
                    "completion_time": m["completion_time"],
                    "duration": m["duration"],
                }
                for m in payload["pending_moves"]
            ]
            gs.resting = {tuple(r["pos"]): r["until"] for r in payload["resting"]}
            gs.resting_duration = {tuple(r["pos"]): r["duration"] for r in payload["resting"]}
            gs.airborne = {tuple(a["pos"]): a["until"] for a in payload["airborne"]}
            self.game_state = gs

            self._pending_settled.extend(
                {
                    "from": tuple(m["from"]),
                    "to": tuple(m["to"]),
                    "token": m["token"],
                    "captured_token": m["captured"],
                }
                for m in payload["settled_moves"]
            )

    def pop_newly_settled(self) -> list[dict]:
        """Drains moves settled since the last call, for the caller's move-history panel."""
        with self._lock:
            batch, self._pending_settled = self._pending_settled, []
            return batch

    def advance_time(self, ms) -> list:
        """Cosmetic-only local clock advance for smooth interpolation between
        authoritative server snapshots; never mutates board or pending state."""
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
