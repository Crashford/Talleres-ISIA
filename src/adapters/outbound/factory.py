"""Composición de persistencia; la aplicación desconoce SQLite, PostgreSQL y DATABASE_URL."""

import os
from contextlib import contextmanager
from collections.abc import Iterator

from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort

SQLITE_PREFIX = "sqlite:///"
POSTGRES_PREFIX = "postgresql://"


@contextmanager
def repository_factory(database_url: str | None = None) -> Iterator[IncidentRepositoryPort]:
    url = database_url if database_url is not None else os.environ.get("DATABASE_URL", "sqlite:///:memory:")

    if url.startswith(SQLITE_PREFIX):
        path = url[len(SQLITE_PREFIX):]
        if not path:
            raise ValueError("DATABASE_URL debe indicar una ruta SQLite válida.")
        with SQLiteIncidentRepository(path) as repo:
            yield repo
        return

    if url.startswith(POSTGRES_PREFIX):
        from src.adapters.outbound.postgres_repository import PostgresIncidentRepository

        with PostgresIncidentRepository(url) as repo:
            yield repo
        return

    raise ValueError("DATABASE_URL debe usar sqlite:///... o postgresql://...")


create_repository = repository_factory
