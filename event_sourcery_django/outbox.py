import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import ContextManager, Iterator, cast
from uuid import UUID

from event_sourcery.event_store import RawEvent, StreamId
from event_sourcery.event_store.interfaces import (
    OutboxFiltererStrategy,
    OutboxStorageStrategy,
)
from event_sourcery_django.models import OutboxEntry

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class DjangoOutboxStorageStrategy(OutboxStorageStrategy):
    _filterer: OutboxFiltererStrategy

    def put_into_outbox(self, events: list[RawEvent]) -> None:
        def entry_from_event(event: RawEvent) -> OutboxEntry:
            as_dict = dict(event)
            created_at = cast(datetime, as_dict["created_at"])
            as_dict["created_at"] = created_at.isoformat()
            as_dict["uuid"] = str(as_dict["uuid"])
            as_dict["stream_id"] = str(as_dict["stream_id"])
            return OutboxEntry(
                created_at=datetime.utcnow(),
                data=as_dict,
                stream_name=event.stream_id.name,
            )

        OutboxEntry.objects.bulk_create(
            entry_from_event(event) for event in events if self._filterer(event)
        )

    def outbox_entries(self, limit: int) -> Iterator[ContextManager[RawEvent]]:
        entries = (
            OutboxEntry.objects.select_for_update(skip_locked=True)
            .filter(
                tries_left__gt=0,
            )
            .order_by("id")[:limit]
        )

        for entry in entries:
            yield self._publish_context(entry)

    @contextmanager
    def _publish_context(self, entry: OutboxEntry) -> Iterator[RawEvent]:
        raw = RawEvent(
            uuid=UUID(entry.data["uuid"]),
            stream_id=StreamId(
                from_hex=entry.data["stream_id"],
                name=entry.stream_name,
            ),
            created_at=datetime.fromisoformat(entry.data["created_at"]),
            version=entry.data["version"],
            name=entry.data["name"],
            data=entry.data["data"],
            context=entry.data["context"],
        )
        try:
            yield raw
        except Exception:
            logger.exception("Failed to publish message #%d", entry.id)
            entry.tries_left -= 1
            entry.save()
        else:
            entry.delete()
