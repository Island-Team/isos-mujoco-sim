#!/usr/bin/env python3
"""Failure accounting and framed socket faults for the Q03 baseline runner."""

import importlib.util
from pathlib import Path
import socket
import struct
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
        samples.append({"elapsed_ns": 7_000_000, "ok": False})
        actual = bench.summary(samples, 1_000_000_000)
        self.assertEqual((actual["success"], actual["failure"]), (4, 1))
        self.assertEqual(actual["median_ms"], 3)
        self.assertEqual(actual["p99_ms"], 8)
        self.assertEqual(actual["throughput_per_s"], 4)

    def test_unavailable_socket_counts_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            group = bench.measure(Path(directory) / "absent.sock", "base_observe", 1, .1, "missing")
        self.assertEqual(group["summary"]["failure"], 1)

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


if __name__ == "__main__":
    unittest.main()
