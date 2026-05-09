# CloudCatcher Data Dictionary And File Map

Date reviewed: 2026-05-09

This document records the current application structure, main runtime files, MongoDB-backed data shapes, and API/frontend responsibilities found during repo inspection.

## Current Runtime Summary

CloudCatcher is currently implemented as:

- Backend: FastAPI, Motor/MongoDB, Pydantic models, APScheduler.
- Frontend: CRA/CRACO React app, Tailwind, shadcn/Radix-style UI primitives.
- Database: MongoDB collections accessed directly from `backend/app/main.py` and service modules.
- Active backend entrypoint: `backend/server.py`, which re-exports `app` from `backend/app/main.py`.
- Active frontend entrypoint: `frontend/src/index.js`, which renders `frontend/src/App.js`.

The repository also contains `Z_Cloudwatcher/`, which appears to be a duplicate/archive of the same project state, and `backend/legacy/practice_arena/`, which is an archived Flask/SQLite prototype kept for reference only.

Naming note: the product should be CloudCatcher, but many files, docs, UI labels, env defaults, and tests still say CloudWatcher or Cloud Watcher. This is not currently a runtime blocker.

## Active Backend File Map

| File | Purpose |
| --- | --- |
| `backend/server.py` | Compatibility wrapper for `uvicorn server:app`; imports `app` from `app.main`. |
| `backend/app/main.py` | Main FastAPI app. Contains Mongo setup, Pydantic models, mock generators, helper functions, WebSocket manager, and all API route handlers. |
| `backend/app/core/auth.py` | JWT authentication, bcrypt password hashing, refresh token creation, token blacklisting, roles, permissions, and user auth service. |
| `backend/app/core/connectors.py` | Provider adapter implementations for AWS, Azure, GCP, and DigitalOcean. Normalizes cloud provider instance data into the app inventory shape. |
| `backend/app/core/credentials_encryption.py` | Fernet-based encryption/decryption for provider credentials stored in the database. |
| `backend/app/db/connection.py` | Database factory. Selects SQLite by default for demo mode, or Mongo when `DB_BACKEND=mongo`. |
| `backend/app/db/sqlite_adapter.py` | Async SQLite document-store adapter that supports the Mongo/Motor call subset used by the app. |
| `backend/app/services/scheduler.py` | APScheduler integration for periodic account sync, recommendation generation, and notification dispatch. |
| `backend/app/services/remediation.py` | Basic remediation action generation for idle/stopped instances and placeholder execution flow. |
| `backend/app/services/email_service.py` | Resend-backed email sending plus HTML templates for verification, password reset, alert, and sync-complete notifications. |
| `backend/app/services/notification_service.py` | Slack and Microsoft Teams webhook notification service. |
| `backend/app/services/wafr.py` | AWS Well-Architected Framework Review automation skeleton. |
| `backend/requirements.txt` | Python dependencies. Contains duplicated/conflicting dependency pins that should be cleaned before reproducible setup work. |
| `backend/.env.example` | Backend environment template for Mongo, JWT, Fernet key, CORS, scheduler, email, and webhooks. |
| `backend/app/**/__init__.py` | Package markers. |

## Archived Backend File Map

| Path | Purpose |
| --- | --- |
| `backend/legacy/practice_arena/README.md` | Notes for archived Flask/SQLite MVP. |
| `backend/legacy/practice_arena/backend/app.py` | Old Flask API with provider connection, sync, polling, and alert email logic. |
| `backend/legacy/practice_arena/backend/db.py` | Old SQLite helper functions for credentials, instances, and sync logs. |
| `backend/legacy/practice_arena/backend/connectors/*.py` | Old provider connector implementations. |
| `backend/legacy/practice_arena/backend/requirements.txt` | Old Flask prototype dependencies. |

Archive rule: do not wire `backend/legacy/` back into active runtime unless deliberately extracting a pattern.

## Active Frontend File Map

