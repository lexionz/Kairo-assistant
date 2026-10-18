import json
import sqlite3
import time
import uuid
from pathlib import Path


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.directory / "kairo.sqlite", check_same_thread=False)
        self.db.executescript("CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, at REAL, task TEXT, tool TEXT, outcome TEXT, evidence TEXT); CREATE TABLE IF NOT EXISTS memory(id TEXT PRIMARY KEY, text TEXT); CREATE TABLE IF NOT EXISTS knowledge(id TEXT PRIMARY KEY, payload TEXT, expires REAL);")

    def record(self, task, tool, outcome, evidence=None):
        with self.db:
            self.db.execute("INSERT INTO audit VALUES(?,?,?,?,?,?)", (uuid.uuid4().hex, time.time(), task, tool, outcome, json.dumps(evidence or {})))

    def remember(self, text):
        if not text.strip() or len(text) > 2000:
            raise ValueError("Memory must contain 1–2000 characters")
        identity = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO memory VALUES(?,?)", (identity, text))
        return {"saved": identity}

    def memories(self):
        return [{"id": row[0], "text": row[1]} for row in self.db.execute("SELECT id,text FROM memory LIMIT 100")]

    def forget(self, identity):
        with self.db:
            self.db.execute("DELETE FROM memory WHERE id=?", (identity,))
            self.db.execute("DELETE FROM knowledge WHERE id=?", (identity,))

    def knowledge(self):
        return [{"id": row[0], **json.loads(row[1]), "expired": row[2] <= time.time()} for row in self.db.execute("SELECT id,payload,expires FROM knowledge LIMIT 100")]

    def save_knowledge(self, proposal):
        payload = json.dumps(proposal, ensure_ascii=False)
        if len(payload) > 32000 or proposal["verification"]["status"] != "corroborated":
            raise ValueError("Knowledge proposal is oversized or unverified")
        identity = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO knowledge VALUES(?,?,?)", (identity, payload, proposal["review_after"]))
        return {"saved": identity, "review_after": proposal["review_after"]}

    def recall(self, query):
        words = set(query.casefold().split())
        records = [{"id": row[0], "text": row[1]} for row in self.db.execute("SELECT id,text FROM memory")]
        records += [{"id": row[0], **json.loads(row[1])} for row in self.db.execute("SELECT id,payload FROM knowledge WHERE expires > ?", (time.time(),))]
        ranked = sorted(records, key=lambda item: sum(word in json.dumps(item).casefold() for word in words), reverse=True)
        return ranked[:8]

    def activity(self):
        return [{"at": row[0], "tool": row[1], "outcome": row[2], "evidence": json.loads(row[3])} for row in self.db.execute("SELECT at,tool,outcome,evidence FROM audit ORDER BY at DESC LIMIT 100")]

    def close(self):
        self.db.close()
