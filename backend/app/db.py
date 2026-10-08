import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://allocator:allocator_local@localhost:5432/allocator")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, isolation_level="REPEATABLE READ")
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