| File | Purpose |
| --- | --- |
| `frontend/src/index.js` | React root bootstrap. |
| `frontend/src/App.js` | Route tree. Defines public login/register routes and protected app routes. |
| `frontend/src/lib/api.js` | Axios API client. Adds bearer token, refreshes expired tokens, exports backend API wrappers. |
| `frontend/src/lib/utils.js` | `cn()` helper for combining Tailwind classes. |
| `frontend/src/components/ProtectedRoute.jsx` | LocalStorage token gate, public-route redirect, current-user helper, logout helper, admin helper. |
| `frontend/src/components/Layout.jsx` | App shell with desktop sidebar, mobile nav, user menu, and global sync button. |
| `frontend/src/pages/Login.jsx` | Login screen. Currently displays demo credentials that are not seeded by the backend. |
| `frontend/src/pages/Register.jsx` | Registration form with optional organization creation. |
| `frontend/src/pages/Dashboard.jsx` | Dashboard stats, recent recommendations, provider/state breakdowns, correlated cost/security alerts. |
| `frontend/src/pages/CloudAccounts.jsx` | Cloud account CRUD UI, provider credential form, per-account sync action. |
| `frontend/src/pages/Inventory.jsx` | Instance table, provider/account/state/name/region filters, sync action, instance detail dialog. |
| `frontend/src/pages/Recommendations.jsx` | Recommendation list, category/severity/status filters, generation action, status update workflow. |
| `frontend/src/pages/Settings.jsx` | Admin-only user list and audit log view. |
| `frontend/src/hooks/use-toast.js` | Local toast hook inspired by react-hot-toast; app mostly uses `sonner`. |
| `frontend/src/components/ui/*.jsx` | shadcn/Radix UI primitive wrappers used by the application pages. |
| `frontend/src/index.css` | Tailwind imports, design tokens, font setup, global theme styles. |
| `frontend/src/App.css` | App-specific neo-brutalist utilities, provider/state/severity styling, animations. |
| `frontend/package.json` | Frontend scripts and dependencies. |
| `frontend/craco.config.js` | CRACO config, alias setup, dev-server visual edit hooks, optional health endpoint setup. |
| `frontend/tailwind.config.js` | Tailwind theme extension and content paths. |
| `frontend/components.json` | shadcn/ui configuration. |
| `frontend/jsconfig.json` | `@/*` source alias for editor/build resolution. |
| `frontend/public/index.html` | HTML shell and font preconnect/import tags. |

## Frontend Dev Plugin Map

| File | Purpose |
| --- | --- |
| `frontend/plugins/visual-edits/dev-server-setup.js` | Development-only middleware for visual editing and a `/ping` endpoint. |
| `frontend/plugins/visual-edits/babel-metadata-plugin.js` | Development Babel plugin that adds JSX metadata for visual editing. |
| `frontend/plugins/health-check/webpack-health-plugin.js` | Optional webpack compile health tracker. |
| `frontend/plugins/health-check/health-endpoints.js` | Optional dev-server health endpoints. |

## Current Database Collections And Data Shapes

These are inferred from active backend reads/writes. In Mongo mode these map to MongoDB collections. In SQLite mode they are stored as JSON documents in the native SQLite `documents` table, keyed by collection name and document id.

### `users`

Created by `AuthService.register_user`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | App-generated user id, e.g. `usr_<hex>`. |
| `email` | string | Login identifier. Should be unique but no index is declared in code. |
| `password` | string | Bcrypt hash. |
| `name` | string | Display name. |
| `role` | string | `user`, `admin`, or `msp_admin`. |
| `organization_id` | string/null | Set when user registers with an organization. |
| `email_verified` | boolean | Present but verification is skipped for demo login. |
| `created_at` | ISO datetime string | Creation time. |
| `last_login_at` | ISO datetime string/null | Updated on successful login. |
| `settings` | object | Notification/user preferences. |

### `organizations`

Created when registering with `organization_name`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | App-generated org id, e.g. `org_<hex>`. |
| `name` | string | Organization name. |
| `created_at` | ISO datetime string | Creation time. |
| `settings` | object | Currently empty by default. |

### `tokens_blacklist`

Used for logout and refresh-token rotation.

| Field | Type | Notes |
| --- | --- | --- |
| `token` | string | JWT string. |
| `blacklisted_at` | ISO datetime string | When token was revoked. |
| `expires_at` | ISO datetime string | Token expiration. |

### `cloud_accounts`

Created by `POST /api/cloud-accounts`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID. |
| `provider` | string | `aws`, `azure`, `gcp`, or `do`. |
| `account_name` | string/null | User-facing account label. |
| `account_identifier` | string/null | Derived from credentials: account/project/subscription id. |
| `status` | string | `connected`, `error`, `disabled`, or `syncing`. |
| `last_checked_at` | ISO datetime string/null | Updated before sync attempts. |
| `last_sync_at` | ISO datetime string/null | Updated on successful sync. |
| `last_error` | string/null | Last sync error. |
| `instance_count` | number | Count from last sync. |
| `created_at` | ISO datetime string | Creation time. |
| `updated_at` | ISO datetime string | Update time. |
| `credentials` | encrypted string/object | Encrypted by Fernet on create/update; some code handles legacy plain objects. |

