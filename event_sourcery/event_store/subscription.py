from dataclasses import dataclass, field
from datetime import timedelta
from typing import Generator, Iterator, Type, TypeAlias

from event_sourcery.event_store import Event, Position, Recorded, RecordedRaw
from event_sourcery.event_store.event import Serde
from event_sourcery.event_store.event_store import Category
from event_sourcery.event_store.interfaces import StorageStrategy

Seconds: TypeAlias = timedelta | int | float
RecordedGenerator: TypeAlias = Generator[RecordedRaw, None, None]


class ReadySubscription:
    def take(self, max_count: int, within: Seconds) -> list[Recorded]:
        pass

    def iter(self, within: Seconds | None = None) -> Generator[Recorded, None, None]:
        pass

class CategorySubscription(ReadySubscription):
    category: pass


class EventTypeSubscription(ReadySubscription):
    event_type: list


@dataclass
class Subscription:
    serde: Serde
    from_position: int

    _subscription_build: pass

    def to_category(self) -> CategorySubscription:
        pass

    def to_events(self) -> EventTypeSubscription:
        pass

    def take(self, max_count: int, within: Seconds) -> list[Recorded]:
        return [
            self.serde.deserialize_record(r)
            for r in self._raw.take(max_count, within)
        ]

    def iter(self, within: Seconds | None = None) -> Generator[Recorded, None, None]:
        for raw in self._raw.iter(within):
            yield self.serde.deserialize_record(raw)
