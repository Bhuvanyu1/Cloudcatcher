from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class InsertOneResult:
    inserted_id: str


@dataclass
class InsertManyResult:
    inserted_ids: List[str]


@dataclass
class UpdateResult:
    matched_count: int
    modified_count: int


@dataclass
class DeleteResult:
    deleted_count: int


class SQLiteDatabase:
    """Small async document-store facade over native SQLite.

    This adapter intentionally supports only the Mongo/Motor subset currently
    used by the app. It keeps demo persistence local while preserving existing
    call sites such as `db.users.find_one(...)`.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._collections: Dict[str, SQLiteCollection] = {}

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    collection TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, doc_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_collection
                ON documents(collection)
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def __getattr__(self, collection_name: str) -> "SQLiteCollection":
        if collection_name.startswith("_"):
            raise AttributeError(collection_name)
        if collection_name not in self._collections:
            self._collections[collection_name] = SQLiteCollection(self, collection_name)
        return self._collections[collection_name]

    async def close(self) -> None:
        return None


class SQLiteCollection:
    def __init__(self, database: SQLiteDatabase, name: str) -> None:
        self.database = database
        self.name = name

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        doc = dict(document)
        doc_id = self._document_id(doc)
        await asyncio.to_thread(self._upsert_sync, doc_id, doc)
        return InsertOneResult(inserted_id=doc_id)

    async def insert_many(self, documents: Iterable[Dict[str, Any]]) -> InsertManyResult:
        docs = [dict(document) for document in documents]
        inserted_ids = [self._document_id(doc) for doc in docs]
        await asyncio.to_thread(self._upsert_many_sync, list(zip(inserted_ids, docs)))
        return InsertManyResult(inserted_ids=inserted_ids)

    def find(
        self,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> "SQLiteCursor":
        return SQLiteCursor(self, query or {}, projection)

    async def find_one(
        self,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[Sequence[Tuple[str, int]]] = None,
    ) -> Optional[Dict[str, Any]]:
        docs = await self.find(query, projection).sort(sort or []).limit(1).to_list(1)
        return docs[0] if docs else None

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> UpdateResult:
        docs = await asyncio.to_thread(self._find_raw_sync, query)
        if not docs:
            return UpdateResult(matched_count=0, modified_count=0)

        doc_id, doc = docs[0]
        updated_doc = self._apply_update(doc, update)
        await asyncio.to_thread(self._upsert_sync, doc_id, updated_doc)
        return UpdateResult(matched_count=1, modified_count=1)

    async def delete_one(self, query: Dict[str, Any]) -> DeleteResult:
        docs = await asyncio.to_thread(self._find_raw_sync, query)
        if not docs:
            return DeleteResult(deleted_count=0)

        doc_id, _ = docs[0]
        await asyncio.to_thread(self._delete_ids_sync, [doc_id])
        return DeleteResult(deleted_count=1)

    async def delete_many(self, query: Optional[Dict[str, Any]] = None) -> DeleteResult:
        docs = await asyncio.to_thread(self._find_raw_sync, query or {})
        doc_ids = [doc_id for doc_id, _ in docs]
        if doc_ids:
            await asyncio.to_thread(self._delete_ids_sync, doc_ids)
        return DeleteResult(deleted_count=len(doc_ids))

    async def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        docs = await asyncio.to_thread(self._find_raw_sync, query or {})
        return len(docs)

    def _document_id(self, document: Dict[str, Any]) -> str:
        return str(
            document.get("id")
            or document.get("action_id")
            or document.get("token")
            or uuid.uuid4()
        )

    def _upsert_sync(self, doc_id: str, document: Dict[str, Any]) -> None:
        with self.database._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents(collection, doc_id, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(collection, doc_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self.name, doc_id, json.dumps(document, default=str)),
            )
            conn.commit()

    def _upsert_many_sync(self, rows: List[Tuple[str, Dict[str, Any]]]) -> None:
        if not rows:
            return
        with self.database._connect() as conn:
            conn.executemany(
                """
                INSERT INTO documents(collection, doc_id, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(collection, doc_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (self.name, doc_id, json.dumps(document, default=str))
                    for doc_id, document in rows
                ],
            )
            conn.commit()

    def _find_raw_sync(self, query: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        with self.database._connect() as conn:
            rows = conn.execute(
                "SELECT doc_id, data FROM documents WHERE collection = ?",
                (self.name,),
            ).fetchall()

        docs: List[Tuple[str, Dict[str, Any]]] = []
        for row in rows:
            doc = json.loads(row["data"])
            if _matches_query(doc, query):
                docs.append((row["doc_id"], doc))
        return docs

    def _delete_ids_sync(self, doc_ids: List[str]) -> None:
        if not doc_ids:
            return
        with self.database._connect() as conn:
            conn.executemany(
                "DELETE FROM documents WHERE collection = ? AND doc_id = ?",
                [(self.name, doc_id) for doc_id in doc_ids],
            )
            conn.commit()

    @staticmethod
    def _apply_update(document: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        updated = dict(document)
        if "$set" in update:
            for key, value in update["$set"].items():
                _set_nested_value(updated, key, value)
            return updated

        for key, value in update.items():
            _set_nested_value(updated, key, value)
        return updated


class SQLiteCursor:
    def __init__(
        self,
        collection: SQLiteCollection,
        query: Dict[str, Any],
        projection: Optional[Dict[str, int]],
    ) -> None:
        self.collection = collection
        self.query = query
        self.projection = projection
        self._skip = 0
        self._limit: Optional[int] = None
        self._sort: List[Tuple[str, int]] = []

    def skip(self, count: int) -> "SQLiteCursor":
        self._skip = max(0, count)
        return self

    def limit(self, count: int) -> "SQLiteCursor":
        self._limit = max(0, count)
        return self

    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "SQLiteCursor":
        if isinstance(key_or_list, str):
            self._sort = [(key_or_list, direction if direction is not None else 1)]
        elif key_or_list:
            self._sort = [(field, sort_dir) for field, sort_dir in key_or_list]
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        raw_docs = await asyncio.to_thread(self.collection._find_raw_sync, self.query)
        docs = [doc for _, doc in raw_docs]

        for field, direction in reversed(self._sort):
            docs.sort(
                key=lambda doc: _sort_value(_get_nested_value(doc, field)),
                reverse=direction < 0,
            )

        if self._skip:
            docs = docs[self._skip :]

        effective_limit = self._limit
        if length is not None:
            effective_limit = min(effective_limit, length) if effective_limit is not None else length
        if effective_limit is not None:
            docs = docs[:effective_limit]

        return [_project_document(doc, self.projection) for doc in docs]

    async def distinct(self, field: str) -> List[Any]:
        docs = await self.to_list(None)
        values = []
        seen = set()
        for doc in docs:
            value = _get_nested_value(doc, field)
            key = json.dumps(value, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                values.append(value)
        return values


def _matches_query(document: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for key, expected in query.items():
        actual = _get_nested_value(document, key)
        if isinstance(expected, dict):
            if not _matches_operator(actual, expected):
                return False
        elif actual != expected:
            return False
    return True


def _matches_operator(actual: Any, expected: Dict[str, Any]) -> bool:
    for operator, value in expected.items():
        if operator == "$options":
            continue
        if operator == "$ne":
            if actual == value:
                return False
        elif operator == "$in":
            if actual not in value:
                return False
        elif operator == "$lt":
            if actual is None or not actual < value:
                return False
        elif operator == "$regex":
            flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
            if actual is None or re.search(str(value), str(actual), flags) is None:
                return False
        else:
            raise ValueError(f"Unsupported SQLite query operator: {operator}")
    return True


def _get_nested_value(document: Dict[str, Any], dotted_key: str) -> Any:
    current: Any = document
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_nested_value(document: Dict[str, Any], dotted_key: str, value: Any) -> None:
    current = document
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _project_document(
    document: Dict[str, Any],
    projection: Optional[Dict[str, int]],
) -> Dict[str, Any]:
    projected = dict(document)
    projected.pop("_id", None)

    if not projection:
        return projected

    excluding = all(not value for value in projection.values())
    if excluding:
        for key, include in projection.items():
            if not include:
                projected.pop(key, None)
        return projected

    included = {
        key: _get_nested_value(document, key)
        for key, include in projection.items()
        if include and _get_nested_value(document, key) is not None
    }
    return included


def _sort_value(value: Any) -> Tuple[bool, str]:
    return (value is None, "" if value is None else str(value))
