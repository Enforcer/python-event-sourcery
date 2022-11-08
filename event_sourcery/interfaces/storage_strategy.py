import abc
from typing import Callable, Iterator

from event_sourcery.dto.raw_event_dict import RawEventDict
from event_sourcery.types.stream_id import StreamId


class StorageStrategy(abc.ABC):
    @abc.abstractmethod
    def fetch_events(
        self,
        stream_id: StreamId | None,
        stream_name: str | None,
        start: int | None = None,
        stop: int | None = None,
    ) -> list[RawEventDict]:
        pass

    @abc.abstractmethod
    def iter(self, *stream_ids: StreamId) -> Iterator[RawEventDict]:
        pass

    @abc.abstractmethod
    def insert_events(self, events: list[RawEventDict]) -> None:
        pass

    @abc.abstractmethod
    def save_snapshot(self, snapshot: RawEventDict) -> None:
        pass

    @abc.abstractmethod
    def ensure_stream(
        self, stream_id: StreamId | None, stream_name: str | None, expected_version: int
    ) -> StreamId:
        pass

    @abc.abstractmethod
    def delete_stream(self, stream_id: StreamId) -> None:
        pass

    @abc.abstractmethod
    def run_after_commit(self, callback: Callable[[], None]) -> None:
        pass
