import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from server.engine_adapter.adapter import create_engine
from server.logic import rating
from shared.config import (
    AIR_CAPTURE_KEY,
    AIRBORNE_KEY,
    BLACK,
    BLACK_USERNAME_KEY,
    CAPTURED_KEY,
    CAPTURED_TOKEN_KEY,
    CLOCK_KEY,
    EMPTY_CELL,
    KING,
    LOCKED_KEY,
    MOVE_COMPLETION_TIME_KEY,
    MOVE_DURATION_KEY,
    MOVE_FROM_KEY,
    MOVE_TOKEN_KEY,
    MOVE_TO_KEY,
    MSG_DISCONNECT_COUNTDOWN,
    MSG_GAME_OVER,
    MSG_GAME_STARTED,
    MSG_GAME_UPDATE,
    MSG_JUMP_REJECTED,
    MSG_MOVE_REJECTED,
    PENDING_MOVES_KEY,
    POS_KEY,
    RESTING_DURATION_KEY,
    RESTING_KEY,
    RESTING_UNTIL_KEY,
    SETTLED_MOVES_KEY,
    WHITE,
    WHITE_USERNAME_KEY,
    YOUR_COLOR_KEY,
)
from shared.model.piece import token_color, token_type
from shared.protocol import Envelope
from shared.rules import rule_engine
from shared.rules.move_validator import validate_jump, validate_move

logger = logging.getLogger("server")


@dataclass
class PlayerSlot:
    client_id: str
    username: str
    rating: int
    websocket: object
    color: str


def _slot(participant, color: str) -> PlayerSlot:
    return PlayerSlot(
        client_id=participant.client_id,
        username=participant.username,
        rating=participant.rating,
        websocket=participant.websocket,
        color=color,
    )


