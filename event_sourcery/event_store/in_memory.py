import time
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass, field
from datetime import timedelta
from operator import getitem
from typing import ContextManager, Dict, Generator, Iterator

from typing_extensions import Self

from event_sourcery.event_store import Event, EventRegistry, EventStore
from event_sourcery.event_store.event import Position, RawEvent, RecordedRaw, Serde
from event_sourcery.event_store.exceptions import ConcurrentStreamWriteError
from event_sourcery.event_store.factory import (
    Engine,
    EventStoreFactory,
    NoOutboxStorageStrategy,
    no_filter,
)
from event_sourcery.event_store.interfaces import (
    OutboxFiltererStrategy,
    OutboxStorageStrategy,
    StorageStrategy,
    SubscriptionStrategy,
)
from event_sourcery.event_store.outbox import Outbox
from event_sourcery.event_store.stream_id import StreamId
from event_sourcery.event_store.subscription import Subscriber
from event_sourcery.event_store.versioning import NO_VERSIONING, Versioning


@dataclass
class Storage:
    events: list[RawEvent] = field(default_factory=list, init=False)
    _data: dict[StreamId, list[RawEvent]] = field(default_factory=dict, init=False)
    _versions: dict[StreamId, int | None] = field(default_factory=dict, init=False)

    @property
    def current_position(self) -> int:
        return len(self.events)

    def __contains__(self, stream_id: object) -> bool:
        return stream_id in self._data

    def create(self, stream_id: StreamId, version: Versioning) -> None:
        self._data[stream_id] = []
        if version is NO_VERSIONING:
            self._versions[stream_id] = None
        else:
            self._versions[stream_id] = 0

    def append(self, events: list[RawEvent]) -> None:
        self.events.extend(events)
        for event in events:
            stream_id = event.stream_id
            self._data[stream_id].append(event)
            self._versions[stream_id] = event.version

    def replace(self, with_snapshot: RawEvent) -> None:
        stream_id = with_snapshot.stream_id
        self._data[stream_id] = [with_snapshot]
        self._versions[stream_id] = with_snapshot.version

    def read(self, stream_id: StreamId) -> list[RawEvent]:
        return copy(self._data[stream_id])

    def delete(self, stream_id: StreamId) -> None:
        del self._data[stream_id]

    def get_version(self, stream_id: StreamId) -> int | None:
        return self._versions[stream_id]


@dataclass
class InMemorySubscription(Iterator[list[RecordedRaw]]):
    _storage: Storage
    _current_position: int
    _batch_size: int
    _timelimit: timedelta

    def _pop_record(self) -> tuple[RawEvent, Position] | None:
        if len(self._storage.events) <= self._current_position:
            return None
        record = self._storage.events[self._current_position]
        self._current_position += 1
        return record, self._current_position - 1

    def __next__(self) -> list[RecordedRaw]:
        batch: list[tuple[RawEvent, Position]] = []

        start = time.monotonic()
        while len(batch) < self._batch_size:
            record = self._pop_record()
            if record is not None:
                batch.append(record)
            time.sleep(0.1)
            if time.monotonic() - start > self._timelimit.total_seconds():
                break

        return [
            RecordedRaw(entry=copy(record), position=position)
            for record, position in batch
        ]


@dataclass
class InMemoryToCategorySubscription(InMemorySubscription):
    _category: str

    def _pop_record(self) -> tuple[RawEvent, Position] | None:
        while True:
            record = super()._pop_record()
            if record is None:
                return None
            raw, position = record
            if raw.stream_id.category != self._category:
                continue
            return record


@dataclass
class InMemoryToEventTypesSubscription(InMemorySubscription):
    _types: list[str]

    def _pop_record(self) -> tuple[RawEvent, Position] | None:
        while True:
            record = super()._pop_record()
            if record is None:
                return None
            raw, position = record
            if raw.name not in self._types:
                continue
            return record


@dataclass
class InMemoryOutboxStorageStrategy(OutboxStorageStrategy):
    MAX_PUBLISH_ATTEMPTS = 3
    _filterer: OutboxFiltererStrategy
    _outbox: list[tuple[RawEvent, int]] = field(default_factory=list, init=False)

    def put_into_outbox(self, events: list[RawEvent]) -> None:
        self._outbox.extend([(e, 0) for e in events if self._filterer(e)])

    def outbox_entries(self, limit: int) -> Iterator[ContextManager[RawEvent]]:
        for entry in self._outbox[:limit]:
            yield self._publish_context(*entry)

    @contextmanager
    def _publish_context(
        self,
        event: RawEvent,
        failure_count: int,
    ) -> Generator[RawEvent, None, None]:
        index = self._outbox.index((event, failure_count))
        try:
            yield event
        except Exception:
            failure_count += 1
            if self._reached_max_number_of_attempts(failure_count):
                del self._outbox[index]
            else:
                self._outbox[index] = (event, failure_count)
        else:
            del self._outbox[index]

    def _reached_max_number_of_attempts(self, failure_count: int) -> bool:
        return failure_count >= self.MAX_PUBLISH_ATTEMPTS


