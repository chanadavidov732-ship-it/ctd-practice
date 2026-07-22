import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bus.event_bus import event_bus
from bus.events import ClientConnected, PlayerJoinedRoom, RoomCreated, ViewerJoinedRoom
from server.auth.auth import login as auth_login
from server.auth.auth import register as auth_register
from server.logic.room_manager import room_manager
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


async def handle_echo(payload: dict, ctx: ConnectionContext) -> dict:
    return payload


async def handle_login(payload: dict, ctx: ConnectionContext) -> dict:
    return await auth_login(payload.get("username", ""), payload.get("password", ""))


async def handle_register(payload: dict, ctx: ConnectionContext) -> dict:
    return await auth_register(payload.get("username", ""), payload.get("password", ""))


async def handle_menu_select(payload: dict, ctx: ConnectionContext) -> dict:
    choice = payload.get("choice")
    if choice not in ("play", "room"):
        return {"received": False, "message": f"unknown menu choice: {choice}"}
    return {"received": True, "choice": choice, "message": f"'{choice}' selection received"}


async def handle_create_room(payload: dict, ctx: ConnectionContext) -> dict:
    room = room_manager.create_room(ctx.client_id)
    ctx.room_id = room.room_id
    connection_registry.add(room.room_id, ctx.websocket, ctx.client_id)
    await event_bus.publish(RoomCreated(room_id=room.room_id, client_id=ctx.client_id))
    return {
        "room_id": room.room_id,
        "role": "player",
        "player_count": len(room.players),
        "viewer_count": len(room.viewers),
    }


async def handle_join_room(payload: dict, ctx: ConnectionContext) -> dict:
    room_id = payload.get("room_id", "")
    room = room_manager.join_room(room_id, ctx.client_id)
    if room is None:
        return {"success": False, "message": "room not found"}

    ctx.room_id = room_id
    connection_registry.add(room_id, ctx.websocket, ctx.client_id)
    role = room.role_of(ctx.client_id)

    if role == "player":
        await event_bus.publish(PlayerJoinedRoom(room_id=room_id, client_id=ctx.client_id))
    else:
        await event_bus.publish(ViewerJoinedRoom(room_id=room_id, client_id=ctx.client_id))

    return {
        "success": True,
        "room_id": room_id,
        "role": role,
        "player_count": len(room.players),
        "viewer_count": len(room.viewers),
    }


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


HANDLERS = {
    "echo": handle_echo,
    "login": handle_login,
    "register": handle_register,
    "menu_select": handle_menu_select,
    "create_room": handle_create_room,
    "join_room": handle_join_room,
    "cancel_room": handle_cancel_room,
}

RESPONSE_TYPE = {
    "login": "login_result",
    "register": "register_result",
    "menu_select": "menu_ack",
    "create_room": "room_state",
    "join_room": "room_state",
    "cancel_room": "room_state",
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
                response = Envelope(
                    type=RESPONSE_TYPE.get(envelope.type, envelope.type),
                    payload=await handler(envelope.payload, ctx),
                    request_id=envelope.request_id,
                )

            logger.info("sending to %s: %s", client, response.to_dict())
            await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
        await _leave_room(ctx)
