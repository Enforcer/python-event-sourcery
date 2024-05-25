from functools import singledispatchmethod
from typing import Sequence, cast

from event_sourcery.event_store.context import get_context
from event_sourcery.event_store.event import Event, Metadata, Position, RawEvent, Serde
from event_sourcery.event_store.interfaces import StorageStrategy
from event_sourcery.event_store.stream_id import StreamId
from event_sourcery.event_store.versioning import (
    NO_VERSIONING,
    ExplicitVersioning,
    Versioning,
)


class EventStore:
    def __init__(self, storage_strategy: StorageStrategy, serde: Serde) -> None:
        self._storage_strategy = storage_strategy
        self._serde = serde

    def load_stream(
        self,
        stream_id: StreamId,
        start: int | None = None,
        stop: int | None = None,
    ) -> Sequence[Metadata]:
        context = get_context()
        events = self._storage_strategy.fetch_events(
            stream_id, start=start, stop=stop, context=context
        )
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
        self._append(
            stream_id=stream_id,
            events=(first,) + events,
            expected_version=expected_version,
        )

    def _append(
        self,
        stream_id: StreamId,
        events: Sequence[Metadata],
        expected_version: int | Versioning,
    ) -> None:
        new_version = events[-1].version
        versioning: Versioning
        if expected_version is not NO_VERSIONING:
            versioning = ExplicitVersioning(
                expected_version=cast(int, expected_version),
                initial_version=cast(int, new_version),
            )
        else:
            versioning = NO_VERSIONING

        context = get_context()
        self._storage_strategy.insert_events(
            stream_id=stream_id,
            versioning=versioning,
            events=self._serialize_events(events, stream_id),
            context=context,
        )

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

    @property
    def position(self) -> Position | None:
        return self._storage_strategy.current_position