### `instances`

Written by sync paths.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID for local record. |
| `provider` | string | Cloud provider. |
| `cloud_account_id` | string | Owning cloud account id. |
| `region_or_zone` | string/null | Region/zone normalized from provider. |
| `instance_id` | string | Provider resource id. |
| `name` | string/null | Provider tag/name. |
| `instance_type_or_size` | string/null | VM size/type. |
| `state` | string/null | Provider state. |
| `public_ip` | string/null | Public IPv4 where available. |
| `private_ip` | string/null | Private IPv4 where available. |
| `tags` | object | Provider tags/labels. |
| `raw` | object | Raw provider payload. |
| `first_seen_at` | ISO datetime string | Set on sync insertion. |
| `last_seen_at` | ISO datetime string | Set on sync insertion. |
| `updated_at` | ISO datetime string | Set on sync insertion. |

Current behavior deletes all instances for an account before inserting the new sync result.

### `recommendations`

Generated from instance inventory.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID. |
| `provider` | string/null | Provider associated with resource. |
| `cloud_account_id` | string/null | Owning cloud account id. |
| `resource_type` | string | Defaults to `instance`. |
| `resource_id` | string/null | Provider resource id. |
| `category` | string | `finops` or `secops`. |
| `rule_id` | string | Example: `FINOPS-001`, `SECOPS-001`. |
| `severity` | string | `low`, `medium`, `high`. |
| `title` | string | Recommendation title. |
| `description` | string | Recommendation body. |
| `evidence` | object | Supporting fields. |
| `status` | string | `open`, `dismissed`, `resolved`. |
| `created_at` | ISO datetime string | Creation time. |
| `updated_at` | ISO datetime string | Last update time. |

### `audit_events`

Written by auth, account, sync, recommendation, scheduler, email, and notification flows.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID. |
| `event_type` | string | Example: `user.login`, `sync.completed`. |
| `entity_type` | string | Example: `user`, `cloud_account`, `system`. |
| `entity_id` | string/null | Related app id where available. |
| `payload` | object | Event details. |
| `created_at` | ISO datetime string | Event time. |

### `alerts`

Written by webhook ingestion and anomaly detection.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID. |
| `provider` | string/null | Optional provider. |
| `cloud_account_id` | string/null | Optional cloud account id. |
| `alert_type` | string | Alert/anomaly type. |
| `severity` | string | Alert severity. |
| `resource_id` | string/null | Related resource id. |
| `payload` | object | Source-specific alert payload. |
| `created_at` | ISO datetime string | Alert time. |

### `remediation_actions`

Written by `RemediationEngine.analyze_and_remediate(dry_run=False)`.

| Field | Type | Notes |
| --- | --- | --- |
| `action_id` | string | Action id, e.g. `rightsize_<instance_id>`. |
| `instance_id` | string | Target provider instance id. |
| `cloud_account_id` | string | Owning cloud account. |
| `action_type` | string | Example: `terminate_idle`. |
| `severity` | string | Action severity. |
| `estimated_savings` | number | Estimated monthly savings. |
| `requires_approval` | boolean | Approval flag. |
| `auto_execute` | boolean | Auto-execution flag. |
| `description` | string | Human-readable action. |
| `status` | string | `pending`, `approved`, `executed`, or `failed`. |
| `executed_at` | ISO datetime string | Set on execution. |
| `executed_by` | string | Approver/executor identifier. |

### `wafr_assessments`

Written by `POST /api/wafr/assess/{account_id}`.

| Field | Type | Notes |
| --- | --- | --- |
| `account_id` | string | AWS cloud account id. |
| `timestamp` | ISO datetime string | Assessment time. |
| `results` | object | WAFR assessment result object. |

### `tenants`

Referenced by auth row-level security helper but not actively exposed through current routes.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Tenant id. |
| `name` | string | Tenant name. |
| `msp_organization_id` | string | Parent MSP organization id. |
| `settings` | object | Tenant settings. |
| `status` | string | Defaults to `active` in model. |
| `created_at` | ISO datetime string | Creation time. |

