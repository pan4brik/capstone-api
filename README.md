# capstone-api

A small FastAPI backend with several endpoints — a health check, an in-memory
notes list (`GET`/`POST /notes`), `GET /rates` (live currency data from the
external Frankfurter API, `api.frankfurter.dev`), and `POST /ask` (answers a
question grounded only in the stored notes, via the Gemini API). Ships with a
pytest suite (external calls are mocked) that runs on every push via GitHub
Actions.

There is no CORS layer — a Next.js BFF is the only intended caller, and write
endpoints (`POST /notes`, `POST /ask`) require a shared secret (see
Configuration below).

## Requirements

- Python 3.10 or newer — check with `python --version` (or `python3 --version`).
  On Windows use the `py` launcher; on many Linux/macOS setups the command is
  `python3`. Every command below calls pip as `python -m pip` so it behaves the
  same however Python sits on your PATH.

## Run it

    git clone https://github.com/pan4brik/capstone-api.git
    cd capstone-api

**1 — create and activate a virtual environment**

macOS / Linux (bash or zsh):

    python3 -m venv my-venv
    source my-venv/bin/activate

Windows (PowerShell):

    py -m venv my-venv
    my-venv\Scripts\Activate.ps1

Windows (cmd.exe):

    py -m venv my-venv
    my-venv\Scripts\activate.bat

Other shells: fish → `source my-venv/bin/activate.fish` · Git Bash on Windows →
`source my-venv/Scripts/activate`

> If PowerShell refuses with "running scripts is disabled on this system", run
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that window
> first, or just use cmd.exe.

**2 — install dependencies and start the server**

    python -m pip install -r requirements.txt
    python -m uvicorn main:app --reload

API on http://localhost:8000 — interactive docs at http://localhost:8000/docs.
Stop with Ctrl+C; leave the venv with `deactivate`.

## Configuration

| Variable            | Required | Purpose                                                          |
|---------------------|----------|-------------------------------------------------------------------|
| `BFF_SHARED_SECRET` | yes, for writes | `POST /notes` and `POST /ask` reject every request unless it carries a matching `X-BFF-Secret` header. |
| `GEMINI_API_KEY`     | yes, for `/ask` | Sent to the Gemini API; without it `/ask` returns `{"error": "llm api failure"}`. |

The BFF should also forward an `X-BFF-User-Id` header identifying the
end user on each write request. The rate limiter budgets writes
(`10/minute; 200/day`) per that id; without it, all traffic through the BFF
is budgeted together as one caller, since the API otherwise sees only the
BFF's own address.

## Test it

    python -m pytest -q

## Endpoints

| Method | Path      | Description                                                     |
|--------|-----------|-------------------------------------------------------------------|
| GET    | `/health` | liveness check                                                   |
| GET    | `/notes`  | list notes                                                       |
| POST   | `/notes`  | add a note — JSON body `{"title": "...", "body": "..."}`, requires `X-BFF-Secret` |
| GET    | `/rates`  | live exchange rates via `api.frankfurter.dev`                    |
| POST   | `/ask`    | answer a question grounded in the stored notes — JSON body `{"question": "..."}`, requires `X-BFF-Secret` |

## Known gaps

- Notes live in an in-memory list — no database, and they reset every time the
  server restarts.
