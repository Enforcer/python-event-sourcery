import abc
from typing import Any, ClassVar, Sequence, TypeAlias

from event_sourcery.event_store import Recorded
from projections_read_models_experiment.subscription import Subscription

ProjectionName: TypeAlias = str


class Projection(abc.ABC):
    name: ClassVar[ProjectionName] = "Projection"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if cls.name == Projection.name:
            raise Exception(
                f"Adjust {cls.__name__}.name class-level attribute to be unique"
            )

    def __init__(self, subscription: Subscription) -> None:
        self._subscription = subscription

    @property
    def subscription(self) -> Subscription:
        return self._subscription

    @abc.abstractmethod
    def handle_batch(self, batch: Sequence[Recorded]) -> None:
        pass
