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
