from datetime import timedelta
from typing import Iterator

from sqlalchemy import Connection, event
from sqlalchemy.orm import Mapper

from event_sourcery.event_store import Entry, Position, RawEvent, RecordedRaw
from event_sourcery.event_store.event import Serde
from event_sourcery.event_store.interfaces import SubscriptionStrategy
from event_sourcery_sqlalchemy import models


class SqlAlchemySubscriptionStrategy(SubscriptionStrategy):
    def subscribe(
        self,
        from_position: Position | None,
        to_category: str | None,
        to_events: list[str] | None,
    ) -> Iterator[RecordedRaw]:
        raise NotImplementedError

    def subscribe_to_all(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
    ) -> Iterator[list[RecordedRaw]]:
        raise NotImplementedError

    def subscribe_to_category(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
        category: str,
    ) -> Iterator[list[RecordedRaw]]:
        raise NotImplementedError

    def subscribe_to_events(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
        events: list[str],
    ) -> Iterator[list[RecordedRaw]]:
        raise NotImplementedError


class InTransactionSubscription(Iterator[Entry]):
    def __init__(self, serde: Serde) -> None:
        self._serde = serde
        self._events: list[Entry] = []
        event.listen(models.Event, "before_insert", self.append)

    def close(self) -> None:
        event.remove(models.Event, "before_insert", self.append)

    def __next__(self) -> Entry:
        if not self._events:
            raise StopIteration
        return self._events.pop(0)

    def append(self, mapper: Mapper, conn: Connection, model: models.Event) -> None:
        raw = RawEvent(
            uuid=model.uuid,
            stream_id=model.stream_id,
            created_at=model.created_at,
            version=model.version,
            name=model.name,
            data=model.data,
            context=model.event_context,
        )
        entry = Entry(metadata=self._serde.deserialize(raw), stream_id=raw.stream_id)
        self._events.append(entry)
