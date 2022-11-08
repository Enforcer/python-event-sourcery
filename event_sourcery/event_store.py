import abc
from typing import Iterator, Sequence, Type, TypeVar

from event_sourcery.after_commit_subscriber import AfterCommit
from event_sourcery.dto.raw_event_dict import RawEventDict
from event_sourcery.event_registry import BaseEventCls, EventRegistry
from event_sourcery.exceptions import (
    EitherStreamIdOrStreamNameIsRequired,
    Misconfiguration,
    NoEventsToAppend,
)
from event_sourcery.interfaces.event import Event
from event_sourcery.interfaces.outbox_storage_strategy import OutboxStorageStrategy
from event_sourcery.interfaces.serde import Serde
from event_sourcery.interfaces.storage_strategy import StorageStrategy
from event_sourcery.interfaces.subscriber import Subscriber
from event_sourcery.types.stream_id import StreamId

TAggregate = TypeVar("TAggregate")


class EventStore(abc.ABC):
    def __init__(
        self,
        serde: Serde,
        storage_strategy: StorageStrategy,
        outbox_storage_strategy: OutboxStorageStrategy,
        event_base_class: Type[BaseEventCls] | None = None,
        event_registry: EventRegistry | None = None,
        subscriptions: dict[Type[Event], list[Subscriber]] | None = None,
    ) -> None:
        if event_base_class is not None and event_registry is not None:
            raise Misconfiguration(
                "You can specify only one of `event_base_class` or `event_registry`"
            )

        if subscriptions is None:
            subscriptions = {}

        if event_base_class is not None:
            self._event_registry = event_base_class.__registry__
        elif event_registry is not None:
            self._event_registry = event_registry
        else:  # not possible
            pass

        self._serde = serde
        self._storage_strategy = storage_strategy
        self._outbox_storage_strategy = outbox_storage_strategy
        self._subscriptions = subscriptions

    def load_stream(
        self,
        stream_id: StreamId | None = None,
        stream_name: str | None = None,
        start: int | None = None,
        stop: int | None = None,
    ) -> list[Event]:
        events = self._storage_strategy.fetch_events(
            stream_id, stream_name, start=start, stop=stop
        )
        return self._deserialize_events(events)

    def append(
        self,
        events: Sequence[Event],
        stream_id: StreamId | None = None,
        stream_name: str | None = None,
        expected_version: int = 0,
    ) -> None:
        self._append(
            stream_id=stream_id,
            stream_name=stream_name,
            events=events,
            expected_version=expected_version,
        )

    def publish(
        self,
        events: Sequence[Event],
        stream_id: StreamId | None = None,
        stream_name: str | None = None,
        expected_version: int = 0,
    ) -> None:
        serialized_events = self._append(
            stream_id=stream_id,
            stream_name=stream_name,
            events=events,
            expected_version=expected_version,
        )

        # TODO: make it more robust per subscriber?
        for event in events:
            for subscriber in self._subscriptions.get(type(event), []):
                if isinstance(subscriber, AfterCommit):
                    self._storage_strategy.run_after_commit(lambda: subscriber(event))
                else:
                    subscriber(event)

            catch_all_subscribers = self._subscriptions.get(Event, [])  # type: ignore
            for catch_all_subscriber in catch_all_subscribers:
                catch_all_subscriber(event)

        self._outbox_storage_strategy.put_into_outbox(serialized_events)

    def _append(
        self,
        stream_id: StreamId | None,
        stream_name: str | None,
        events: Sequence[Event],
        expected_version: int,
    ) -> list[RawEventDict]:
        if not events:
            raise NoEventsToAppend

        if stream_id is None and stream_name is None:
            raise EitherStreamIdOrStreamNameIsRequired()

        stream_id = self._storage_strategy.ensure_stream(
            stream_id=stream_id,
            stream_name=stream_name,
            expected_version=expected_version,
        )
        serialized_events = self._serialize_events(events, stream_id, expected_version)
        self._storage_strategy.insert_events(serialized_events)
        return serialized_events

    def iter(
        self, *streams_ids: StreamId
    ) -> Iterator[Event]:  # TODO - iter by stream name
        events_iterator = self._storage_strategy.iter(*streams_ids)
        for event in events_iterator:
            yield self._serde.deserialize(
                event, self._event_registry.type_for_name(event["name"])
            )

    def delete_stream(self, stream_id: StreamId) -> None:
        self._storage_strategy.delete_stream(stream_id)

    def save_snapshot(self, stream_id: StreamId, snapshot: Event, version: int) -> None:
        serialized = self._serde.serialize(
            event=snapshot,
            stream_id=stream_id,
            name=self._event_registry.name_for_type(type(snapshot)),
            version=version,
        )
        self._storage_strategy.save_snapshot(serialized)

    def _deserialize_events(self, events: list[RawEventDict]) -> list[Event]:
        return [
            self._serde.deserialize(
                event=event,
                event_type=self._event_registry.type_for_name(event["name"]),
            )
            for event in events
        ]

    def _serialize_events(
        self, events: Sequence[Event], stream_id: StreamId, expected_stream_version: int
    ) -> list[RawEventDict]:
        return [
            self._serde.serialize(
                event=event,
                stream_id=stream_id,
                name=self._event_registry.name_for_type(type(event)),
                version=version,
            )
            for version, event in enumerate(events, start=expected_stream_version + 1)
        ]
