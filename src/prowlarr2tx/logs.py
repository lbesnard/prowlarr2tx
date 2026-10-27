import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from .config import log_dir

_SECRET = re.compile(r"(apikey=)[^&\s'\"]+", re.IGNORECASE)


class RedactFilter(logging.Filter):
    def filter(self, record):
        record.msg = _SECRET.sub(r"\1***", record.getMessage())
        record.args = ()
        return True


def setup_logging(level="INFO"):
    root = logging.getLogger("prowlarr2tx")
    if root.handlers:
        return root
    root.setLevel(getattr(logging, level.upper()))
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(job)s] %(message)s")

    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        d = log_dir()
        d.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(d / "prowlarr2tx.log", maxBytes=5_000_000, backupCount=3)
        )
    except OSError as exc:
        print(f"warning: file logging disabled: {exc}", file=sys.stderr)

    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(RedactFilter())
        root.addHandler(h)
    return root


def job_logger(name):
    return logging.LoggerAdapter(logging.getLogger("prowlarr2tx"), {"job": name})
