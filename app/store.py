import json
import os
from datetime import datetime, timezone
from pathlib import Path

class InteractionStore:
    def __init__(self):
        self.data_dir = Path(os.getenv("DATA_DIR", "data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "interactions.jsonl"
        self.logs_path = self.data_dir / "farm_logs.jsonl"

    def _append(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            payload = {"recorded_at": datetime.now(timezone.utc).isoformat(), **record}
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append(self, record: dict) -> None:
        self._append(self.path, record)

    def append_farm_log(self, record: dict) -> None:
        self._append(self.logs_path, record)

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def history(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        rows = self._read(self.path)
        if session_id:
            rows = [row for row in rows if row.get("session_id") == session_id]
        return rows[-limit:]

    def metrics(self) -> dict:
        rows = self._read(self.path)
        by_language = {}
        for row in rows:
            language = row.get("language", "unknown")
            by_language[language] = by_language.get(language, 0) + 1
        return {
            "total_interactions": len(rows),
            "unique_sessions": len({row.get("session_id") for row in rows if row.get("session_id")} ),
            "by_language": by_language,
            "escalated_cases": sum(1 for row in rows if row.get("requires_human")),
            "farm_logs": len(self._read(self.logs_path)),
            "warning": "Metrics are only meaningful after real pilot data is collected"
        }
