import argparse
import signal
import sys
import threading
import time
from pathlib import Path

from . import __version__
from .config import ConfigError, config_dir, discover_jobs, load_job
from .job import run_job
from .logs import job_logger, setup_logging
from .state import StateCorruptError


def _select_jobs(args):
    if args.jobs_dir is None and args.jobs:
        # Explicit file paths are allowed: `prowlarr2tx run ./my.json`
        picked = []
        by_name = None
        for ref in args.jobs:
            if ref.endswith(".json") and Path(ref).is_file():
                picked.append(load_job(ref))
                continue
            if by_name is None:
                by_name = {j.name: j for j in discover_jobs()}
            if ref not in by_name:
                raise ConfigError(f"unknown job '{ref}' (have: {', '.join(by_name)})")
            picked.append(by_name[ref])
        return picked
    jobs = discover_jobs(args.jobs_dir)
    if args.jobs:
        wanted = set(args.jobs)
        missing = wanted - {j.name for j in jobs}
        if missing:
            raise ConfigError(f"unknown job(s): {', '.join(sorted(missing))}")
        jobs = [j for j in jobs if j.name in wanted]
    return jobs


def _run_safely(job):
    log = job_logger(job.name)
    try:
        run_job(job)
        return True
    except StateCorruptError as exc:
        log.error("%s", exc)
    except Exception as exc:
        log.error("Job failed: %s: %s", type(exc).__name__, exc)
    return False


def cmd_run(args):
    jobs = _select_jobs(args)
    results = [_run_safely(j) for j in jobs]
    return 0 if all(results) else 1


def cmd_list(args):
    for j in _select_jobs(args):
        print(f"{j.name}\tevery {j.interval_hours:g}h\t{j.url}\tstate={j.state_path}")
    return 0


def cmd_daemon(args):
    jobs = _select_jobs(args)
    log = job_logger("daemon")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    next_run = {j.name: 0.0 for j in jobs}
    log.info("Daemon started with %d job(s): %s", len(jobs), ", ".join(next_run))
    while not stop.is_set():
        now = time.monotonic()
        for j in jobs:
            if now >= next_run[j.name]:
                _run_safely(j)
                next_run[j.name] = time.monotonic() + j.interval_hours * 3600
        wait = max(1.0, min(next_run.values()) - time.monotonic())
        stop.wait(wait)
    log.info("Daemon stopped")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="prowlarr2tx", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--jobs-dir", help=f"directory of job *.json (default: {config_dir()}/jobs)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in (
        ("run", cmd_run, "run jobs once and exit"),
        ("daemon", cmd_daemon, "run jobs forever on their intervals"),
        ("list", cmd_list, "list configured jobs"),
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("jobs", nargs="*", help="job names or .json paths (default: all)")
        p.set_defaults(fn=fn)

    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    try:
        return args.fn(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
