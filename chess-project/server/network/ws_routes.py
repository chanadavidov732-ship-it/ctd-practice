import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bus.event_bus import event_bus
from bus.events import ClientConnected, PlayerJoinedRoom, PlayerQueued, RoomCreated, ViewerJoinedRoom
from server.auth.auth import login as auth_login
from server.auth.auth import register as auth_register
from server.logic.game_session import game_session_manager
from server.logic.matchmaking import QueuedPlayer, matchmaking
from server.logic.room_manager import RoomParticipant, room_manager
from server.network.connection_registry import connection_registry
from server.network.room_broadcaster import broadcast_room_state
from shared.config import MENU_CHOICE_PLAY, MENU_CHOICE_ROOM, MSG_PLAY_QUEUED, MSG_ROOM_STATE
from shared.protocol import Envelope

logger = logging.getLogger("server")

router = APIRouter()


class ConnectionContext:
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.room_id: str | None = None
        self.username: str | None = None
        self.rating: int | None = None


async def handle_echo(payload: dict, ctx: ConnectionContext) -> dict:
    return payload


async def handle_login(payload: dict, ctx: ConnectionContext) -> dict:
    result = await auth_login(payload.get("username", ""), payload.get("password", ""))
    if result.get("success"):
        ctx.username = payload.get("username", "")
        ctx.rating = result.get("rating")
    return result


async def handle_register(payload: dict, ctx: ConnectionContext) -> dict:
    return await auth_register(payload.get("username", ""), payload.get("password", ""))


async def handle_menu_select(payload: dict, ctx: ConnectionContext) -> dict:
    choice = payload.get("choice")
    if choice not in (MENU_CHOICE_PLAY, MENU_CHOICE_ROOM):
        return {"received": False, "message": f"unknown menu choice: {choice}"}
    return {"received": True, "choice": choice, "message": f"'{choice}' selection received"}


def _participant(ctx: "ConnectionContext") -> RoomParticipant:
    return RoomParticipant(client_id=ctx.client_id, username=ctx.username, rating=ctx.rating, websocket=ctx.websocket)


async def _send_ack_then_publish(ctx: "ConnectionContext", ack: Envelope, event) -> None:
    await ctx.websocket.send_json(ack.to_dict())
    await event_bus.publish(event)


async def handle_create_room(payload: dict, ctx: ConnectionContext) -> dict:
    room = room_manager.create_room(_participant(ctx))
    ctx.room_id = room.room_id
    connection_registry.add(room.room_id, ctx.websocket, ctx.client_id)
    await event_bus.publish(RoomCreated(room_id=room.room_id, client_id=ctx.client_id))
    return {
        "room_id": room.room_id,
        "role": "player",
        "player_count": room.player_count,
        "viewer_count": room.viewer_count,
    }


async def handle_join_room(payload: dict, ctx: ConnectionContext) -> dict | None:
    room_id = payload.get("room_id", "")
    room = room_manager.join_room(room_id, _participant(ctx))
    if room is None:
        return {"success": False, "message": "room not found"}

    ctx.room_id = room_id
    connection_registry.add(room_id, ctx.websocket, ctx.client_id)
    role = room.role_of(ctx.client_id)

    ack = Envelope(
        type=MSG_ROOM_STATE,
        payload={
            "success": True,
            "room_id": room_id,
            "role": role,
            "player_count": room.player_count,
            "viewer_count": room.viewer_count,
        },
    )
    event = PlayerJoinedRoom(room_id=room_id, client_id=ctx.client_id) if role == "player" \
        else ViewerJoinedRoom(room_id=room_id, client_id=ctx.client_id)
    await _send_ack_then_publish(ctx, ack, event)
    return None


async def handle_cancel_room(payload: dict, ctx: ConnectionContext) -> dict:
    room_id = payload.get("room_id", "")
    if ctx.room_id != room_id:
        return {"success": False, "message": "not in that room"}

    await _leave_room(ctx)
    return {"success": True, "message": "left room"}


