from typing import ClassVar, Sequence

from event_sourcery.event_store import Recorded
from projections_read_models_experiment import add_example_data
from projections_read_models_experiment.event_store import beginning, event_store
from projections_read_models_experiment.events import InvoiceIssued, InvoiceVoided
from projections_read_models_experiment.logger import logger
from projections_read_models_experiment.projection import Projection, ProjectionName
from projections_read_models_experiment.projector import Projector
from projections_read_models_experiment.subscription import Subscription, subscribe


class Fiscal(Projection):
    name: ClassVar[ProjectionName] = "fiscal2024"

    def __init__(
        self,
        subscription: Subscription,
    ) -> None:
        super().__init__(subscription=subscription)
        # Projection is a client code, so there might be a need to simply
        # pass something, e.g. sqlalchemy's session or config
        self._invoices_amounts: dict[int, int] = {}

    def handle_batch(self, batch: Sequence[Recorded]) -> None:
        for recorded in batch:
            logger.debug("Handling event %r", recorded.metadata.event)
            event = recorded.metadata.event
            match event:
                case InvoiceIssued():
                    self._invoices_amounts[event.invoice_id] = event.amount
                case InvoiceVoided():
                    del self._invoices_amounts[event.invoice_id]

        # Update something e.g. in a DB
        logger.info(
            "Total income for taxation is %d", sum(self._invoices_amounts.values())
        )


if __name__ == "__main__":
    add_example_data.do(event_store)

    projections = [
        Fiscal(
            subscription=subscribe(start_from=beginning).to_events(
                to=[InvoiceIssued, InvoiceVoided]
            ),
        ),
    ]

    projector = Projector(event_store=event_store)
    projector.run(projections)
    # run again to see in logs how saved position is reused
    projector.run(projections)
