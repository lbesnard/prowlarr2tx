"""Job discovery and loading.

Layout (XDG by default, each directory overridable for containers):

    config dir  $PROWLARR2TX_CONFIG_DIR  ~/.config/prowlarr2tx   jobs/*.json
    state dir   $PROWLARR2TX_STATE_DIR   ~/.local/state/prowlarr2tx   <job>.json
    log dir     $PROWLARR2TX_LOG_DIR     ~/.local/state/prowlarr2tx/logs
"""

import json
import os
import re
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


def _env_dir(var, default):
    return Path(os.environ.get(var) or default).expanduser()


def config_dir():
    xdg = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return _env_dir("PROWLARR2TX_CONFIG_DIR", Path(xdg) / "prowlarr2tx")


def state_dir():
    xdg = os.environ.get("XDG_STATE_HOME") or "~/.local/state"
    return _env_dir("PROWLARR2TX_STATE_DIR", Path(xdg) / "prowlarr2tx")


def log_dir():
    return _env_dir("PROWLARR2TX_LOG_DIR", state_dir() / "logs")


@dataclass
class Job:
    name: str
    url: str
    api_key: str
    indexer_id: int
    category_id: int
    query: str
    min_grabs: int
    max_results: int
    tx_host: str
    tx_port: int
    tx_username: str
    tx_password: str
    download_dir: str
    tx_protocol: str = "http"
    tx_path: str = "/transmission/rpc"
    timeout: int = 90
    interval_hours: float = 1.0
    state_path: Path = field(default=None)


def _require(section, key, where):
    try:
        return section[key]
    except (KeyError, TypeError):
        raise ConfigError(f"{where}: missing '{key}'") from None


def parse_transmission(tx, where):
    """Accept host as a bare name or a URL like https://host[:port][/rpc/path]."""
    host = str(_require(tx, "host", where))
    protocol = tx.get("protocol", "http")
    path = tx.get("path", "/transmission/rpc")
    port = tx.get("port")
    if "://" in host:
        parts = urlsplit(host)
        protocol = parts.scheme
        host = parts.hostname or ""
        port = port or parts.port
        if parts.path.strip("/"):
            path = parts.path
    if protocol not in ("http", "https") or not host:
        raise ConfigError(f"{where}: invalid transmission host/protocol")
    return host, int(port or (443 if protocol == "https" else 9091)), protocol, path


def load_job(path, name=None):
    path = Path(path)
    name = name or path.stem
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc

    where = str(path)
    prowlarr = _require(raw, "prowlarr", where)
    tx = _require(raw, "transmission", where)
    search = _require(raw, "search", where)

    tx_host, tx_port, tx_protocol, tx_path = parse_transmission(tx, where)
    env_key = "PROWLARR2TX_API_KEY_" + re.sub(r"\W", "_", name).upper()
    api_key = os.environ.get(env_key) or _require(prowlarr, "api_key", where)

    return Job(
        name=name,
        url=_require(prowlarr, "url", where),
        api_key=api_key,
        indexer_id=_require(prowlarr, "indexer_id", where),
        category_id=_require(prowlarr, "category_id", where),
        timeout=int(prowlarr.get("timeout", 90)),
        query=_require(search, "query", where),
        min_grabs=int(search.get("min_grabs", 0)),
        max_results=int(search.get("max_results", 100)),
        tx_host=tx_host,
        tx_port=tx_port,
        tx_protocol=tx_protocol,
        tx_path=tx_path,
        tx_username=tx.get("username"),
        tx_password=tx.get("password"),
        download_dir=_require(tx, "download_dir", where),
        interval_hours=float(raw.get("interval_hours", 1)),
        state_path=state_dir() / f"{raw.get('state', name)}.json",
    )


def discover_jobs(directory=None):
    jobs_dir = Path(directory) if directory else config_dir() / "jobs"
    if not jobs_dir.is_dir():
        raise ConfigError(f"jobs directory not found: {jobs_dir}")
    paths = sorted(jobs_dir.glob("*.json"))
    if not paths:
        raise ConfigError(f"no *.json jobs in {jobs_dir}")
    return [load_job(p) for p in paths]
