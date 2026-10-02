from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .store import StateStore
from .types import now


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    version: int
    instructions: str
    status: str
    checksum: str


class SkillStore:
    """Versioned skill candidates; only promoted versions may be selected at runtime."""
    def __init__(self, store: StateStore) -> None:
        self.store = store
        with store.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS skills(
                name TEXT NOT NULL, version INTEGER NOT NULL, instructions TEXT NOT NULL,
                status TEXT NOT NULL, checksum TEXT NOT NULL, metadata TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY(name, version))""")

    def propose(self, name: str, instructions: str, metadata: dict | None = None) -> Skill:
        if not name.replace("-", "").replace("_", "").isalnum() or not instructions.strip():
            raise ValueError("skill name and instructions are required")
        with self.store.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version), 0) AS version FROM skills WHERE name=?", (name,)).fetchone()
            version = row["version"] + 1
            checksum = hashlib.sha256(instructions.encode()).hexdigest()
            conn.execute("INSERT INTO skills VALUES(?,?,?,?,?,?,?)", (name, version, instructions, "candidate", checksum, json.dumps(metadata or {}), now()))
        return Skill(name, version, instructions, "candidate", checksum)

    def promote(self, name: str, version: int, tests_passed: bool) -> Skill:
        if not tests_passed: raise ValueError("a skill cannot be promoted without passing tests")
        with self.store.connect() as conn:
            row = conn.execute("SELECT * FROM skills WHERE name=? AND version=?", (name, version)).fetchone()
            if not row: raise KeyError(f"unknown skill {name}@{version}")
            conn.execute("UPDATE skills SET status='retired' WHERE name=? AND status='promoted'", (name,))
            conn.execute("UPDATE skills SET status='promoted' WHERE name=? AND version=?", (name, version))
        return Skill(name, version, row["instructions"], "promoted", row["checksum"])

    def load(self, name: str) -> Skill | None:
        with self.store.connect() as conn:
            row = conn.execute("SELECT * FROM skills WHERE name=? AND status='promoted'", (name,)).fetchone()
        return Skill(row["name"], row["version"], row["instructions"], row["status"], row["checksum"]) if row else None