async def _leave_room(ctx: ConnectionContext) -> None:
    room_id = ctx.room_id
    if room_id is None:
        return
    room_manager.leave_room(room_id, ctx.client_id)
    connection_registry.remove(room_id, ctx.websocket)
    ctx.room_id = None
    await broadcast_room_state(room_id, exclude_client_id=ctx.client_id)


async def handle_play(payload: dict, ctx: ConnectionContext) -> dict | None:
    if ctx.username is None:
        return {"success": False, "message": "must be logged in to play"}

    player = QueuedPlayer(
        client_id=ctx.client_id,
        username=ctx.username,
        rating=ctx.rating,
        websocket=ctx.websocket,
    )
    matchmaking.enqueue(player)

    ack = Envelope(
        type=MSG_PLAY_QUEUED,
        payload={"success": True, "message": "queued for a match", "rating": ctx.rating},
    )
    event = PlayerQueued(client_id=ctx.client_id, username=ctx.username, rating=ctx.rating)
    await _send_ack_then_publish(ctx, ack, event)
    return None


async def handle_cancel_play(payload: dict, ctx: ConnectionContext) -> dict:
    player = matchmaking.remove_and_cancel_timeout(ctx.client_id)
    if player is None:
        return {"success": False, "message": "not in queue"}
    return {"success": True, "message": "left queue"}


async def _leave_queue(ctx: ConnectionContext) -> None:
    matchmaking.remove_and_cancel_timeout(ctx.client_id)


async def _handle_game_disconnect(ctx: ConnectionContext) -> None:
    session = game_session_manager.get_for_client(ctx.client_id)
    if session is not None:
        await session.handle_disconnect(ctx.client_id)


def _parse_pos(value) -> tuple | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(v, int) for v in value):
        return (value[0], value[1])
    return None


async def handle_move(payload: dict, ctx: ConnectionContext) -> dict | None:
    session = game_session_manager.get_for_client(ctx.client_id)
    if session is None:
        return {"success": False, "message": "not in an active game"}

    from_pos = _parse_pos(payload.get("from"))
    to_pos = _parse_pos(payload.get("to"))
    if from_pos is None or to_pos is None:
        return {"success": False, "message": "invalid move payload"}

    await session.handle_move(ctx.client_id, from_pos, to_pos)
    return None


async def handle_jump(payload: dict, ctx: ConnectionContext) -> dict | None:
    session = game_session_manager.get_for_client(ctx.client_id)
    if session is None:
        return {"success": False, "message": "not in an active game"}

    pos = _parse_pos(payload.get("pos"))
    if pos is None:
        return {"success": False, "message": "invalid jump payload"}

    await session.handle_jump(ctx.client_id, pos)
    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = f"{websocket.client.host}:{websocket.client.port}"
    logger.info("client connected: %s", client)
    ctx = ConnectionContext(websocket, client)
    await event_bus.publish(ClientConnected(client_id=client))
    try:
        while True:
            data = await websocket.receive_json()
            response = await _dispatch(Envelope.from_dict(data), ctx, client)
            if response is None:
                continue
            logger.info("sending to %s: %s", client, response.to_dict())
            await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
        await _leave_room(ctx)
        await _leave_queue(ctx)
        await _handle_game_disconnect(ctx)


async def _dispatch(envelope: Envelope, ctx: "ConnectionContext", client: str) -> Envelope | None:
    from server.config import HANDLERS, RESPONSE_TYPE

    logger.info("received from %s: %s", client, envelope.to_dict())

    handler = HANDLERS.get(envelope.type)
    if handler is None:
        return Envelope(
            type="error",
            payload={"message": f"unknown message type: {envelope.type}"},
            request_id=envelope.request_id,
        )

    payload = await handler(envelope.payload, ctx)
    if payload is None:
        return None
    return Envelope(
        type=RESPONSE_TYPE.get(envelope.type, envelope.type),
        payload=payload,
        request_id=envelope.request_id,
    )
