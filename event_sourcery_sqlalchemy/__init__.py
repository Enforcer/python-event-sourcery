__all__ = [
    "configure_models",
    "models",
    "SqlAlchemyStorageStrategy",
    "SQLStoreFactory",
    "SQLEngine",
]

from dataclasses import dataclass
from functools import partial
from typing import Type, cast

from sqlalchemy.orm import Session
from typing_extensions import Self

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
from event_sourcery.event_store.interfaces import OutboxFiltererStrategy
from event_sourcery.event_store.outbox import Outbox
from event_sourcery.event_store.subscription import Subscriber, SubscriberEngine
from event_sourcery_sqlalchemy import models
from event_sourcery_sqlalchemy.event_store import SqlAlchemyStorageStrategy
from event_sourcery_sqlalchemy.models import configure_models
from event_sourcery_sqlalchemy.outbox import SqlAlchemyOutboxStorageStrategy
from event_sourcery_sqlalchemy.subscription import (
    InTransactionSubscription,
    SqlAlchemySubscriptionStrategy,
)


class SQLEngine(Engine):
    def subscribe_in_transaction(self) -> InTransactionSubscription:
        return InTransactionSubscription(self.serde)


@dataclass(repr=False)
class SQLStoreFactory(EventStoreFactory):
    session: Session
    _serde: Serde = Serde(Event.__registry__)
    _outbox_strategy: SqlAlchemyOutboxStorageStrategy | None = None

    def build(self) -> SQLEngine:
        engine = SQLEngine()
        engine.event_store = EventStore(
            SqlAlchemyStorageStrategy(self.session, self._outbox_strategy),
            self._outbox_strategy or NoOutboxStorageStrategy(),
            SqlAlchemySubscriptionStrategy(),
            self._serde,
        )
        engine.outbox = Outbox(
            self._outbox_strategy or NoOutboxStorageStrategy(),
            self._serde,
        )
        engine.subscriber = cast(
            Type[Subscriber],
            partial(
                SubscriberEngine,
                strategy=SqlAlchemySubscriptionStrategy(),
                serde=self._serde,
            ),
        )
        engine.serde = self._serde
        return engine

    def with_event_registry(self, event_registry: EventRegistry) -> Self:
        self._serde = Serde(event_registry)
        return self

    def with_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = SqlAlchemyOutboxStorageStrategy(
            self.session,
            filterer,
        )
        return self

    def without_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = None
        return self
