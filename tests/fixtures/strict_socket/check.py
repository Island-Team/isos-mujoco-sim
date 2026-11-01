#!/usr/bin/env python3
"""Check the frozen R05 design matrix without claiming runtime behavior."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("cases.json")
data = json.loads(FIXTURE.read_text(encoding="utf-8"))
cases = data["cases"]
ids = [case["id"] for case in cases]
assert len(ids) == len(set(ids))
assert len(cases) >= 30
assert data["feature"] == "strict-socket-v1"
assert data["managed_flag"] == "--managed-strict-socket"
assert data["movement_capacity"] == 65536
assert data["reserved_stop_capacity"] == 4096
for case in cases:
    assert case["mode"] in {
        "direct", "managed_launch", "strict", "eos_readiness",
        "strict_sequence", "strict_concurrent", "strict_capacity",
        "strict_frame", "eos_restart",
    }, case["id"]
    assert isinstance(case["expect"], dict) and case["expect"], case["id"]

required = {
    "direct-legacy-node-ignored", "managed-rejects-legacy-listener",
    "managed-rejects-benchmark-listener", "managed-health-feature",
    "eos-refuses-missing-feature", "strict-camera-kind", "strict-arm-kind",
    "strict-wrong-numeric-type", "strict-identical-retransmission",
    "strict-conflicting-replay", "strict-concurrent-duplicate",
    "strict-no-eviction-replay", "strict-stop-reserve",
    "strict-truncated-frame", "strict-oversized-frame",
    "eos-uncertain-no-replay",
}
assert required <= set(ids)

for relative in (
    "docs/mujoco/interfaces/socket.md",
    "docs_cn/mujoco/interfaces/socket_cn.md",
    "docs/mujoco/design.md",
    "docs_cn/mujoco/design_cn.md",
    "docs/mujoco/usage.md",
    "docs_cn/mujoco/usage_cn.md",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    for token in ("strict-socket-v1", "--managed-strict-socket", "R05", "R06"):
        assert token in text, (relative, token)

print(f"R05 design matrix: {len(cases)} unique cases; JSON and EN/CN markers valid")
print("This checks the frozen design matrix; CTest exercises simulator behavior")
