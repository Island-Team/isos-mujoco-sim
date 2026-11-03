# Q03 simulator qualification design

[中文](../../docs_cn/mujoco/q03-qualification_cn.md)

**Status:** owner source checks and selected local cross-owner Q03 replay passed; Q04 merged-head release review remains open. The simulator owns scene loading, deterministic reset, physics, rendering, its private socket, and benchmark scoring. EOS owns the robot-facing route. Never expose benchmark ground truth through EOS, EGIA, or UI.

**Q03 owner baseline (2026-11-03):** the direct socket harness is implemented in `tests/q03_socket_bench.py`, with private `benchmark-reset` and negative unit tests. The measured run is local evidence, not the cross-owner installed replay or release approval. Complete initial output remains in ignored `logs/test/20261103-q03-mujoco/`; the final renderer-probe bundle is in `logs/test/20261103-q03-mujoco-review-final/`, and the collision-free raw samples and six child logs are in `logs/test/20261103-q03-mujoco-review-final-2/`.

## Fixed inputs and owner checks

Build from the fetched `master` commit with MuJoCo 3.16.0 and record the compiler, CMake, CTest, library, source and scene hashes. Run tracked C++ sources through `clang-format --dry-run --Werror`; run CMake configure/build and full CTest, then the focused strict socket/capacity/Stop, scene, engine and benchmark tests. Run the node-contribution fixture and construct a fresh `island/mujoco-sim@0.1.1` bundle in an empty output directory. Save its manifest/archive SHA-256 and verify it through IsOS in a clean home. Keep complete command, output and exit records under ignored `logs/test/<run-id>/`, including failed attempts.

The installed owner replay must select both catalog scenes, prove exact package and scene admission, observe a read-only frame, send one admitted base or arm command through EOS, inject simulator death, and observe the current-run failure and governed Stop/reap. Preserve selected graph revision, run IDs, package receipt, child identity and the cross-owner verifier result. Independent standalone CTest is necessary but does not substitute for this installed replay.

## Initial socket baseline

Use a private, owner-only v2 Unix socket and no GUI. For each of `assets/scene.xml` and `assets/scenes/navigation/scene.xml`, launch three fresh simulator processes. Use a direct non-managed benchmark process (never an EOS-owned managed child) with private absolute, distinct `--socket`, `--benchmark-socket`, `--v2-socket`, and `--scene` paths. For example, `build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`. Require a successful private `Reset(seed=42)` and record its response before each process warm-up; keep the engine paused, with no asynchronous stepping, for all measured requests. Use the package EGL-only `SimEngine::RenderCamera` path and 640×480 `cam-0` capture. The socket does not export a resolved renderer identity; enable the opt-in EGL context probe on the child, record its runtime EGL vendor and GL renderer from the child log, and assert the observed JPEG format, byte length and image dimensions on every repetition. After 20 warm-up calls, issue 200 serial `base_observe` requests and 20 serial `camera_capture` requests. Record every monotonic elapsed time, response status and byte count, and the measured wall duration for each operation group. Report successful requests/s or frames/s, midpoint median and nearest-rank p99 in milliseconds for each process and pooled samples; report all failures and timeouts separately. This measures the simulator socket, not IsOS HTTP, EOS Dispatcher or browser latency. No performance target is inferred from the initial measurements.

The harness must fail clearly on unavailable socket, malformed response, timeout, wrong scene and unexpected child exit; focused tests must cover those paths. An independent agent reviews this design before implementation and reviews the harness, evidence and PR before merge into MuJoCo `master`. The Q03 cross-owner summary records final exact pins; Q04 owns publication and tags.

## Reproducible owner evidence

From the repository root, set `MUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0` and run:

```sh
git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror
cmake -S . -B build-q03 -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build-q03 -j4
ctest --test-dir build-q03 --output-on-failure
ctest --test-dir build-q03 -R 'strict-socket|strict-capacity|strict-stop|v2-socket|benchmark-eval|engine-test|scene-catalog|bundle-catalog|q03-socket' --output-on-failure
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tests/node_contributions.py
python3 tools/build-backend-bundle.py --build-dir build-q03 --output logs/test/20261103-q03-mujoco-review-final/bundle
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/pick-place.json
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scenes/navigation/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/navigation.json
```

