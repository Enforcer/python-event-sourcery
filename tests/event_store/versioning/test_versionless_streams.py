from uuid import uuid4

from event_sourcery.event_store import EventStore
from tests.events import SomeEventFactory


def test_can_append_events_to_stream_without_notion_of_versioning(
    event_store: EventStore,
) -> None:
    stream_id = uuid4()
    events = [
        SomeEventFactory(),
        SomeEventFactory(),
    ]

    event_store.append([events[0]], stream_id=stream_id)
    event_store.append([events[1]], stream_id=stream_id)

    read_events = event_store.load_stream(stream_id=stream_id)
    assert read_events == events
