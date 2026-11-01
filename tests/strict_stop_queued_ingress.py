#!/usr/bin/env python3
"""Queued partial frames retain their accept-time 250 ms ingress deadline."""

from pathlib import Path
import os
import signal
import socket
import sys
import tempfile
import time

from strict_stop import call, launch, partial, stop_process


def socket_fd_count(pid):
    count = 0
    for descriptor in Path(f"/proc/{pid}/fd").iterdir():
        try:
            count += os.readlink(descriptor).startswith("socket:[")
        except FileNotFoundError:
            pass
    return count


def wait_for_socket_count(pid, expected):
    deadline = time.monotonic() + 0.20
    while time.monotonic() < deadline:
        if socket_fd_count(pid) == expected:
            return
        time.sleep(0.002)
    raise AssertionError(f"server did not reach {expected} accepted socket fds")


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        process = launch(binary, scene, path)
        try:
            baseline = socket_fd_count(process.pid)
            generation = call(companion, "health")["generation_id"]
            wait_for_socket_count(process.pid, baseline)
            earlier = [partial(companion) for _ in range(3)]
            try:
                wait_for_socket_count(process.pid, baseline + 3)
                for client in earlier:
                    client.setblocking(False)
                    try:
                        response = client.recv(1, socket.MSG_DONTWAIT)
                    except BlockingIOError:
                        pass
                    else:
                        raise AssertionError(f"earlier partial client already closed: {response!r}")
                queued = partial(companion)
                try:
                    wait_for_socket_count(process.pid, baseline + 4)
                    queued.setblocking(False)
                    try:
                        response = queued.recv(1, socket.MSG_DONTWAIT)
                    except BlockingIOError:
                        pass
                    else:
                        raise AssertionError(f"queued partial client already closed: {response!r}")
                    queued.settimeout(2)
                    os.kill(process.pid, signal.SIGSTOP)
                    try:
                        time.sleep(0.35)
                    finally:
                        started = time.monotonic()
                        os.kill(process.pid, signal.SIGCONT)
                    try:
                        response = queued.recv(1)
                    except ConnectionResetError:
                        response = b""
                    elapsed = time.monotonic() - started
                    assert response == b""
                    assert elapsed < 0.20, f"queued frame got a fresh deadline: {elapsed:.3f}s"
                finally:
                    queued.close()
            finally:
                for client in earlier:
                    client.close()

            earlier = [partial(companion) for _ in range(2)]
            try:
                time.sleep(0.10)
                connected = time.monotonic()
                stop = call(companion, "stop", command_id="queued-valid-stop",
                            generation_id=generation)
                elapsed = time.monotonic() - connected
                assert stop["ok"] and stop["accepted"], stop
                assert elapsed < 0.65, f"valid stop classification exceeded queue bound: {elapsed:.3f}s"
            finally:
                for client in earlier:
                    client.close()
        finally:
            stop_process(process, path)
    print("queued partial frame expired at accept-time deadline; valid stop remained bounded")


if __name__ == "__main__":
    main()
