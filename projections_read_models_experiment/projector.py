from esdbclient.exceptions import DeadlineExceeded

from event_sourcery.event_store import EventStore, Position, Recorded
from projections_read_models_experiment.logger import logger
from projections_read_models_experiment.projection import Projection, ProjectionName
from projections_read_models_experiment.subscription import Subscription


class Projector:
    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store

        # I believe it should be backed by same mechanism as StorageStrategy
        # I bet EventStoreDB have this built-in, for other backends
        # we'd have to store it in respective DB
        self._projections_positions: dict[ProjectionName, Position] = {}

    def run(self, projections: list[Projection]) -> None:
        for projection in projections:
            saved_position = self._projections_positions.get(projection.name)
            logger.debug(
                "Running projection %s, saved_position %r",
                projection.name,
                saved_position,
            )
            # I think there should be a limit on how many recorded
            # events return at once maximum

            start_from = saved_position or projection.subscription.start_from
            match projection.subscription:
                case Subscription(to_events=None, to_category=None):
                    subscription = self._event_store.subscribe_to_all(
                        start_from=start_from
                    )
                case Subscription(to_events=None):
                    subscription = self._event_store.subscribe_to_category(
                        start_from=start_from, to=projection.subscription.to_category
                    )
                case Subscription(to_category=None):
                    subscription = self._event_store.subscribe_to_events(
                        start_from=start_from, to=projection.subscription.to_events
                    )

            ev: Recorded | None = None
            batch = []
            try:
                for ev in subscription:
                    batch.append(ev)
            except DeadlineExceeded:  # this shouldn't be raised IMO
                projection.handle_batch(batch)

                if ev is not None:
                    logger.debug(
                        "Projection %s run finished, saving position %r",
                        projection.name,
                        ev.position,
                    )
                    self._projections_positions[projection.name] = ev.position
