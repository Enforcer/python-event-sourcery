from uuid import uuid4

import pytest

from event_sourcery import AUTO_VERSION
from event_sourcery.event_store import EventStore
from event_sourcery.exceptions import (
    CannotUseAnyVersioningForStreamCreatedWithOtherVersioning,
    CannotUseAutoVersioningForStreamCreatedWithAnyVersioning,
    CannotUseExpectedVersionForStreamCreatedWithAnyVersioning,
)
from tests.events import SomeEventFactory


def test_does_not_allow_mixing_non_versioned_stream_with_explicitly_versioned(
    event_store: EventStore,
) -> None:
    stream_id = uuid4()
    event_store.append([SomeEventFactory()], stream_id=stream_id)

    with pytest.raises(CannotUseExpectedVersionForStreamCreatedWithAnyVersioning):
        event_store.append(
            [SomeEventFactory()], stream_id=stream_id, expected_version=1
        )


def test_does_not_allow_mixing_non_versioned_stream_with_auto_versioned(
    event_store: EventStore,
) -> None:
    stream_id = uuid4()
    event_store.append([SomeEventFactory()], stream_id=stream_id)

    with pytest.raises(CannotUseAutoVersioningForStreamCreatedWithAnyVersioning):
        event_store.append(
            [SomeEventFactory()], stream_id=stream_id, expected_version=AUTO_VERSION
        )


def test_does_not_allow_mixing_auto_versioned_stream_with_non_versioned(
    event_store: EventStore,
) -> None:
    stream_id = uuid4()
    event = SomeEventFactory()
    event_store.append([event], stream_id=stream_id, expected_version=AUTO_VERSION)

    with pytest.raises(CannotUseAnyVersioningForStreamCreatedWithOtherVersioning):
        event_store.append([SomeEventFactory()], stream_id=stream_id)


def test_allows_mixing_auto_and_explicit_versioning(event_store: EventStore) -> None:
    stream_id = uuid4()
    event_store.append(
        [SomeEventFactory()], stream_id=stream_id, expected_version=AUTO_VERSION
    )
    event_store.append([SomeEventFactory()], stream_id=stream_id, expected_version=1)
    event_store.append(
        [SomeEventFactory()], stream_id=stream_id, expected_version=AUTO_VERSION
    )
    event_store.append([SomeEventFactory()], stream_id=stream_id, expected_version=3)

    events = event_store.load_stream(stream_id=stream_id)

    assert len(events) == 4
    assert [event.version for event in events] == [1, 2, 3, 4]
