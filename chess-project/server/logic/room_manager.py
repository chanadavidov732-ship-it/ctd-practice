from dataclasses import dataclass

from shared.config import MAX_ROOM_PLAYERS


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

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def viewer_count(self) -> int:
        return len(self.viewers)

    @property
    def is_full(self) -> bool:
        return self.player_count >= MAX_ROOM_PLAYERS

    def role_of(self, client_id: str) -> str | None:
        if any(p.client_id == client_id for p in self.players):
            return "player"
        if any(p.client_id == client_id for p in self.viewers):
            return "viewer"
        return None

    def viewer_websockets(self) -> list:
        return [v.websocket for v in self.viewers]

    def find_viewer(self, client_id: str) -> RoomParticipant | None:
        return next((v for v in self.viewers if v.client_id == client_id), None)

    def start_game(self) -> tuple[RoomParticipant, RoomParticipant]:
        self.game_started = True
        return self.players[0], self.players[1]


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
        if not room.is_full:
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
        from server.config import ID_ALPHABET, ID_LENGTH
        from server.logic.id_gen import generate_id

        return generate_id(ID_ALPHABET, ID_LENGTH, is_taken=lambda candidate: candidate in self._rooms)


room_manager = RoomManager()
