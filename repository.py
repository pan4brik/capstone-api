from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

SEED_TITLES = ('note 1', 'note 2', 'note 3')


class NoteCreate(BaseModel):
    title: str = Field(min_length=1)
    body: str = ''


class Note(NoteCreate):
    id: str


class NotesRepository(Protocol):
    async def list_notes(self) -> list[Note]: ...

    async def add_note(self, data: NoteCreate) -> Note: ...


class InMemoryNotesRepository:
    """Notes kept in a process-local list. Resets on restart (see README)."""

    def __init__(self) -> None:
        self._notes: list[Note] = [
            Note(id=str(uuid4()), title=title) for title in SEED_TITLES
        ]

    async def list_notes(self) -> list[Note]:
        return self._notes

    async def add_note(self, data: NoteCreate) -> Note:
        note = Note(id=str(uuid4()), **data.model_dump())
        self._notes.append(note)
        return note
