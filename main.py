import os
import secrets
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from httpx import AsyncClient, RequestError
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from repository import InMemoryNotesRepository, Note, NoteCreate, NotesRepository

app = FastAPI()


def rate_limit_key(request: Request) -> str:
    """Per-BFF-user budget when the BFF forwards X-BFF-User-Id; else per remote address."""
    user_id = request.headers.get('x-bff-user-id')
    return user_id or get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

WRITE_RATE_LIMIT = '10/minute;200/day'

notes_repo: NotesRepository = InMemoryNotesRepository()


def get_notes_repo() -> NotesRepository:
    return notes_repo


async def require_bff_secret(x_bff_secret: str | None = Header(default=None)):
    """BFF_SHARED_SECRET must be set and the header must match it."""
    expected = os.environ.get('BFF_SHARED_SECRET')
    if not expected or not secrets.compare_digest(x_bff_secret or '', expected):
        raise HTTPException(status_code=401, detail='invalid or missing BFF secret')


BASE_URL = 'https://api.frankfurter.dev/v2'

GEMINI_MODEL = 'gemini-flash-lite-latest'
GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/'
    f'models/{GEMINI_MODEL}:generateContent'
)
GEMINI_SYSTEM_INSTRUCTION = (
    'Answer the question using only the notes provided. '
    "If the answer is not in the notes, say you don't know."
)
MAX_QUESTION_LEN = 500
MAX_NOTES_IN_PROMPT = 20
MAX_BODY_CHARS = 500
MAX_ANSWER_TOKENS = 256


@app.get('/health')
async def get_health():
    return {"status": "ok"}


@app.get('/notes', response_model=list[Note])
async def get_notes(
    repo: NotesRepository = Depends(get_notes_repo),
    _: None = Depends(require_bff_secret),
):
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
@limiter.shared_limit(WRITE_RATE_LIMIT, scope='writes')
async def create_note(
    request: Request,
    note: NoteCreate,
    repo: NotesRepository = Depends(get_notes_repo),
    _: None = Depends(require_bff_secret),
):
    return await repo.add_note(note)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LEN)


def build_ask_prompt(notes: list[Note], question: str) -> str:
    lines = ['Notes:']
    for note in notes[:MAX_NOTES_IN_PROMPT]:
        body = note.body[:MAX_BODY_CHARS].strip()
        lines.append(f'- {note.title}: {body}' if body else f'- {note.title}')
    lines += ['', f'Question: {question}']
    return '\n'.join(lines)


def extract_answer(payload: dict) -> str | None:
    candidates = payload.get('candidates') or []
    if not candidates:
        return None
    parts = candidates[0].get('content', {}).get('parts') or []
    answer = ''.join(part.get('text', '') for part in parts).strip()
    return answer or None


@app.post('/ask')
@limiter.shared_limit(WRITE_RATE_LIMIT, scope='writes')
async def ask_notes(
    request: Request,
    payload: Question,
    repo: NotesRepository = Depends(get_notes_repo),
    _: None = Depends(require_bff_secret),
):
    prompt = build_ask_prompt(await repo.list_notes(), payload.question)
    try:
        async with AsyncClient() as ac:
            response = await ac.post(
                GEMINI_URL,
                params={'key': os.environ.get('GEMINI_API_KEY', '')},
                json={
                    'systemInstruction': {
                        'parts': [{'text': GEMINI_SYSTEM_INSTRUCTION}]
                    },
                    'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                    'generationConfig': {'maxOutputTokens': MAX_ANSWER_TOKENS},
                },
            )

        if response.status_code != status.HTTP_200_OK:
            return {'error': 'llm api failure'}

        answer = extract_answer(response.json())
        if answer is None:
            return {'error': 'no answer produced'}

        return {'answer': answer}
    except RequestError:
        return {'error': 'cannot reach llm api'}
