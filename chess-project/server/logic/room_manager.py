import secrets
import string
from dataclasses import dataclass

ROOM_ID_ALPHABET = string.ascii_uppercase + string.digits
ROOM_ID_LENGTH = 6


@dataclass
class RoomParticipant:
    client_id: str
    username: str
    rating: int
    websocket: object


class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: list[RoomParticipant] = []
        self.viewers: list[RoomParticipant] = []
        self.game_started = False

    def role_of(self, client_id: str) -> str | None:
        if any(p.client_id == client_id for p in self.players):
            return "player"
        if any(p.client_id == client_id for p in self.viewers):
            return "viewer"
        return None


class RoomManager:
    def __init__(self):
        self._rooms: dict[str, Room] = {}

    def create_room(self, participant: RoomParticipant) -> Room:
        room_id = self._generate_room_id()
        room = Room(room_id)
        room.players.append(participant)
        self._rooms[room_id] = room
        return room

    def join_room(self, room_id: str, participant: RoomParticipant) -> Room | None:
        room = self._rooms.get(room_id)
        if room is None:
            return None
        if len(room.players) < 2:
            room.players.append(participant)
        else:
            room.viewers.append(participant)
        return room

    def leave_room(self, room_id: str, client_id: str) -> Room | None:
        room = self._rooms.get(room_id)
        if room is None:
            return None
        room.players = [p for p in room.players if p.client_id != client_id]
        room.viewers = [p for p in room.viewers if p.client_id != client_id]
        if not room.players and not room.viewers:
            del self._rooms[room_id]
            return None
        return room

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def _generate_room_id(self) -> str:
        while True:
            candidate = "".join(secrets.choice(ROOM_ID_ALPHABET) for _ in range(ROOM_ID_LENGTH))
            if candidate not in self._rooms:
                return candidate


room_manager = RoomManager()
