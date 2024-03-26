import logging
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import islice
from typing import ContextManager, Generator, Iterator

from esdbclient import EventStoreDBClient, RecordedEvent
from esdbclient.exceptions import DeadlineExceeded, NotFound
from esdbclient.persistent import PersistentSubscription

from event_sourcery.event_store import RawEvent
from event_sourcery.event_store.interfaces import (
    OutboxFiltererStrategy,
    OutboxStorageStrategy,
)
from event_sourcery_esdb import dto

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class ESDBOutboxStorageStrategy(OutboxStorageStrategy):
    OUTBOX_NAME = "outbox"
    MAX_PUBLISH_ATTEMPTS = 3
    _client: EventStoreDBClient
    _filterer: OutboxFiltererStrategy
    _active_subscription: PersistentSubscription | None = None

    def create_subscription(self) -> None:
        try:
            self._client.get_subscription_info(self.OUTBOX_NAME)
        except NotFound:
            self._client.create_subscription_to_all(
                self.OUTBOX_NAME,
                from_end=True,
            )

    @contextmanager
    def _context(
        self,
        limit: int | None = None,
    ) -> Generator[Iterator[RecordedEvent], None, None]:
        self._active_subscription = self._client.read_subscription_to_all(
            self.OUTBOX_NAME,
            timeout=10,
        )
        yield islice(self._active_subscription, limit or 100)
        self._active_subscription.stop()
        self._active_subscription = None

    @property
    def active_subscription(self) -> PersistentSubscription:
        assert self._active_subscription is not None
        return self._active_subscription

    def outbox_entries(self, limit: int) -> Iterator[ContextManager[RawEvent]]:
        info = self._client.get_subscription_info(self.OUTBOX_NAME)
        if info.live_buffer_count == 0:
            return

        with self._context(limit) as subscription:
            try:
                for entry in subscription:
                    if self._filterer(event := dto.raw_event(entry)):
                        yield self._publish_context(entry, event)
            except DeadlineExceeded:
                pass

    @contextmanager
    def _publish_context(
        self,
        entry: RecordedEvent,
        event: RawEvent,
    ) -> Generator[RawEvent, None, None]:
        try:
            yield event
        except Exception:
            logger.exception("Failed to publish message #%d", entry.id)
            failure_count = (entry.retry_count or 0) + 1
            if self._reached_max_number_of_attempts(failure_count):
                self.active_subscription.nack(entry.id, action="park")
            else:
                self.active_subscription.nack(entry.id, action="retry")
        else:
            self.active_subscription.ack(entry.id)

    def _reached_max_number_of_attempts(self, failure_count: int) -> bool:
        return failure_count >= self.MAX_PUBLISH_ATTEMPTS
