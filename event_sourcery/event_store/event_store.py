from functools import singledispatchmethod
from typing import Callable, Iterator, Sequence, Type, TypeAlias, cast

from event_sourcery.event_store.event import (
    Event,
    Metadata,
    Position,
    RawEvent,
    Recorded,
    Serde,
)
from event_sourcery.event_store.interfaces import OutboxStorageStrategy, StorageStrategy
from event_sourcery.event_store.stream_id import StreamId
from event_sourcery.event_store.versioning import (
    NO_VERSIONING,
    ExplicitVersioning,
    Versioning,
)

Category: TypeAlias = str


class EventStore:
    def __init__(
        self,
        storage_strategy: StorageStrategy,
        outbox_storage_strategy: OutboxStorageStrategy,
        serde: Serde,
    ) -> None:
        self._storage_strategy = storage_strategy
        self._outbox_storage_strategy = outbox_storage_strategy
        self._serde = serde

    def run_outbox(
        self,
        publisher: Callable[[Metadata, StreamId], None],
        limit: int = 100,
    ) -> None:
        stream = self._outbox_storage_strategy.outbox_entries(limit=limit)
        for entry in stream:
            with entry as raw_event_dict:
                event = self._serde.deserialize(raw_event_dict)
                publisher(event, raw_event_dict.stream_id)

    def load_stream(
        self,
        stream_id: StreamId,
        start: int | None = None,
        stop: int | None = None,
    ) -> Sequence[Metadata]:
        events = self._storage_strategy.fetch_events(stream_id, start=start, stop=stop)
        return self._deserialize_events(events)

    @singledispatchmethod
    def append(
        self,
        first: Metadata,
        *events: Metadata,
        stream_id: StreamId,
        expected_version: int | Versioning = 0,
    ) -> None:
        self._append(
            stream_id=stream_id,
            events=(first,) + events,
            expected_version=expected_version,
        )

    @append.register
    def _append_events(
        self,
        *events: Event,
        stream_id: StreamId,
        expected_version: int | Versioning = 0,
    ) -> None:
        wrapped_events = self._wrap_events(expected_version, events)
        self.append(
            *wrapped_events,
            stream_id=stream_id,
            expected_version=expected_version,
        )

    @singledispatchmethod
    def _wrap_events(
        self,
        expected_version: int,
        events: Sequence[Event],
    ) -> Sequence[Metadata]:
        return [
            Metadata.wrap(event=event, version=version)
            for version, event in enumerate(events, start=expected_version + 1)
        ]

    @_wrap_events.register
    def _wrap_events_versioning(
        self, expected_version: Versioning, events: Sequence[Event]
    ) -> Sequence[Metadata]:
        return [Metadata.wrap(event=event, version=None) for event in events]

    @singledispatchmethod
    def publish(
        self,
        first: Metadata,
        *events: Metadata,
        stream_id: StreamId,
        expected_version: int | Versioning = 0,
    ) -> None:
        serialized_events = self._append(
            stream_id=stream_id,
            events=(first,) + events,
            expected_version=expected_version,
        )
        self._outbox_storage_strategy.put_into_outbox(serialized_events)

    def _append(
        self,
        stream_id: StreamId,
        events: Sequence[Metadata],
        expected_version: int | Versioning,
    ) -> list[RawEvent]:
        new_version = events[-1].version
        versioning: Versioning
        if expected_version is not NO_VERSIONING:
            versioning = ExplicitVersioning(
                expected_version=cast(int, expected_version),
                initial_version=cast(int, new_version),
            )
        else:
            versioning = NO_VERSIONING

        self._storage_strategy.ensure_stream(
            stream_id=stream_id,
            versioning=versioning,
        )
        serialized_events = self._serialize_events(events, stream_id)
        self._storage_strategy.insert_events(serialized_events)
        return serialized_events

    def delete_stream(self, stream_id: StreamId) -> None:
        self._storage_strategy.delete_stream(stream_id)

    def save_snapshot(self, stream_id: StreamId, snapshot: Metadata) -> None:
        serialized = self._serde.serialize(event=snapshot, stream_id=stream_id)
        self._storage_strategy.save_snapshot(serialized)

    def _deserialize_events(self, events: list[RawEvent]) -> list[Metadata]:
        return [self._serde.deserialize(e) for e in events]

    def _serialize_events(
        self,
        events: Sequence[Metadata],
        stream_id: StreamId,
    ) -> list[RawEvent]:
        return [self._serde.serialize(event=e, stream_id=stream_id) for e in events]

    def subscribe_to_all(self, start_from: Position) -> Iterator[Recorded]:
        return map(
            self._serde.deserialize_record,
            self._storage_strategy.subscribe_to_all(start_from),
        )

    def subscribe_to_category(
        self,
        start_from: Position,
        to: Category,
    ) -> Iterator[Recorded]:
        return map(
            self._serde.deserialize_record,
            self._storage_strategy.subscribe_to_category(
                start_from,
                category=str(to),
            ),
        )

    def subscribe_to_events(
        self,
        start_from: Position,
        to: list[Type[Event]],
    ) -> Iterator[Recorded]:
        return map(
            self._serde.deserialize_record,
            self._storage_strategy.subscribe_to_events(
                start_from,
                [self._serde.registry.name_for_type(et) for et in to],
            ),
        )

    @property
    def position(self) -> Position | None:
        return self._storage_strategy.current_position

    def batch_subscribe(
        self,
        from_position: Position,
        max_events: int,
        within: float,
    ) -> Iterator[list[Recorded]]:
        pass


class Subscriber:
    def __init__(
        self,
        storage_strategy: StorageStrategy,
        serde: Serde,
    ) -> None:
        self._storage_strategy = storage_strategy
        self._serde = serde

    def from_position(self):
        pass

    def to_category(self) -> BuilderCategory:
        pass


event_store = EventStore()
subscription = event_store.subscribe().from_position(100).to_category().take(10, within=30)

take(subscription, 10, within=30)