The post-format full CTest passed 25/25 and the focused set passed 16/16. The static R05 and R06 fixture matrices passed 31 and 48 cases; the node contribution checker passed. The first formatting check failed in three pre-existing files (`tests/smoke.cpp`, `src/service.cpp`, `src/gui.cpp`, 86 diagnostics); a separate formatting-only commit corrected them and the final tracked C++ check passed. The final package builder produced `mujoco-sim-v0.1.1-linux-x86_64.tar.gz` with SHA-256 `05a9346db26f43510c1986ff7431038ae29197ac85300a2f1efd1211f3458fe6`. The installed IsOS→EOS replay remains open for the cross-owner gate.

On this x86_64 Linux host, C++ is GCC 13.3.0, MuJoCo is the installed 3.16.0 tree, and the benchmark uses the package EGL path without a GUI. `environment.json` records the kernel, tool versions, source pin, binaries, scenes, library and archive hashes. The runtime probe resolved EGL vendor `NVIDIA` and GL renderer `NVIDIA GeForce RTX 2080 Ti/PCIe/SSE2` for all six processes. With seed 42, paused scenes, 20 warm-up observations, three fresh processes per scene and 200 observations plus 20 captures per process, the final raw run recorded:

| Scene | Operation | Success/failure | Throughput | Median | p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| Pick-place | `base_observe` | 600/0 | 17,549/s | 0.054 ms | 0.089 ms |
| Pick-place | `camera_capture` | 60/0 | 716 frames/s | 1.261 ms | 2.961 ms |
| Navigation | `base_observe` | 600/0 | 18,033/s | 0.053 ms | 0.074 ms |
| Navigation | `camera_capture` | 60/0 | 731 frames/s | 1.262 ms | 2.453 ms |

Throughput uses successful calls divided by summed measured group wall time. Median is the midpoint of sorted successful samples; p99 is nearest rank. Earlier raw attempts in the same log directory differ, likely from local load; no performance target or cross-host claim follows from this baseline. Each repetition records its own values, successful `Reset(seed=42)`, observed JPEG probe dimensions and all sample statuses, bytes and timeout flags. Failed requests record zero accepted payload bytes; summaries count timeouts separately. The opt-in child log records the runtime EGL vendor and GL renderer after context creation; the socket response supplies the observed JPEG dimensions. Log filenames use the benchmark output stem, keeping the two `scene.xml` workloads separate. The prior run overwrote child logs because both scenes shared that basename; its raw samples remain preserved but its child logs are superseded by this run. These numbers cover only the private simulator socket.

### Selected installed archive evidence, 2026-11-03

The selected 0.1.1 bundle records MuJoCo source commit `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`; this exact source identity must remain in `release.json`. The selected release file SHA-256 is `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`, and the archive asset SHA-256 is `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`. EOS Q03 selection SHA-256 is `116aef2846750a96275645e4dec3021ad716ce6fb80b05c087a2ce377a74b990`; frozen review main and case build receipts have SHA-256 `977293e097779f636cb70bde9f3d5657bc9351b0b9f67534ca7beb41a97ef915` and `20b2dc444d4f90ca1e4cf4b8a2404893c53cd20de19a090ce02debf0c539ab5d`.

In the sealed clean-home replay, IsOS verified and installed that archive, selected the `pick-place` scene and available camera/base/manipulator devices, and EOS launched the verified MuJoCo executable as its direct child. A real 640×480 camera frame reached EOS, EGIA Vision and browser observations. R06/A03 selected-pin fault trials passed child death, stop/reap and restart checks without replaying uncertain movement; final deployment Stop was confirmed with no managed survivors. The six selected case groups and `Q01_FULL_VERIFIED` are preserved under ignored EOS `logs/test/20261103-q03-selected-final-15/`. The private socket benchmark above remains a separate fixed-workload measurement. This installed replay covers a local simulated hosted Origin; Q04 merged-head review and tag publication remain open. Changing the package source HEAD requires rebuilding and reverifying the 0.1.1 bundle.
