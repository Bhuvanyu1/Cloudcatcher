import json
import os
import threading
import time
import smtplib
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from email.message import EmailMessage

from db import (
    init_db,
    upsert_credentials,
    get_credentials,
    upsert_instances,
    list_instances,
    insert_sync_log,
    list_sync_logs,
    get_instance_states,
)
from connectors import get_connector

load_dotenv()

app = Flask(__name__)
DB_PATH = "cloudwatcher.sqlite3"
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
POLLING_ENABLED = os.getenv("POLLING_ENABLED", "true").lower() in ("1", "true", "yes", "on")
POLLING_STATE = {"running": False, "last_run": None, "last_error": None}
ALERTS_ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() in ("1", "true", "yes", "on")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ALERT_TO = os.getenv("ALERT_TO", "")


def utc_now():
    return datetime.utcnow().isoformat() + "Z"


def parse_recipients(value):
    return [v.strip() for v in value.split(",") if v.strip()]


def send_email(subject, body):
    if not ALERTS_ENABLED:
        return False
    recipients = parse_recipients(ALERT_TO)
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and recipients):
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return True


def build_state_alert(instance, prev_state, new_state):
    name = instance.get("name") or instance.get("instance_id") or "unknown"
    provider = instance.get("provider") or "unknown"
    region = instance.get("region") or "unknown"
    instance_id = instance.get("instance_id") or "unknown"
    subject = f"Cloud Watcher: {provider} instance {instance_id} is {new_state}"
    body = (
        f"Instance state change detected\\n\\n"
        f"Provider: {provider}\\n"
        f"Name: {name}\\n"
        f"Instance ID: {instance_id}\\n"
        f"Region: {region}\\n"
        f"Previous state: {prev_state}\\n"
        f"Current state: {new_state}\\n"
        f"Timestamp: {utc_now()}\\n"
    )
    return subject, body


def run_sync(source):
    started_at = utc_now()
    started_ts = time.time()
    results = {}
    total = 0

    for provider in ["aws", "azure"]:
        existing_states = get_instance_states(DB_PATH, provider)
        creds = get_credentials(DB_PATH, provider)
        if not creds:
            results[provider] = {"connected": False}
            continue

        connector = get_connector(provider)
        if not connector:
            results[provider] = {"connected": True, "error": "Connector not found"}
            continue

        try:
            items = connector.list_instances(creds)
            state_changes = []
            for inst in items:
                key = (inst.get("provider"), inst.get("instance_id"), inst.get("region"))
                prev_state = existing_states.get(key)
                new_state = inst.get("state")
                if (
                    prev_state
                    and new_state
                    and prev_state != new_state
                    and prev_state in ("running", "stopped")
                    and new_state in ("running", "stopped")
                ):
                    state_changes.append((inst, prev_state, new_state))

            upsert_instances(DB_PATH, items, utc_now())
            for inst, prev_state, new_state in state_changes:
                try:
                    subject, body = build_state_alert(inst, prev_state, new_state)
                    send_email(subject, body)
                except Exception:
                    pass
            results[provider] = {"connected": True, "count": len(items)}
            total += len(items)
        except Exception as exc:
            results[provider] = {"connected": True, "error": str(exc)}

    finished_at = utc_now()
    duration_ms = int((time.time() - started_ts) * 1000)
    try:
        insert_sync_log(DB_PATH, source, started_at, finished_at, duration_ms, total, results)
    except Exception:
        pass
    return results, total


def polling_loop():
    POLLING_STATE["running"] = True
    while True:
        try:
            run_sync("polling")
            POLLING_STATE["last_error"] = None
        except Exception as exc:
            POLLING_STATE["last_error"] = str(exc)
        POLLING_STATE["last_run"] = utc_now()
        time.sleep(POLL_INTERVAL_SECONDS)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/connect/<provider>", methods=["POST"])
def connect_provider(provider):
    provider = provider.lower()
    connector = get_connector(provider)
    if not connector:
        return jsonify({"ok": False, "error": "Unsupported provider"}), 400

    if not request.is_json:
        return jsonify({"ok": False, "error": "Expected JSON body"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

    # Minimal validation per provider
    required_fields = {
        "aws": ["access_key_id", "secret_access_key", "region"],
        "azure": ["tenant_id", "client_id", "client_secret", "subscription_id"],
    }[provider]

    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        upsert_credentials(DB_PATH, provider, data, utc_now())
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "provider": provider})


@app.route("/sync", methods=["POST"])
def sync_all():
    results, total = run_sync("manual")
    return jsonify({"ok": True, "results": results, "total": total})


@app.route("/instances", methods=["GET"])
def instances():
    provider = request.args.get("provider")
    try:
        rows = list_instances(DB_PATH, provider)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"count": len(rows), "items": rows})


@app.route("/polling/status", methods=["GET"])
def polling_status():
    return jsonify(
        {
            "enabled": POLLING_ENABLED,
            "interval_seconds": POLL_INTERVAL_SECONDS,
            "running": POLLING_STATE["running"],
            "last_run": POLLING_STATE["last_run"],
            "last_error": POLLING_STATE["last_error"],
        }
    )


@app.route("/sync/logs", methods=["GET"])
def sync_logs():
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid limit"}), 400
    limit = max(1, min(limit, 500))
    rows = list_sync_logs(DB_PATH, limit=limit)
    return jsonify({"count": len(rows), "items": rows})


if __name__ == "__main__":
    init_db(DB_PATH)
    should_start = POLLING_ENABLED and (
        os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    )
    if should_start:
        thread = threading.Thread(target=polling_loop, daemon=True)
        thread.start()
    app.run(host="0.0.0.0", port=5050, debug=True)
