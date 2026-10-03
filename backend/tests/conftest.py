from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.models import analysis as _analysis_models  # noqa: F401 — registra o modelo em Base.metadata
from app.models import chat_message as _chat_message_models  # noqa: F401 — registra o modelo em Base.metadata
from app.models import content as _content_models  # noqa: F401 — registra o modelo em Base.metadata
from app.models import learning_path as _learning_path_models  # noqa: F401 — registra o modelo em Base.metadata
from app.models import (  # noqa: F401 — registra o modelo em Base.metadata
    learning_path_enrollment as _learning_path_enrollment_models,
)
from app.models import methodology as _methodology_models  # noqa: F401 — registra o modelo em Base.metadata
from app.models import (  # noqa: F401 — registra o modelo em Base.metadata
    methodology_chunk as _methodology_chunk_models,
)
from app.models import user as _user_models  # noqa: F401 — registra o modelo em Base.metadata

TEST_DB_NAME = "gerad_test"


def _admin_url(database: str = "postgres") -> str:
    settings = get_settings()
    base = settings.DATABASE_URL.rsplit("/", 1)[0]
    return f"{base}/{database}"


@pytest.fixture(scope="session")
def test_engine():
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin_engine.dispose()

    engine = create_engine(_admin_url(TEST_DB_NAME))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin_engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    trans.rollback()
    connection.close()
