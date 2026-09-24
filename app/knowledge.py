import json
import os
from pathlib import Path

class KnowledgeBase:
    def __init__(self, path: str | None = None):
        project_root = Path(__file__).resolve().parent.parent
        configured = path or os.getenv("KNOWLEDGE_PATH")
        self.path = Path(configured) if configured else project_root / "data" / "knowledge_cards.json"
        if not self.path.is_absolute():
            self.path = project_root / self.path
        self.cards = json.loads(self.path.read_text())

    def retrieve(self, crop: str | None, query: str) -> list[dict]:
        terms = set(query.lower().split())
        candidates = []
        for card in self.cards:
            if card["review_status"] != "approved":
                continue
            if crop and card["crop"] != crop:
                continue
            score = len(terms.intersection(set(card["keywords"])))
            if score or not crop:
                candidates.append((score, card))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [card for _, card in candidates[:3]]
