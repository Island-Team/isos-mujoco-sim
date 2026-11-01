# Build and run

**First use of the integrated path:** build and test the simulator below; install or link the exact verified package as described in [backend.md](backend.md); preview `sim-hardware` through IsOS and choose a scene; Validate and Apply one graph revision; run IsOS and wait for EOS and simulator strict health; inspect read-only camera/base/arm observations and the current run's first ready or failure event in IsOS Logs; then stop the deployment through IsOS. Managed base/arm movement remains unavailable until R06 proves physical stop. The standalone launcher and timed evaluator later on this page are separate development workflows. See [the package](interfaces/package.md), [socket](interfaces/socket.md), [design](design.md#r05-cross-owner-qualification) and [implementation TODO](todo.md).

[中文](../../docs_cn/mujoco/usage_cn.md)

[Package overview](README.md) · [Benchmark tasks](benchmarks.md)

Build the simulator separately from EOS. Install MuJoCo 3.16.0, copy [`.env.example`](../../.env.example) to the ignored `.env`, and set `MUJOCO_ROOT` there to its real installation directory. It must contain `include/mujoco/mujoco.h`, `lib/libmujoco.so`, `bin/compile`, and `bin/simulate`. CMake also needs C++20, protobuf, gRPC, and libjpeg.

```sh
. ./.env
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT to your installed MuJoCo 3.16.0 directory}"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Standalone launcher

The root scripts manage a standalone simulator in the background. They load the local `.env` and optional ignored `launch.conf`; [launch.conf.example](../../launch.conf.example) shows the defaults. Relative scene, executable, and run-directory paths are resolved from the repository root. The default run directory is `.run/mujoco/`, with owner-only simulator and benchmark sockets, logs, and process records.

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
./launch.sh --scene navigation --gui
./kill.sh
```

`--gui` opens MuJoCo's independent `simulate` viewer for the same XML. It requires a desktop display and the `MUJOCO_ROOT` viewer tools; it does not show the live simulator state or seeded reset variation. `--no-gui` is the default. `--manual-step`, `--run-dir PATH`, and `--executable PATH` override launcher defaults. If you use a custom run directory, pass the same `--run-dir` to `kill.sh`. The stop script checks the recorded process identity and only stops processes started by `launch.sh`; it does not stop EOS-owned simulator processes. Inspect `.run/mujoco/simulator.log` or `viewer.log` if startup fails.

For direct execution without the process scripts, the executable requires absolute paths for its robot socket, benchmark socket, and scene. Add a distinct absolute `--v2-socket` path when testing the current EOS adapter protocol. `--scene` chooses one supported profile when the process starts. `--manual-step` starts paused; otherwise the simulator advances at the 2 ms physics step in real time. A benchmark `Reset` also pauses it for deterministic stepping. Socket paths must differ, and the scene must be a regular file.

