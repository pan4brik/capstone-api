import pytest

import main
from repository import InMemoryNotesRepository


@pytest.fixture(autouse=True)
def reset_state():
    """Fresh in-memory store per test; rate limiter off unless a test opts in."""
    main.notes_repo = InMemoryNotesRepository()
    main.limiter.reset()
    main.limiter.enabled = False
    yield
    main.limiter.enabled = True
