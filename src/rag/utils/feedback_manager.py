import json
import time
import uuid
from pathlib import Path


class FeedbackManager:
    def __init__(self, data_dir: Path):
        self.feedback_file = data_dir / "feedback.jsonl"
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

    def log_feedback(
        self,
        answer_id: str,
        rating: int,
        comment: str | None = None,
        query: str = "",
        answer: str = "",
    ):
        """
        rating: 1 for positive, -1 for negative
        """
        entry = {
            "timestamp": time.time(),
            "feedback_id": uuid.uuid4().hex,
            "answer_id": answer_id,
            "query": query,
            "answer": answer,
            "rating": rating,
            "comment": comment or "",
        }

        # Append to JSONL file
        with open(self.feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_stats(self):
        if not self.feedback_file.exists():
            return {"positive": 0, "negative": 0, "total": 0}

        pos = 0
        neg = 0
        with open(self.feedback_file, encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data["rating"] > 0:
                        pos += 1
                    else:
                        neg += 1
                except json.JSONDecodeError:
                    pass
        return {"positive": pos, "negative": neg, "total": pos + neg}
