import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from server.engine_adapter.adapter import check_move_reason, create_engine
from server.logic import rating
from shared.model.piece import token_color, token_type
from shared.protocol import Envelope
from shared.rules import rule_engine

logger = logging.getLogger("server")

TICK_MS = 100
TICK_INTERVAL_SECONDS = TICK_MS / 1000


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
        self._finished = False

    def _color_of(self, client_id: str) -> str | None:
        for p in self.players:
            if p.client_id == client_id:
                return p.color
        return None

    async def start(self) -> None:
        await self._broadcast(Envelope(type="game_started", payload=self._state_payload()))
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def add_viewer(self, websocket) -> None:
        self.viewers.append(websocket)
        await websocket.send_json(Envelope(type="game_update", payload=self._state_payload()).to_dict())

    async def handle_move(self, client_id: str, from_pos: tuple, to_pos: tuple) -> None:
        if self._finished:
            return
        color = self._color_of(client_id)
        if color is None:
            return

        if not (self.board.is_inside(from_pos) and self.board.is_inside(to_pos)):
            await self._send_to(client_id, "move_rejected", {"reason": "OUT_OF_BOUNDS"})
            return

        token = self.board.get_piece(from_pos)
        if token == "." or token_color(token) != color:
            await self._send_to(client_id, "move_rejected", {"reason": "NOT_YOUR_PIECE"})
            return

        reason = check_move_reason(self.board, from_pos, to_pos)
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

        if not self.board.is_inside(pos):
            await self._send_to(client_id, "jump_rejected", {"reason": "OUT_OF_BOUNDS"})
            return

        token = self.board.get_piece(pos)
        if token == "." or token_color(token) != color:
            await self._send_to(client_id, "jump_rejected", {"reason": "NOT_YOUR_PIECE"})
            return

        self.engine.request_jump(pos)

    async def _tick_loop(self) -> None:
        try:
            while not self._finished:
                await asyncio.sleep(TICK_INTERVAL_SECONDS)
                settled = self.engine.advance_time(TICK_MS)
                if settled:
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

    def _state_payload(self, settled=None) -> dict:
        return {
            "session_id": self.session_id,
            "board": [row[:] for row in self.board.grid],
            "settled_moves": [
                {"from": list(m["from"]), "to": list(m["to"]), "captured": m["captured_token"]}
                for m in (settled or [])
            ],
        }

    async def _finish_game(self, winner_color: str) -> None:
        self._finished = True
        winner = next(p for p in self.players if p.color == winner_color)
        loser = next(p for p in self.players if p.color != winner_color)

        new_ratings = {}
        if None not in (winner.username, loser.username, winner.rating, loser.rating):
            new_winner_rating, new_loser_rating = await rating.apply_match_result(
                winner.username, winner.rating, loser.username, loser.rating, score_a=1,
            )
            new_ratings = {winner.username: new_winner_rating, loser.username: new_loser_rating}

        logger.info("game over: session_id=%s winner=%s (%s)", self.session_id, winner.username, winner_color)
        await self._broadcast(Envelope(type="game_over", payload={
            "session_id": self.session_id,
            "winner_color": winner_color,
            "winner_username": winner.username,
            "new_ratings": new_ratings,
        }))
        game_session_manager.remove(self.session_id)

    async def _send_to(self, client_id: str, msg_type: str, payload: dict) -> None:
        for p in self.players:
            if p.client_id == client_id:
                await p.websocket.send_json(Envelope(type=msg_type, payload=payload).to_dict())
                return

    async def _broadcast(self, envelope: Envelope) -> None:
        for p in self.players:
            await p.websocket.send_json(envelope.to_dict())
        for viewer_ws in self.viewers:
            await viewer_ws.send_json(envelope.to_dict())


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
