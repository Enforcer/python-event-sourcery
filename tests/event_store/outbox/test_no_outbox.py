import pytest

from event_sourcery.event_store import EventStore, EventStoreFactory, StreamId
from tests.event_store.outbox.conftest import PublisherMock
from tests.factories import an_event


@pytest.fixture()
def event_store(event_store_factory: EventStoreFactory) -> EventStore:
    engine = event_store_factory.without_outbox().build()
    return engine.event_store


def test_nothing_when_using_outbox_on_eventstore_without_outbox(
    publisher: PublisherMock,
    event_store: EventStore,
) -> None:
    event_store.publish(an_event(version=1), stream_id=StreamId())
    event_store.run_outbox(publisher)
    publisher.assert_not_called()
