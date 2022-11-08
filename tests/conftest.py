from typing import Any, Iterator, Protocol, Type, cast

import pytest
from _pytest.fixtures import SubRequest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from event_sourcery.event_registry import BaseEventCls, EventRegistry
from event_sourcery.event_store import EventStore
from event_sourcery.interfaces.event import Event
from event_sourcery.interfaces.outbox_storage_strategy import OutboxStorageStrategy
from event_sourcery.interfaces.storage_strategy import StorageStrategy
from event_sourcery.interfaces.subscriber import Subscriber
from event_sourcery_pydantic.event import Event as BaseEvent
from event_sourcery_pydantic.serde import PydanticSerde
from event_sourcery_sqlalchemy.sqlalchemy_event_store import SqlAlchemyStorageStrategy
from event_sourcery_sqlalchemy.sqlalchemy_outbox import SqlAlchemyOutboxStorageStrategy


class EventStoreFactoryCallable(Protocol):
    GUARD: object = object()

    def __call__(
        self,
        subscriptions: dict[Type[Event], list[Subscriber]] | None | object = GUARD,
        event_base_class: Type[BaseEventCls] | None | object = GUARD,
        event_registry: EventRegistry | None | object = GUARD,
    ) -> EventStore:
        pass


@pytest.fixture()
def event_store_factory(
    storage_strategy: StorageStrategy,
    outbox_storage_strategy: OutboxStorageStrategy,
) -> EventStoreFactoryCallable:
    defaults = dict(
        serde=PydanticSerde(),
        storage_strategy=storage_strategy,
        event_base_class=BaseEvent,
        outbox_storage_strategy=outbox_storage_strategy,
    )

    def _callable(**kwargs: Any) -> EventStore:
        arguments = defaults.copy()
        for key, value in kwargs.items():
            if value is not EventStoreFactoryCallable.GUARD:
                arguments[key] = value

        return EventStore(**arguments)  # type: ignore

    return cast(EventStoreFactoryCallable, _callable)


@pytest.fixture()
def event_store(event_store_factory: EventStoreFactoryCallable) -> EventStore:
    return event_store_factory()


class DeclarativeBase(Protocol):
    metadata: MetaData


@pytest.fixture(scope="session")
def declarative_base() -> DeclarativeBase:
    from sqlalchemy.ext.declarative import as_declarative

    from event_sourcery_sqlalchemy.models import configure_models

    @as_declarative()
    class Base:
        pass

    configure_models(Base)

    return cast(DeclarativeBase, Base)


@pytest.fixture()
def storage_strategy(session: Session) -> StorageStrategy:
    return SqlAlchemyStorageStrategy(session)


@pytest.fixture()
def outbox_storage_strategy(session: Session) -> OutboxStorageStrategy:
    return SqlAlchemyOutboxStorageStrategy(session)


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    session = Session(bind=engine)
    yield session
    session.close()


@pytest.fixture(params=["sqlite://", "postgresql://es:es@localhost/es"])
def engine(request: SubRequest, declarative_base: DeclarativeBase) -> Iterator[Engine]:
    engine = create_engine(request.param, future=True)
    try:
        declarative_base.metadata.create_all(bind=engine)
    except OperationalError:
        pytest.skip(f"{engine.url.drivername} test database not available, skipping")
    else:
        yield engine

        engine.dispose()
        declarative_base.metadata.drop_all(bind=engine)
