import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List
from enum import Enum
import copy


class EventType(Enum):
    CREATED = 1
    UPDATED = 2
    DELETED = 3
    UNKNOWN = 4
    HEARTBEAT = 5


@dataclass
class Event:
    type: EventType
    data: Any

    def __post_init__(self):
        if isinstance(self.type, int):
            self.type = EventType(self.type)

    def __repr__(self):
        # return f"type={self.type}, data={self.data}"
        return f"{self.type} {type(self.data)}"


def event_decoder(obj):
    if "type" in obj:
        obj["type"] = EventType[obj["type"]]
    return obj


class Subscriber:
    """这个叫 Subscriber不合适, 应该是 TopicEventQueue"""

    def __init__(self):
        self.queue = asyncio.Queue()

    async def enqueue(self, event: Event):
        await self.queue.put(event)

    async def receive(self) -> Any:
        return await self.queue.get()


class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Subscriber]] = {}

    def subscribe(self, topic: str) -> Subscriber:
        # print(f"subscribe {topic}")
        subscriber = Subscriber()
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(subscriber)
        return subscriber

    def unsubscribe(self, topic: str, subscriber: Subscriber):
        if topic in self.subscribers:
            self.subscribers[topic].remove(subscriber)
            if not self.subscribers[topic]:
                del self.subscribers[topic]

    async def publish(self, topic: str, event: Event):
        # print(f"publish {event}")
        known_topic = ["systemload", "worker"]
        if topic not in known_topic:
            print(f"publish {event}")
        if topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                await subscriber.enqueue(copy.deepcopy(event))


event_bus = EventBus()
