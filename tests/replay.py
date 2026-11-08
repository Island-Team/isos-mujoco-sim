#!/usr/bin/env python3
"""Q03 selected-archive IsOS → EOS → MuJoCo installed qualification.

Each repetition uses a fresh home and the exact supplied release/archive. JSON
contains raw monotonic timing samples; no performance threshold is asserted.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import socket
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PIN = {"id": "island/mujoco-sim", "version": "0.1.2"}
CAMERA = "eos/hardware/camera/front"
BASE = "eos/hardware/base/drive"


class IsosHTTPError(RuntimeError):
    def __init__(self, path, status_code, body):
        self.path, self.status_code, self.body = path, status_code, body
        super().__init__(f"IsOS {path}: HTTP {status_code}: {body}")


def route(path):
    head, sep, query = path.partition("?")
    mapped = {"process-status":"runtime/process-status","process-control":"runtime/control","logs":"runtime/logs"}.get(head,head)
    return mapped + (sep + query if sep else "")

def readiness_process_status(home):
    """Retry only a busy manager's process-status 503; retain its raw reply."""
    try:
        return home.api("process-status")
    except IsosHTTPError as error:
        if error.path != "process-status" or error.status_code != 503:
            raise
        attempt = {"monotonic_ns": time.monotonic_ns(), "status_code": error.status_code,
                   "body": error.body, "error": str(error)}
        home.readiness_status_503_attempts.append(attempt)
        summary = home.readiness_503_summary()
        (home.args.output / f"{home.scene}-{home.repetition}-readiness-status-503.json").write_text(
            json.dumps(summary, indent=2) + "\n")
        print("Q03 readiness process-status 503", json.dumps(attempt), flush=True)
        return None


def readiness_failure_evidence(home, started_ns, error):
    finished_ns = time.monotonic_ns()
    record = {"schema_version": 1, "scene": home.scene,
              "repetition": home.repetition, "start_monotonic_ns": started_ns,
              "failure_monotonic_ns": finished_ns,
              "elapsed_ms": (finished_ns - started_ns) / 1e6,
              "readiness_deadline_s": 180,
              "exception": {"type": type(error).__name__, "message": str(error)},
              "process_status_503": home.readiness_503_summary()}
    (home.args.output / f"{home.scene}-{home.repetition}-readiness-failure.json").write_text(
        json.dumps(record, indent=2) + "\n")
    return record


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def summarize(samples_ms, elapsed_s):
    if not samples_ms or elapsed_s <= 0:
        raise ValueError("positive elapsed time and nonempty samples required")
    ordered = sorted(samples_ms)
    return {"count": len(samples_ms), "throughput_per_s": len(samples_ms) / elapsed_s,
            "median_ms": statistics.median(ordered),
            "p99_ms": ordered[math.ceil(0.99 * len(ordered)) - 1]}


def summarize_results(results):
    summaries = {}
    for scene, label in (("pick-place", "pick_place"), ("navigation", "navigation")):
        selected = [row for row in results if row["scene"] == scene]
        if not selected:
            raise ValueError(f"missing {scene} runs")
        starts = [row["startup_ms"] for row in selected]
        captures = [sample for row in selected for sample in row["captures_ms"]]
        if not captures:
            raise ValueError(f"missing {scene} capture samples")
        summaries[f"{label}_start_summary"] = summarize(starts, sum(starts) / 1000)
        summaries[f"{label}_capture_summary"] = summarize(
            captures, sum(row["capture_elapsed_s"] for row in selected))
    return summaries


def correlated_bridge_events(lines, run_id, command_id):
    selected = [item for item in lines if item.get("run_id") == run_id
                and item.get("event_code") == "bridge_primitive_result"
                and item.get("correlation_id") == command_id]
    assert any(item.get("fields", {}).get("phase") == "submit" for item in selected), (
        "no correlated bridge submit event")
    assert any(item.get("fields", {}).get("phase") == "followup"
               and item.get("fields", {}).get("status") == "Completed"
               for item in selected), "no correlated bridge Completed follow-up event"
    return selected


def wait_for(check, timeout_s, description):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if time.monotonic() >= deadline:
                break
            if result:
                return result
        except (OSError, ValueError, KeyError) as error:
            last = str(error)
        time.sleep(0.1)
    raise TimeoutError(f"{description} did not become ready in {timeout_s}s: {last}")


