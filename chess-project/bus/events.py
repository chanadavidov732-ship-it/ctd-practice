from dataclasses import dataclass


@dataclass
class ClientConnected:
    client_id: str


@dataclass
class RoomCreated:
    room_id: str
    client_id: str


@dataclass
class PlayerJoinedRoom:
    room_id: str
    client_id: str


@dataclass
class ViewerJoinedRoom:
    room_id: str
    client_id: str


@dataclass
class PlayerQueued:
    client_id: str
    username: str
    rating: int


@dataclass
class MatchFound:
    match_id: str
    client_id_a: str
    client_id_b: str


@dataclass
class MatchTimeout:
    client_id: str
