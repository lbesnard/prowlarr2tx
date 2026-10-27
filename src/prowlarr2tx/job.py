import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from transmission_rpc import Client
from urllib3.util.retry import Retry

from .logs import job_logger
from .state import load_state, save_state


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def normalize_query(q):
    return unicodedata.normalize("NFKD", q).encode("ascii", "ignore").decode("ascii")


def make_session():
    session = requests.Session()
    retry = Retry(
        total=10,
        backoff_factor=3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def should_download(db, guid, grabs, min_grabs):
    entry = db.get(guid)
    if entry and (entry.get("never_download") or entry.get("downloaded")):
        return False
    return grabs >= min_grabs


def search(job, session):
    resp = session.get(
        urljoin(job.url, "/api/v1/search"),
        headers={"X-Api-Key": job.api_key},
        params={
            "indexerIds": str(job.indexer_id),
            "categories": str(job.category_id),
            "query": normalize_query(job.query),
            "limit": str(job.max_results),
        },
        timeout=job.timeout,
    )
    resp.raise_for_status()
    return resp.json()


def run_job(job, session=None, client=None):
    """Run one search/download pass. Returns the number of torrents added."""
    log = job_logger(job.name)
    session = session or make_session()
    db = load_state(job.state_path)

    results = search(job, session)
    log.info("Found %d items from Prowlarr", len(results))

    client = client or Client(
        host=job.tx_host,
        port=job.tx_port,
        username=job.tx_username,
        password=job.tx_password,
    )

    added = 0
    for rr in sorted(results, key=lambda x: x.get("grabs") or 0, reverse=True):
        guid = rr["guid"]
        grabs = int(rr.get("grabs") or 0)
        now = now_utc()
        entry = db.setdefault(
            guid,
            {
                "title": rr.get("title"),
                "first_seen": now,
                "last_seen": now,
                "last_grabs": grabs,
                "downloaded": False,
                "never_download": False,
            },
        )
        entry["last_seen"] = now
        entry["last_grabs"] = grabs

        if not should_download(db, guid, grabs, job.min_grabs):
            continue

        log.info("Downloading: %s (%d grabs)", rr.get("title"), grabs)
        try:
            torrent = session.get(rr["downloadUrl"], timeout=30)
            torrent.raise_for_status()
            client.add_torrent(torrent.content, download_dir=job.download_dir)
        except Exception as exc:  # one bad torrent must not abort the run
            log.error("Failed to add %s: %s", rr.get("title"), exc)
            continue

        entry["downloaded"] = True
        added += 1
        save_state(job.state_path, db)

    save_state(job.state_path, db)
    log.info("Search completed, %d added", added)
    return added