## API Surface

All active routes are under `/api`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health/version check. |
| `POST` | `/auth/register` | Register user. |
| `POST` | `/auth/login` | Login and issue access/refresh tokens. |
| `POST` | `/auth/logout` | Blacklist tokens. |
| `POST` | `/auth/refresh` | Rotate refresh/access token. |
| `POST` | `/auth/verify-email` | Verify email token. |
| `POST` | `/auth/request-password-reset` | Request reset token. |
| `POST` | `/auth/reset-password` | Reset password. |
| `GET` | `/auth/me` | Get current user details. |
| `GET` | `/users` | Admin user listing. |
| `DELETE` | `/users/{user_id}` | Admin user deletion. |
| `WS` | `/ws/{user_id}` | WebSocket updates. |
| `POST` | `/cloud-accounts` | Create cloud account. |
| `GET` | `/cloud-accounts` | List cloud accounts. |
| `GET` | `/cloud-accounts/{account_id}` | Get one cloud account. |
| `PATCH` | `/cloud-accounts/{account_id}` | Update cloud account. |
| `DELETE` | `/cloud-accounts/{account_id}` | Delete account, instances, and recommendations. |
| `POST` | `/sync` | Sync all enabled accounts using real providers. |
| `POST` | `/sync/{account_id}` | Sync one account using current mock generator path. |
| `GET` | `/instances` | List/filter normalized instances. |
| `GET` | `/instances/{instance_id}` | Get one instance by provider instance id. |
| `GET` | `/recommendations` | List/filter recommendations. |
| `PATCH` | `/recommendations/{recommendation_id}` | Update recommendation status. |
| `POST` | `/recommendations/run` | Regenerate recommendations from current inventory. |
| `GET` | `/alerts` | List alerts. |
| `POST` | `/alerts/webhook` | Ingest external alert. |
| `POST` | `/alerts/detect` | Run basic anomaly detection. |
| `POST` | `/remediation/analyze` | Analyze inventory and optionally create remediation actions. |
| `GET` | `/remediation/actions` | List remediation actions. |
| `POST` | `/remediation/actions/{action_id}/approve` | Execute approved remediation action. |
| `POST` | `/wafr/assess/{account_id}` | Run AWS WAFR assessment. |
| `GET` | `/dashboard/correlated-alerts` | List resources with cost and security issues. |
| `GET` | `/dashboard/stats` | Aggregate dashboard counters and correlated alerts. |
| `GET` | `/audit-events` | List recent audit events. |
| `GET` | `/scheduler/jobs` | Admin scheduler job listing. |
| `POST` | `/scheduler/trigger/{job_id}` | Admin manual scheduler trigger. |
| `POST` | `/email/test` | Admin test email. |
| `POST` | `/notifications/test` | Admin Slack/Teams test. |

## Current Architecture Concerns

- `backend/app/main.py` is too large and mixes data models, DB access, route handlers, mock data, and domain logic.
- Backend routes directly use Mongo collection APIs, so a SQLite swap should introduce a data access layer instead of replacing calls inline everywhere.
- Demo credentials are advertised in the frontend but not deterministically seeded by the backend.
- Auth protection is inconsistent. Several sensitive routes, including cloud account and inventory operations, do not require auth even though frontend routes are protected.
- `POST /api/sync` uses real cloud APIs, while `POST /api/sync/{account_id}` still uses mock instance generation. That is useful for demos but should be explicit.
- The app has no declared Mongo indexes or schema migration layer.
- `backend/requirements.txt` has duplicate/conflicting dependency declarations.
- `.env` files exist locally and should remain untracked.

## Runtime Smoke Test: 2026-05-09

Local environment checks:

- Backend virtualenv exists and uses Python 3.13.0.
- Backend `.env` exists with expected keys: `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `ENCRYPTION_KEY`, `JWT_SECRET_KEY`, `SYNC_INTERVAL_MINUTES`, `APP_URL`, `SENDER_EMAIL`, `RESEND_API_KEY`, `SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`.
- Frontend `.env` exists with `REACT_APP_BACKEND_URL`.
- Frontend is configured to call `http://localhost:8002`.
- `yarn` is not globally installed, but `npm` is available.
- `mongod` and `mongosh` were not found on PATH.
- Port `127.0.0.1:27017` was not accepting connections.

Backend checks:

