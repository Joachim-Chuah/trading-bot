import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from db.database import Base
from db import models  # noqa: F401

load_dotenv()


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(os.getenv("DATABASE_URL"))
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    # create_savepoint: session.commit() releases a savepoint instead of
    # committing the outer transaction, so teardown rollback always works.
    Session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
