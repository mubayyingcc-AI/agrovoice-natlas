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

                self._postgres = psycopg
                self._init_postgres()
            except Exception as exc:
                # Keep local/demo startup resilient, but expose the fallback in metrics.
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

    @property
    def backend(self) -> str:
        return "postgres" if self._postgres else "jsonl"

    def _init_postgres(self) -> None:
        with self._postgres.connect(self.database_url) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    interaction_id TEXT PRIMARY KEY,
                    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    session_id TEXT,
                    language TEXT NOT NULL,
                    transcription TEXT NOT NULL,
                    intent TEXT,
                    crop TEXT,
                    risk_level TEXT,
                    answer TEXT,
                    source_card_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                    requires_human BOOLEAN NOT NULL DEFAULT FALSE,
                    trace JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS farm_logs (
                    log_id TEXT PRIMARY KEY,
                    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    session_id TEXT,
                    language TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    activity_text TEXT NOT NULL,
                    crop TEXT
                )
                """
            )
            conn.commit()

    def _append(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            payload = {"recorded_at": datetime.now(timezone.utc).isoformat(), **record}
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append(self, record: dict) -> None:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                conn.execute(
                    """
                    INSERT INTO interactions
                    (interaction_id, session_id, language, transcription, intent, crop,
                     risk_level, answer, source_card_ids, requires_human, trace)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb)
                    ON CONFLICT (interaction_id) DO NOTHING
                    """,
                    (
                        record["interaction_id"], record.get("session_id"), record["language"],
                        record["transcription"], record.get("intent"), record.get("crop"),
                        record.get("risk_level"), record.get("answer"),
                        json.dumps(record.get("source_card_ids", [])), record.get("requires_human", False),
                        json.dumps(record.get("trace", {})),
                    ),
                )
                conn.commit()
            return
        self._append(self.path, record)

    def append_farm_log(self, record: dict) -> None:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                conn.execute(
                    """
                    INSERT INTO farm_logs
                    (log_id, session_id, language, activity, activity_text, crop)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (log_id) DO NOTHING
                    """,
                    (record["log_id"], record.get("session_id"), record["language"],
                     record["activity"], record["activity_text"], record.get("crop")),
                )
                conn.commit()
            return
        self._append(self.logs_path, record)

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _postgres_rows(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        where = "WHERE session_id = %s" if session_id else ""
        params: tuple[Any, ...] = (session_id, limit) if session_id else (limit,)
        with self._postgres.connect(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT interaction_id, recorded_at, session_id, language, transcription, intent, crop, risk_level, answer, source_card_ids, requires_human, trace FROM interactions {where} ORDER BY recorded_at DESC LIMIT %s",
                params,
            ).fetchall()
        names = ["interaction_id", "recorded_at", "session_id", "language", "transcription", "intent", "crop", "risk_level", "answer", "source_card_ids", "requires_human", "trace"]
        result = []
        for row in rows:
            item = dict(zip(names, row))
            if hasattr(item["recorded_at"], "isoformat"):
                item["recorded_at"] = item["recorded_at"].isoformat()
            result.append(item)
        return list(reversed(result))

    def history(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        if self._postgres:
            return self._postgres_rows(session_id=session_id, limit=limit)
        rows = self._read(self.path)
        if session_id:
            rows = [row for row in rows if row.get("session_id") == session_id]
        return rows[-limit:]

    def get(self, interaction_id: str) -> dict | None:
        if self._postgres:
            rows = self._postgres_rows(limit=200)
            return next((row for row in rows if row.get("interaction_id") == interaction_id), None)
        for row in self._read(self.path):
            if row.get("interaction_id") == interaction_id:
                return row
        return None

    def metrics(self) -> dict:
        if self._postgres:
            with self._postgres.connect(self.database_url) as conn:
                total = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
                sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM interactions WHERE session_id IS NOT NULL").fetchone()[0]
                escalated = conn.execute("SELECT COUNT(*) FROM interactions WHERE requires_human").fetchone()[0]
                farm_logs = conn.execute("SELECT COUNT(*) FROM farm_logs").fetchone()[0]
                by_language = {row[0]: row[1] for row in conn.execute("SELECT language, COUNT(*) FROM interactions GROUP BY language")}
            return {"total_interactions": total, "unique_sessions": sessions, "by_language": by_language, "escalated_cases": escalated, "farm_logs": farm_logs, "backend": "postgres", "warning": "Metrics are only meaningful after real pilot data is collected"}

        rows = self._read(self.path)
        by_language = {}
        for row in rows:
            language = row.get("language", "unknown")
            by_language[language] = by_language.get(language, 0) + 1
        return {"total_interactions": len(rows), "unique_sessions": len({row.get("session_id") for row in rows if row.get("session_id")}), "by_language": by_language, "escalated_cases": sum(1 for row in rows if row.get("requires_human")), "farm_logs": len(self._read(self.logs_path)), "backend": "jsonl", "warning": "Metrics are only meaningful after real pilot data is collected"}
