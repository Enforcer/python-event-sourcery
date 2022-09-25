from uuid import uuid4

from event_sourcery import AUTO_VERSION, EventStore
from tests.events import SomeEventFactory


def test_auto_versioning_adds_versions_to_events(event_store: EventStore) -> None:
    stream_id = uuid4()
    event_store.append(
        SomeEventFactory.build_batch(size=2),
        stream_id=stream_id,
        expected_version=AUTO_VERSION,
    )
    event_store.append(
        SomeEventFactory.build_batch(size=3),
        stream_id=stream_id,
        expected_version=AUTO_VERSION,
    )
    event_store.append(
        SomeEventFactory.build_batch(size=2),
        stream_id=stream_id,
        expected_version=AUTO_VERSION,
    )

    read_events = event_store.load_stream(stream_id=stream_id)
    versions = [event.version for event in read_events]

    assert versions == [1, 2, 3, 4, 5, 6, 7]
