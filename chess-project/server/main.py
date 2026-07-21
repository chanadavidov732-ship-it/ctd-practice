import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from shared.protocol import Envelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

app = FastAPI()


def handle_echo(payload: dict) -> dict:
    return payload


HANDLERS = {
    "echo": handle_echo,
}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = f"{websocket.client.host}:{websocket.client.port}"
    logger.info("client connected: %s", client)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
