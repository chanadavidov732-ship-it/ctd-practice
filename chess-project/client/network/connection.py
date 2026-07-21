import json
import logging

import websockets

from shared.protocol import Envelope

logger = logging.getLogger("client")


class ServerConnection:
    def __init__(self, uri: str):
        self.uri = uri
        self._ws = None

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.uri)
        logger.info("connected to %s", self.uri)

    async def send(self, envelope: Envelope) -> None:
        logger.info("sending: %s", envelope.to_dict())
        await self._ws.send(json.dumps(envelope.to_dict()))

    async def receive(self) -> Envelope:
        raw = await self._ws.recv()
        envelope = Envelope.from_dict(json.loads(raw))
        logger.info("received: %s", envelope.to_dict())
        return envelope

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            logger.info("connection closed")
