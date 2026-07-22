from server.logic.room_manager import room_manager
from server.network.connection_registry import connection_registry
from shared.protocol import Envelope


async def broadcast_room_state(room_id: str, exclude_client_id: str) -> None:
    room = room_manager.get_room(room_id)
    if room is None:
        return

    envelope = Envelope(
        type="room_state",
        payload={
            "room_id": room_id,
            "player_count": len(room.players),
            "viewer_count": len(room.viewers),
        },
    )
    for websocket in connection_registry.others(room_id, exclude_client_id):
        await websocket.send_json(envelope.to_dict())
