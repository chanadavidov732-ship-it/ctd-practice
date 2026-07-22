import asyncio
from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event) -> None:
        for handler in self._subscribers[type(event)]:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result


event_bus = EventBus()
