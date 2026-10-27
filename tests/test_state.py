import json
import os

import pytest

from prowlarr2tx import state
from prowlarr2tx.state import StateCorruptError, load_state, save_state


def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    save_state(p, {"a": 1})
    assert load_state(p) == {"a": 1}


def test_failed_write_keeps_original(tmp_path, monkeypatch):
    p = tmp_path / "s.json"
    save_state(p, {"keep": "me"})

    def disk_full(fd):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(state.os, "fsync", disk_full)
    with pytest.raises(OSError):
        save_state(p, {"new": "data"})

    assert json.loads(p.read_text()) == {"keep": "me"}
    assert not (tmp_path / "s.json.tmp").exists()


def test_corrupt_state_is_preserved_not_reset(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("")
    with pytest.raises(StateCorruptError):
        load_state(p)
    assert not p.exists()
    assert (tmp_path / "s.json.corrupt").exists()


def test_missing_state_is_empty(tmp_path):
    assert load_state(tmp_path / "nope.json") == {}
