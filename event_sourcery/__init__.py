__all__ = [
    "configure_models",
    "get_event_store",
    "Event",
    "get_outbox",
    "Repository",
    "Aggregate",
    "AUTO_VERSION",
    "ANY_VERSION",
]

from typing import Callable, Type

from sqlalchemy.orm import Session

from event_sourcery.aggregate import Aggregate
from event_sourcery.dummy_outbox_storage_strategy import DummyOutboxStorageStrategy
from event_sourcery.event_store import EventStore
from event_sourcery.interfaces.event import Event as EventProtocol
from event_sourcery.interfaces.outbox_storage_strategy import OutboxStorageStrategy
from event_sourcery.interfaces.subscriber import Subscriber
from event_sourcery.outbox import Outbox
from event_sourcery.repository import Repository
from event_sourcery.versioning import ANY_VERSION, AUTO_VERSION
from event_sourcery_pydantic.event import Event
from event_sourcery_pydantic.serde import PydanticSerde
from event_sourcery_sqlalchemy.models import configure_models
from event_sourcery_sqlalchemy.sqlalchemy_event_store import SqlAlchemyStorageStrategy
from event_sourcery_sqlalchemy.sqlalchemy_outbox import SqlAlchemyOutboxStorageStrategy


def get_event_store(
    session: Session,
    subscriptions: dict[Type[EventProtocol], list[Subscriber]] | None = None,
    with_outbox: bool = True,
) -> EventStore:
    outbox_storage: OutboxStorageStrategy
    if with_outbox:
        outbox_storage = SqlAlchemyOutboxStorageStrategy(session)
    else:
        outbox_storage = DummyOutboxStorageStrategy()

    return EventStore(
        serde=PydanticSerde(),
        storage_strategy=SqlAlchemyStorageStrategy(session),
        outbox_storage_strategy=outbox_storage,
        event_base_class=Event,
        subscriptions=subscriptions,
    )


def get_outbox(session: Session, publisher: Callable[[EventProtocol], None]) -> Outbox:
    return Outbox(
        serde=PydanticSerde(),
        storage_strategy=SqlAlchemyOutboxStorageStrategy(session),
        event_base_class=Event,
        publisher=publisher,
    )
