import logging

from bus.events import ClientConnected

logger = logging.getLogger("bus")


def on_client_connected(event: ClientConnected) -> None:
    logger.info("event received: ClientConnected(client_id=%s)", event.client_id)
