from event_sourcery.event_store import Event


class InvoiceIssued(Event):
    invoice_id: int
    amount: int


class InvoiceVoided(Event):
    invoice_id: int
