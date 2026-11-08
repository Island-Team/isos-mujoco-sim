# IsOS MuJoCo simulator

[中文](README_cn.md) · [First-run guide](docs/mujoco/usage/dev.md) · [Documentation overview](docs/mujoco/README.md)

This repository has two runnable paths. The active benchmark is upstream RoboCasa365 `CloseFridge`, launched locally through its Python environment. The C++ MuJoCo simulator supplies a native development core and an IsOS/EOS package wrapper. Its pick-and-place and navigation scenes remain compatibility fixtures. EOS connects to the wrapper for robot-facing devices and primitives; a trusted evaluator alone uses its private benchmark socket. RoboCasa does not yet have an EOS adapter.

## Build everything

On Linux, install MuJoCo **3.3.1**, a C++20 compiler, CMake 3.22+, protobuf, gRPC, libjpeg, Python 3, `git`, `wget`, and `uv`. Copy the sample environment file and set `MUJOCO_ROOT` to the absolute MuJoCo installation directory. It must contain `include/mujoco/mujoco.h`, `lib/libmujoco.so.3.3.1`, `bin/compile`, and `bin/simulate`.

```sh
cp .env.example .env
# Edit .env: export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`config.toml` holds repository-wide defaults and points to `config/benchmarks/robocasa.toml` for benchmark settings; the ignored `.env` overrides matching values. `./build.sh` builds every C++ target in `build/`, including `mujoco-core` and `eos-mujoco-sim`. In dev mode it also checks RoboCasa source, private Python runtime, and assets, asking before any needed download. To start the wrapper locally and stop it afterward:

The committed `SIM_PROFILE = "isos-pkg"` selects the IsOS package build. For local development, add `export SIM_PROFILE=dev` to `.env`; then `./build.sh` also prepares RoboCasa and `./launch.sh` opens its live camera GUI by default. `--no-gui` runs without a window. In `isos-pkg`, `./build.sh` builds the native targets and `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY` creates the package asset. IsOS server integration remains in the managed backend guide.

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

The wrapper runs in the background, reports its socket paths, and logs to `logs/dev/native/latest.log`. Use `--scene navigation` for the other compatibility fixture. In dev mode, `--scene` opens a separate static viewer by default; it requires a desktop display. The launcher removes stale sockets only after checking that no process owns them. See the [first-run guide](docs/mujoco/usage/dev.md#build-and-run-the-native-simulator) for configuration fields, expected results, and troubleshooting.

## Find and select a task

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
./launch.sh --list-scenes
./launch.sh --scene navigation --no-gui
```

`--list-benchmarks` reads RoboCasa's registered tasks for the selected split; the default `target` split has 50 tasks in the pinned checkout. `--filter` narrows the list. `CloseFridge` is the verified local smoke task. Selecting another task or a fixed kitchen scene with `--kitchen-scene 1:1` makes the launcher or default build prompt before downloading about 8 GB of additional compressed object assets; the default seeded scene needs only the first-task assets. `--list-scenes` shows the two native compatibility scenes. Save the default benchmark task, split, kitchen scene, seed, and step budget in `config/benchmarks/robocasa.toml` or override them in `.env`; `./launch.sh` uses those defaults. See the [selection guide](docs/mujoco/benchmarks/Robocasa/README.md#list-and-select-a-task).

## Run RoboCasa

After `./build.sh` completes, run the benchmark from the repository root:

```sh
./launch.sh --robocasa --seed 42 --steps 20
```

If RoboCasa is still missing, `./launch.sh` also asks before downloading the pinned source, robosuite, and task assets. By default, they live under ignored `.local/`; set `ROBOCASA_ROOT` in [config.toml](config.toml) or `.env` to use another source checkout. The script installs a private Python 3.11 environment and prints a JSON result with the task, instruction, seed, action count, and success flag. It takes random bounded actions, so `success: false` is a valid smoke result. See the [first-run guide](docs/mujoco/usage/dev.md#run-the-first-robocasa-task) and [benchmark method](docs/mujoco/benchmarks/Robocasa/README.md).

In dev mode, RoboCasa shows its live camera frame during the episode and holds the final frame until a key is pressed in the image window. Run `./launch.sh --benchmark CloseFridge --no-gui` for terminal-only execution. Output is saved in `logs/dev/robocasa/latest.log`; each run also has a timestamped log. The optional robosuite model/IK/mimicgen messages and Gymnasium observation-space warnings come from the upstream environment and do not prevent this smoke run.

The GUI is 768 pixels wide by default. Set `[gui].width` in `config/benchmarks/robocasa.toml` or `BENCHMARK_GUI_WIDTH` in `.env`, or pass `--gui-width 960`, to enlarge it without changing benchmark observations. Use `--camera robot0_agentview_right` or `--camera robot0_eye_in_hand` to switch views. `--camera-width` and `--camera-height` change the actual rendered observation resolution; see the [camera configuration](docs/mujoco/benchmarks/Robocasa/README.md#camera-and-display-configuration).

## Use with IsOS and EOS

The local `island/mujoco-sim@0.1.2` candidate packages the C++ wrapper for an IsOS graph. Build a bundle, verify its manifest, link or install it in IsOS, then Validate, Apply, and Run the graph. EOS owns the simulator child and exposes ordinary device capabilities to agents. Follow the [managed backend guide](docs/mujoco/usage/isos-pkg.md) for the exact package and graph commands, readiness checks, logs, and stop procedure. The published `0.1.1` release used MuJoCo 3.16.0; these source instructions target 3.3.1.

The [documentation overview](docs/mujoco/README.md) links the interfaces, source ownership, benchmark provenance, design, and verification records. [GitHub repository](https://github.com/Island-Team/isos-mujoco-sim).