class Home:
    def __init__(self, args, path, scene, repetition, ports):
        self.args, self.path, self.scene, self.repetition = args, path, scene, repetition
        self.home = path / "home"
        self.isos_port, self.ui_port, self.bridge_port, self.config_port = ports
        self.env = dict(os.environ, ISOS_HOME=str(self.home),
                        ISOS_HTTP_PORT=str(self.isos_port), ISOSUI_PORT=str(self.ui_port),
                        ISOS_AETHER_BIN_DIR=str(args.eos_bin_dir),
                        ISOSUI_DIST_DIR=str(args.ui_dist), MUJOCO_ROOT=str(args.mujoco_root),
                        MUJOCO_RENDERER_PROBE="1")
        self.serve = self.run = None
        self.files = []
        self.readiness_status_503_attempts = []

    def readiness_503_summary(self):
        attempts = self.readiness_status_503_attempts
        return {"count": len(attempts), "attempts": attempts,
                "last_error": attempts[-1]["error"] if attempts else None}

    def command(self, *argv):
        result = subprocess.run([str(self.args.isos_bin), *map(str, argv)], env=self.env,
                                text=True, capture_output=True, timeout=90)
        print("$ isos", *argv, "exit", result.returncode, flush=True)
        print(result.stdout, result.stderr, flush=True)
        if result.returncode:
            raise RuntimeError(f"isos {argv} exited {result.returncode}")
        return result.stdout

    def api(self, path, method="GET", data=None):
        request = Request(f"http://127.0.0.1:{self.isos_port}/api/isos/v1/{route(path)}",
                          method=method, data=None if data is None else json.dumps(data).encode(),
                          headers={"Content-Type": "application/json",
                                   "Origin": f"http://127.0.0.1:{self.isos_port}"})
        try:
            with urlopen(request, timeout=200 if path == "process-control" and data and data.get("operation") == "run" else 15) as response:
                body = json.load(response)
        except HTTPError as error:
            raise IsosHTTPError(path, error.code, error.read().decode()) from error
        if body["ok"] is not True:
            raise RuntimeError(body)
        return body["data"]

    def eos(self, payload):
        request = Request(f"http://127.0.0.1:{self.bridge_port}/api/eos/v2/control",
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json",
                                   "Origin": f"http://127.0.0.1:{self.ui_port}"})
        try:
            with urlopen(request, timeout=10) as response:
                body = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"EOS {payload['op']}: HTTP {error.code}: {error.read().decode()}") from error
        if body["ok"] is not True:
            raise RuntimeError(body)
        return body

    def spawn(self, operation):
        handle = (self.path / f"{operation}.log").open("w")
        self.files.append(handle)
        child = subprocess.Popen([str(self.args.isos_bin), operation], env=self.env,
                                 stdout=handle, stderr=subprocess.STDOUT, text=True)
        return child

    def prepare(self):
        manifest, archive = self.args.manifest, self.args.archive
        release = json.loads(manifest.read_text())
        selected = next(item for item in release["assets"] if item["name"] == archive.name)
        assert release["id"] == PIN["id"] and release["version"] == PIN["version"]
        assert selected["sha256"] == sha(archive) and selected["size_bytes"] == archive.stat().st_size
        self.command("init", "--mode", "dev")
        self.command("pkg", "verify", manifest, archive)
        self.command("pkg", "install", "--manifest", manifest, "--asset", archive,
                     "--allow-unapproved")
        listed = json.loads(self.command("pkg", "list", "--json"))
        pin = [item for item in listed if item["id"] == PIN["id"] and item["version"] == PIN["version"]]
        assert len(pin) == 1 and pin[0]["status"] == "verified" and pin[0]["available"]
        store = self.home / "data/packages/island/mujoco-sim/0.1.2"
        receipt = json.loads((store / "receipt.json").read_text())
        assert receipt["schema_version"] == 2 and receipt["source_kind"] == "local_candidate"
        assert receipt["asset_sha256"] == selected["sha256"]
        assert receipt["release_sha256"] == sha(store / "release.json")
        assert receipt["payload_sha256"] and len(receipt["payload_sha256"]) == 64
        stored_release = json.loads((store / "release.json").read_text())
        assert (stored_release["id"], stored_release["version"]) == (PIN["id"], PIN["version"])
        assert any(item["sha256"] == selected["sha256"] for item in stored_release["assets"])
        sets = json.loads(self.command("pkg", "node-sets"))["sets"]
        assert any(item["id"] == "sim-hardware" and item["package"] == PIN for item in sets)
        graph_path = self.home / "config/deployments/default.nodes.json"
        values = self.path / "values.json"
        values.write_text(json.dumps({"scene": self.scene,
                                      "socket": str(self.home / "run/default-mujoco.sock")}))
        preview = json.loads(self.command("pkg", "preview-set", PIN["id"], PIN["version"],
                                          "sim-hardware", graph_path, "--values", values))["graph"]
        components = preview["cores"]["isos"]["layers"]["process"]["groups"]["component"]["nodes"]
        for name, port in (("bridge", self.bridge_port), ("config", self.config_port)):
            components[name]["settings"]["args"][-1] = f"127.0.0.1:{port}"
            components[name]["settings"]["ready_tcp"] = f"127.0.0.1:{port}"
        bindings = preview["cores"]["eos"]["layers"]["dispatcher"]["groups"]["base"]["nodes"]
        selected_binding = [name for name, node in bindings.items()
                            if node["settings"].get("primitive_name") == "base.velocity"]
        assert len(selected_binding) == 1
        binding_path = f"eos/dispatcher/base/{selected_binding[0]}"
        source_path = "isosui/input/keyboard/drive"
        isos_gateway = "isos/interface/gateway/key_to_base"
        eos_gateway = "eos/interface/gateway/control"
        preview["cores"]["isosui"] = {"layers":{"input":{"groups":{"keyboard":{"nodes":{
            "drive":{"id":"drive","node_type":"isosui.input.keyboard@v0.1",
                     "label":"Drive key","description":"Selected forward key input",
                     "settings":{"key":"KeyW"}}
        }}}}}}
        preview["cores"]["isos"]["layers"]["interface"] = {"groups":{"gateway":{"nodes":{
            "key_to_base":{"id":"key_to_base","node_type":"isos.interface.http_gateway@v0.1",
                "label":"Key movement bridge","description":"Converts run-bound key state to a fixed base lease",
                "settings":{"target":binding_path,"x_m_s":0.2,"y_m_s":0.0,
                            "yaw_rad_s":0.0,"valid_for_ms":150},
                "inputs":{"state":{"node":source_path,"output":"state"}}}
        }}}}
        preview["cores"]["eos"]["layers"]["interface"]["groups"]["gateway"] = {"nodes":{
            "control":{"id":"control","node_type":"eos.interface.http_gateway@v0.1",
                       "label":"EOS movement gateway","description":"Run-fenced HTTP movement ingress",
                       "inputs":{"movement":{"node":isos_gateway,"output":"movement"}}}
        }}
        bindings[selected_binding[0]].setdefault("inputs", {})["request"] = {
            "node":eos_gateway,"output":"movement"}
        candidate = self.path / "candidate.nodes.json"
        candidate.write_text(json.dumps(preview, indent=2) + "\n")
        self.command("config", "validate", candidate)
        revision = sha(graph_path)
        self.command("config", "apply", candidate, "--revision", revision)
        applied = sha(graph_path)
        assert applied != revision
        prefix = f"{self.scene}-{self.repetition}"
        (self.args.output / f"{prefix}-receipt.json").write_bytes((store / "receipt.json").read_bytes())
        (self.args.output / f"{prefix}-graph.json").write_bytes(graph_path.read_bytes())
        return {"archive_sha256": sha(archive), "manifest_sha256": sha(manifest),
                "receipt_sha256": sha(store / "receipt.json"),
                "release_sha256": receipt["release_sha256"],
                "payload_sha256": receipt["payload_sha256"], "graph_revision": applied,
                "graph_sha256": applied, "graph_path": str(graph_path),
                "binding_path": f"eos/dispatcher/base/{selected_binding[0]}"}

    def execute(self):
        meta = self.prepare()
        self.serve = self.spawn("serve")
        wait_for(lambda: self.api("process-status"), 20, "IsOS manager")
        start_ns = time.monotonic_ns()
        self.api("process-control", "POST", {"schema_version": "0.1.0", "operation": "run"})

        def ready():
            if self.serve.poll() is not None:
                raise RuntimeError(f"isos serve exited {self.serve.returncode}")
            status = readiness_process_status(self)
            if status is None:
                return None
            if status["state"] != "running" or status["active_revision"] != meta["graph_revision"]:
                return None
            processes = {item["id"]: item for item in status["processes"]}
            if set(processes) != {"eos", "bridge", "config"}:
                return None
            discovered = self.eos({"op": "discover"})
            camera = next((item for item in discovered.get("nodes", [])
                           if item.get("path") == CAMERA), None)
            if camera is None:
                return None
            health = self.eos({"op": "health", "node_path": CAMERA})["health"]
            if health.get("state") != "healthy":
                return None
            run_id = status.get("run_id")
            if not run_id:
                return None
            # EOS publishes eos_ready only after strict simulator health.
            lines = self.api("logs?source=eos&limit=100")["lines"]
            event = next((item for item in lines if item.get("run_id") == run_id
                          and item.get("event_code") == "eos_ready"), None)
            if event is None:
                return None
            frame = self.eos({"op": "capture", "node_path": CAMERA})["frame"]
            if frame.get("width_px") != 640 or frame.get("height_px") != 480:
                return None
            return {"status": status, "health": health, "event": event,
                    "frame_size_px": [frame["width_px"], frame["height_px"]]}

        try:
            readiness = wait_for(ready, 180, "same-revision owner and strict EOS camera")
        except Exception as error:
            print("Q03 readiness failure",
                  json.dumps(readiness_failure_evidence(self, start_ns, error)), flush=True)
            raise
        end_ns = time.monotonic_ns()
        startup_ms = (end_ns - start_ns) / 1e6
        status, event = readiness["status"], readiness["event"]
        run_id = status["run_id"]
        assert status["active_revision"] == meta["graph_revision"]
        activation = f"drive-{self.scene}-{self.repetition}"
        def send_key(phase, sequence):
            return self.api("nodes/events", "POST", {
                "schema_version":"0.1.0", "source_node":"isosui/input/keyboard/drive",
                "output":"state", "data_type":"key_state", "run_id":run_id,
                "active_revision":meta["graph_revision"],
                "payload":{"state":phase,"activation_id":activation,"sequence":sequence}})
        pressed = send_key("pressed", 1)
        assert pressed["state"] == "active", pressed
        time.sleep(0.07)
        refreshed = send_key("refresh", 2)
        assert refreshed["state"] == "active", refreshed
        released = send_key("released", 3)
        assert released["state"] == "released", released
        eos_pid = next(item["pid"] for item in status["processes"] if item["id"] == "eos")
        children = Path(f"/proc/{eos_pid}/task/{eos_pid}/children").read_text().split()
        simulator_pids = [int(pid) for pid in children
                          if b"eos-mujoco-sim" in Path(f"/proc/{pid}/cmdline").read_bytes()]
        assert len(simulator_pids) == 1, f"expected one EOS-owned simulator, found {simulator_pids}"
        samples = []
        capture_start_ns = time.monotonic_ns()
        for _ in range(20):
            begun = time.monotonic_ns()
            frame = self.eos({"op": "capture", "node_path": CAMERA})["frame"]
            assert frame["width_px"] == 640 and frame["height_px"] == 480
            samples.append((time.monotonic_ns() - begun) / 1e6)
        capture_elapsed_s = (time.monotonic_ns() - capture_start_ns) / 1e9
        now = self.eos({"op": "time"})["monotonic_ns"]
        movement = {"type": "body_velocity", "x_m_s": 0.02,
                    "y_m_s": 0.0, "yaw_rad_s": 0.0, "valid_for_ms": 100}
        command_id = f"q03-{self.scene}-{self.repetition}"
        result = self.eos({"op": "primitive_typed", "header": {
            "data_type_id": "base_movement", "data_type_version": "1.0",
            "primitive_name": "base.velocity", "primitive_version": "1.0.0",
            "source_path": meta["binding_path"], "target_path": BASE,
            "active_revision": meta["graph_revision"], "command_id": command_id,
            "sequence": 100, "deadline_monotonic_ns": now + 5_000_000_000,
            "payload_length_bytes": len(json.dumps(movement, separators=(",", ":")).encode()),
            "codec": "json_v1"}, "payload": movement})["result"]
        assert result["status"] != "Rejected", result
        def completed_result():
            latest = self.eos({"op": "result", "command_id": command_id,
                               "active_revision": meta["graph_revision"]})["result"]
            assert latest["command_id"] == command_id
            return latest if latest["status"] != "InProgress" else None
        followup = wait_for(completed_result, 15, "correlated primitive result")
        assert followup["status"] == "Completed", followup
        log_lines = self.api("logs?source=eos&limit=200")["lines"]
        bridge_lines = self.api("logs?source=bridge&limit=200")["lines"]
        correlated = correlated_bridge_events(bridge_lines, run_id, command_id)
        simulator_log = self.home / "data/logs/default/owner/eos/package-process.log"
        simulator_lines = [json.loads(line) for line in simulator_log.read_text().splitlines()]
        renderer = [item["message"] for item in simulator_lines
                    if "renderer_probe egl_vendor=" in item.get("message", "")]
        assert renderer, "no current-run MuJoCo EGL renderer probe"
        (self.args.output / f"{self.scene}-{self.repetition}-mujoco.log").write_bytes(
            simulator_log.read_bytes())
        stopped = self.api("process-control", "POST", {"schema_version": "0.1.0",
                                                        "operation": "stop"})
        terminal = stopped["terminal"]
        assert terminal["run_id"] == run_id and terminal["outcome"] == "confirmed", terminal
        assert all(item["outcome"] == "confirmed" for item in terminal["processes"])
        final_status = wait_for(lambda: self.api("process-status")
                                if self.api("process-status")["state"] == "stopped" else None,
                                20, "deployment stop")
        assert final_status["terminal"] == terminal
        assert not (self.home / "run/default-mujoco.sock").exists()
        assert not Path(f"/proc/{simulator_pids[0]}").exists(), "simulator was not reaped"
        return {**meta, "scene": self.scene, "repetition": self.repetition,
                "run_id": run_id, "startup_ms": startup_ms,
                "startup_start_monotonic_ns": start_ns,
                "startup_end_monotonic_ns": end_ns,
                "readiness_owner_status": status,
                "readiness_camera_health": readiness["health"],
                "readiness_frame_size_px": readiness["frame_size_px"],
                "readiness_process_status_503": self.readiness_503_summary(),
                "startup_success": 1, "startup_failure": 0,
                "captures_ms": samples, "capture_success": len(samples), "capture_failure": 0,
                "capture_elapsed_s": capture_elapsed_s,
                "capture_summary": summarize(samples, capture_elapsed_s),
                "processes": status["processes"], "simulator_pid": simulator_pids[0],
                "eos_ready_event": event,
                "command_id": command_id, "command_status": result["status"],
                "followup_status": followup["status"], "terminal": terminal,
                "eos_log_count": len(log_lines), "bridge_result_events": correlated,
                "renderer_probe": renderer[0]}

    def close(self):
        for child in (self.run, self.serve):
            if child is not None and child.poll() is None:
                child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
        for handle in self.files:
            handle.close()


