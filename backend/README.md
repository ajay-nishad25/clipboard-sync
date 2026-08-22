# Clipboard Sync Backend

Phase 2 provides a development-only Django REST API backed by SQLite. It stores
plain-text clipboard entries for API testing only; it does not connect to the
desktop agent, Android, WebSockets, Channels, or authentication.

## Prerequisites

- Python 3.11 or later

## Environment setup

From `backend/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Set a local Django development secret. Do not commit its value:

```powershell
$env:DJANGO_SECRET_KEY = "choose-a-long-unique-local-development-value"
```

`DJANGO_DEBUG` defaults to `True` for this POC. See `.env.example` for the
expected variable names; Django does not load `.env` files automatically.

## Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

## Database migrations

```powershell
python manage.py migrate
```

SQLite stores local data in `db.sqlite3`, which is ignored by Git.

## Start the development server

```powershell
python manage.py runserver
```

The server listens on `http://127.0.0.1:8000/` by default. This is a local,
development-only server.

## API endpoints

### Create an entry

`POST /api/clipboard/`

Required JSON fields:

```json
{
  "device_id": "desktop-001",
  "content": "Hello World"
}
```

Example PowerShell request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/clipboard/ `
  -ContentType "application/json" `
  -Body '{"device_id":"desktop-001","content":"Hello World"}'
```

It returns `201 Created` with the entry, including its database-generated `id`
and `created_at` timestamp. `content` must be a non-empty JSON string.

### Get the latest entry

`GET /api/clipboard/latest/`

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/
```

It returns `200 OK` with the latest entry, or `404 Not Found` with a JSON
detail message when no entry has been created.

## Test

```powershell
python manage.py test
```

The test suite uses Django's built-in test runner and an isolated test database.
