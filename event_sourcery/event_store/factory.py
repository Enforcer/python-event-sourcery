import abc
from typing import ContextManager, Iterator

from typing_extensions import Self

from event_sourcery.event_store.event import EventRegistry, RawEvent, Serde
from event_sourcery.event_store.event_store import EventStore
from event_sourcery.event_store.interfaces import (
    OutboxFiltererStrategy,
    OutboxStorageStrategy,
)
from event_sourcery.event_store.outbox import Outbox
from event_sourcery.event_store.subscription import Subscriber


def no_filter(entry: RawEvent) -> bool:
    return True


class NoOutboxStorageStrategy(OutboxStorageStrategy):
    def outbox_entries(self, limit: int) -> Iterator[ContextManager[RawEvent]]:
        return iter([])


class Engine:
    serde: Serde
    event_store: EventStore
    outbox: Outbox
    subscriber: Subscriber


class EventStoreFactory(abc.ABC):
    @abc.abstractmethod
    def build(self) -> Engine:
        pass

    @abc.abstractmethod
    def with_event_registry(self, event_registry: EventRegistry) -> Self:
        pass

    @abc.abstractmethod
    def with_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        pass

    @abc.abstractmethod
    def without_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        pass
