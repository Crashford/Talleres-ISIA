"""Composición de persistencia; la aplicación desconoce SQLite y DATABASE_URL."""

import os
from contextlib import contextmanager
from collections.abc import Iterator

from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort


@contextmanager
def repository_factory(database_url: str | None = None) -> Iterator[IncidentRepositoryPort]:
    url = database_url if database_url is not None else os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    prefix = "sqlite:///"
    if not url.startswith(prefix) or not url[len(prefix):]:
        raise ValueError("DATABASE_URL debe indicar SQLite: sqlite:///ruta o sqlite:///:memory:")
    path = url[len(prefix):]
    with SQLiteIncidentRepository(path) as repo:
        yield repo
