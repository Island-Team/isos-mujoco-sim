#!/usr/bin/env python3
"""Replay native hardware interfaces in a custom MJCF scene with live GUI and bounded exit."""

import argparse
import json
from pathlib import Path
import signal
import subprocess
import time

from strictsocket import exchange


def call(path: Path, op: str, node: str, **fields):
    request = {"version": "2.0.0", "id": f"full-{op}-{time.monotonic_ns()}",
               "op": op, "node": node, **fields}
    result = exchange(path, request)
    assert result is not None, f"no response to {op}"
    reply, payload = result
    assert reply["id"] == request["id"], reply
    return reply, payload


def accepted(path: Path, op: str, node: str, **fields):
    reply, payload = call(path, op, node, **fields)
    assert reply["ok"] and reply.get("accepted", True), reply
    return reply, payload


def run(binary: Path, template: Path, output: Path, gui: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    scene = output / "custom-scene.xml"
    source = template.read_text()
    assert 'model="eos_benchmark_v1"' in source
    scene.write_text(source.replace('model="eos_benchmark_v1"',
                                    'model="full_interface_replay"', 1))
    assets = template.parent / "menagerie"
    link = output / "menagerie"
    if not link.exists():
        link.symlink_to(assets, target_is_directory=True)
    socket = output / "native.sock"
    stop_socket = Path(str(socket) + ".stop")
    command = [str(binary), "--managed-strict-socket", "--v2-socket", str(socket),
               "--scene", str(scene)]
    if gui:
        command.append("--gui")
    summary = {"scene": str(scene), "gui": gui, "commands": []}
    with (output / "native-service.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not (socket.is_socket() and stop_socket.is_socket()):
                assert process.poll() is None, "native service exited before readiness"
                time.sleep(0.05)
            assert socket.is_socket() and stop_socket.is_socket(), "native sockets did not become ready"
            for node in ("cam-0", "base-0", "arm-0", "gripper-0"):
                health, _ = accepted(socket, "health", node)
                assert "strict-socket-v1" in health["features"], health
                if node != "cam-0":
                    assert "strict-stop-v1" in health["features"], health
            generation = health["generation_id"]
            for op, node in (("camera_capture", "cam-0"),
                             ("base_observe", "base-0"),
                             ("manipulator_observe", "arm-0"),
                             ("gripper_observe", "gripper-0")):
                reply, payload = accepted(socket, op, node)
                summary["commands"].append({"op": op, "node": node, "sequence": reply["sequence"],
                                            "payload_bytes": len(payload)})
                if op == "camera_capture":
                    assert payload.startswith(b"\xff\xd8") and payload.endswith(b"\xff\xd9")
            bad, _ = call(socket, "base_move", "base-0", command_id="invalid-range",
                          generation_id=generation, stop_epoch="0", linear_x_m_s=5,
                          linear_y_m_s=0, angular_z_rad_s=0, valid_for_ms=200)
            assert not bad["ok"] and bad["error"]["code"] == "out_of_range", bad
            commands = (
                ("base_move", "base-0", {"linear_x_m_s": 0.15, "linear_y_m_s": 0,
                                         "angular_z_rad_s": 0, "valid_for_ms": 300}),
                ("manipulator_move", "arm-0", {"joint_positions_rad": [0.1, -0.2, 0.1, 0, 0, 0]}),
                ("gripper_move", "gripper-0", {"close": True}),
            )
            for index, (op, node, fields) in enumerate(commands):
                reply, _ = accepted(socket, op, node, command_id=f"full-action-{index}",
                                    generation_id=generation, stop_epoch="0", **fields)
                summary["commands"].append({"op": op, "node": node,
                                            "sequence": reply["sequence"]})
                time.sleep(0.3)
            proof, _ = accepted(stop_socket, "stop", "base-0", command_id="full-stop",
                                generation_id=generation)
            assert all(proof[key] == "stopped" for key in
                       ("base_stop", "arm_stop", "gripper_stop")), proof
            summary["stop_epoch"] = proof["stop_epoch"]
            late, _ = call(socket, "base_move", "base-0", command_id="late-action",
                           generation_id=generation, stop_epoch="0", linear_x_m_s=0.1,
                           linear_y_m_s=0, angular_z_rad_s=0, valid_for_ms=200)
            assert not late["ok"] and late["error"]["code"] == "stop_fenced", late
            summary["result"] = "passed"
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
            process.wait(timeout=20)
            assert process.returncode == 0, f"native service exit {process.returncode}"
            assert not socket.exists() and not stop_socket.exists(), "socket survived shutdown"
    (output / "native-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    run(args.binary.resolve(), args.template.resolve(), args.output.resolve(), args.gui)