- `python -m compileall backend/app` passed.
- Backend dependency import smoke test passed for FastAPI, Motor, APScheduler, and boto3.
- FastAPI started successfully on `127.0.0.1:8002` after local port-binding permission was granted.
- `GET /api/health` returned `200` with version `2.0.0`.
- Data-backed endpoints failed because MongoDB was unavailable:
  - `POST /api/auth/login` returned `500`.
  - `GET /api/cloud-accounts` returned `500`.
  - `GET /api/dashboard/stats` returned `500`.
- Root cause from server logs: `pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 61] Connection refused, Timeout: 30s`.

Frontend checks:

- `npm run build` completed successfully.
- Build warnings:
  - `frontend/src/pages/Inventory.jsx`: `useEffect` has missing dependency `fetchData`.
  - `frontend/src/pages/Recommendations.jsx`: `useEffect` has missing dependency `fetchData`.
- `npm start` served the React dev app on `127.0.0.1:3000` after local port-binding permission was granted.
- `GET /` returned `200`.
- `GET /login` returned `200`.

Smoke-test conclusion:

- The frontend shell and build path work.
- The backend process starts and health works.
- The app is not usable for login/dashboard/account flows on this machine while MongoDB is missing or stopped.
- This validates the demo need for either a reliable local database bootstrap or a SQLite-backed demo mode.

## Runtime Smoke Test After SQLite Adapter: 2026-05-09

Backend checks in default SQLite mode:

- FastAPI started on `127.0.0.1:8002`.
- SQLite database file was created at `backend/cloudcatcher.sqlite3`.
- Startup seeded the real demo admin user:
  - Email: `admin@cloudwatcher.com`
  - Role: `admin`
  - Name: `CloudCatcher Demo Admin`
- `GET /api/health` returned `200`.
- `POST /api/auth/login` with demo credentials returned `200`.
- `GET /api/cloud-accounts` returned `200`.
- `GET /api/dashboard/stats` returned `200`.
- Creating a demo AWS account returned `200`.
- `POST /api/sync/{account_id}` returned `200` and generated mock instances.
- `GET /api/instances?limit=2` returned `200`.
- `GET /api/recommendations?limit=3` returned `200`.
- Authenticated `GET /api/auth/me` returned `200`.
- Authenticated `GET /api/users` returned `200`.
- Authenticated `GET /api/scheduler/jobs` returned `200`.

Frontend checks after backend changes:

- `npm run build` still completed successfully.
- Existing warnings remain:
  - `frontend/src/pages/Inventory.jsx`: missing `fetchData` dependency in `useEffect`.
  - `frontend/src/pages/Recommendations.jsx`: missing `fetchData` dependency in `useEffect`.

Post-change conclusion:

- Default local/demo backend now works without MongoDB.
- MongoDB remains available by setting `DB_BACKEND=mongo`.
- The SQLite adapter is suitable for local demo data and developer flow, not a final scale persistence design.

## SQLite Swap Notes

Implemented first-pass approach:

1. `backend/app/db/connection.py` provides the factory.
2. `DB_BACKEND=sqlite` or unset uses a local native SQLite file.
3. `DB_BACKEND=mongo` uses the existing Motor/MongoDB path.
4. `backend/app/db/sqlite_adapter.py` provides a Mongo-like async collection facade so current route code can keep calling `db.users.find_one(...)`, `db.instances.find(...).to_list(...)`, etc.
5. SQLite mode seeds the real demo admin by default. Mongo mode does not seed unless `SEED_DEMO_USER=true` is explicitly set.

This is intentionally a demo-safe compatibility layer, not a final persistence architecture. A stricter repository layer can still be introduced later once the backend monolith is split into routers/services/models.

Recommended minimal SQLite tables for demo:

- `users`
- `organizations`
- `tokens_blacklist`
- `cloud_accounts`
- `instances`
- `recommendations`
- `audit_events`
- `alerts`
- `remediation_actions`
- `wafr_assessments`

For flexible JSON-heavy fields, store JSON text columns for `settings`, `credentials`, `tags`, `raw`, `evidence`, `payload`, and `results`.

Current SQLite implementation:

- File path defaults to `backend/cloudcatcher.sqlite3`.
- Override path with `SQLITE_DB_PATH`.
- Physical table: `documents(collection, doc_id, data, created_at, updated_at)`.
- JSON-heavy fields are serialized into the `data` JSON column.
- Query/filter/sort/projection logic is implemented in Python for the app's current Mongo-style call subset.