Direct launch without `--managed-strict-socket` remains the legacy socket `2.0.0` mode: existing framed clients may omit or reuse `node` and `command_id`, and the historical gRPC actuator listener remains available. This is useful for old integrations but does not qualify a managed IsOS graph. The strict flag is an EOS-owned launch choice derived from verified generated configuration, not a graph setting or a standalone launcher default. EOS now launches the verified child with that flag and checks strict health for every declared device; the scoped R05 replay is recorded in the [design](design.md#r05-cross-owner-qualification). See the [socket contract](interfaces/socket.md).

```sh
build/eos-mujoco-sim \
  --socket /tmp/eos-simulator.sock \
  --benchmark-socket /tmp/eos-benchmark.sock \
  --scene "$PWD/assets/scenes/navigation/scene.xml" \
  --manual-step
```

The Unix sockets are owner-only (`0600`). Use a private runtime directory for evaluation and give the benchmark socket only to the evaluator. Stop the process with `SIGINT` or `SIGTERM`; it removes its sockets on normal shutdown. `--help` prints the available flags.

## IsOS and EOS deployment

For the current IsOS/EOS path, build and link a local `island/mujoco-sim@0.1.1` bundle as described in the [backend guide](backend.md). The published v1.0.1 package uses the retired graph shape; its [release guide](package-release.md) remains for historical installations. MuJoCo 3.16.0 is an operator-provided dependency; set `MUJOCO_ROOT` to the real installation before building the bundle and running the graph.

```sh
python3 tools/build-backend-bundle.py --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.1 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

Stage and select EOS and IsosUI builds with `isos build eos`, `isos version select eos <selector>`, `isos build isosui`, and `isos version select isosui <selector>`. A selector identifies one exact receipt; when multiple EOS builds share a commit, use its source fingerprint. `isos init` exits without starting services. Run `isos serve` in a terminal, preview the installed `sim-hardware` node set with `isos pkg preview-set` or the IsOS API, choose the scene and owner-only socket, then Validate and Apply the draft with the revision-checked IsOS interface. The IsosUI catalog editor is part of the later U01 workbench gate. The preset adds the EOS-owned simulator process, three generic hardware adapters, dispatcher bindings, and typed connections. IsOS preserves an authored graph until the operator applies the new revision.

**P02 package catalog and IsOS selection.** The bundle builder now emits the `0.1.0` catalog descriptor and seven-node `@v0.1` preset with stable `scene`, `camera_device`, `base_device` and `manipulator_device` parameters. Build and inspect the bundle with `python3 tools/build-backend-bundle.py --build-dir build-p02 --output <empty-directory>`; `backend-v2.json` contains two scene IDs, their labels, profiles and SHA-256 values, plus the three device descriptions and scene support lists. After P01 verifies the exact `island/mujoco-sim@0.1.1` receipt, the IsOS P02/P03 slices expose available IDs, Validate and Apply the selected scene and devices against the current saved revision, and retain unavailable saved IDs for correction. A scene edit creates a new saved revision; Restart is required to replace the EOS-owned child. See the [P02 package contract](interfaces/package.md#p02-descriptor-extension) and [negative fixtures](../../tests/fixtures/scene_catalog/negative-cases.json).

Run `isos run` in another terminal to start the applied deployment. IsOS preflights the exact package, assets, scene, MuJoCo library, EOS executables, sockets, and ports before starting graph children. EOS starts the simulator as its direct child. R06 must prove physical stop ordering before managed movement is enabled. `isos deployment stop` stops the deployment only; `isos stop` shuts down the manager, API, UI, deployment, and independent IsOS services. EGIA uses EOS's normal agent interface and never connects to the private benchmark socket. The service manager for model-like processes is separate from this hardware graph.

**R05 managed readiness, scoped qualified:** after Apply, EOS launches the verified child in strict mode and probes `health` for every graph-declared camera, base and arm device. It requires `version:"2.0.0"`, the echoed request ID, `ok:true`, `accepted:true` and `features` containing `strict-socket-v1`. Treat a socket file or process startup line as progress, not readiness. A missing feature, wrong device, failed camera render or exited child leaves the backend unavailable; inspect the current run's first failure event. The pinned cross-owner replay passed this path for pick-place and navigation, including read-only capture and observations. The live EOS catalog deliberately exposes only `safety.estop` for MuJoCo: it withholds `base.velocity` and `arm.movej` until R06 supplies the physical terminal stop fence. Do not attempt a managed movement primitive as part of this R05 first-use replay. See the [qualification](design.md#r05-cross-owner-qualification).

To verify the simulator owner slice directly, start `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"` in a private directory and send a framed `health` request with `node:"base-0"`. The response must echo the ID and include `ok:true`, `accepted:true` and `strict-socket-v1`. Managed launch rejects `--socket` and `--benchmark-socket`; direct launch without the flag continues to support them. `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` replays the owner checks, including full retention capacity.

For a P02 catalog failure, inspect the unavailable scene/device reason and the first package or Apply failure event before changing the draft. A changed linked asset requires explicit relink under the P01 receipt rule. A missing `MUJOCO_ROOT` library blocks launch readiness; a scene/profile mismatch blocks Apply. The graph and running child retain their prior revisions on these failures.

Stop through `isos deployment stop` after inspecting the result and current run logs. R05 adds strict identity and retransmission protection; R06 still must prove the dedicated stop lane, separate base/arm acknowledgment and physical stop before simulator termination and reap. Until R06 passes, an `accepted:true` stop reply alone is not evidence of confirmed safe stop.

**R06 first-use target, implementation candidate pending qualification:** after a new bundle with `strict-stop-v1` has passed its owner and cross-owner gates, run the same Validate/Apply/Run path. The managed child derives an owner-only companion socket at the main socket path plus `.stop`; no graph field is added. Check that `health` for each actuator reports both `strict-socket-v1` and `strict-stop-v1` and that EOS probes the companion stop socket before its catalog offers `base.velocity` or `arm.movej`. EOS sends the matching 32-character `generation_id` from both health paths and `stop_epoch:"0"` with the first bounded managed movement and sends the current proved epoch with later movements; a stale **new** command fails `stop_fenced`, while an identical old command ID returns its stored R05 result. Submit the movement through EOS, then use EOS/IsOS stop while a movement or capture is active. EOS sends governed stops with that generation ID to the companion socket. A delayed request from an old child fails `stale_generation`. Its strict `stop` response must echo its request ID and contain `base_stop:"stopped"`, `arm_stop:"stopped"`, the matching `generation_id`, a nonempty decimal-string `stop_epoch`, `ok:true`, and `accepted:true`; EOS must record the matching terminal result before it terminates and reaps its direct child. The values are defined in the [socket contract](interfaces/socket.md#r06-managed-stop-contract-design-target): status strings are unitless proof states, while `stop_epoch` is a child-local ordering counter used as a movement precondition. A missing/unknown status, timeout, child crash or `stop_outcome_unknown` means safe stop is unconfirmed; inspect the first correlated failure event and the EOS journal, then verify bounded child and both socket paths are cleaned up. Do not infer physical stop from process exit or `accepted` alone. This is a target replay; EOS keeps managed movement out of its public catalog until the R06 cross-owner gate passes.

The v2 package permits `MUJOCO_GUI=1` in the simulator node's `settings.env`. It opens a live X11 view from the same simulator engine used by the v2 socket. The standalone `--gui` launcher below opens a separate static MuJoCo viewer instead. See [backend.md](backend.md) for the node and socket contracts.

## Timed agent episode

This is a separate direct-launch legacy evaluation workflow, outside an EOS-managed strict deployment. Start the simulator with its private benchmark socket and attach the intended evaluator or legacy agent harness. The R05 managed child has no benchmark listener, because Reset and Step can alter its engine state outside Dispatcher. This example resets seed 42, resumes real-time simulation for 30 wall-clock seconds, pauses, and prints one JSON score object:

```sh
build/benchmark-eval \
  --benchmark-socket /absolute/path/to/benchmark.sock \
  --task navigation \
  --seed 42 \
  --duration-s 30
```

Use `--task pick-place` with `assets/scene.xml`, or `--task navigation` with `assets/scenes/navigation/scene.xml`. The evaluator does not inspect the scene or run an agent policy, so the caller must match `--task` to the selected scene. It accepts a positive duration up to 3600 seconds. Its `success` is all three goals for pick and place or `navigation` alone for navigation; collision count and elapsed simulated time are reported separately. See [benchmark method](benchmarks.md) for multi-seed reporting.

## Scene inspection and verification

The standalone viewer compiles MJCF first. It shows the XML's initial layout; seeded variations happen only during `Reset` in the running simulator.

```sh
. ./.env
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT to your installed MuJoCo 3.16.0 directory}"
tools/scene-view.sh --scene "$PWD/assets/scene.xml"
tools/scene-view.sh --check --scene "$PWD/assets/scenes/navigation/scene.xml"
tools/scene-view.sh --snapshot /tmp/navigation.png --scene "$PWD/assets/scenes/navigation/scene.xml"
```

The interactive viewer needs a desktop display. `--check` validates model loading headlessly; `--snapshot` needs MuJoCo's `bin/render`. Run `ctest --test-dir build --output-on-failure` for engine, socket, evaluator, and scene checks. A passing viewer check establishes XML loadability, while the engine and smoke checks exercise reset, commands, service behavior, and scoring.

**Related:** [Design](design.md) · [EOS simulator interface](interfaces/simulator.md) · [Benchmark interface](interfaces/benchmark.md)
