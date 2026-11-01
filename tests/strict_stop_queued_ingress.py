#!/usr/bin/env python3
"""Queued partial frames retain their accept-time 250 ms ingress deadline."""

from pathlib import Path
import socket
import sys
import tempfile
import time

from strict_stop import call, launch, partial, stop_process


def main():
    binary, scene = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "managed.sock"
        companion = Path(str(path) + ".stop")
        process = launch(binary, scene, path)
        try:
            generation = call(companion, "health")["generation_id"]
            earlier = [partial(companion) for _ in range(3)]
            try:
                time.sleep(0.10)
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
                    connected = time.monotonic()
                    assert queued.recv(1) == b""
                    elapsed = time.monotonic() - connected
                    assert elapsed < 0.33, f"queued frame got a fresh deadline: {elapsed:.3f}s"
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
