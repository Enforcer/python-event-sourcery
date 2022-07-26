import abc
from typing import Callable, Type

from event_sourcery.interfaces.base_event import Event
from event_sourcery.interfaces.event import Metadata
from event_sourcery.interfaces.outbox_storage_strategy import OutboxStorageStrategy
from event_sourcery.interfaces.serde import Serde


class Outbox(abc.ABC):
    CHUNK_SIZE = 100

    def __init__(
        self,
        serde: Serde,
        storage_strategy: OutboxStorageStrategy,
        event_base_class: Type[Event],
        publisher: Callable[[Metadata], None],
    ) -> None:
        self._serde = serde
        self._storage_strategy = storage_strategy
        self._event_registry = event_base_class.__registry__
        self._publisher = publisher

    def run_once(self) -> None:
        raw_event_dicts = self._storage_strategy.outbox_entries(limit=self.CHUNK_SIZE)
        for entry_id, raw_event_dict in raw_event_dicts:
            event = self._serde.deserialize(
                event=raw_event_dict,
                event_type=self._event_registry.type_for_name(raw_event_dict["name"]),
            )
            try:
                self._publisher(event)
            except Exception:
                self._storage_strategy.decrease_tries_left(entry_id)
            else:
                self._storage_strategy.remove_from_outbox(entry_id)
