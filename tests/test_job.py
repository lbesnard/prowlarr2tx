from pathlib import Path

from prowlarr2tx.config import Job
from prowlarr2tx.job import run_job, should_download
from prowlarr2tx.logs import RedactFilter
from prowlarr2tx.state import load_state

import logging


def make_job(tmp_path):
    return Job(
        name="t", url="http://p", api_key="k", indexer_id=1, category_id=1000,
        query="x", min_grabs=10, max_results=5, tx_host="h", tx_port=9091,
        tx_username=None, tx_password=None, download_dir="/d",
        state_path=tmp_path / "t.json",
    )


class Resp:
    def __init__(self, payload=None, content=b"t"):
        self._p, self.content = payload, content

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, results):
        self.results = results

    def get(self, url, **kw):
        return Resp(self.results) if "search" in url else Resp()


class FakeClient:
    def __init__(self):
        self.added = []

    def add_torrent(self, content, download_dir):
        self.added.append(download_dir)


def test_should_download():
    db = {"d": {"downloaded": True}, "n": {"never_download": True}, "s": {}}
    assert not should_download(db, "d", 999, 10)
    assert not should_download(db, "n", 999, 10)
    assert should_download(db, "s", 10, 10)
    assert not should_download(db, "new", 9, 10)


def test_run_downloads_once(tmp_path):
    job = make_job(tmp_path)
    results = [
        {"guid": "a", "title": "A", "grabs": 50, "downloadUrl": "http://d/a"},
        {"guid": "b", "title": "B", "grabs": 1, "downloadUrl": "http://d/b"},
    ]
    client = FakeClient()
    assert run_job(job, FakeSession(results), client) == 1
    assert run_job(job, FakeSession(results), client) == 0  # no re-download
    assert len(client.added) == 1
    db = load_state(job.state_path)
    assert db["a"]["downloaded"] and not db["b"]["downloaded"]


def test_api_key_redacted():
    rec = logging.LogRecord("x", logging.INFO, "", 0, "GET http://h/1/download?apikey=SECRET&link=z", (), None)
    RedactFilter().filter(rec)
    assert "SECRET" not in rec.getMessage()


def test_job_name_completion(tmp_path):
    import argparse
    import shutil
    from prowlarr2tx.cli import complete_jobs

    example = Path(__file__).parent.parent / "examples" / "job.example.json"
    for name in ("alpha", "beta"):
        shutil.copy(example, tmp_path / f"{name}.json")
    ns = argparse.Namespace(jobs_dir=str(tmp_path), jobs=["beta"])
    assert complete_jobs("", ns) == ["alpha"]
    assert complete_jobs("z", ns) == []
