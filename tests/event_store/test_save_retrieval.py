from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from event_sourcery.event_store import EventStore
from event_sourcery.exceptions import NoEventsToAppend
from tests.events import NastyEventWithJsonUnfriendlyTypes, SomeEvent


def test_save_retrieve(event_store: EventStore) -> None:
    stream_uuid = uuid4()
    events = [SomeEvent(first_name="Test")]
    event_store.append(stream_id=stream_uuid, events=events)
    loaded_events = event_store.load_stream(stream_uuid)

    assert loaded_events == events


def test_save_retrieve_part_of_stream(event_store: EventStore) -> None:
    stream_uuid = uuid4()
    events = [
        SomeEvent(first_name="Testing", version=1),
        SomeEvent(first_name="is", version=2),
        SomeEvent(first_name="a", version=3),
        SomeEvent(first_name="good", version=4),
        SomeEvent(first_name="thing", version=5),
    ]
    event_store.append(stream_id=stream_uuid, events=events)
    loaded_events = event_store.load_stream(stream_uuid, start=2, stop=5)

    assert loaded_events == events[1:4]


def test_loading_not_existing_stream_returns_empty_list(
    event_store: EventStore,
) -> None:
    assert event_store.load_stream(stream_id=uuid4()) == []


def test_stores_retrieves_metadata(event_store: EventStore) -> None:
    an_event = SomeEvent(
        first_name="Luke", metadata={"correlation_id": uuid4(), "ip": "127.0.0.1"}
    )
    stream_id = uuid4()

    event_store.append(stream_id=stream_id, events=[an_event])
    events = event_store.load_stream(stream_id=stream_id)

    assert events == [an_event]


def test_is_able_to_handle_non_trivial_formats(event_store: EventStore) -> None:
    an_event = NastyEventWithJsonUnfriendlyTypes(
        uuid=uuid4(),
        a_datetime=datetime.now(tz=timezone.utc),
        second_datetime=datetime.utcnow(),
        a_date=date.today(),
    )
    stream_id = uuid4()

    event_store.append(stream_id=stream_id, events=[an_event])
    events = event_store.load_stream(stream_id=stream_id)

    assert events == [an_event]


def test_raises_exception_for_empty_stream(event_store: EventStore) -> None:
    with pytest.raises(NoEventsToAppend):
        event_store.append(stream_id=uuid4(), events=[])
