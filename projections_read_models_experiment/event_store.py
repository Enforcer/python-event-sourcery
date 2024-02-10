import atexit

from esdbclient import EventStoreDBClient, StreamState

from event_sourcery.event_store import EventStore
from event_sourcery_esdb import ESDBStoreFactory

client = EventStoreDBClient(uri="esdb://localhost:2113?Tls=false")
beginning = client.get_commit_position()


def cleanup() -> None:
    for event in client._connection.streams.read(commit_position=beginning):
        if not event.stream_name.startswith("$"):
            client.delete_stream(
                event.stream_name,
                current_version=StreamState.ANY,
            )
    for sub in client.list_subscriptions():
        client.delete_subscription(sub.group_name)


atexit.register(cleanup)

event_store: EventStore = ESDBStoreFactory(client).without_outbox().build()
