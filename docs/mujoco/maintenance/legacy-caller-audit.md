# Legacy caller audit (2026-11-04)

[中文](../../../docs_cn/mujoco/maintenance/legacy-caller-audit.md)

The managed IsOS path uses the strict framed v2 socket. The following older paths still have callers, so they are retained.

| Candidate | Build, runtime, or test caller | Decision |
|---|---|---|
| `src/service.cpp`, `src/service.h`, `proto/simulator.proto` | `src/main.cpp` calls `Serve`; direct `launch.sh` passes `--socket` and `--benchmark-socket`; `tests/smoke.sh`, `tests/eval.py`, and `smoke-rpc` exercise the gRPC paths. The simulator proto is mirrored in EOS. | Retain direct-run compatibility and the published proto. Managed strict mode forbids both listeners. |
| `proto/benchmark.proto`, `benchmark-eval` | The trusted direct-run evaluator uses Reset, Step, and score RPCs; `tests/eval.py` exercises it. | Retain, private to the evaluator. |
| `benchmark-reset` | `tests/q03_socket_bench.py` uses this private tool for deterministic seeded resets in the Q03 socket benchmark; the Q03 qualification commands name the target. | Retain until the benchmark harness has a replacement. |
| `--v2-socket` direct mode | `tests/v2.py` and the Q03 harness exercise it; direct clients may coexist with the historical listeners. | Retain. The README and English usage example now show all three distinct sockets. |

No candidate above is unused implementation. The IsOS-managed child still starts with `--managed-strict-socket` and only the owner-only v2 and companion stop sockets.

## Current baseline

- Commands: `eos-mujoco-sim --help` lists direct `--socket`, `--benchmark-socket`, optional `--v2-socket`, and `--managed-strict-socket`; `launch.sh`/`kill.sh` own a standalone process; `benchmark-eval` is evaluator-only.
- Installation: `CMakeLists.txt` installs only `eos-mujoco-sim` to `bin`. `tools/build-backend-bundle.py` produces the separate IsOS package; tests and benchmark tools are not installed by CMake.
- Interfaces: the direct historical gRPC simulator and benchmark sockets remain private; the managed path exposes only the framed v2 socket and derived `.stop` companion. The exact request and response contract is `docs/mujoco/interfaces/socket.md`.
- Graph versions: `tools/node_contributions.py` emits seven `@v0.1` registered types; `tools/scene_catalog.py` emits catalog `0.1.0`. IsOS owns authored graph versioning and persistence; the simulator does not edit the applied graph.
