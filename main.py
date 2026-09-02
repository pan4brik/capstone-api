import os
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, RequestError

from repository import InMemoryNotesRepository, Note, NoteCreate, NotesRepository

app = FastAPI()

notes_repo: NotesRepository = InMemoryNotesRepository()


def get_notes_repo() -> NotesRepository:
    return notes_repo


origins = ['http://localhost:3000']

if frontend_origin := os.environ.get('FRONTEND_ORIGIN'):
    origins.append(frontend_origin)

BASE_URL = 'https://api.frankfurter.dev/v2'


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=['GET']
)


@app.get('/health')
async def get_health():
    return {"status": "ok"}


@app.get('/notes', response_model=list[Note])
async def get_notes(repo: NotesRepository = Depends(get_notes_repo)):
    return await repo.list_notes()


@app.get('/rates')
async def get_exchange_rates():
    try:
        async with AsyncClient(
            base_url=BASE_URL
        ) as ac:
            response = await ac.get('/rates')

        if response.status_code != status.HTTP_200_OK:
            return {'status': 'external api failure'}

        return response.json()
    except RequestError:
        return {'status': 'cannot reach external api'}


@app.post('/notes', response_model=Note)
async def create_note(
    note: NoteCreate, repo: NotesRepository = Depends(get_notes_repo)
):
    return await repo.add_note(note)
