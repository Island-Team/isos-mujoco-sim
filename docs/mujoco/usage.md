# Build and run

**First use of the integrated path:** build and test the simulator below; install or link the exact verified package as described in [backend.md](backend.md); preview `sim-hardware` in IsosUI and choose a scene; validate and Apply one graph revision; run IsOS and wait for EOS and simulator health; use only EOS-declared controls and observations; then inspect the current run's first ready or failure event in IsOS Logs before filtering by node/correlation ID; finally stop the deployment through IsOS. The standalone launcher and timed evaluator later on this page are optional development workflows. See [the package](interfaces/package.md), [socket](interfaces/socket.md), [target algorithms](design.md) and [implementation TODO](todo.md). Selector metadata, shared correlation logs and full stop coordination are target behavior, not current guarantees.

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

Stage and select EOS and IsosUI builds with `isos build eos`, `isos version select eos <selector>`, `isos build isosui`, and `isos version select isosui <selector>`. A selector identifies one exact receipt; when multiple EOS builds share a commit, use its source fingerprint. `isos init` exits without starting services. Run `isos serve` in a terminal, open the Graph workbench, preview the installed `sim-hardware` node set with the chosen scene and owner-only socket, then Validate and Apply the draft. The preset adds the EOS-owned simulator process, three generic hardware adapters, dispatcher bindings, and typed connections. IsOS preserves an authored graph until the operator applies the new revision.

Run `isos run` in another terminal to start the applied deployment. IsOS preflights the exact package, assets, scene, MuJoCo library, EOS executables, sockets, and ports before starting graph children. EOS starts the simulator as its direct child and stops admitted actuators before terminating it. `isos deployment stop` stops the deployment only; `isos stop` shuts down the manager, API, UI, deployment, and independent IsOS services. EGIA uses EOS's normal agent interface and never connects to the private benchmark socket. The service manager for model-like processes is separate from this hardware graph.

The v2 package permits `MUJOCO_GUI=1` in the simulator node's `settings.env`. It opens a live X11 view from the same simulator engine used by the v2 socket. The standalone `--gui` launcher below opens a separate static MuJoCo viewer instead. See [backend.md](backend.md) for the node and socket contracts.

## Timed agent episode

Start the simulator and EOS/EGIA agent first. The evaluator connects only to the private benchmark socket. This example resets seed 42, resumes real-time simulation for 30 wall-clock seconds while the separate agent acts, pauses, and prints one JSON score object:

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
