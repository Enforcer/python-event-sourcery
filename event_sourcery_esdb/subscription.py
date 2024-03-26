from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import Callable, Iterator

import esdbclient.exceptions
from esdbclient import EventStoreDBClient, RecordedEvent

from event_sourcery.event_store import Position, RecordedRaw
from event_sourcery.event_store.interfaces import SubscriptionStrategy
from event_sourcery_esdb import dto


@dataclass(repr=False)
class ESDBSubscriptionStrategy(SubscriptionStrategy):
    _client: EventStoreDBClient

    @staticmethod
    def _iterator(
        builder: Callable[[], Iterator[RecordedEvent]],
        size: int,
    ) -> Iterator[list[RecordedRaw]]:
        subscription = builder()
        batch = []
        while True:
            try:
                raw = dto.raw_record(next(subscription))
                builder = partial(builder, commit_position=raw.position)
                batch.append(raw)
                if len(batch) == size:
                    yield batch
                    batch = []
            except esdbclient.exceptions.DeadlineExceeded:
                yield batch
                batch = []
                subscription = builder()

    def subscribe_to_all(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
    ) -> Iterator[list[RecordedRaw]]:
        builder = partial(
            self._client.subscribe_to_all,
            commit_position=start_from,
            timeout=timelimit.total_seconds(),
        )
        return self._iterator(builder, batch_size)

    def subscribe_to_category(
        self,
        start_from: Position | None,
        batch_size: int,
        timelimit: timedelta,
        category: str,
    ) -> Iterator[list[RecordedRaw]]:
        builder = partial(
            self._client.subscribe_to_all,
            commit_position=start_from,
            timeout=timelimit.total_seconds(),
            filter_include=[
                f"{category}-\\w+",
            ],
            filter_by_stream_name=True,
        )
        return self._iterator(builder, batch_size)

    def subscribe_to_events(
        self,
        start_from: Position,
        batch_size: int,
        timelimit: timedelta,
        events: list[str],
    ) -> Iterator[list[RecordedRaw]]:
        builder = partial(
            self._client.subscribe_to_all,
            commit_position=start_from,
            timeout=timelimit.total_seconds(),
            filter_include=events,
            filter_by_stream_name=False,
        )
        return self._iterator(builder, batch_size)
