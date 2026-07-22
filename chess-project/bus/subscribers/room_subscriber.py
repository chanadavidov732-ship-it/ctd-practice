from bus.event_bus import event_bus
from bus.events import PlayerJoinedRoom, RoomCreated, ViewerJoinedRoom
from bus.listeners.room_listener import on_player_joined_room, on_room_created, on_viewer_joined_room


def register_room_listeners() -> None:
    event_bus.subscribe(RoomCreated, on_room_created)
    event_bus.subscribe(PlayerJoinedRoom, on_player_joined_room)
    event_bus.subscribe(ViewerJoinedRoom, on_viewer_joined_room)
