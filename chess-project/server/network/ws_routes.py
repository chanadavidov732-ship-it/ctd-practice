import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bus.event_bus import event_bus
from bus.events import ClientConnected
from server.auth.auth import login as auth_login
from server.auth.auth import register as auth_register
from shared.protocol import Envelope

logger = logging.getLogger("server")

router = APIRouter()


async def handle_echo(payload: dict) -> dict:
    return payload


async def handle_login(payload: dict) -> dict:
    return await auth_login(payload.get("username", ""), payload.get("password", ""))


async def handle_register(payload: dict) -> dict:
    return await auth_register(payload.get("username", ""), payload.get("password", ""))


HANDLERS = {
    "echo": handle_echo,
    "login": handle_login,
    "register": handle_register,
}

RESPONSE_TYPE = {
    "login": "login_result",
    "register": "register_result",
}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = f"{websocket.client.host}:{websocket.client.port}"
    logger.info("client connected: %s", client)
    event_bus.publish(ClientConnected(client_id=client))
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
                    payload=await handler(envelope.payload),
                    request_id=envelope.request_id,
                )

            logger.info("sending to %s: %s", client, response.to_dict())
            await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
