from dataclasses import dataclass
from typing import Type

from event_sourcery.event_store import Event, Position
from event_sourcery.event_store.event_store import Category


@dataclass(frozen=True)
class Subscription:
    start_from: Position
    to_events: list[Type[Event]] | None = None
    to_category: Category | None = None

    def __post_init__(self) -> None:
        if self.to_events is not None and self.to_category is not None:
            raise Exception("Use only one - either events or category to project!")


@dataclass
class _SubscriptionFactory:
    start_from: Position

    def to_events(self, to: list[Type[Event]]) -> Subscription:
        return Subscription(start_from=self.start_from, to_events=to)

    def to_category(self, to: Category) -> Subscription:
        return Subscription(start_from=self.start_from, to_category=to)


def subscribe(start_from: Position) -> _SubscriptionFactory:
    return _SubscriptionFactory(start_from=start_from)
