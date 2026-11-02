#!/usr/bin/env python3
"""Failure accounting and framed socket faults for the Q03 baseline runner."""

import importlib.util
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest


spec = importlib.util.spec_from_file_location("q03_socket_bench", Path(__file__).with_name("q03_socket_bench.py"))
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class BenchTests(unittest.TestCase):
    def test_midpoint_median_nearest_rank_p99_and_failure(self):
        samples = [{"elapsed_ns": value, "ok": True} for value in (1_000_000, 2_000_000, 4_000_000, 8_000_000)]
        samples.append({"elapsed_ns": 7_000_000, "ok": False, "bytes": 0, "timeout": True})
        actual = bench.summary(samples, 1_000_000_000)
        self.assertEqual((actual["success"], actual["failure"]), (4, 1))
        self.assertEqual(actual["median_ms"], 3)
        self.assertEqual(actual["p99_ms"], 8)
        self.assertEqual(actual["throughput_per_s"], 4)
        self.assertEqual(actual["timeout"], 1)

    def test_unavailable_socket_counts_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            group = bench.measure(Path(directory) / "absent.sock", "base_observe", 1, .1, "missing")
        self.assertEqual(group["summary"]["failure"], 1)
        self.assertEqual(group["summary"]["timeout"], 0)
        self.assertEqual(group["samples"][0]["bytes"], 0)

    def test_malformed_and_short_responses(self):
        for frame in (struct.pack("<II", 999999, 0), struct.pack("<II", 4, 0) + b"nope", b"\x01"):
            with self.subTest(frame=frame), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "test.sock"
                ready = threading.Event()

                def serve():
                    with socket.socket(socket.AF_UNIX) as listener:
                        listener.bind(str(path))
                        listener.listen(1)
                        ready.set()
                        with listener.accept()[0] as connection:
                            connection.recv(4096)
                            connection.sendall(frame)

                thread = threading.Thread(target=serve)
                thread.start()
                ready.wait(1)
                with self.assertRaises((RuntimeError, ValueError)):
                    bench.exchange(path, "base_observe", "test", .1)
                thread.join(1)

    def test_timeout_and_wrong_response_identity(self):
        for frame in (None, b'{"version":"2.0.0","id":"wrong","ok":true}'):
            with self.subTest(frame=frame), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "test.sock"
                ready = threading.Event()

                def serve():
                    with socket.socket(socket.AF_UNIX) as listener:
                        listener.bind(str(path))
                        listener.listen(1)
                        ready.set()
                        with listener.accept()[0] as connection:
                            connection.recv(4096)
                            if frame is None:
                                time.sleep(.2)
                            else:
                                connection.sendall(struct.pack("<II", len(frame), 0) + frame)

                thread = threading.Thread(target=serve)
                thread.start()
                ready.wait(1)
                with self.assertRaises((OSError, RuntimeError)):
                    bench.exchange(path, "base_observe", "test", .05)
                thread.join(1)

    def test_unexpected_child_exit(self):
        class Exited:
            returncode = 7

            def poll(self):
                return 7

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "exited before socket ready"):
                bench.wait_socket(Path(directory) / "missing.sock", Exited(), .1)

    def test_capture_probe_records_observed_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sock"
            ready = threading.Event()
            payload = b"\xff\xd8" + b"x" * 1100
            reply = json.dumps({"version": "2.0.0", "id": "probe", "ok": True,
                                "format": "jpeg", "width_px": 640, "height_px": 480,
                                "rgb_length": len(payload), "sequence": 0}).encode()

            def serve():
                with socket.socket(socket.AF_UNIX) as listener:
                    listener.bind(str(path))
                    listener.listen(1)
                    ready.set()
                    with listener.accept()[0] as connection:
                        connection.recv(4096)
                        connection.sendall(struct.pack("<II", len(reply), len(payload)) + reply + payload)

            thread = threading.Thread(target=serve)
            thread.start()
            ready.wait(1)
            actual = bench.exchange(path, "camera_capture", "probe", 1)
            thread.join(1)
            self.assertEqual(actual, {"bytes": len(payload), "sequence": 0,
                                      "width_px": 640, "height_px": 480})

    def test_runtime_renderer_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "child.log"
            path.write_text("renderer_probe egl_vendor=Mesa Project gl_renderer=llvmpipe (LLVM 17)\n")
            self.assertEqual(bench.read_renderer_probe(path),
                             {"egl_vendor": "Mesa Project", "gl_renderer": "llvmpipe (LLVM 17)"})
            path.write_text("renderer_probe egl_vendor=Mesa Project gl_renderer=unavailable\n")
            with self.assertRaisesRegex(RuntimeError, "renderer probe"):
                bench.read_renderer_probe(path)

    def test_wrong_scene_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "wrong-scene.xml"
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("q03_socket_bench.py")),
                 "--sim", sys.executable, "--reset", sys.executable,
                 "--scene", str(missing), "--json", str(Path(directory) / "out.json")],
                capture_output=True, text=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("wrong-scene.xml", result.stderr)


if __name__ == "__main__":
    unittest.main()
