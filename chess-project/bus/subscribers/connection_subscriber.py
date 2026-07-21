from bus.event_bus import event_bus
from bus.events import ClientConnected
from bus.listeners.connection_listener import on_client_connected


def register_connection_listeners() -> None:
    event_bus.subscribe(ClientConnected, on_client_connected)
