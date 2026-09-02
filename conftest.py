import pytest

import main
from repository import InMemoryNotesRepository


@pytest.fixture(autouse=True)
def reset_notes_repo():
    """Give every test a fresh in-memory store so create tests don't leak."""
    main.notes_repo = InMemoryNotesRepository()
    yield
