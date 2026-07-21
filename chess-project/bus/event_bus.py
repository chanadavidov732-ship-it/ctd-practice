from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)


event_bus = EventBus()
