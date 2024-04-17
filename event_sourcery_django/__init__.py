__all__ = [
    "DjangoStoreFactory",
]

from dataclasses import dataclass
from functools import partial
from typing import cast

from typing_extensions import Self

from event_sourcery import event_store as es
from event_sourcery.event_store import (
    Event,
    EventRegistry,
    EventStore,
    EventStoreFactory,
)
from event_sourcery.event_store.event import Serde
from event_sourcery.event_store.factory import (
    Engine,
    NoOutboxStorageStrategy,
    no_filter,
)
from event_sourcery.event_store.interfaces import (
    OutboxFiltererStrategy,
    OutboxStorageStrategy,
)
from event_sourcery.event_store.outbox import Outbox


@dataclass(repr=False)
class DjangoStoreFactory(EventStoreFactory):
    _serde: Serde = Serde(Event.__registry__)
    _outbox_strategy: OutboxStorageStrategy | None = None

    def build(self) -> Engine:
        from event_sourcery_django.event_store import DjangoStorageStrategy
        from event_sourcery_django.subscription import DjangoSubscriptionStrategy

        engine = Engine()
        engine.event_store = EventStore(
            DjangoStorageStrategy(),
            self._outbox_strategy or NoOutboxStorageStrategy(),
            DjangoSubscriptionStrategy(),
            self._serde,
        )
        engine.outbox = Outbox(
            self._outbox_strategy or NoOutboxStorageStrategy(),
            self._serde,
        )
        engine.subscriber = cast(
            es.subscription.Positioner,
            partial(
                es.subscription.Engine,
                strategy=DjangoSubscriptionStrategy(),
                serde=self._serde,
            ),
        )
        engine.serde = self._serde
        return engine

    def with_event_registry(self, event_registry: EventRegistry) -> Self:
        self._serde = Serde(event_registry)
        return self

    def with_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        from event_sourcery_django.outbox import DjangoOutboxStorageStrategy

        self._outbox_strategy = DjangoOutboxStorageStrategy(filterer)
        return self

    def without_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = None
        return self