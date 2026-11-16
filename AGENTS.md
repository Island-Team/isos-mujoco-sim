# Repository agent guide

Follow [Island coding conventions 1.4.0](docs/island/conventions.v1.4.0.md) and the [MuJoCo documentation index](docs/mujoco/README.md). This file maps the current source and ownership; the owning `interfaces/` pages define public behavior. Read the relevant `start/`, `interfaces/`, and `core/` pages before changing a boundary. Keep English `docs/` and Chinese `docs_cn/` pages, examples, and links aligned.

## Current source and ownership

`src/mujoco/` owns scene loading, deterministic reset, physics, rendering, and private benchmark scoring. `src/isos/` owns the native service and strict socket. `src/plugin/` builds the C++20 `isos_node_v2` adapter loaded by EOS. `robocasa_core/` is the Python user hardware API; `tools/robocasa_worker.py` runs it in a separate IsOS-owned service. `tools/nodes.py` and `tools/bundle.py` declare and package both services. Source, package, node type, graph, ABI, and socket versions are independent.

IsOS owns verified package selection, service configuration, graph Apply, and child supervision. EOS owns Dispatcher admission, the robot-facing hardware boundary, health, and Stop proof. EGIA acts through EOS. Preserve the current EOS graph port and payload contracts when changing an adapter; camera `frame` is also consumed by the EOS Vision route. The native `cam-0` device renders JPEG from the selected scene, while RoboCasa cameras return RGB8. Keep service and device behavior isolated. Do not expose benchmark ground truth or `proto/benchmark.proto` to EOS or EGIA. If changing the retained simulator RPC, keep `proto/simulator.proto` aligned with its EOS-owned counterpart when that source is available.

## Change and verification workflow

Create a focused `refactor(v2)/<topic>` branch from the confirmed integration target and follow the shared publication workflow. Update the owning contract, implementation, fixtures, tests, and first-use guidance together. Keep scene metadata, provenance, task rules, interface examples, and verification instructions under [docs/mujoco/](docs/mujoco/README.md) in sync. A new scene needs deterministic reset, a defined success condition, source attribution and license review, load and replay tests, and usable EOS-visible capabilities. Describe current behavior in present tense and future behavior as a labeled target.

Use the repository's CMake and C++20 patterns, root formatting rules, Python boundary tests, CTest, and selected-service IsOS package checks. Test success, rejection, service failure, and Stop at the affected boundary. Save complete check output under ignored `data/test/<run-id>/` and record commands and outcomes in the owning guide. A local build or package check is evidence for a candidate, not publication of a release.
