import os
from pathlib import Path

import pytest

_DB = Path(__file__).parent / "test.db"
os.environ.update(
    GEMINI_API_KEY="test-key",
    DATABASE_URL=f"sqlite+aiosqlite:///{_DB}",
    LOG_LEVEL="WARNING",
    RATE_LIMIT_PER_MINUTE="10000",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    for suffix in ("", "-wal", "-shm"):
        Path(f"{_DB}{suffix}").unlink(missing_ok=True)
