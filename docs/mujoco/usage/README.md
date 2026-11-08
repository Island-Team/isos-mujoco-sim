# Build and run

**First use of the integrated path:** build and test the simulator below; install or link the exact verified package as described in [backend.md](isos-pkg.md); preview `sim-hardware` through IsOS and choose a scene; Validate and Apply one graph revision; run IsOS and wait for EOS and simulator strict health; inspect read-only camera/base/arm observations and the current run's first ready or failure event in IsOS Logs; then stop the deployment through IsOS. The merged R06 owner lane and scoped cross-owner replay have exercised governed base/arm movement and stop; broader R06 qualification remains open. The standalone launcher and RoboCasa smoke episode later on this page are local development workflows. See [the package](../interfaces/package.md), [socket](../interfaces/socket.md), [design](../architecture.md#r05-cross-owner-qualification) and [implementation TODO](../todo.md).

[中文](../../../docs_cn/mujoco/usage/README_cn.md)

The [Q03 qualification design](../q03-qualification.md) fixes the selected installed replay and initial socket benchmark before release.

[Package overview](../README.md) · [First run](dev.md) · [Benchmark tasks](../benchmarks/Robocasa/README.md)

Build the simulator separately from EOS. With `SIM_PROFILE=dev`, `./build.sh` builds native targets and checks RoboCasa, asking before any missing source, runtime, or asset download. The committed `isos-pkg` default builds native targets only. `./build.sh --output <empty absolute directory>` builds only the IsOS package asset. Install MuJoCo 3.3.1, copy [`.env.example`](../../../.env.example) to the ignored `.env`, and set `MUJOCO_ROOT` there to its real installation directory. It must contain `include/mujoco/mujoco.h`, `lib/libmujoco.so`, `bin/compile`, and `bin/simulate`. CMake also needs C++20, protobuf, gRPC, and libjpeg.

`src/mujoco/` owns the native simulation engine and has a direct development executable. `src/isos/` owns the package-facing process and EOS socket adapters. After building, use `build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20` to load, reset, and step the core without starting sockets. Use `build/eos-mujoco-sim` or the standalone launcher below to exercise the wrapper.

```sh
cp .env.example .env
# Edit .env: set MUJOCO_ROOT to the absolute MuJoCo 3.3.1 installation path.
./build.sh
ctest --test-dir build --output-on-failure
```

## RoboCasa benchmark

`./launch.sh` launches the configured upstream RoboCasa smoke episode. List tasks with `./launch.sh --list-benchmarks --filter Fridge` and kitchen scene choices with `./launch.sh --list-kitchens`; select one with `./launch.sh --benchmark CloseFridge --seed 42 --steps 20`. Set task and camera defaults in `config/benchmarks/robocasa.toml`, selected by root `BENCHMARK_CONFIG`, or override them with `BENCHMARK_*` variables in `.env`, then use `./launch.sh --show-config` to inspect them. Set `ROBOCASA_ROOT` to use another checkout; an empty value uses ignored `.local/robocasa`. The launcher asks before downloading missing source, runtime, or assets, including the larger asset set needed for other tasks or a fixed kitchen scene. See the [benchmark method](../benchmarks/Robocasa/README.md).

## Standalone launcher

With `--scene`, the root scripts manage the legacy C++ simulator in the background. They read root [config.toml](../../../config.toml) first, then the optional ignored `.env`, whose values override the TOML defaults. The supported keys are `MUJOCO_ROOT`, `SIM_EXECUTABLE`, `SIM_SCENE`, `SIM_RUN_DIR`, `SIM_GUI`, and `SIM_MANUAL_STEP`; the last two are booleans. Relative scene, executable, and run-directory paths are resolved from the repository root. The default run directory is `.run/mujoco/`, with owner-only simulator and benchmark sockets and process records. Local output is in ignored `logs/dev/`, with per-run files and `latest.log` shortcuts.

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
./launch.sh --scene navigation --gui
./kill.sh
```

`--gui` opens MuJoCo's independent `simulate` viewer for the same XML. It requires a desktop display and the `MUJOCO_ROOT` viewer tools; it does not show the live simulator state or seeded reset variation. The dev profile opens the GUI by default; `--no-gui` disables it. The isos-pkg profile defaults to headless. `--manual-step`, `--run-dir PATH`, and `--executable PATH` override launcher defaults. If you use a custom run directory, pass the same `--run-dir` to `kill.sh`. The stop script checks the recorded process identity and only stops processes started by `launch.sh`; it does not stop EOS-owned simulator processes. Inspect `logs/dev/native/latest.log` or the corresponding `*-viewer.log` if startup fails.

For direct execution without the process scripts, the executable requires absolute paths for its robot socket, benchmark socket, and scene. Add a distinct absolute `--v2-socket` path when testing the current EOS adapter protocol. `--scene` chooses one supported profile when the process starts. `--manual-step` starts paused; otherwise the simulator advances at the 2 ms physics step in real time. A benchmark `Reset` also pauses it for deterministic stepping. Socket paths must differ, and the scene must be a regular file.

Direct launch without `--managed-strict-socket` remains the legacy socket `2.0.0` mode: existing framed clients may omit or reuse `node` and `command_id`, and the historical gRPC actuator listener remains available. This is useful for old integrations but does not qualify a managed IsOS graph. The strict flag is an EOS-owned launch choice derived from verified generated configuration, not a graph setting or a standalone launcher default. EOS now launches the verified child with that flag and checks strict health for every declared device; the scoped R05 replay is recorded in the [design](../architecture.md#r05-cross-owner-qualification). See the [socket contract](../interfaces/socket.md).

```sh
build/eos-mujoco-sim \
  --socket /tmp/eos-simulator.sock \
  --benchmark-socket /tmp/eos-benchmark.sock \
  --v2-socket /tmp/eos-v2.sock \
  --scene "$PWD/assets/scenes/navigation/scene.xml" \
  --manual-step
