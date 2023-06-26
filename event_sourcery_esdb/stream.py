import sys
from collections import UserString
from typing import Tuple, cast

from event_sourcery.types import StreamId


class Name(UserString):
    uuid: StreamId

    def __init__(
        self,
        stream_id: StreamId | None = None,
        stream_name: str | None = None,
    ) -> None:
        if stream_id is None and stream_name is None:
            raise ValueError

        self.uuid = stream_id or self._get_id(stream_name or "")
        super().__init__(self.uuid.hex)

    @staticmethod
    def _get_id(from_name: str) -> StreamId:
        if from_name.endswith("-snapshot"):
            from_name, _ = from_name.rsplit("-", 1)
        return StreamId(from_hex=from_name)

    @property
    def metadata(self) -> str:
        return f"$${self!s}"

    @property
    def snapshot(self) -> str:
        return f"{self!s}-snapshot"


class Position(int):
    def __new__(cls, value: int | str | None) -> "Position | None":  # type: ignore
        if value is None:
            return None
        return super().__new__(Position, value)

    @classmethod
    def as_previous(cls, to_version: int) -> "Position | None":
        previous_version = to_version - 1
        return cls.from_version(previous_version)

    @classmethod
    def from_version(cls, version: int) -> "Position | None":
        assert version >= 0
        if version == 0:
            return None
        return Position(version - 1)

    def as_version(self) -> int:
        return self + 1


MAX_POSITION = Position(sys.maxsize)


def scope(
    start_version: int | None,
    stop_version: int | None,
) -> Tuple[Position | None, int]:
    start = cast(
        Position | None, start_version and Position.from_version(start_version)
    )
    stop = stop_version and Position.from_version(stop_version) or MAX_POSITION
    return start, stop - (start or 0)