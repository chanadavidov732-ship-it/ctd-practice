import asyncio
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
        from server.config import RATING_RANGE

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

    def remove_and_cancel_timeout(self, client_id: str) -> QueuedPlayer | None:
        player = self.remove(client_id)
        if player is not None and player.timeout_task is not None:
            player.timeout_task.cancel()
        return player

    @staticmethod
    def generate_match_id() -> str:
        from server.config import ID_ALPHABET, ID_LENGTH
        from server.logic.id_gen import generate_id

        return generate_id(ID_ALPHABET, ID_LENGTH)


matchmaking = Matchmaking()
