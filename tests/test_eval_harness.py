from rag.eval.harness import run_eval


class DummyPipeline:
    def __init__(self):
        self.calls = 0

    def query_fast(self, question, filters=None, mode="default"):
        self.calls += 1
        return {
            "retrieval": [{"chunk_id": "c1"}, {"chunk_id": "c2"}],
            "llm": {"answer": f"Answer for {question}", "provenance": ["c1"]},
            "validation": {"valid": self.calls % 2 == 1, "issues": []},
            "latency_ms": {"total_ms": float(100 + self.calls)},
        }


class DummyFailingPipeline:
    def query_fast(self, question, filters=None, mode="default"):
        raise RuntimeError(f"boom: {question}")


def test_eval_harness_metrics_basic():
    pipeline = DummyPipeline()
    questions = [
        {
            "id": "q1",
            "question": "q1",
            "expected_chunks": ["c1"],
            "expected_answer_contains": ["answer"],
        },
        {
            "id": "q2",
            "question": "q2",
            "expected_chunks": ["c9"],
            "expected_answer_contains": ["answer"],
        },
    ]
    report = run_eval(pipeline, questions, mode="default")

    assert report["metrics"]["total_questions"] == 2
    assert report["metrics"]["retrieval_recall_at_k"] is not None
    assert report["metrics"]["citation_hit_rate"] == 1.0
    assert report["metrics"]["invalid_answer_rate"] == 0.5
    assert report["metrics"]["p95_latency_ms"] >= 100


def test_eval_harness_handles_query_exceptions():
    pipeline = DummyFailingPipeline()
    questions = [{"id": "q1", "question": "q1"}]

    report = run_eval(pipeline, questions, mode="default")

    assert report["metrics"]["total_questions"] == 1
    assert report["metrics"]["invalid_answer_rate"] == 1.0
    assert report["runs"][0]["error"]["code"] == "EVAL_QUERY_FAILED"
