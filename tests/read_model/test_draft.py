import pytest
from sqlalchemy import BigInteger, create_engine, Integer, String
from sqlalchemy.orm import mapped_column, registry, Session

from event_sourcery.event_store import (
    EventStore, Position, Recorded, StreamId,
)
from event_sourcery_sqlalchemy.guid import GUID
from tests.bdd import Given, Then, When
from tests.conftest import DeclarativeBase
from tests.factories import an_event


class AheadOfStream(Exception):
    pass


class Cursor:
    __tablename__ = "tests_projection_cursor"
    name = mapped_column(String(255), nullable=False, primary_key=True)
    position = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), nullable=True, default=None,
    )


class ReadModel:
    __tablename__ = "tests_read_model_result"
    event_id = mapped_column(GUID(), index=True, unique=True, primary_key=True)


class Projection:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def cursor(self) -> Cursor | None:
        cursor = (
            self._session.query(Cursor)
            .filter_by(name="testing projection")
            .one_or_none()
        )
        if cursor is None:
            cursor = Cursor()
            cursor.name = "testing projection"
            self._session.add(cursor)
            self._session.flush()
        return cursor

    @property
    def position(self) -> Position | None:
        return self.cursor.position

    @property
    def continue_from(self) -> Position:
        return self.cursor.position or 0

    def apply(self, event: Recorded) -> None:
        if self.position is not None and event.position <= self.position:
            raise AheadOfStream(self.position)
        row = ReadModel()
        row.event_id = event.metadata.uuid
        self.cursor.position = event.position
        self._session.add(row)
        self._session.flush()


@pytest.fixture(scope="module")
def declarative_base(declarative_base: DeclarativeBase) -> DeclarativeBase:
    register = registry(metadata=declarative_base.metadata, class_registry={})
    register.map_declaratively(Cursor)
    register.map_declaratively(ReadModel)
    return declarative_base


@pytest.fixture()
def session(declarative_base: DeclarativeBase) -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    declarative_base.metadata.create_all(bind=engine)
    return Session(bind=engine)


@pytest.fixture()
def projection(session: Session) -> Projection:
    return Projection(session)


def test_project_events(
    session: Session,
    projection: Projection,
    event_store: EventStore,
    given: Given,
    when: When,
    then: Then,
) -> None:
    subscription = event_store.subscribe_to_all(projection.continue_from)

    given.events(event1 := an_event(), event2 := an_event(), on=StreamId())
    given.events(event3 := an_event(), event4 := an_event(), on=StreamId())

    when(projection).apply(next(subscription))
    when(projection).apply(next(subscription))
    when(projection).apply(next(subscription))
    when(projection).apply(next(subscription))

    assert projection.position == event_store.position
    assert session.query(ReadModel).filter_by(event_id=event1.uuid).one()
    assert session.query(ReadModel).filter_by(event_id=event2.uuid).one()
    assert session.query(ReadModel).filter_by(event_id=event3.uuid).one()
    assert session.query(ReadModel).filter_by(event_id=event4.uuid).one()


def test_error_when_projecting_events_twice(
    session: Session,
    projection: Projection,
    event_store: EventStore,
    given: Given,
    when: When,
    then: Then,
) -> None:
    original_position = projection.continue_from
    subscription = event_store.subscribe_to_all(original_position)

    given.events(an_event(), on=StreamId())

    when(projection).apply(next(subscription))

    with pytest.raises(AheadOfStream):
        subscription = event_store.subscribe_to_all(original_position)
        when(projection).apply(next(subscription))
