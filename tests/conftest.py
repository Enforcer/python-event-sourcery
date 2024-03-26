from typing import Protocol, cast

import pytest
from sqlalchemy import MetaData

from event_sourcery.event_store import (
    EventStore,
    EventStoreFactory,
    InMemoryEventStoreFactory,
)
from event_sourcery.event_store.factory import Engine
from tests import bdd


class DeclarativeBase(Protocol):
    metadata: MetaData


@pytest.fixture(scope="session")
def declarative_base() -> DeclarativeBase:
    from sqlalchemy.orm import as_declarative

    from event_sourcery_sqlalchemy.models import configure_models

    @as_declarative()
    class Base:
        pass

    configure_models(Base)

    return cast(DeclarativeBase, Base)


@pytest.fixture()
def event_store_factory() -> EventStoreFactory:
    return InMemoryEventStoreFactory()


@pytest.fixture()
def engine(event_store_factory: EventStoreFactory) -> Engine:
    return event_store_factory.build()


@pytest.fixture()
def event_store(engine: Engine) -> EventStore:
    return engine.event_store


@pytest.fixture()
def given(engine: Engine) -> bdd.Given:
    return bdd.Given(engine)


@pytest.fixture()
def when(engine: Engine) -> bdd.When:
    return bdd.When(engine)


@pytest.fixture()
def then(engine: Engine) -> bdd.Then:
    return bdd.Then(engine)
