"""Download-state persistence that cannot be truncated by a failed write."""

import json
import os
from pathlib import Path


class StateCorruptError(Exception):
    pass


def load_state(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        return data
    except ValueError as exc:
        # Never carry on with {}: that would re-download everything.
        backup = path.with_name(path.name + ".corrupt")
        os.replace(path, backup)
        raise StateCorruptError(
            f"{path} is unreadable ({exc}); moved to {backup}. "
            "Restore it or delete the backup to start fresh."
        ) from exc


def save_state(path, data):
    """Write to a temp file, fsync, then atomically replace the original.

    If the disk is full the original file is left untouched.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
