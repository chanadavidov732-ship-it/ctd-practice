import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from server.engine_adapter.adapter import create_engine
from server.logic import rating
from shared.model.piece import token_color, token_type
from shared.protocol import Envelope
from shared.rules import rule_engine
from shared.rules.move_validator import validate_jump, validate_move

logger = logging.getLogger("server")

TICK_MS = 100
TICK_INTERVAL_SECONDS = TICK_MS / 1000
DISCONNECT_RESIGN_SECONDS = 20


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

    def _color_of(self, client_id: str) -> str | None:
        for p in self.players:
            if p.client_id == client_id:
                return p.color
        return None

    async def start(self) -> None:
        base_payload = self._state_payload()
        for p in self.players:
            await self._safe_send(p.websocket, Envelope(type="game_started", payload={**base_payload, "your_color": p.color}))
        for viewer_ws in self.viewers:
            await self._safe_send(viewer_ws, Envelope(type="game_started", payload={**base_payload, "your_color": None}))
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def add_viewer(self, websocket) -> None:
        self.viewers.append(websocket)
        payload = {**self._state_payload(), "your_color": None}
        await self._safe_send(websocket, Envelope(type="game_update", payload=payload))

    async def handle_move(self, client_id: str, from_pos: tuple, to_pos: tuple) -> None:
        if self._finished:
            return
        color = self._color_of(client_id)
        if color is None:
            return

        reason = validate_move(self.board, color, from_pos, to_pos)
        if reason != rule_engine.OK:
            await self._send_to(client_id, "move_rejected", {"reason": reason})
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
            await self._send_to(client_id, "jump_rejected", {"reason": reason})
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
            for remaining in range(DISCONNECT_RESIGN_SECONDS, 0, -1):
                if self._finished:
                    return
                await self._broadcast(Envelope(type="disconnect_countdown", payload={
                    "session_id": self.session_id,
                    "disconnected_username": disconnected_player.username,
                    "seconds_remaining": remaining,
                }))
                await asyncio.sleep(1)

            if self._finished:
                return
            winner_color = "b" if disconnected_player.color == "w" else "w"
            await self._finish_game(winner_color, reason="disconnect")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("session %s: auto-resign countdown failed", self.session_id)

    async def _tick_loop(self) -> None:
        try:
            while not self._finished:
                await asyncio.sleep(TICK_INTERVAL_SECONDS)
                settled = self.engine.advance_time(TICK_MS)
                # Broadcast on every tick that has anything actually happening (a move/jump
                # in flight, a piece resting, or something just settled) so clients can
                # interpolate smooth motion; skip broadcasting while the board is fully idle.
                anything_active = (
                    settled
                    or self.game_state.pending_moves
                    or self.game_state.resting
                    or self.game_state.airborne
                )
                if anything_active:
                    await self._broadcast(Envelope(type="game_update", payload=self._state_payload(settled)))

                if self.engine.is_over:
                    loser_color = next(
                        (token_color(m["captured_token"]) for m in settled if token_type(m["captured_token"]) == "K"),
                        None,
                    )
                    if loser_color is not None:
                        winner_color = "b" if loser_color == "w" else "w"
                        await self._finish_game(winner_color)
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("session %s: tick loop failed", self.session_id)

    def _state_payload(self, settled=None) -> dict:
        return {
            "session_id": self.session_id,
            "board": [row[:] for row in self.board.grid],
            "clock": self.game_state.clock,
            "locked": [list(pos) for pos in self.game_state.locked],
            "pending_moves": [
                {
                    "from": list(m["from"]),
                    "to": list(m["to"]),
                    "token": m["token"],
                    "completion_time": m["completion_time"],
                    "duration": m["duration"],
                }
                for m in self.game_state.pending_moves
            ],
            "resting": [
                {"pos": list(pos), "until": until, "duration": self.game_state.resting_duration.get(pos)}
                for pos, until in self.game_state.resting.items()
            ],
            "airborne": [{"pos": list(pos), "until": until} for pos, until in self.game_state.airborne.items()],
            "settled_moves": [
                {
                    "from": list(m["from"]),
                    "to": list(m["to"]),
                    "token": m["token"],
                    "captured": m["captured_token"],
                }
                for m in (settled or [])
            ],
            "white_username": next(p.username for p in self.players if p.color == "w"),
            "black_username": next(p.username for p in self.players if p.color == "b"),
        }

    async def _finish_game(self, winner_color: str, reason: str = "king_captured") -> None:
        if self._finished:
            return
        self._finished = True
        # Don't cancel ourselves: _finish_game is also called from within
        # _auto_resign_countdown's own task once its 20s countdown completes.
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
                winner.username, winner.rating, loser.username, loser.rating, score_a=1,
            )
            new_ratings = {winner.username: new_winner_rating, loser.username: new_loser_rating}

        logger.info("game over: session_id=%s winner=%s (%s) reason=%s", self.session_id, winner.username, winner_color, reason)
        await self._broadcast(Envelope(type="game_over", payload={
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
        players = [_slot(player_a, "w"), _slot(player_b, "b")]
        session = GameSession(session_id=match_id, players=players)
        self._register(session)
        await session.start()
        return session

    async def start_for_room(self, room_id: str, player_a, player_b, viewer_websockets: list) -> GameSession:
        players = [_slot(player_a, "w"), _slot(player_b, "b")]
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
