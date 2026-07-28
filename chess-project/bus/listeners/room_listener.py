import logging

from bus.events import PlayerJoinedRoom, RoomCreated, ViewerJoinedRoom
from server.logic.game_session import game_session_manager
from server.logic.room_manager import room_manager
from server.network.room_broadcaster import broadcast_room_state

logger = logging.getLogger("bus")


async def on_room_created(event: RoomCreated) -> None:
    logger.info("event received: RoomCreated(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)


async def on_player_joined_room(event: PlayerJoinedRoom) -> None:
    logger.info("event received: PlayerJoinedRoom(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)

    room = room_manager.get_room(event.room_id)
    if room is not None and room.is_full and not room.game_started:
        player_a, player_b = room.start_game()
        await game_session_manager.start_for_room(room.room_id, player_a, player_b, room.viewer_websockets())


async def on_viewer_joined_room(event: ViewerJoinedRoom) -> None:
    logger.info("event received: ViewerJoinedRoom(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)

    session = game_session_manager.get_for_room(event.room_id)
    if session is not None:
        room = room_manager.get_room(event.room_id)
        viewer = room.find_viewer(event.client_id) if room else None
        if viewer is not None:
            await session.add_viewer(viewer.websocket)