```

The Unix sockets are owner-only (`0600`). Use a private runtime directory for evaluation and give the benchmark socket only to the evaluator. Stop the process with `SIGINT` or `SIGTERM`; it removes its sockets on normal shutdown. `--help` prints the available flags.

## IsOS and EOS deployment

For the current IsOS/EOS path, build and link a local `island/mujoco-sim@0.1.2` bundle as described in the [backend guide](isos-pkg.md). The published v1.0.1 package uses the retired graph shape; its [release guide](../package-release.md) remains for historical installations. MuJoCo 3.3.1 is an operator-provided dependency; set `MUJOCO_ROOT` to the real installation before building the bundle and running the graph.

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

Stage and select EOS and IsosUI builds with `isos build eos`, `isos version select eos <selector>`, `isos build isosui`, and `isos version select isosui <selector>`. A selector identifies one exact receipt; when multiple EOS builds share a commit, use its source fingerprint. `isos init` exits without starting services. Run `isos serve` in a terminal, preview the installed `sim-hardware` node set with `isos pkg preview-set` or the IsOS API, choose the scene and owner-only socket, then Validate and Apply the draft with the revision-checked IsOS interface. The IsosUI catalog editor is part of the later U01 workbench gate. The preset adds the EOS-owned simulator process, three generic hardware adapters, dispatcher bindings, and typed connections. IsOS preserves an authored graph until the operator applies the new revision.

**P02 package catalog and IsOS selection.** The bundle builder now emits the `0.1.0` catalog descriptor and seven-node `@v0.1` preset with stable `scene`, `camera_device`, `base_device` and `manipulator_device` parameters. Build and inspect the bundle with `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <empty-directory>`; `backend-v2.json` contains two scene IDs, their labels, profiles and SHA-256 values, plus the three device descriptions and scene support lists. After P01 verifies the exact `island/mujoco-sim@0.1.2` receipt, the IsOS P02/P03 slices expose available IDs, Validate and Apply the selected scene and devices against the current saved revision, and retain unavailable saved IDs for correction. A scene edit creates a new saved revision; Restart is required to replace the EOS-owned child. See the [P02 package contract](../interfaces/package.md#p02-descriptor-extension) and [negative fixtures](../../../tests/fixtures/scene_catalog/negative-cases.json).

Run `isos run` in another terminal to start the applied deployment. IsOS preflights the exact package, assets, scene, MuJoCo library, EOS executables, sockets, and ports before starting graph children. EOS starts the simulator as its direct child. The scoped R06 replay proved physical stop ordering for pick-place and navigation; broader failure qualification remains open. `isos deployment stop` stops the deployment only; `isos stop` shuts down the manager, API, UI, deployment, and independent IsOS services. EGIA uses EOS's normal agent interface and never connects to the private benchmark socket. The service manager for model-like processes is separate from this hardware graph.

**R05 managed readiness, scoped qualified:** after Apply, EOS launches the verified child in strict mode and probes `health` for every graph-declared camera, base and arm device. It requires `version:"2.0.0"`, the echoed request ID, `ok:true`, `accepted:true` and `features` containing `strict-socket-v1`. Treat a socket file or process startup line as progress, not readiness. A missing feature, wrong device, failed camera render or exited child leaves the backend unavailable; inspect the current run's first failure event. The pinned cross-owner replay passed this path for pick-place and navigation, including read-only capture and observations. At that R05 baseline, the EOS catalog exposed only `safety.estop` for MuJoCo and withheld `base.velocity` and `arm.movej`; the R06 replay below subsequently exercised governed movement and stop. The R05 replay itself released no managed movement. See the [qualification](../architecture.md#r05-cross-owner-qualification).

To verify the simulator owner slice directly, start `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"` in a private directory and send a framed `health` request with `node:"base-0"`. The response must echo the ID and include `ok:true`, `accepted:true` and `strict-socket-v1`. Managed launch rejects `--socket` and `--benchmark-socket`; direct launch without the flag continues to support them. `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` replays the owner checks, including full retention capacity.

