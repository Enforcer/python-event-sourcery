from event_sourcery.event_store import EventStore, StreamId
from projections_read_models_experiment.events import InvoiceIssued, InvoiceVoided


def do(event_store: EventStore) -> None:
    stream_1 = StreamId(name="stream_1")
    stream_2 = StreamId(name="stream_2")
    stream_3 = StreamId(name="stream_2")

    event_store.append(
        InvoiceIssued(invoice_id=1, amount=100),
        InvoiceVoided(invoice_id=1),
        stream_id=stream_1,
    )
    event_store.append(
        InvoiceIssued(invoice_id=2, amount=69),
        InvoiceIssued(invoice_id=3, amount=50),
        stream_id=stream_2,
    )
    event_store.append(
        InvoiceIssued(invoice_id=4, amount=100),
        InvoiceVoided(invoice_id=4),
        stream_id=stream_3,
    )
