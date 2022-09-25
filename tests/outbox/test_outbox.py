from unittest.mock import Mock
from uuid import uuid4

import pytest

from event_sourcery.event_store import EventStore
from event_sourcery.interfaces.outbox_storage_strategy import OutboxStorageStrategy
from event_sourcery.outbox import Outbox
from event_sourcery_pydantic.event import Event
from event_sourcery_pydantic.serde import PydanticSerde
from tests.events import SomeEvent


@pytest.fixture()
def publisher() -> Mock:
    return Mock()


@pytest.fixture()
def outbox(outbox_storage_strategy: OutboxStorageStrategy, publisher: Mock) -> Outbox:
    return Outbox(
        serde=PydanticSerde(),
        storage_strategy=outbox_storage_strategy,
        event_base_class=Event,
        publisher=publisher,
    )


def test_calls_publisher(
    outbox: Outbox, publisher: Mock, event_store: EventStore
) -> None:
    an_event = SomeEvent(first_name="John")
    event_store.publish(stream_id=uuid4(), events=[an_event])

    outbox.run_once()

    publisher.assert_called_once_with(an_event)


def test_sends_only_once_in_case_of_success(
    outbox: Outbox, publisher: Mock, event_store: EventStore
) -> None:
    an_event = SomeEvent(first_name="John")
    event_store.publish(stream_id=uuid4(), events=[an_event])

    for _ in range(2):
        outbox.run_once()

    publisher.assert_called_once_with(an_event)


def test_tries_to_send_up_to_three_times(
    outbox: Outbox, publisher: Mock, event_store: EventStore
) -> None:
    an_event = SomeEvent(first_name="John")
    event_store.publish(stream_id=uuid4(), events=[an_event])
    publisher.side_effect = ValueError

    for _ in range(4):
        outbox.run_once()

    assert len(publisher.mock_calls) == 3