def main():
    parser = argparse.ArgumentParser()
    for name in ("isos-bin", "eos-bin-dir", "ui-dist", "mujoco-root", "manifest", "archive", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--pick-place-starts", type=int, default=5)
    args = parser.parse_args()
    if args.pick_place_starts < 1:
        parser.error("--pick-place-starts must be positive")
    for path in (args.isos_bin, args.eos_bin_dir / "aether-runtime", args.ui_dist / "index.html",
                 args.mujoco_root / "lib/libmujoco.so.3.3.1", args.manifest, args.archive):
        if not path.is_file():
            parser.error(f"missing selected input: {path}")
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    # Reuse the same path and ports only after complete Stop/cleanup. This keeps
    # all five pick-place graph bytes/revisions identical across clean homes.
    selected_ports = set()
    while len(selected_ports) < 4:
        selected_ports.add(free_port())
    ports = tuple(sorted(selected_ports))
    with tempfile.TemporaryDirectory(prefix="isos-q03-installed-") as temporary:
        root = Path(temporary) / "case"
        for scene, count in (("pick-place", args.pick_place_starts), ("navigation", 1)):
            for repetition in range(count):
                root.mkdir()
                home = Home(args, root, scene, repetition, ports)
                try:
                    result = home.execute()
                    print("PASS", scene, repetition, result["startup_ms"], flush=True)
                    results.append(result)
                    (args.output / f"{scene}-{repetition}.json").write_text(
                        json.dumps(result, indent=2) + "\n")
                finally:
                    candidate = home.path / "candidate.nodes.json"
                    if candidate.exists():
                        (args.output / f"{scene}-{repetition}-candidate.nodes.json").write_bytes(candidate.read_bytes())
                    log_tree = home.home / "data/logs"
                    if log_tree.exists():
                        shutil.copytree(log_tree, args.output / f"{scene}-{repetition}-logs", dirs_exist_ok=True)
                    event_log = home.home / "data/logs/default/events.log"
                    if event_log.exists():
                        (args.output / f"{scene}-{repetition}-events.log").write_bytes(event_log.read_bytes())
                    home.close()
                    for name in ("serve.log", "run.log"):
                        source = home.path / name
                        if source.exists():
                            (args.output / f"{scene}-{repetition}-{name}").write_bytes(source.read_bytes())
                    shutil.rmtree(root)
    revisions = {row["graph_revision"] for row in results if row["scene"] == "pick-place"}
    assert len(revisions) == 1, f"pick-place graph bytes changed across clean homes: {revisions}"
    output = {"schema_version": 1, "percentile_method": "nearest-rank p99; midpoint median",
              "results": results, **summarize_results(results)}
    (args.output / "installed.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"pick_place_start_summary": output["pick_place_start_summary"],
                      "pick_place_capture_summary": output["pick_place_capture_summary"],
                      "scenes": [row["scene"] for row in results]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
