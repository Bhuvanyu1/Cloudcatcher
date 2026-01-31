import json
import sqlite3


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            provider TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS instances (
            provider TEXT NOT NULL,
            account TEXT,
            region TEXT,
            instance_id TEXT NOT NULL,
            name TEXT,
            size TEXT,
            state TEXT,
            public_ip TEXT,
            private_ip TEXT,
            tags TEXT,
            raw TEXT,
            updated_at TEXT,
            PRIMARY KEY (provider, instance_id, region)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            total INTEGER NOT NULL,
            results TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_credentials(db_path, provider, data, updated_at):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO credentials (provider, data, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            data=excluded.data,
            updated_at=excluded.updated_at
        """,
        (provider, json.dumps(data), updated_at),
    )
    conn.commit()
    conn.close()


def get_credentials(db_path, provider):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT data FROM credentials WHERE provider = ?", (provider,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["data"])


def upsert_instances(db_path, instances, updated_at):
    if not instances:
        return
    conn = get_conn(db_path)
    cur = conn.cursor()
    for inst in instances:
        cur.execute(
            """
            INSERT INTO instances (
                provider, account, region, instance_id, name, size, state,
                public_ip, private_ip, tags, raw, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, instance_id, region) DO UPDATE SET
                account=excluded.account,
                name=excluded.name,
                size=excluded.size,
                state=excluded.state,
                public_ip=excluded.public_ip,
                private_ip=excluded.private_ip,
                tags=excluded.tags,
                raw=excluded.raw,
                updated_at=excluded.updated_at
            """,
            (
                inst.get("provider"),
                inst.get("account"),
                inst.get("region"),
                inst.get("instance_id"),
                inst.get("name"),
                inst.get("size"),
                inst.get("state"),
                inst.get("public_ip"),
                inst.get("private_ip"),
                json.dumps(inst.get("tags") or {}, default=str),
                json.dumps(inst.get("raw") or {}, default=str),
                updated_at,
            ),
        )
    conn.commit()
    conn.close()


def list_instances(db_path, provider=None):
    conn = get_conn(db_path)
    cur = conn.cursor()
    if provider:
        cur.execute("SELECT * FROM instances WHERE provider = ?", (provider,))
    else:
        cur.execute("SELECT * FROM instances")
    rows = cur.fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(row)
        item["tags"] = json.loads(item["tags"]) if item.get("tags") else {}
        item["raw"] = json.loads(item["raw"]) if item.get("raw") else {}
        items.append(item)
    return items


def get_instance_states(db_path, provider):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT provider, instance_id, region, state FROM instances WHERE provider = ?",
        (provider,),
    )
    rows = cur.fetchall()
    conn.close()
    states = {}
    for row in rows:
        key = (row["provider"], row["instance_id"], row["region"])
        states[key] = row["state"]
    return states


def insert_sync_log(db_path, source, started_at, finished_at, duration_ms, total, results):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sync_logs (source, started_at, finished_at, duration_ms, total, results)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            started_at,
            finished_at,
            duration_ms,
            total,
            json.dumps(results, default=str),
        ),
    )
    conn.commit()
    conn.close()


def list_sync_logs(db_path, limit=100):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM sync_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    items = []
    for row in rows:
        item = dict(row)
        item["results"] = json.loads(item["results"]) if item.get("results") else {}
        items.append(item)
    return items
