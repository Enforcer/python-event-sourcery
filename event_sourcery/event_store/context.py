from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Context:
    tenant_id: int | None


_event_store_context: ContextVar[Context] = ContextVar(
    "event_sourcery_event_store_context"
)


@contextmanager
def event_sourcery_context(tenant_id: int) -> Iterator[None]:
    """Could be used with many different event store instances.

    Also, in e.g. middleware. Not necessarily in the place when EventStore is used.
    """
    new_context = Context(tenant_id=tenant_id)
    token = _event_store_context.set(new_context)
    yield
    _event_store_context.reset(token)


def get_context() -> Context:
    try:
        return _event_store_context.get()
    except LookupError:
        return Context(tenant_id=None)
