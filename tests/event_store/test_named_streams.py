from uuid import uuid4

import pytest

from event_sourcery.event_store import EventStore
from event_sourcery.exceptions import (
    AnotherStreamWithThisNameButOtherIdExists,
    EitherStreamIdOrStreamNameIsRequired,
)
from tests.events import SomeEvent


def test_can_append_then_load_with_named_stream(event_store: EventStore) -> None:
    an_event = SomeEvent(first_name="Dziabong")
    event_store.append(stream_name="Test #1", events=[an_event])

    events = event_store.load_stream(stream_name="Test #1")

    assert events == [an_event]


@pytest.mark.skip("Hard to say how .iter api should change")
def test_can_iter_over_named_stream(event_store: EventStore) -> None:
    an_event = SomeEvent(first_name="Ciapong")
    event_store.append(stream_name="Test #2", events=[an_event])

    list(event_store.iter())


def test_can_append_then_load_with_named_stream_with_assigned_uuid(
    event_store: EventStore,
) -> None:
    an_event = SomeEvent(first_name="Brzdeng")
    stream_id = uuid4()
    event_store.append(stream_id=stream_id, stream_name="Test #3", events=[an_event])

    events_by_stream_id = event_store.load_stream(stream_id=stream_id)
    events_by_stream_name = event_store.load_stream(stream_name="Test #3")

    assert events_by_stream_id == events_by_stream_name == [an_event]


def test_lets_appending_by_both_id_and_name_then_just_name(
    event_store: EventStore,
) -> None:
    an_event = SomeEvent(first_name="Cing")
    stream_id = uuid4()
    event_store.append(stream_id=stream_id, stream_name="Test #4", events=[an_event])
    another_event = SomeEvent(first_name="Ciang")
    event_store.append(stream_name="Test #4", events=[another_event])

    events_by_stream_id = event_store.load_stream(stream_id=stream_id)
    events_by_stream_name = event_store.load_stream(stream_name="Test #4")

    assert (
        events_by_stream_id
        == events_by_stream_name
        == [
            an_event,
            another_event,
        ]
    )


def test_does_not_allow_to_steal_name_for_other_stream_id(
    event_store: EventStore,
) -> None:
    an_event = SomeEvent(first_name="Ciong")
    stream_id = uuid4()
    event_store.append(stream_id=stream_id, stream_name="Test #5", events=[an_event])
    another_event = SomeEvent(first_name="Ciong 2")
    another_stream_id = uuid4()

    with pytest.raises(AnotherStreamWithThisNameButOtherIdExists):
        event_store.append(
            stream_id=another_stream_id,
            stream_name="Test #5",
            events=[another_event],
            expected_version=1,
        )


def test_raises_exception_if_name_nor_id_given(event_store: EventStore) -> None:
    an_event = SomeEvent(first_name="Ciang 2")

    with pytest.raises(EitherStreamIdOrStreamNameIsRequired):
        event_store.append(events=[an_event])
