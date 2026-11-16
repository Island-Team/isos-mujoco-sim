#!/usr/bin/env python3
"""Record and replay bounded actions in three distinct RoboCasa kitchens."""

import argparse
import json
import os
from pathlib import Path
import subprocess


SCENES = ("1:1", "2:2", "3:3")


def episode(python: Path, runner: Path, output: Path, scene: str,
            actions: Path, replay: bool, gui: bool) -> dict:
    label = "replay" if replay else "record"
    command = [str(python), str(runner), "--task", "CloseFridge", "--split", "target",
               "--kitchen-scene", scene, "--seed", "42", "--steps", "3",
               "--gui-exit-ms", "300", "--replay-actions" if replay else "--record-actions",
               str(actions), "--gui" if gui else "--no-gui"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=180, env=os.environ.copy())
    (output / f"{scene.replace(':', '-')}-{label}.log").write_text(result.stdout)
    assert result.returncode == 0, f"{scene} {label} exited {result.returncode}; see log"
    summaries = [json.loads(line) for line in result.stdout.splitlines()
                 if line.startswith('{"camera":')]
    assert len(summaries) == 1, f"{scene} {label} missing summary"
    summary = summaries[0]
    assert summary["scene"] == scene and summary["steps"] == 3, summary
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python", type=Path)
    parser.add_argument("runner", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--no-gui", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for scene in SCENES:
        actions = output / f"{scene.replace(':', '-')}-actions.json"
        recorded = episode(args.python.absolute(), args.runner.resolve(), output, scene,
                           actions, False, not args.no_gui)
        replayed = episode(args.python.absolute(), args.runner.resolve(), output, scene,
                           actions, True, False)
        assert recorded == replayed, f"{scene} replay result changed"
        results.append({"scene": scene, "actions": len(json.loads(actions.read_text())["actions"]),
                        "result": recorded})
        print(f"{scene}: recorded and replayed {results[-1]['actions']} actions", flush=True)
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
