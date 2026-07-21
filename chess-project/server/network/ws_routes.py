import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bus.event_bus import event_bus
from bus.events import ClientConnected
from shared.protocol import Envelope

logger = logging.getLogger("server")

router = APIRouter()


def handle_echo(payload: dict) -> dict:
    return payload


HANDLERS = {
    "echo": handle_echo,
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
                    type=envelope.type,
                    payload=handler(envelope.payload),
                    request_id=envelope.request_id,
                )

            logger.info("sending to %s: %s", client, response.to_dict())
            await websocket.send_json(response.to_dict())
    except WebSocketDisconnect:
        logger.info("client disconnected: %s", client)
