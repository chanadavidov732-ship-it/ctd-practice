import asyncio
import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket


@dataclass
class QueuedPlayer:
    client_id: str
    username: str
    rating: int
    websocket: WebSocket
    timeout_task: Optional[asyncio.Task] = None


class Matchmaking:
    def __init__(self):
        self._queue: list[QueuedPlayer] = []

    def enqueue(self, player: QueuedPlayer) -> None:
        self._queue.append(player)

    def get(self, client_id: str) -> QueuedPlayer | None:
        for player in self._queue:
            if player.client_id == client_id:
                return player
        return None

    def find_opponent(self, rating: int, exclude_client_id: str) -> QueuedPlayer | None:
        from server.config import RATING_RANGE  # deferred: server.config imports ws_routes,
        # which transitively reaches this module at import time -- circular otherwise.

        for player in self._queue:
            if player.client_id == exclude_client_id:
                continue
            if abs(player.rating - rating) <= RATING_RANGE:
                return player
        return None

    def remove(self, client_id: str) -> QueuedPlayer | None:
        for i, player in enumerate(self._queue):
            if player.client_id == client_id:
                return self._queue.pop(i)
        return None

    @staticmethod
    def generate_match_id() -> str:
        from server.config import MATCH_ID_ALPHABET, MATCH_ID_LENGTH  # deferred: see the note
        # in find_opponent above -- same circular-import reason.

        return "".join(secrets.choice(MATCH_ID_ALPHABET) for _ in range(MATCH_ID_LENGTH))


matchmaking = Matchmaking()
