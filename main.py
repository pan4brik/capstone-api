from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

my_notes = [{'title': 'note 1'}, {'title': 'note 2'}, {'title': 'note 3'}]


class Note(BaseModel):
    title: str


@app.get('/health')
async def get_health():
    return {"status": "ok"}


@app.get('/notes', response_model=list[Note])
async def get_notes():
    return my_notes


@app.post('/notes', response_model=Note)
async def create_note(note: Note):
    my_notes.append(note)
    return note
