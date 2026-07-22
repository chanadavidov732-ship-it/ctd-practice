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
    if choice not in ("play", "room"):
        return {"received": False, "message": f"unknown menu choice: {choice}"}
    return {"received": True, "choice": choice, "message": f"'{choice}' selection received"}


def _participant(ctx: "ConnectionContext") -> RoomParticipant:
    return RoomParticipant(client_id=ctx.client_id, username=ctx.username, rating=ctx.rating, websocket=ctx.websocket)


async def handle_create_room(payload: dict, ctx: ConnectionContext) -> dict:
    room = room_manager.create_room(_participant(ctx))
    ctx.room_id = room.room_id
    connection_registry.add(room.room_id, ctx.websocket, ctx.client_id)
    await event_bus.publish(RoomCreated(room_id=room.room_id, client_id=ctx.client_id))
    return {
        "room_id": room.room_id,
        "role": "player",
        "player_count": len(room.players),
        "viewer_count": len(room.viewers),
    }


async def handle_join_room(payload: dict, ctx: ConnectionContext) -> dict | None:
    room_id = payload.get("room_id", "")
    room = room_manager.join_room(room_id, _participant(ctx))
    if room is None:
        return {"success": False, "message": "room not found"}

    ctx.room_id = room_id
    connection_registry.add(room_id, ctx.websocket, ctx.client_id)
    role = room.role_of(ctx.client_id)

    # Sent directly and awaited before publishing: if this join completes the
    # room's player pair, the PlayerJoinedRoom listener starts a GameSession and
    # pushes "game_started" synchronously, which must not arrive before this ack.
    ack = Envelope(
        type="room_state",
        payload={
            "success": True,
            "room_id": room_id,
            "role": role,
            "player_count": len(room.players),
            "viewer_count": len(room.viewers),
        },
    )
    await ctx.websocket.send_json(ack.to_dict())

    if role == "player":
        await event_bus.publish(PlayerJoinedRoom(room_id=room_id, client_id=ctx.client_id))
    else:
        await event_bus.publish(ViewerJoinedRoom(room_id=room_id, client_id=ctx.client_id))

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

    # Sent directly (not returned) and awaited before publishing: the PlayerQueued
    # listener may find an immediate match and push match_found synchronously, and
    # that must not reach this client before its own "queued" ack does.
    ack = Envelope(
        type="play_queued",
        payload={"success": True, "message": "queued for a match", "rating": ctx.rating},
    )
    await ctx.websocket.send_json(ack.to_dict())

    await event_bus.publish(PlayerQueued(client_id=ctx.client_id, username=ctx.username, rating=ctx.rating))
    return None


async def handle_cancel_play(payload: dict, ctx: ConnectionContext) -> dict:
    player = matchmaking.remove(ctx.client_id)
    if player is None:
        return {"success": False, "message": "not in queue"}
    if player.timeout_task is not None:
        player.timeout_task.cancel()
    return {"success": True, "message": "left queue"}


async def _leave_queue(ctx: ConnectionContext) -> None:
    player = matchmaking.remove(ctx.client_id)
    if player is not None and player.timeout_task is not None:
        player.timeout_task.cancel()


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


HANDLERS = {
    "echo": handle_echo,
    "login": handle_login,
    "register": handle_register,
    "menu_select": handle_menu_select,
    "create_room": handle_create_room,
    "join_room": handle_join_room,
    "cancel_room": handle_cancel_room,
    "play": handle_play,
    "cancel_play": handle_cancel_play,
    "move": handle_move,
    "jump": handle_jump,
}

RESPONSE_TYPE = {
    "login": "login_result",
    "register": "register_result",
    "menu_select": "menu_ack",
    "create_room": "room_state",
    "cancel_room": "room_state",
    "cancel_play": "play_cancelled",
}


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
            envelope = Envelope.from_dict(data)
            logger.info("received from %s: %s", client, envelope.to_dict())

            handler = HANDLERS.get(envelope.type)
            if handler is None:
                response = Envelope(
                    type="error",
                    payload={"message": f"unknown message type: {envelope.type}"},
                    request_id=envelope.request_id,
                )
            else:
                payload = await handler(envelope.payload, ctx)
                if payload is None:
                    # handler already sent its own envelope(s) directly (ordering-sensitive case)
                    continue
                response = Envelope(
                    type=RESPONSE_TYPE.get(envelope.type, envelope.type),
                    payload=payload,
                    request_id=envelope.request_id,
                )

            logger.info("sending to %s: %s", client, response.to_dict())
            await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
        await _leave_room(ctx)
        await _leave_queue(ctx)