class GameSession:
    def __init__(self, session_id: str, players: list[PlayerSlot], viewers: Optional[list] = None, room_id: Optional[str] = None):
        self.session_id = session_id
        self.room_id = room_id
        self.players = players
        self.viewers = viewers or []
        self.board, self.game_state, self.arbiter, self.engine = create_engine()
        self._tick_task: Optional[asyncio.Task] = None
        self._disconnect_task: Optional[asyncio.Task] = None
        self._finished = False
        self.captures = {WHITE: 0, BLACK: 0}

    def _color_of(self, client_id: str) -> str | None:
        for p in self.players:
            if p.client_id == client_id:
                return p.color
        return None

    async def start(self) -> None:
        base_payload = self._state_payload()
        for p in self.players:
            await self._safe_send(p.websocket, Envelope(type=MSG_GAME_STARTED, payload={**base_payload, YOUR_COLOR_KEY: p.color}))
        for viewer_ws in self.viewers:
            await self._safe_send(viewer_ws, Envelope(type=MSG_GAME_STARTED, payload={**base_payload, YOUR_COLOR_KEY: None}))
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def add_viewer(self, websocket) -> None:
        self.viewers.append(websocket)
        payload = {**self._state_payload(), YOUR_COLOR_KEY: None}
        await self._safe_send(websocket, Envelope(type=MSG_GAME_UPDATE, payload=payload))

    async def handle_move(self, client_id: str, from_pos: tuple, to_pos: tuple) -> None:
        if self._finished:
            return
        color = self._color_of(client_id)
        if color is None:
            return

        reason = validate_move(self.board, color, from_pos, to_pos)
        if reason != rule_engine.OK:
            await self._send_to(client_id, MSG_MOVE_REJECTED, {"reason": reason})
            return

        self.engine.request_move(from_pos, to_pos)

    async def handle_jump(self, client_id: str, pos: tuple) -> None:
        if self._finished:
            return
        color = self._color_of(client_id)
        if color is None:
            return

        reason = validate_jump(self.board, color, pos)
        if reason != rule_engine.OK:
            await self._send_to(client_id, MSG_JUMP_REJECTED, {"reason": reason})
            return

        self.engine.request_jump(pos)

    async def handle_disconnect(self, client_id: str) -> None:
        if self._finished or self._disconnect_task is not None:
            return
        player = next((p for p in self.players if p.client_id == client_id), None)
        if player is None:
            return
        self._disconnect_task = asyncio.create_task(self._auto_resign_countdown(player))

    async def _auto_resign_countdown(self, disconnected_player: PlayerSlot) -> None:
        try:
            resigned = await self._broadcast_disconnect_countdown(disconnected_player)
            if not resigned and not self._finished:
                winner_color = BLACK if disconnected_player.color == WHITE else WHITE
                await self._finish_game(winner_color, reason="disconnect")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("session %s: auto-resign countdown failed", self.session_id)

    async def _broadcast_disconnect_countdown(self, disconnected_player: PlayerSlot) -> bool:
        from server.config import DISCONNECT_RESIGN_SECONDS

        for remaining in range(DISCONNECT_RESIGN_SECONDS, 0, -1):
            if self._finished:
                return True
            await self._broadcast(Envelope(type=MSG_DISCONNECT_COUNTDOWN, payload={
                "session_id": self.session_id,
                "disconnected_username": disconnected_player.username,
                "seconds_remaining": remaining,
            }))
            await asyncio.sleep(1)
        return self._finished

    async def _tick_loop(self) -> None:
        from server.config import TICK_INTERVAL_SECONDS, TICK_MS

        try:
            while not self._finished:
                await asyncio.sleep(TICK_INTERVAL_SECONDS)
                before = self._snapshot_lock_state()
                settled = self.engine.advance_time(TICK_MS)
                self._record_captures(settled)
                freed = self._locks_freed_since(before)

                anything_active = (
                    settled
                    or self.game_state.pending_moves
                    or self.game_state.resting
                    or self.game_state.airborne
                    or freed
                )
                if anything_active:
                    await self._broadcast(Envelope(type=MSG_GAME_UPDATE, payload=self._state_payload(settled)))

                winner_color = self._winner_from_settled(settled)
                if winner_color is not None:
                    await self._finish_game(winner_color)
                if self.engine.is_over:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("session %s: tick loop failed", self.session_id)

    def _record_captures(self, settled) -> None:
        for move in settled:
            if move[CAPTURED_TOKEN_KEY] == EMPTY_CELL:
                continue
            mover_color = token_color(move[MOVE_TOKEN_KEY])
            capturing_color = (BLACK if mover_color == WHITE else WHITE) if move.get(AIR_CAPTURE_KEY) else mover_color
            self.captures[capturing_color] += 1

    def _snapshot_lock_state(self) -> tuple[set, set, set]:
        return set(self.game_state.locked), set(self.game_state.resting), set(self.game_state.airborne)

    def _locks_freed_since(self, before: tuple[set, set, set]):
        locked_before, resting_before, airborne_before = before
        return (
            (locked_before - self.game_state.locked)
            or (resting_before - set(self.game_state.resting))
            or (airborne_before - set(self.game_state.airborne))
        )

    def _winner_from_settled(self, settled) -> str | None:
        if not self.engine.is_over:
            return None
        loser_color = next(
            (token_color(m[CAPTURED_TOKEN_KEY]) for m in settled if token_type(m[CAPTURED_TOKEN_KEY]) == KING),
            None,
        )
        if loser_color is None:
            return None
        return BLACK if loser_color == WHITE else WHITE

    def _state_payload(self, settled=None) -> dict:
        return {
            "session_id": self.session_id,
            "board": [row[:] for row in self.board.grid],
            CLOCK_KEY: self.game_state.clock,
            LOCKED_KEY: [list(pos) for pos in self.game_state.locked],
            PENDING_MOVES_KEY: [
                {
                    MOVE_FROM_KEY: list(m[MOVE_FROM_KEY]),
                    MOVE_TO_KEY: list(m[MOVE_TO_KEY]),
                    MOVE_TOKEN_KEY: m[MOVE_TOKEN_KEY],
                    MOVE_COMPLETION_TIME_KEY: m[MOVE_COMPLETION_TIME_KEY],
                    MOVE_DURATION_KEY: m[MOVE_DURATION_KEY],
                }
                for m in self.game_state.pending_moves
            ],
            RESTING_KEY: [
                {POS_KEY: list(pos), RESTING_UNTIL_KEY: until, RESTING_DURATION_KEY: self.game_state.resting_duration.get(pos)}
                for pos, until in self.game_state.resting.items()
            ],
            AIRBORNE_KEY: [{POS_KEY: list(pos), RESTING_UNTIL_KEY: until} for pos, until in self.game_state.airborne.items()],
            SETTLED_MOVES_KEY: [
                {
                    MOVE_FROM_KEY: list(m[MOVE_FROM_KEY]),
                    MOVE_TO_KEY: list(m[MOVE_TO_KEY]),
                    MOVE_TOKEN_KEY: m[MOVE_TOKEN_KEY],
                    CAPTURED_KEY: m[CAPTURED_TOKEN_KEY],
                }
                for m in (settled or [])
            ],
            WHITE_USERNAME_KEY: next(p.username for p in self.players if p.color == WHITE),
            BLACK_USERNAME_KEY: next(p.username for p in self.players if p.color == BLACK),
        }

    async def _finish_game(self, winner_color: str, reason: str = "king_captured") -> None:
        if self._finished:
            return
        self._finished = True
        if (
            self._disconnect_task is not None
            and self._disconnect_task is not asyncio.current_task()
            and not self._disconnect_task.done()
        ):
            self._disconnect_task.cancel()

        winner = next(p for p in self.players if p.color == winner_color)
        loser = next(p for p in self.players if p.color != winner_color)

        new_ratings = {}
        if None not in (winner.username, loser.username, winner.rating, loser.rating):
            new_winner_rating, new_loser_rating = await rating.apply_match_result(
                winner.username, winner.rating, loser.username, loser.rating,
                captures_winner=self.captures[winner_color], captures_loser=self.captures[loser.color],
            )
            new_ratings = {winner.username: new_winner_rating, loser.username: new_loser_rating}

        logger.info("game over: session_id=%s winner=%s (%s) reason=%s", self.session_id, winner.username, winner_color, reason)
        await self._broadcast(Envelope(type=MSG_GAME_OVER, payload={
            "session_id": self.session_id,
            "winner_color": winner_color,
            "winner_username": winner.username,
            "reason": reason,
            "new_ratings": new_ratings,
        }))
        game_session_manager.remove(self.session_id)

    async def _send_to(self, client_id: str, msg_type: str, payload: dict) -> None:
        for p in self.players:
            if p.client_id == client_id:
                await self._safe_send(p.websocket, Envelope(type=msg_type, payload=payload))
                return

    async def _broadcast(self, envelope: Envelope) -> None:
        for p in self.players:
            await self._safe_send(p.websocket, envelope)
        for viewer_ws in self.viewers:
            await self._safe_send(viewer_ws, envelope)

    async def _safe_send(self, websocket, envelope: Envelope) -> None:
        try:
            await websocket.send_json(envelope.to_dict())
        except Exception:
            logger.warning("session %s: failed to send %s to a disconnected socket", self.session_id, envelope.type)


