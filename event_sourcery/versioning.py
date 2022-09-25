import abc
import itertools
from typing import Iterator, cast


class Versioning:
    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return f"<Versioning {self._name}>"


AUTO_VERSION = Versioning("AUTO_VERSION")
ANY_VERSION = Versioning("ANY_VERSION")


class VersioningStrategy(abc.ABC):
    @property
    @abc.abstractmethod
    def version_for_new_stream(self) -> int | None:
        pass

    @property
    @abc.abstractmethod
    def expected_version(self) -> int | None:
        pass

    @abc.abstractmethod
    def versions(self, stream_version: int | None) -> Iterator[int | None]:
        pass

    @property
    @abc.abstractmethod
    def stream_version_increase(self) -> int | None:
        pass


class ExplicitVersioning(VersioningStrategy):
    def __init__(self, expected_version: int, events_to_append: int) -> None:
        self._expected_version = expected_version
        self._events_to_append = events_to_append

    @property
    def version_for_new_stream(self) -> int | None:
        return 1

    @property
    def expected_version(self) -> int | None:
        return self._expected_version

    def versions(self, stream_version: int | None) -> Iterator[int | None]:
        return iter(
            range(
                self._expected_version + 1,
                self._expected_version + 1 + self._events_to_append,
            )
        )

    @property
    def stream_version_increase(self) -> int | None:
        return self._events_to_append


class AutoVersioning(VersioningStrategy):
    def __init__(self, events_to_append: int) -> None:
        self._events_to_append = events_to_append
        self._stream_version: int | None = None

    @property
    def version_for_new_stream(self) -> int | None:
        return 1

    @property
    def expected_version(self) -> int | None:
        return self._stream_version

    def versions(self, stream_version: int | None) -> Iterator[int | None]:
        # in auto versioning this won't be None
        self._stream_version = cast(int, stream_version)

        if self._stream_version == 1:
            start = 1
        else:
            start = self._stream_version + 1

        return iter(range(start, start + self._events_to_append))

    @property
    def stream_version_increase(self) -> int | None:
        if self._stream_version == 1:
            return self._events_to_append - 1
        else:
            return self._events_to_append


class NoVersioning(VersioningStrategy):
    @property
    def version_for_new_stream(self) -> int | None:
        return None

    @property
    def expected_version(self) -> int | None:
        return None

    def versions(self, stream_version: int | None) -> Iterator[int | None]:
        return itertools.cycle([None])

    @property
    def stream_version_increase(self) -> int | None:
        return None


def build_versioning_strategy(
    expected_version: int | Versioning, events_to_append: int
) -> VersioningStrategy:
    if expected_version is ANY_VERSION:
        return NoVersioning()
    elif expected_version is AUTO_VERSION:
        return AutoVersioning(events_to_append)
    elif isinstance(expected_version, int):
        return ExplicitVersioning(expected_version, events_to_append)
    else:
        raise NotImplementedError(
            f"This versioning ({expected_version}) is not supported"
        )
