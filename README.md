# capstone-api

A small FastAPI backend with several endpoints — a health check, an in-memory
notes list (`GET`/`POST /notes`), and `GET /rates`, which calls the external
Frankfurter API (`api.frankfurter.dev`) for live currency data. Ships with a
pytest suite (the external call is mocked) that runs on every push via GitHub
Actions.

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

## Test it

    python -m pytest -q

## Endpoints

| Method | Path      | Description                                    |
|--------|-----------|-----------------------------------------------|
| GET    | `/health` | liveness check                                |
| GET    | `/notes`  | list notes                                    |
| POST   | `/notes`  | add a note — JSON body `{"title": "..."}`     |
| GET    | `/rates`  | live exchange rates via `api.frankfurter.dev` |

## Known gaps

- Notes live in an in-memory list — no database, no stable `id`, and they reset
  every time the server restarts.
- CORS currently allows only `GET` requests from `http://localhost:3000`.
