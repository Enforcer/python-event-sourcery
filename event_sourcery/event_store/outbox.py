from typing import Callable

from event_sourcery.event_store.event import Metadata, Serde
from event_sourcery.event_store.interfaces import OutboxStorageStrategy
from event_sourcery.event_store.stream_id import StreamId


class Outbox:
    def __init__(self, strategy: OutboxStorageStrategy, serde: Serde) -> None:
        self._strategy = strategy
        self._serde = serde

    def run_outbox(
        self,
        publisher: Callable[[Metadata, StreamId], None],
        limit: int = 100,
    ) -> None:
        stream = self._strategy.outbox_entries(limit=limit)
        for entry in stream:
            with entry as raw_event_dict:
                event = self._serde.deserialize(raw_event_dict)
                publisher(event, raw_event_dict.stream_id)
