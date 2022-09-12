from unittest.mock import patch

import alembic.config
import pytest
from es_library import db
from es_library.api import app
from es_library.tests.dsl import PrivateApi, PublicApi
from fastapi.testclient import TestClient
from sqlalchemy import create_engine


@pytest.fixture(scope="session")
def database_setup() -> None:
    engine = create_engine(
        "postgresql://event_sourcery:event_sourcery@localhost:5432/event_sourcery"
    )
    with engine.connect() as connection:
        connection.connection.set_isolation_level(0)
        connection.execute("DROP DATABASE IF EXISTS event_sourcery_tests")
        connection.execute("CREATE DATABASE event_sourcery_tests")
    args = [
        "-c",
        "alembic_tests.ini",
        "--raiseerr",
        "upgrade",
        "head",
    ]
    alembic.config.main(args)
    test_engine = create_engine(
        "postgresql://event_sourcery:event_sourcery@localhost:5432/event_sourcery_tests"
    )
    db.engine = test_engine


@pytest.fixture()
def cleanup_db() -> None:
    yield
    with db.engine.connect() as connection:
        connection.execute("TRUNCATE TABLE books_read_model")
        connection.execute("TRUNCATE TABLE books")
        connection.execute("TRUNCATE TABLE event_sourcery_events")
        connection.execute("TRUNCATE TABLE event_sourcery_streams")


@pytest.fixture()
def client(database_setup, cleanup_db) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def public_api(client: TestClient) -> PublicApi:
    return PublicApi(client)


@pytest.fixture()
def private_api(client: TestClient) -> PrivateApi:
    return PrivateApi(client)
