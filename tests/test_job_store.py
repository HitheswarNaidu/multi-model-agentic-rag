from rag.utils.job_store import JobStore


def test_job_store_create_update_get(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")

    job_id = store.create_job(
        {
            "status": "queued",
            "total_files": 0,
            "processed_files": 0,
            "chunks_indexed": 0,
        }
    )
    job = store.get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == "queued"

    store.update_job(job_id, {"status": "running", "processed_files": 1})
    updated = store.get_job(job_id)
    assert updated["status"] == "running"
    assert updated["processed_files"] == 1

