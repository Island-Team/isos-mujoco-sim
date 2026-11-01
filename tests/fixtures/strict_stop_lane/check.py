#!/usr/bin/env python3
"""Validate the frozen R06 design matrix without claiming runtime behavior."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
data = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
cases = data["cases"]
ids = [case["id"] for case in cases]
assert len(cases) == 47 and len(ids) == len(set(ids))
assert data["wire_version"] == "2.0.0"
assert data["feature"] == "strict-stop-v1"
assert data["stop_deadline_ms"] == 1000
assert data["ingress_deadline_ms"] == 250
assert data["ingress_slots"] == 8
assert data["stop_socket_suffix"] == ".stop"
assert data["stop_ingress_slots"] == 2
assert data["reserved_stop_slots"] == 1
for case in cases:
    assert case["mode"] in {
        "direct", "managed_health", "concurrent", "capacity", "stop_result",
        "eos_boundary", "dedup", "fence", "capture", "launch",
        "lifecycle", "strict_frame",
    }, case["id"]
    assert isinstance(case["expect"], dict) and case["expect"], case["id"]

required = {
    "stop-preempts-blocked-arm", "stop-preempts-blocked-base",
    "stop-preempts-blocked-capture", "stop-preempts-partial-frame",
    "stop-both-ack", "stop-base-only", "stop-arm-only", "stop-neither",
    "stop-prior-move-queued", "stop-prior-move-committing",
    "stop-old-frame-arrives-late", "stop-missing-move-token",
    "move-identical-replay-after-stop", "move-conflicting-epoch-after-stop",
    "move-stale-new-key-after-stop", "stop-preempts-eight-partial-main-frames",
    "stop-preempts-two-partial-stop-frames", "managed-stop-health-proof",
    "managed-stop-socket-path-overlength", "managed-stop-socket-bind-failure",
    "managed-health-generation-match", "move-old-child-generation-rejected",
    "stop-old-child-generation-rejected",
    "capture-stuck-egl", "gui-unavailable-cleanup",
    "child-crash-stop-unknown", "timeout-forced-stop-unknown",
    "restart-new-child-generation", "direct-legacy-stop-shape",
}
assert required <= set(ids)
for relative in (
    "docs/mujoco/interfaces/socket.md", "docs_cn/mujoco/interfaces/socket_cn.md",
    "docs/mujoco/design.md", "docs_cn/mujoco/design_cn.md",
    "docs/mujoco/usage.md", "docs_cn/mujoco/usage_cn.md",
):
    content = (ROOT / relative).read_text(encoding="utf-8")
    for marker in ("R06", "strict-stop-v1", "base_stop", "arm_stop", "stop_epoch", "generation_id", ".stop"):
        assert marker in content, (relative, marker)

print(f"R06 design matrix: {len(cases)} unique cases; JSON and EN/CN markers valid")
print("Static design check only; CTest and cross-owner replay must prove behavior")
