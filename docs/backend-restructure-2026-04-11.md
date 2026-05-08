# Backend Restructure Log

Date: `2026-04-11`

## Why This Was Done

The original `backend/` directory mixed three different concerns:

- The active FastAPI backend.
- A nested `PracticeArena` prototype with its own `.git/` and `.venv/`.
- Runtime/setup debris such as `.env`, SQLite files, and cache folders.

That layout made imports fragile, confused setup docs, and left the repository with an invalid nested-repo/submodule state.

## Step-by-Step Changes

1. Audited the original backend tree and confirmed the active service was the FastAPI code in `backend/server.py`.
2. Confirmed `backend/PracticeArena` was an embedded legacy prototype and not part of the active runtime path.
3. Created a package-based layout for the active backend:
   - `backend/app/`
   - `backend/app/core/`
   - `backend/app/services/`
4. Moved the active modules into the package:
   - `backend/server.py` -> `backend/app/main.py`
   - `backend/auth.py` -> `backend/app/core/auth.py`
   - `backend/connectors.py` -> `backend/app/core/connectors.py`
   - `backend/credentials_encryption.py` -> `backend/app/core/credentials_encryption.py`
   - `backend/email_service.py` -> `backend/app/services/email_service.py`
   - `backend/notification_service.py` -> `backend/app/services/notification_service.py`
   - `backend/remediation.py` -> `backend/app/services/remediation.py`
   - `backend/scheduler.py` -> `backend/app/services/scheduler.py`
   - `backend/wafr.py` -> `backend/app/services/wafr.py`
5. Added package entry files:
   - `backend/app/__init__.py`
   - `backend/app/core/__init__.py`
   - `backend/app/services/__init__.py`
6. Restored the existing startup workflow by adding a compatibility wrapper:
   - `backend/server.py` now re-exports `app` from `backend/app/main.py`
   - Existing command still works: `uvicorn server:app --host 0.0.0.0 --port 8001 --reload`
7. Fixed path-sensitive code introduced by the old flat layout:
   - `.env` loading now resolves from the backend root instead of the package folder
   - scheduler imports now use package-relative modules
   - connector access now goes through a defined `fetch_instances(...)` entrypoint
   - encrypted credentials are decrypted before sync jobs run
   - updated cloud-account credentials are re-encrypted before persistence
   - scheduler helper imports (`get_scheduled_jobs`, `trigger_job_now`, `stop_scheduler`) are imported explicitly by the main app
8. Created a tracked backend environment template:
   - `backend/.env.example`
9. Extracted a clean archive of the legacy Flask MVP into source-only form:
   - `backend/legacy/practice_arena/`
   - Kept: source files, README files, `.env.example`
   - Dropped from the repo copy: nested `.git/`, `.venv/`, `.env`, SQLite files, caches, OS artifacts
10. Removed the original nested `backend/PracticeArena` directory from the active backend tree after preserving a clean archive copy.
11. Updated repository ignore rules so tracked examples remain visible while real secrets and SQLite data stay ignored.
12. Updated root documentation to reflect the new backend structure and environment variables.

## Resulting Backend Layout

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── connectors.py
│   │   └── credentials_encryption.py
│   └── services/
│       ├── __init__.py
│       ├── email_service.py
│       ├── notification_service.py
│       ├── remediation.py
│       ├── scheduler.py
│       └── wafr.py
├── legacy/
│   └── practice_arena/
├── server.py
├── requirements.txt
└── .env.example
```

## Operational Notes

- Active backend entrypoint: `backend/app/main.py`
- Backward-compatible local entrypoint: `backend/server.py`
- Archived prototype: `backend/legacy/practice_arena/`
- The legacy prototype is reference material only and should not be wired back into the active runtime tree.

## Follow-Up Guardrails

- Keep new backend modules inside `backend/app/`; do not reintroduce top-level service modules.
- Treat `backend/legacy/` as archive-only.
- Do not commit `.env`, `.venv`, SQLite files, or nested repos inside `backend/`.
- If the FastAPI app is split further, prefer `backend/app/api/`, `backend/app/models/`, and `backend/app/services/` rather than returning to a flat layout.

## Verification

- `python3 -m compileall backend` completed successfully after the restructure.
- A wrapper/import smoke test was attempted with stub backend environment variables:
  - Command path exercised: `backend/server.py` -> `backend/app/main.py`
  - Result: import halted on `ModuleNotFoundError: No module named 'fastapi'`
  - Meaning: the new layout is syntactically valid, but full runtime startup still depends on installing backend Python dependencies in the local environment.
