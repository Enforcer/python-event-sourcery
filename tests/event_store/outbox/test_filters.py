from uuid import uuid4

import pytest

from event_sourcery.event_store import EventStore, EventStoreFactory, StreamId
from event_sourcery.event_store.interfaces import OutboxFiltererStrategy
from tests.event_store.outbox.conftest import PublisherMock
from tests.factories import an_event


@pytest.fixture()
def filter_everything() -> OutboxFiltererStrategy:
    return lambda event: False


@pytest.fixture()
def event_store(
    filter_everything: OutboxFiltererStrategy,
    event_store_factory: EventStoreFactory,
) -> EventStore:
    engine = event_store_factory.with_outbox(filterer=filter_everything).build()
    return engine.event_store


def test_no_entries_when_everything_was_filtered(
    publisher: PublisherMock,
    event_store: EventStore,
) -> None:
    event_store.publish(an_event(version=1), stream_id=StreamId(uuid4()))
    event_store.run_outbox(publisher)
    publisher.assert_not_called()
