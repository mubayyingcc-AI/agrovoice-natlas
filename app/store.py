import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class InteractionStore:
    """Durable PostgreSQL store with JSONL fallback for local development."""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self._postgres = None
        if self.database_url:
            try:
                import psycopg
                from psycopg.types.json import Jsonb
                self._postgres = psycopg
                self._jsonb = Jsonb
                self._init_postgres()
            except Exception as exc:
                self._postgres = None
                self._database_error = str(exc)
        project_root = Path(__file__).resolve().parent.parent
        configured = os.getenv("DATA_DIR")
        self.data_dir = Path(configured) if configured else project_root / "data"
        if not self.data_dir.is_absolute():
            self.data_dir = project_root / self.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "interactions.jsonl"
        self.logs_path = self.data_dir / "farm_logs.jsonl"
        self.escalations_path = self.data_dir / "escalations.jsonl"

    @property
    def backend(self) -> str:
        return "postgres" if self._postgres else "jsonl"

    def _init_postgres(self) -> None:
        with self._postgres.connect(self.database_url) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), session_id TEXT,
                language TEXT NOT NULL, transcription TEXT NOT NULL, intent TEXT, crop TEXT, risk_level TEXT,
                answer TEXT, source_card_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                requires_human BOOLEAN NOT NULL DEFAULT FALSE, trace JSONB NOT NULL DEFAULT '{}'::jsonb)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS farm_logs (
                log_id TEXT PRIMARY KEY, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), session_id TEXT,
                language TEXT NOT NULL, activity TEXT NOT NULL, activity_text TEXT NOT NULL, crop TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS escalations (
                escalation_id TEXT PRIMARY KEY, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                source_interaction_id TEXT REFERENCES interactions(interaction_id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'open', reason TEXT NOT NULL, assigned_to TEXT,
                resolution_note TEXT, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            conn.commit()

    def _append(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"recorded_at": datetime.now(timezone.utc).isoformat(), **record}, ensure_ascii=False) + "\n")

    def append(self, record: dict) -> None:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                conn.execute("""INSERT INTO interactions
                    (interaction_id, session_id, language, transcription, intent, crop, risk_level, answer,
                     source_card_ids, requires_human, trace)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                    ON CONFLICT (interaction_id) DO NOTHING""", (
                    record["interaction_id"], record.get("session_id"), record["language"], record["transcription"],
                    record.get("intent"), record.get("crop"), record.get("risk_level"), record.get("answer"),
                    self._jsonb(record.get("source_card_ids", [])), record.get("requires_human", False), self._jsonb(record.get("trace", {}))))
                conn.commit()
            return
        self._append(self.path, record)

    def append_farm_log(self, record: dict) -> None:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                conn.execute("""INSERT INTO farm_logs (log_id, session_id, language, activity, activity_text, crop)
                    VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (log_id) DO NOTHING""", (
                    record["log_id"], record.get("session_id"), record["language"], record["activity"], record["activity_text"], record.get("crop")))
                conn.commit()
            return
        self._append(self.logs_path, record)

    def create_escalation(self, record: dict) -> dict:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                row = conn.execute("""INSERT INTO escalations (escalation_id, source_interaction_id, status, reason, assigned_to)
                    VALUES (%s, %s, %s, %s, %s) RETURNING escalation_id, source_interaction_id, status, reason, assigned_to, resolution_note""", (
                    record["escalation_id"], record.get("source_interaction_id"), record.get("status", "open"), record["reason"], record.get("assigned_to"))).fetchone()
                conn.commit()
            return self._escalation_dict(row)
        payload = {"recorded_at": datetime.now(timezone.utc).isoformat(), **record}
        self._append(self.escalations_path, record)
        return payload

    @staticmethod
    def _escalation_dict(row) -> dict:
        names = ["escalation_id", "source_interaction_id", "status", "reason", "assigned_to", "resolution_note"]
        return dict(zip(names, row))

    def list_escalations(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                if status:
                    rows = conn.execute("SELECT escalation_id, source_interaction_id, status, reason, assigned_to, resolution_note FROM escalations WHERE status=%s ORDER BY recorded_at DESC LIMIT %s", (status, limit)).fetchall()
                else:
                    rows = conn.execute("SELECT escalation_id, source_interaction_id, status, reason, assigned_to, resolution_note FROM escalations ORDER BY recorded_at DESC LIMIT %s", (limit,)).fetchall()
            return [self._escalation_dict(row) for row in rows]
        rows = self._read(self.escalations_path)
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows[-limit:][::-1]

    def update_escalation(self, escalation_id: str, update: dict) -> dict | None:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                row = conn.execute("""UPDATE escalations SET status=%s, assigned_to=%s, resolution_note=%s, updated_at=NOW()
                    WHERE escalation_id=%s RETURNING escalation_id, source_interaction_id, status, reason, assigned_to, resolution_note""", (
                    update["status"], update.get("assigned_to"), update.get("resolution_note"), escalation_id)).fetchone()
                conn.commit()
            return self._escalation_dict(row) if row else None
        rows = self._read(self.escalations_path)
        for row in rows:
            if row.get("escalation_id") == escalation_id:
                row.update(update)
                self.escalations_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
                return row
        return None

    def _read(self, path: Path) -> list[dict]:
        if not path.exists(): return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _postgres_rows(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        where = "WHERE session_id = %s" if session_id else ""
        params = (session_id, limit) if session_id else (limit,)
        with self._postgres.connect(self.database_url) as conn:
            rows = conn.execute(f"SELECT interaction_id, recorded_at, session_id, language, transcription, intent, crop, risk_level, answer, source_card_ids, requires_human, trace FROM interactions {where} ORDER BY recorded_at DESC LIMIT %s", params).fetchall()
        names = ["interaction_id", "recorded_at", "session_id", "language", "transcription", "intent", "crop", "risk_level", "answer", "source_card_ids", "requires_human", "trace"]
        result = []
        for row in rows:
            item = dict(zip(names, row))
            if hasattr(item["recorded_at"], "isoformat"): item["recorded_at"] = item["recorded_at"].isoformat()
            result.append(item)
        return list(reversed(result))

    def history(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        if self._postgres: return self._postgres_rows(session_id, limit)
        rows = self._read(self.path)
        if session_id: rows = [row for row in rows if row.get("session_id") == session_id]
        return rows[-limit:]

    def get(self, interaction_id: str) -> dict | None:
        if self._postgres: return next((row for row in self._postgres_rows(limit=200) if row.get("interaction_id") == interaction_id), None)
        return next((row for row in self._read(self.path) if row.get("interaction_id") == interaction_id), None)

    def metrics(self) -> dict:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                total = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
                sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM interactions WHERE session_id IS NOT NULL").fetchone()[0]
                escalated = conn.execute("SELECT COUNT(*) FROM interactions WHERE requires_human").fetchone()[0]
                farm_logs = conn.execute("SELECT COUNT(*) FROM farm_logs").fetchone()[0]
                open_escalations = conn.execute("SELECT COUNT(*) FROM escalations WHERE status='open'").fetchone()[0]
                by_language = {row[0]: row[1] for row in conn.execute("SELECT language, COUNT(*) FROM interactions GROUP BY language")}
            return {"total_interactions": total, "unique_sessions": sessions, "by_language": by_language, "escalated_cases": escalated, "open_escalations": open_escalations, "farm_logs": farm_logs, "backend": "postgres", "warning": "Metrics are only meaningful after real pilot data is collected"}
        rows = self._read(self.path)
        by_language = {}
        for row in rows: by_language[row.get("language", "unknown")] = by_language.get(row.get("language", "unknown"), 0) + 1
        return {"total_interactions": len(rows), "unique_sessions": len({row.get("session_id") for row in rows if row.get("session_id")}), "by_language": by_language, "escalated_cases": sum(1 for row in rows if row.get("requires_human")), "open_escalations": len([x for x in self._read(self.escalations_path) if x.get("status") == "open"]), "farm_logs": len(self._read(self.logs_path)), "backend": "jsonl", "warning": "Metrics are only meaningful after real pilot data is collected"}