@dataclass
class InMemorySubscriptionStrategy(SubscriptionStrategy):
    _storage: Storage

    def subscribe_to_all(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
    ) -> Iterator[list[RecordedRaw]]:
        return InMemorySubscription(self._storage, start_from, batch_size, timelimit)

    def subscribe_to_category(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
        category: str,
    ) -> Iterator[list[RecordedRaw]]:
        return InMemoryToCategorySubscription(
            self._storage,
            start_from,
            batch_size,
            timelimit,
            category,
        )

    def subscribe_to_events(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
        events: list[str],
    ) -> Iterator[list[RecordedRaw]]:
        return InMemoryToEventTypesSubscription(
            self._storage,
            start_from,
            batch_size,
            timelimit,
            events,
        )


class InMemoryStorageStrategy(StorageStrategy):
    def __init__(
        self,
        storage: Storage,
        outbox_strategy: InMemoryOutboxStorageStrategy | None,
    ) -> None:
        self._names: Dict[str | None, str] = {}
        self._storage = storage
        self._outbox = outbox_strategy

    def fetch_events(
        self,
        stream_id: StreamId,
        start: int | None = None,
        stop: int | None = None,
    ) -> list[RawEvent]:
        if stream_id not in self._storage:
            return []
        stream = getitem(
            self._storage.read(stream_id),
            slice(start and start - 1, stop and stop - 1),
        )
        return list(stream)

    def insert_events(
        self, stream_id: StreamId, versioning: Versioning, events: list[RawEvent]
    ) -> None:
        self._ensure_stream(stream_id=stream_id, versioning=versioning)
        self._storage.append(events)
        if self._outbox:
            self._outbox.put_into_outbox(events)

    def save_snapshot(self, snapshot: RawEvent) -> None:
        self._storage.replace(with_snapshot=snapshot)

    def _ensure_stream(self, stream_id: StreamId, versioning: Versioning) -> None:
        if stream_id not in self._storage:
            self._storage.create(stream_id, versioning)

        versioning.validate_if_compatible(self._storage.get_version(stream_id))

        if versioning is not NO_VERSIONING and versioning.expected_version:
            last_version = (
                self._storage.get_version(stream_id)
                if stream_id in self._storage
                else None
            )
            if last_version != versioning.expected_version:
                raise ConcurrentStreamWriteError(
                    last_version,
                    versioning.expected_version,
                )

    def delete_stream(self, stream_id: StreamId) -> None:
        if stream_id in self._storage:
            self._storage.delete(stream_id)

    @property
    def current_position(self) -> Position | None:
        current_position = self._storage.current_position
        return current_position and Position(current_position)


@dataclass(repr=False)
class InMemoryEventStoreFactory(EventStoreFactory):
    serde = Serde(Event.__registry__)

    _storage: Storage = field(default_factory=Storage)
    _outbox_strategy: InMemoryOutboxStorageStrategy | None = None
    _subscription_strategy: InMemorySubscriptionStrategy = field(init=False)

    def __post_init__(self) -> None:
        self._subscription_strategy = InMemorySubscriptionStrategy(self._storage)

    def build(self) -> Engine:
        engine = Engine()
        engine.event_store = EventStore(
            InMemoryStorageStrategy(self._storage, self._outbox_strategy),
            self._outbox_strategy or NoOutboxStorageStrategy(),
            self._subscription_strategy,
            self.serde,
        )
        engine.outbox = Outbox(
            self._outbox_strategy or NoOutboxStorageStrategy(),
            self.serde,
        )
        engine.subscriber = Subscriber(
            engine.event_store.position or 0,
            self._subscription_strategy,
            self.serde,
        )
        return engine

    def with_event_registry(self, event_registry: EventRegistry) -> Self:
        self.serde = Serde(event_registry)
        return self

    def with_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = InMemoryOutboxStorageStrategy(filterer)
        return self

    def without_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = None
        return self
