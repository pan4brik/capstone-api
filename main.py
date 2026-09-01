import os
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, RequestError
from pydantic import BaseModel


class Note(BaseModel):
    title: str


app = FastAPI()

my_notes = [Note(title='note 1'), Note(title='note 2'), Note(title='note 3')]
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
async def get_notes():
    return my_notes


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
async def create_note(note: Note):
    my_notes.append(note)
    return note
