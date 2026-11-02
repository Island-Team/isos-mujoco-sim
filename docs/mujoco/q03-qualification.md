# Q03 simulator qualification design

[中文](../../docs_cn/mujoco/q03-qualification_cn.md)

**Status:** design candidate; release evidence is open. The simulator owns scene loading, deterministic reset, physics, rendering, its private socket, and benchmark scoring. EOS owns the robot-facing route. Never expose benchmark ground truth through EOS, EGIA, or UI.

## Fixed inputs and owner checks

Build from the fetched `master` commit with MuJoCo 3.16.0 and record the compiler, CMake, CTest, library, source and scene hashes. Run tracked C++ sources through `clang-format --dry-run --Werror`; run CMake configure/build and full CTest, then the focused strict socket/capacity/Stop, scene, engine and benchmark tests. Run the node-contribution fixture and construct a fresh `island/mujoco-sim@0.1.1` bundle in an empty output directory. Save its manifest/archive SHA-256 and verify it through IsOS in a clean home. Keep complete command, output and exit records under ignored `logs/test/<run-id>/`, including failed attempts.

The installed owner replay must select both catalog scenes, prove exact package and scene admission, observe a read-only frame, send one admitted base or arm command through EOS, inject simulator death, and observe the current-run failure and governed Stop/reap. Preserve selected graph revision, run IDs, package receipt, child identity and the cross-owner verifier result. Independent standalone CTest is necessary but does not substitute for this installed replay.

## Initial socket baseline

Use a private, owner-only v2 Unix socket and no GUI. For each of `assets/scene.xml` and `assets/scenes/navigation/scene.xml`, launch three fresh simulator processes. Keep the scene, renderer, camera dimensions and protocol fixed; seed deterministic reset with 42 through the separate private benchmark socket when a reset is needed. After 20 warm-up calls, issue 200 serial `base_observe` requests and 20 serial `camera_capture` requests. Record every monotonic elapsed time, response status and byte count, and the measured wall duration for each operation group. Report successful requests/s or frames/s, midpoint median and nearest-rank p99 in milliseconds for each process and pooled samples; report all failures and timeouts separately. This measures the simulator socket, not IsOS HTTP, EOS Dispatcher or browser latency. No performance target is inferred from the initial measurements.

The harness must fail clearly on unavailable socket, malformed response, timeout, wrong scene and unexpected child exit; focused tests must cover those paths. An independent agent reviews this design before implementation and reviews the harness, evidence and PR before merge into MuJoCo `master`. The Q03 cross-owner summary records final exact pins; Q04 owns publication and tags.
