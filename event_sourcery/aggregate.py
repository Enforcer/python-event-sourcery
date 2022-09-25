from contextlib import contextmanager
from typing import Any, Iterator, Type, cast

from event_sourcery.interfaces.event import Event


class Aggregate:
    def __init__(self) -> None:
        self.__version = 0
        self.__changes: list[Event] = []

    def __rehydrate__(self, event: Event) -> None:
        self._apply(event)
        self.__version = cast(int, event.version)

    @contextmanager
    def __persisting_changes__(self) -> Iterator[Iterator[Event]]:
        yield iter(self.__changes)
        self.__version = cast(int, self.__changes[-1].version)
        self.__changes = []

    @property
    def __version__(self) -> int:
        return self.__version

    def _apply(self, event: Event) -> None:
        raise NotImplementedError()

    def _event(self, event_cls: Type[Event], **kwargs: Any) -> None:
        if self.__changes:
            next_version = cast(int, self.__changes[-1].version) + 1
        else:
            next_version = self.__version + 1

        event = event_cls(version=next_version, **kwargs)
        self._apply(event)
        self.__changes.append(event)
