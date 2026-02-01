# Cloud Watcher (Hackathon MVP)

A lightweight Flask API that connects to multiple cloud providers, normalizes VM/instance inventory, stores it in SQLite, and exposes a minimal REST API.

## Requirements
- Python 3.9+
- macOS/Linux/Windows

## Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration (.env)
Copy `backend/.env.example` to `backend/.env` and update values:
- `POLL_INTERVAL_SECONDS`
- `POLLING_ENABLED`
- `ALERTS_ENABLED`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`

## Run
```bash
cd backend
python app.py
```

The server runs on `http://127.0.0.1:5050` and uses `cloudwatcher.sqlite3` in the backend folder.

## Endpoints
- `GET /health`
- `POST /connect/<provider>`
- `POST /sync`
- `GET /instances?provider=<optional>`
- `GET /polling/status`
- `GET /sync/logs?limit=<optional>`

Providers: `aws`, `azure`

## Example Requests

### Health


```bash
curl http://127.0.0.1:5050/health
```

### Connect AWS
```bash
curl -X POST http://127.0.0.1:5050/connect/aws \
  -H 'Content-Type: application/json' \
  -d '{"access_key_id":"REDACTED","secret_access_key":"REDACTED","region":"eu-north-1"}'
```

### Connect Azure
```bash
curl -X POST http://127.0.0.1:5050/connect/azure \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "...",
    "client_id": "...",
    "client_secret": "...",
    "subscription_id": "..."
  }'
```

### Sync All Providers
```bash
curl -X POST http://127.0.0.1:5050/sync
```

### Polling Status
```bash
curl http://127.0.0.1:5050/polling/status
```

### Sync Logs (latest 100)
```bash
curl http://127.0.0.1:5050/sync/logs
```

### List Instances
```bash
curl http://127.0.0.1:5050/instances
curl http://127.0.0.1:5050/instances?provider=aws
```

## Notes
- Credentials are stored in SQLite (table: `credentials`).
- Instances are upserted into `instances` table with primary key `(provider, instance_id, region)`.
- Avoid logging secrets; the app does not print credential values.

## Polling
Polling runs by default every 5 minutes. Configure via env vars:
- `POLL_INTERVAL_SECONDS` (default: 300)
- `POLLING_ENABLED` (default: true)

## Alerts
Email alerts fire on instance state changes between `running` and `stopped`.
Configure via env vars:
- `ALERTS_ENABLED` (default: true)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`
