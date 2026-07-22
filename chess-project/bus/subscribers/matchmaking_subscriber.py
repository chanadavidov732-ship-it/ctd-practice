from bus.event_bus import event_bus
from bus.events import PlayerQueued
from bus.listeners.matchmaking_listener import on_player_queued


def register_matchmaking_listeners() -> None:
    event_bus.subscribe(PlayerQueued, on_player_queued)