For a P02 catalog failure, inspect the unavailable scene/device reason and the first package or Apply failure event before changing the draft. A changed linked asset requires explicit relink under the P01 receipt rule. A missing `MUJOCO_ROOT` library blocks launch readiness; a scene/profile mismatch blocks Apply. The graph and running child retain their prior revisions on these failures.

Stop through `isos deployment stop` after inspecting the result and current run logs. R05 adds strict identity and retransmission protection; the merged R06 companion lane and scoped replay proved separate base/arm acknowledgment before simulator termination and reap for both scenes. An `accepted:true` reply alone is never evidence of confirmed safe stop; inspect EOS's selected terminal receipt and IsOS's final outcome.

**R06 scoped first-use behavior:** the reviewed `strict-stop-v1` owner implementation merged in [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21), and a real pick-place/navigation IsOS → EOS → MuJoCo replay exercised governed movement and stop. With exact verified owner builds, use the same Validate/Apply/Run path. The managed child derives an owner-only companion socket at the main socket path plus `.stop`; no graph field is added. Check that `health` for each actuator reports both `strict-socket-v1` and `strict-stop-v1` and that EOS probes the companion stop socket before its catalog offers `base.velocity` or `arm.movej`. EOS sends the matching 32-character `generation_id` from both health paths and `stop_epoch:"0"` with the first bounded managed movement and sends the current proved epoch with later movements; a stale **new** command fails `stop_fenced`, while an identical old command ID returns its stored R05 result. Submit the movement through EOS, then use EOS/IsOS stop while a movement or capture is active. EOS sends governed stops with that generation ID to the companion socket. A delayed request from an old child fails `stale_generation`. Its strict `stop` response must echo its request ID and contain `base_stop:"stopped"`, `arm_stop:"stopped"`, the matching `generation_id`, a nonempty decimal-string `stop_epoch`, `ok:true`, and `accepted:true`; EOS must validate that proof before terminating and reaping its direct child, then publish the selected terminal receipt only after cleanup. The values are defined in the [socket contract](../interfaces/socket.md#r06-managed-stop-contract): status strings are unitless proof states, while `stop_epoch` is a child-local ordering counter used as a movement precondition. A missing/unknown status, timeout, child crash or `stop_outcome_unknown` means safe stop is unconfirmed; inspect the first correlated failure event and the EOS journal, then verify bounded child and both socket paths are cleaned up. Do not infer physical stop from process exit or `accepted` alone. The scoped replay confirmed both stop parts, matching generation and epoch `1`, and no surviving child/group/socket; lost stop socket and child crash remained unknown. See the [R06 evidence](../architecture.md#r06-owner-merge-and-scoped-cross-owner-replay). Forced timeout/KILL, GUI unavailability, stale or wrong pipe, and crash recovery still require broader R06 qualification before full M3 control is claimed.

The v2 package permits `MUJOCO_GUI=1` in the simulator node's `settings.env`. It opens a live X11 view from the same simulator engine used by the v2 socket. The standalone `--gui` launcher below opens a separate static MuJoCo viewer instead. See [backend.md](isos-pkg.md) for the node and socket contracts.

## Scene inspection and verification

The standalone viewer compiles MJCF first. It shows the XML's initial layout; seeded variations happen only during `Reset` in the running simulator.

```sh
tools/view.sh --scene "$PWD/assets/scene.xml"
tools/view.sh --check --scene "$PWD/assets/scenes/navigation/scene.xml"
tools/view.sh --snapshot /tmp/navigation.png --scene "$PWD/assets/scenes/navigation/scene.xml"
```

The interactive viewer needs a desktop display. `--check` validates model loading headlessly; `--snapshot` needs MuJoCo's `bin/render`. Run `ctest --test-dir build --output-on-failure` for engine, socket, evaluator, and scene checks. A passing viewer check establishes XML loadability, while the engine and smoke checks exercise reset, commands, service behavior, and scoring.

**Related:** [Design](../architecture.md) · [EOS simulator interface](../interfaces/simulator.md) · [Benchmark interface](../interfaces/benchmark.md)
