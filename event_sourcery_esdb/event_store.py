from dataclasses import dataclass
from typing import cast

from esdbclient import EventStoreDBClient, StreamState
from esdbclient.exceptions import NotFound

from event_sourcery.event_store import (
    NO_VERSIONING,
    Position,
    RawEvent,
    StreamId,
    Versioning,
)
from event_sourcery.event_store.exceptions import ConcurrentStreamWriteError
from event_sourcery.event_store.interfaces import StorageStrategy
from event_sourcery_esdb import dto, stream


@dataclass(repr=False)
class ESDBStorageStrategy(StorageStrategy):
    _client: EventStoreDBClient

    def fetch_events(
        self,
        stream_id: StreamId,
        start: int | None = None,
        stop: int | None = None,
    ) -> list[RawEvent]:
        snapshot = None
        name = stream.Name(stream_id)
        if start is None and (snapshot := self._read_snapshot(name)) is not None:
            start = cast(int, snapshot.version) + 1

        position, limit = stream.scope(start, stop)
        entries = self._client.read_stream(
            stream_name=str(name),
            stream_position=position,
            limit=limit,
        )
        try:
            events = [dto.raw_event(entry) for entry in entries]
            if snapshot:
                return [snapshot] + events
            return events
        except NotFound:
            return []

    def _read_snapshot(self, name: stream.Name) -> RawEvent | None:
        snapshots = self._client.read_stream(
            name.snapshot,
            limit=1,
            backwards=True,
        )
        try:
            last = next(iter(snapshots))
            return dto.snapshot(last)
        except NotFound:
            return None

    def insert_events(
        self, stream_id: StreamId, versioning: Versioning, events: list[RawEvent]
    ) -> None:
        self._ensure_stream(stream_id=stream_id, versioning=versioning)
        for stream_id in {e.stream_id for e in events}:
            stream_name = stream.Name(stream_id)
            stream_events = [e for e in events if e.stream_id == stream_id]
            self._append_events(stream_name, events=stream_events)

    def _append_events(self, name: stream.Name, events: list[RawEvent]) -> int:
        assert all(e.stream_id == name.uuid for e in events)
        return self._client.append_events(
            str(name),
            current_version=StreamState.ANY,
            events=(dto.new_entry(e) for e in events),
        )

    def save_snapshot(self, snapshot: RawEvent) -> None:
        name = stream.Name(snapshot.stream_id)
        stream_position = stream.Position.from_version(cast(int, snapshot.version))
        self._client.append_events(
            name.snapshot,
            current_version=StreamState.ANY,
            events=[dto.new_entry(snapshot, stream_position=stream_position)],
        )

    def _ensure_stream(self, stream_id: StreamId, versioning: Versioning) -> None:
        name = stream.Name(stream_id)

        if versioning is not NO_VERSIONING and versioning.expected_version:
            expected = stream.Position.from_version(versioning.expected_version)
            if position := self._get_stream_position(name) != expected:
                raise ConcurrentStreamWriteError(position, expected)

    def _get_stream_position(self, name: stream.Name) -> stream.Position | None:
        try:
            last = next(
                iter(self._client.get_stream(str(name), backwards=True, limit=1))
            )
            return stream.Position(last.stream_position)
        except NotFound:
            return None

    def delete_stream(self, stream_id: StreamId) -> None:
        name = stream.Name(stream_id)
        try:
            self._client.delete_stream(str(name), current_version=StreamState.ANY)
        except NotFound:
            pass

    @property
    def current_position(self) -> Position | None:
        return Position(self._client.get_commit_position())
