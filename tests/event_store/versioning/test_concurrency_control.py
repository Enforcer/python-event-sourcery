from typing import cast
from uuid import uuid4

import pytest

from event_sourcery import AUTO_VERSION
from event_sourcery.event_store import EventStore
from event_sourcery.exceptions import ConcurrentStreamWriteError
from tests.events import SomeEvent


def test_concurrency_error(event_store: EventStore) -> None:
    stream_id = uuid4()
    event = SomeEvent(first_name="Test")

    with pytest.raises(ConcurrentStreamWriteError):
        event_store.append(stream_id=stream_id, events=[event], expected_version=10)


def test_does_not_raise_concurrency_error_if_no_one_bumped_up_version(
    event_store: EventStore,
) -> None:
    stream_id = uuid4()
    event = SomeEvent(first_name="Test")
    event_store.append(
        stream_id=stream_id, events=[event], expected_version=AUTO_VERSION
    )
    events = event_store.load_stream(stream_id=stream_id)
    another_event = SomeEvent(first_name="TestTwo")
    try:
        event_store.append(
            stream_id=stream_id,
            events=[another_event],
            expected_version=cast(int, events[-1].version),
        )
    except ConcurrentStreamWriteError:
        pytest.fail("Should NOT raise an exception!")
