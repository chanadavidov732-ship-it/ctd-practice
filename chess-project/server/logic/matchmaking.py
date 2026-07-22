import asyncio
import secrets
import string
from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket

MATCH_ID_ALPHABET = string.ascii_uppercase + string.digits
MATCH_ID_LENGTH = 6
RATING_RANGE = 100


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
        return "".join(secrets.choice(MATCH_ID_ALPHABET) for _ in range(MATCH_ID_LENGTH))


matchmaking = Matchmaking()