class GameSessionManager:
    def __init__(self):
        self._by_client_id: dict[str, GameSession] = {}
        self._by_room_id: dict[str, GameSession] = {}

    def get_for_client(self, client_id: str) -> GameSession | None:
        return self._by_client_id.get(client_id)

    def get_for_room(self, room_id: str) -> GameSession | None:
        return self._by_room_id.get(room_id)

    async def start_for_match(self, match_id: str, player_a, player_b) -> GameSession:
        players = [_slot(player_a, WHITE), _slot(player_b, BLACK)]
        session = GameSession(session_id=match_id, players=players)
        self._register(session)
        await session.start()
        return session

    async def start_for_room(self, room_id: str, player_a, player_b, viewer_websockets: list) -> GameSession:
        players = [_slot(player_a, WHITE), _slot(player_b, BLACK)]
        session = GameSession(session_id=room_id, players=players, viewers=viewer_websockets, room_id=room_id)
        self._register(session)
        self._by_room_id[room_id] = session
        await session.start()
        return session

    def _register(self, session: GameSession) -> None:
        for p in session.players:
            self._by_client_id[p.client_id] = session

    def remove(self, session_id: str) -> None:
        for client_id, session in list(self._by_client_id.items()):
            if session.session_id == session_id:
                del self._by_client_id[client_id]
        self._by_room_id.pop(session_id, None)


game_session_manager = GameSessionManager()
