import json
import os
from datetime import datetime, timezone
from pathlib import Path

class InteractionStore:
    def __init__(self):
        self.path = Path(os.getenv("DATA_DIR", "data")) / "interactions.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            payload = {"recorded_at": datetime.now(timezone.utc).isoformat(), **record}
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
