from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .store import StateStore
from .types import now

_TOKEN = re.compile(r"[\w'-]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Memory:
    kind: str
    content: str
    importance: float = 0.5
    metadata: dict | None = None


class MemoryStore:
    """Persistent, privacy-scoped memory with transparent lexical retrieval.

    Semantic/vector retrieval is intentionally pluggable; no unsupported model claim is made.
    """
    ALLOWED_KINDS = {"conversation", "long_term", "semantic", "episodic", "procedural", "user", "project", "failure", "skill"}

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def remember(self, user_id: str, memory: Memory) -> None:
        if memory.kind not in self.ALLOWED_KINDS:
            raise ValueError(f"unknown memory kind: {memory.kind}")
        if not memory.content.strip() or memory.importance < 0 or memory.importance > 1:
            raise ValueError("memory content and importance must be valid")
        timestamp = now()
        with self.store.connect() as conn:
            conn.execute("INSERT INTO memories(user_id,kind,content,importance,metadata,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                         (user_id, memory.kind, memory.content.strip(), memory.importance,
                          json.dumps(memory.metadata or {}, ensure_ascii=False), timestamp, timestamp))

    def retrieve(self, user_id: str, query: str, limit: int = 5) -> list[Memory]:
        terms = set(_TOKEN.findall(query.lower()))
        with self.store.connect() as conn:
            rows = conn.execute("SELECT kind,content,importance,metadata FROM memories WHERE user_id=?", (user_id,)).fetchall()
        def score(row: object) -> tuple[float, float]:
            content_terms = set(_TOKEN.findall(row["content"].lower()))
            overlap = len(terms & content_terms) / max(len(terms), 1)
            return (overlap * 0.75 + row["importance"] * 0.25, row["importance"])
        ranked = sorted(rows, key=score, reverse=True)
        return [Memory(r["kind"], r["content"], r["importance"], json.loads(r["metadata"])) for r in ranked[:limit] if score(r)[0] > 0]
