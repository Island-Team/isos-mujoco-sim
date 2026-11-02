#!/usr/bin/env python3
"""Fixed, paused private-socket baseline; JSON contains every measured sample."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import stat
import struct
import subprocess
import tempfile
import time


def read_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise RuntimeError("short response")
        data.extend(part)
    return bytes(data)


def exchange(path, operation, request_id, timeout):
    request = json.dumps({"version": "2.0.0", "id": request_id,
                          "node": "cam-0" if operation == "camera_capture" else "base-0",
                          "op": operation}, separators=(",", ":")).encode()
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        connection.sendall(struct.pack("<II", len(request), 0) + request)
        length, payload_length = struct.unpack("<II", read_exact(connection, 8))
        if not 0 < length <= 65536 or payload_length > 8 * 1024 * 1024:
            raise RuntimeError("invalid response frame length")
        try:
            metadata = json.loads(read_exact(connection, length))
        except (ValueError, UnicodeError) as error:
            raise RuntimeError("malformed response metadata") from error
        payload = read_exact(connection, payload_length)
    if not isinstance(metadata, dict) or metadata.get("version") != "2.0.0" or metadata.get("id") != request_id:
        raise RuntimeError("malformed response identity")
    if metadata.get("ok") is not True:
        raise RuntimeError(f"{operation} failed: {metadata.get('error')}")
    if operation == "base_observe":
        if payload or len(metadata.get("position_m", [])) != 2:
            raise RuntimeError("malformed base observation")
    else:
        if (metadata.get("format") != "jpeg" or metadata.get("width_px") != 640
                or metadata.get("height_px") != 480 or metadata.get("rgb_length") != len(payload)
                or not payload.startswith(b"\xff\xd8") or len(payload) <= 1000):
            raise RuntimeError("unexpected EGL camera result or dimensions")
    result = {"bytes": len(payload), "sequence": metadata.get("sequence")}
    if operation == "camera_capture":
        result.update({"width_px": metadata["width_px"], "height_px": metadata["height_px"]})
    return result


def summary(samples, duration_ns):
    good = sorted(sample["elapsed_ns"] for sample in samples if sample["ok"])
    count = len(good)
    return {"success": count, "failure": len(samples) - count,
            "timeout": sum(bool(sample.get("timeout")) for sample in samples),
            "duration_ns": duration_ns,
            "throughput_per_s": count * 1e9 / duration_ns if duration_ns else 0,
            "median_ms": ((good[(count - 1) // 2] + good[count // 2]) / 2e6) if count else None,
            "p99_ms": good[math.ceil(count * .99) - 1] / 1e6 if count else None}


def measure(path, operation, count, timeout, prefix):
    samples = []
    start_group = time.monotonic_ns()
    for index in range(count):
        start = time.monotonic_ns()
        try:
            result = exchange(path, operation, f"{prefix}-{index}", timeout)
            sample = {"index": index, "ok": True, "timeout": False, **result}
        except (OSError, RuntimeError) as error:
            sample = {"index": index, "ok": False, "error": str(error),
                      "timeout": isinstance(error, socket.timeout), "bytes": 0}
        sample["elapsed_ns"] = time.monotonic_ns() - start
        samples.append(sample)
    duration = time.monotonic_ns() - start_group
    return {"samples": samples, "summary": summary(samples, duration)}


def wait_socket(path, process, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"simulator exited before socket ready: {process.returncode}")
        if path.is_socket():
            if stat.S_IMODE(path.stat().st_mode) != 0o600:
                raise RuntimeError("v2 socket permission is not 0600")
            return
        time.sleep(.025)
    raise TimeoutError("v2 socket unavailable")


def read_renderer_probe(child_log_path):
    text = child_log_path.read_text(errors="replace")
    matches = re.findall(r"^renderer_probe egl_vendor=(.+) gl_renderer=(.+)$", text, re.MULTILINE)
    if len(matches) != 1 or any(not value.strip() or value.strip() == "unavailable"
                                for value in matches[0]):
        raise RuntimeError("runtime EGL renderer probe missing or unavailable")
    return {"egl_vendor": matches[0][0].strip(), "gl_renderer": matches[0][1].strip()}


def simulator_log_path(output, repetition):
    return output.parent / f"{output.stem}-run{repetition}-simulator.log"


def run_once(args, repetition):
    with tempfile.TemporaryDirectory(prefix="q03-mujoco-") as directory:
        root = Path(directory)
        paths = {name: root / (name + ".sock") for name in ("legacy", "benchmark", "v2")}
        command = [str(args.sim), "--socket", str(paths["legacy"]),
                   "--benchmark-socket", str(paths["benchmark"]),
                   "--v2-socket", str(paths["v2"]), "--scene", str(args.scene),
                   "--manual-step"]
        environment = {**os.environ, "MUJOCO_GUI": "0", "MUJOCO_RENDERER_PROBE": "1"}
        child_log_path = simulator_log_path(args.json, repetition)
        with child_log_path.open("w") as child_log:
            process = subprocess.Popen(command, stdout=child_log, stderr=subprocess.STDOUT, env=environment)
            result = {"repetition": repetition, "command": command,
                      "simulator_log": str(child_log_path),
                      "scene": str(args.scene), "camera": "cam-0", "seed": 42}
            try:
                wait_socket(paths["v2"], process, args.timeout)
                if not paths["benchmark"].is_socket():
                    raise RuntimeError("benchmark socket unavailable")
                reset = subprocess.run([str(args.reset), str(paths["benchmark"]), "42"],
                                       capture_output=True, text=True, timeout=args.timeout)
                if reset.returncode:
                    raise RuntimeError(f"private Reset failed: {reset.stderr.strip()}")
                result["reset"] = json.loads(reset.stdout)
                if result["reset"].get("ok") is not True or result["reset"].get("seed") != 42:
                    raise RuntimeError("malformed Reset response")
                # The first capture initializes EGL and writes the runtime renderer
                # identity to the child log. Assert the observed image properties.
                result["capture_probe"] = exchange(paths["v2"], "camera_capture",
                                                   f"renderer-{repetition}", args.timeout)
                result["renderer_probe"] = read_renderer_probe(child_log_path)
                for index in range(args.warmup):
                    exchange(paths["v2"], "base_observe", f"warmup-{repetition}-{index}", args.timeout)
                result["base_observe"] = measure(paths["v2"], "base_observe",
                                                  args.observe, args.timeout, f"base-{repetition}")
                result["camera_capture"] = measure(paths["v2"], "camera_capture",
                                                    args.capture, args.timeout, f"camera-{repetition}")
                if process.poll() is not None:
                    raise RuntimeError(f"unexpected child exit: {process.returncode}")
                return result
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    raise RuntimeError("simulator did not stop")
                if process.returncode != 0:
                    raise RuntimeError(f"simulator exit {process.returncode}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sim", type=Path, required=True)
    parser.add_argument("--reset", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--observe", type=int, default=200)
    parser.add_argument("--capture", type=int, default=20)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    args.sim = args.sim.resolve(strict=True)
    args.reset = args.reset.resolve(strict=True)
    args.scene = args.scene.resolve(strict=True)
    if min(args.warmup, args.observe, args.capture, args.repetitions) < 1 or args.timeout <= 0:
        parser.error("counts and timeout must be positive")
    report = {"schema": "q03-socket-bench-v1", "scene": str(args.scene),
              "workload": {"warmup": args.warmup, "observe": args.observe,
                           "capture": args.capture, "repetitions": args.repetitions,
                           "seed": 42, "paused": True}, "runs": [], "aggregate": {}}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    try:
        for repetition in range(args.repetitions):
            report["runs"].append(run_once(args, repetition))
        for operation in ("base_observe", "camera_capture"):
            groups = [run[operation] for run in report["runs"]]
            report["aggregate"][operation] = summary(
                [sample for group in groups for sample in group["samples"]],
                sum(group["summary"]["duration_ns"] for group in groups))
    except Exception as error:
        report["fatal_error"] = str(error)
        raise
    finally:
        args.json.write_text(json.dumps(report, indent=2) + "\n")
    if any(report["aggregate"][operation]["failure"] for operation in report["aggregate"]):
        raise RuntimeError("measured socket failures; inspect raw JSON")
    print(json.dumps(report["aggregate"], sort_keys=True))


if __name__ == "__main__":
    main()
