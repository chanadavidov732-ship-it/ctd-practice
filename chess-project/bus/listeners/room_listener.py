import logging

from bus.events import PlayerJoinedRoom, RoomCreated, ViewerJoinedRoom
from server.network.room_broadcaster import broadcast_room_state

logger = logging.getLogger("bus")


async def on_room_created(event: RoomCreated) -> None:
    logger.info("event received: RoomCreated(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)


async def on_player_joined_room(event: PlayerJoinedRoom) -> None:
    logger.info("event received: PlayerJoinedRoom(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)


async def on_viewer_joined_room(event: ViewerJoinedRoom) -> None:
    logger.info("event received: ViewerJoinedRoom(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)
