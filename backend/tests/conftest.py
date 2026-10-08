"""PostgreSQL tests use a private schema per test; never delete application data."""

from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import Base
from app.db import engine


@pytest.fixture
def db():
    name = "test_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {name}"))
    isolated = engine.execution_options(schema_translate_map={None: name})
    Base.metadata.create_all(isolated)
    try:
        with Session(isolated, expire_on_commit=False) as session:
            yield session
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {name} CASCADE"))
