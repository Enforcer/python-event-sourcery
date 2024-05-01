__all__ = [
    "Config",
    "configure_models",
    "models",
    "SqlAlchemyStorageStrategy",
    "SQLAlchemyBackendFactory",
]

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, PositiveInt
from sqlalchemy.orm import Session
from typing_extensions import Self

from event_sourcery import event_store as es
from event_sourcery.event_store import (
    Backend,
    BackendFactory,
    Event,
    EventRegistry,
    EventStore,
)
from event_sourcery.event_store.event import Serde
from event_sourcery.event_store.factory import NoOutboxStorageStrategy, no_filter
from event_sourcery.event_store.interfaces import OutboxFiltererStrategy
from event_sourcery.event_store.outbox import Outbox
from event_sourcery_sqlalchemy import models
from event_sourcery_sqlalchemy.event_store import SqlAlchemyStorageStrategy
from event_sourcery_sqlalchemy.models import configure_models
from event_sourcery_sqlalchemy.outbox import SqlAlchemyOutboxStorageStrategy
from event_sourcery_sqlalchemy.subscription import (
    InTransactionSubscription,
    SqlAlchemySubscriptionStrategy,
)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outbox_attempts: PositiveInt = 3


@dataclass(repr=False)
class SQLAlchemyBackendFactory(BackendFactory):
    _session: Session
    _config: Config = Config()
    _serde: Serde = Serde(Event.__registry__)
    _outbox_strategy: SqlAlchemyOutboxStorageStrategy | None = None

    def build(self) -> Backend:
        backend = Backend()
        backend.event_store = EventStore(
            SqlAlchemyStorageStrategy(self._session, self._outbox_strategy),
            self._serde,
        )
        backend.outbox = Outbox(
            self._outbox_strategy or NoOutboxStorageStrategy(),
            self._serde,
        )
        backend.subscriber = es.subscription.SubscriptionBuilder(
            _serde=self._serde,
            _strategy=SqlAlchemySubscriptionStrategy(),
            in_transaction=InTransactionSubscription(self._serde),
        )
        backend.serde = self._serde
        return backend

    def with_event_registry(self, event_registry: EventRegistry) -> Self:
        self._serde = Serde(event_registry)
        return self

    def with_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = SqlAlchemyOutboxStorageStrategy(
            self._session,
            filterer,
            self._config.outbox_attempts,
        )
        return self

    def without_outbox(self, filterer: OutboxFiltererStrategy = no_filter) -> Self:
        self._outbox_strategy = None
        return self
