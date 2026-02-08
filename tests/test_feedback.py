import json

from rag.utils.feedback_manager import FeedbackManager


def test_feedback_logging(tmp_path):
    fm = FeedbackManager(tmp_path)

    fm.log_feedback("ans1", 1, "Great!", "q1", "a1")
    fm.log_feedback("ans2", -1, "Bad!", "q2", "a2")

    stats = fm.get_stats()
    assert stats["positive"] == 1
    assert stats["negative"] == 1
    assert stats["total"] == 2

    # Check file content
    lines = list(fm.feedback_file.read_text(encoding="utf-8").splitlines())
    assert len(lines) == 2
    d1 = json.loads(lines[0])
    assert d1["answer_id"] == "ans1"
    assert d1["rating"] == 1
