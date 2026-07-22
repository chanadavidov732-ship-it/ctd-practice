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
    if room is not None and len(room.players) == 2 and not room.game_started:
        room.game_started = True
        viewer_websockets = [v.websocket for v in room.viewers]
        await game_session_manager.start_for_room(room.room_id, room.players[0], room.players[1], viewer_websockets)


async def on_viewer_joined_room(event: ViewerJoinedRoom) -> None:
    logger.info("event received: ViewerJoinedRoom(room_id=%s, client_id=%s)", event.room_id, event.client_id)
    await broadcast_room_state(event.room_id, exclude_client_id=event.client_id)

    session = game_session_manager.get_for_room(event.room_id)
    if session is not None:
        room = room_manager.get_room(event.room_id)
        viewer = next((v for v in room.viewers if v.client_id == event.client_id), None) if room else None
        if viewer is not None:
            await session.add_viewer(viewer.websocket)
