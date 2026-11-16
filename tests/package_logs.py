#!/usr/bin/env python3
"""Check IsOS package-service output and EOS records share each replay run identity."""

import json
from pathlib import Path
import sys


def lines(path: Path) -> list[dict]:
    assert path.is_file(), f"missing log: {path}"
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main(root: Path) -> None:
    check = json.loads((root / "check.json").read_text())
    assert check["qualified"] is True and check["managed_replay"] == "passed", check
    seen = set()
    for graph in sorted(root.glob("graph-*/managed-replay")):
        isos = lines(graph / "isos.jsonl")
        eos = lines(graph / "eos.jsonl")
        run_ids = {event.get("run_id") for event in isos if event.get("run_id")}
        assert len(run_ids) == 1, f"{graph}: IsOS run identity missing or mixed"
        run_id = next(iter(run_ids))
        assert any(event.get("run_id") == run_id for event in eos), (
            f"{graph}: EOS records lack IsOS run identity")
        output = [event for event in isos if event.get("event_code") == "package_service_output"]
        assert output, f"{graph}: package service output was not captured"
        for event in output:
            assert event["core"] == "isos" and event["run_id"] == run_id
            assert event["timestamp"] and event["source"] and event["message"]
            fields = event["fields"]
            assert fields["package"] == "island/mujoco-sim"
            assert fields["instance"] in ("native", "robocasa")
            assert fields["stream"] in ("stdout", "stderr")
        ready = [event for event in output if event["message"] in
                 ("mujoco_native_ready", "robocasa_worker_ready")]
        assert len(ready) == 1, f"{graph}: package ready output missing or duplicated"
        instance = ready[0]["fields"]["instance"]
        seen.add(instance)
        print(f"{graph.parent.name}: {instance} ready output and EOS log share {run_id}")
    assert seen == {"native", "robocasa"}, f"service coverage: {seen}"


if __name__ == "__main__":
    main(Path(sys.argv[1]))
