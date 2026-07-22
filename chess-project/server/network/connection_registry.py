from fastapi import WebSocket


class ConnectionRegistry:
    def __init__(self):
        self._rooms: dict[str, dict[WebSocket, str]] = {}

    def add(self, room_id: str, websocket: WebSocket, client_id: str) -> None:
        self._rooms.setdefault(room_id, {})[websocket] = client_id

    def remove(self, room_id: str, websocket: WebSocket) -> None:
        sockets = self._rooms.get(room_id)
        if sockets and websocket in sockets:
            del sockets[websocket]
            if not sockets:
                del self._rooms[room_id]

    def others(self, room_id: str, exclude_client_id: str) -> list[WebSocket]:
        return [ws for ws, cid in self._rooms.get(room_id, {}).items() if cid != exclude_client_id]


connection_registry = ConnectionRegistry()
