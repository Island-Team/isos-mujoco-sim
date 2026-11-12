#!/usr/bin/env python3
"""Check that fixed payload bytes produce a stable package archive."""

import hashlib
import os
from pathlib import Path
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bundle import write_deterministic_archive  # noqa: E402


with tempfile.TemporaryDirectory(prefix="mujoco-archive-") as temporary:
    root = Path(temporary)
    payload = root / "payload"
    (payload / "bin").mkdir(parents=True)
    (payload / "assets").mkdir()
    (payload / "bin/sim").write_bytes(b"fixed executable")
    (payload / "assets/scene.xml").write_bytes(b"<mujoco/>")
    os.chmod(payload / "bin/sim", 0o755)
    first = root / "first.tar.gz"
    second = root / "second.tar.gz"
    write_deterministic_archive(payload, first)
    for entry in payload.rglob("*"):
        os.utime(entry, (1700000000, 1700000000))
    write_deterministic_archive(payload, second)
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    with tarfile.open(first, "r:gz") as archive:
        assert [member.name for member in archive] == [
            "assets", "assets/scene.xml", "bin", "bin/sim"]
        assert all(member.uid == member.gid == member.mtime == 0 for member in archive.getmembers())
        assert archive.getmember("bin/sim").mode & 0o111
    (payload / "assets/scene.xml").write_bytes(b"<mujoco model='changed'/>")
    write_deterministic_archive(payload, second)
    assert hashlib.sha256(first.read_bytes()).digest() != hashlib.sha256(second.read_bytes()).digest()
print("deterministic archive digest: PASS")
