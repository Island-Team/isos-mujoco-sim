# First run from source

[MuJoCo documentation](../README.md) · [Build and run](README.md) · [RoboCasa benchmark](../benchmarks/Robocasa/README.md) · [中文](../../../docs_cn/mujoco/usage/dev_cn.md)

This guide has two local workflows. `./launch.sh` runs the active upstream RoboCasa `CloseFridge` smoke episode in the foreground. `./build.sh` builds this repository's C++ MuJoCo core and IsOS/EOS package wrapper, then prepares RoboCasa after asking before any needed download; `./launch.sh --scene ...` starts that compatibility simulator in the background. The RoboCasa environment does not yet connect to EOS. Use the [managed backend guide](isos-pkg.md) to install the C++ wrapper in IsOS.

## Prerequisites

Run the commands from the repository root on Linux. The RoboCasa setup uses `git`, `wget`, `uv`, Python 3.11, and a network connection for its source and asset downloads. It creates a private Python environment under `.local/robocasa-venv`. The initial download includes several large archives, so ensure the checkout has enough free disk space.

The C++ build requires a MuJoCo **3.3.1** installation, a C++20 compiler, CMake 3.22 or newer, protobuf, gRPC, libjpeg, and Python 3 for build tooling. Set `MUJOCO_ROOT` to an absolute directory containing `include/mujoco/mujoco.h`, `lib/libmujoco.so.3.3.1`, `bin/compile`, and `bin/simulate`. RoboCasa's private Python environment installs its own MuJoCo 3.3.1 package; the native library path is for this repository's C++ build and wrapper.

## Configure local paths

The root [`config.toml`](../../../config.toml) holds repository-wide defaults and selects [`config/benchmarks/robocasa.toml`](../../../config/benchmarks/robocasa.toml) for benchmark settings. Copy the sample file to the ignored `.env` and set your local MuJoCo path. Each matching `.env` assignment overrides `config.toml`. Keep machine-specific paths in `.env` so they do not enter the repository.

```sh
cp .env.example .env
# Edit .env and set your actual absolute path, for example:
# export MUJOCO_ROOT=/opt/mujoco-3.3.1
```

| Key | Default | Used by |
| --- | --- | --- |
| `MUJOCO_ROOT` | Empty; set it in `.env` | Native build, viewer, and IsOS package |
| `SIM_PROFILE` | `isos-pkg`; set `dev` locally | Build and launch profile |
| `DEV_GUI` | `true` | GUI default in dev mode |
| `ROBOCASA_ROOT` | Empty, meaning `.local/robocasa` | RoboCasa source and extracted assets |
| `BENCHMARK_CONFIG` | `config/benchmarks/robocasa.toml` | Benchmark file selected by root `config.toml` |
| `BENCHMARK_TASK` | `CloseFridge` | Default registered RoboCasa task |
| `BENCHMARK_SPLIT` | `target` | Task set: `target`, `pretrain`, or `all` |
| `BENCHMARK_SCENE` | Empty; random scene in the split | Fixed kitchen `layout:style` pair |
| `BENCHMARK_SEED` | `42` | Reset and random action seed |
| `BENCHMARK_STEPS` | `20` | Maximum smoke actions |
| `BENCHMARK_CAMERA` | `robot0_agentview_left` | GUI camera view |
| `BENCHMARK_CAMERA_WIDTH`, `BENCHMARK_CAMERA_HEIGHT` | `256` each | Rendered observation pixels |
| `BENCHMARK_GUI_WIDTH` | `768` | GUI display width; preserves aspect ratio |
| `SIM_EXECUTABLE` | `build/eos-mujoco-sim` | `--scene` launcher |
| `SIM_SCENE` | `assets/scene.xml` | Native launcher default scene |
| `SIM_RUN_DIR` | `.run/mujoco` | Native sockets, log, and process record |
| `SIM_GUI` | `false` | Separate native scene viewer |
| `SIM_MANUAL_STEP` | `false` | Native simulator initial stepping |

Paths in the table other than `MUJOCO_ROOT` can be relative to the repository root. To place the RoboCasa checkout elsewhere, set `ROBOCASA_ROOT` in `config.toml` or add `export ROBOCASA_ROOT=/absolute/path/to/robocasa` to `.env`. The Python environment and robosuite checkout still live under this repository's ignored `.local/` directory.

The `BENCHMARK_*` rows come from `[task]`, `[camera]`, and `[gui]` in the selected benchmark TOML file. The root `BENCHMARK_CONFIG` path selects that file; edit it in `config.toml` to use a different checked-in benchmark preset. `.env` assignments override the loaded benchmark values, and one-run flags override `.env`.

## Build and run the native simulator

After setting `MUJOCO_ROOT`, build all targets, prepare RoboCasa, and run the C++ tests:

```sh
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`./build.sh` writes native binaries to `build/`. With `SIM_PROFILE=dev`, it also checks the RoboCasa source, Python runtime, and assets. If any are missing, it asks before downloading; declining leaves the native binaries built but exits before full setup completes. `mujoco-core` loads and steps the engine directly for development; `eos-mujoco-sim` is the IsOS/EOS-facing wrapper. The tests exercise scene loading, replay, rendering, sockets, package generation, and stop behavior. A failed CMake MuJoCo check usually means `MUJOCO_ROOT` points to another version or a directory without the required headers, library, or tools.

To inspect the compatibility wrapper without IsOS, run:

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

The launcher starts `build/eos-mujoco-sim` in the background and reports its simulator and private benchmark socket paths. The default owner-only run directory is `.run/mujoco/`; read `logs/dev/native/latest.log` if startup fails. `./kill.sh` stops the process recorded by this launcher. Run `./launch.sh --list-scenes` to see the package-owned native scene IDs and XML paths. For another scene, use `--scene navigation` or an XML path. Set `SIM_SCENE` in configuration and run `./launch.sh --native` to use that default. `--gui` opens a separate static MuJoCo viewer and requires a display; it does not show the running simulator's live state. If you pass `--run-dir PATH` to `launch.sh`, pass the same path to `kill.sh`.

These native scenes are compatibility fixtures. For package construction, installation, graph validation, readiness, logging, and managed stop, continue with the [IsOS/EOS backend guide](isos-pkg.md). That path uses the exact `island/mujoco-sim@0.1.2` local candidate and does not turn the RoboCasa smoke episode into an EOS benchmark.

## Run the first RoboCasa task

List and select a registered task, or inspect the effective defaults first:

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
```

The task list shows type, upstream horizon, and whether this repository has verified its local smoke run. `--list-kitchens` shows the kitchen layout and style candidates for the selected split; a task can exclude individual candidates; the target split uses paired scenes `1:1` through `10:10`. Omit `--kitchen-scene` to let RoboCasa choose a scene from the split. `--list-benchmarks --split all` lists all registered RoboCasa tasks; `--filter TEXT` narrows the output without changing configuration. The bundled asset set verifies `CloseFridge` with RoboCasa's seeded scene choice. Selecting another task or a fixed kitchen scene prompts before downloading the full object collections (about 8 GB compressed, plus extraction). Declining leaves the first-task assets available. After full setup, a fixed target scene can be selected with `./launch.sh --benchmark CloseFridge --kitchen-scene 1:1 --steps 20`. Set the `[task]` values in `config/benchmarks/robocasa.toml` for shared defaults or in `.env` for local overrides. One-run flags take precedence over both files.

```sh
./launch.sh --robocasa --seed 42 --steps 20
```

With `SIM_PROFILE=dev`, bare `./launch.sh` runs the configured task with its live camera GUI and holds the final frame until a key is pressed in the image window. Use `--no-gui` for a terminal-only run. In `isos-pkg`, specify `--benchmark` to run RoboCasa explicitly. If setup was not completed by `./build.sh`, the launcher checks for RoboCasa source, the Python runtime, and assets. It asks `Download and set up ...? [y/N]` before fetching anything; answer `y` to install at `ROBOCASA_ROOT` or the local default. A `N` answer exits without starting an episode. Subsequent runs reuse the downloaded source and assets. The setup can also be run explicitly with `./tools/robocasasetup.sh` after deciding to download; `python3 tools/robocasasource.py check --path .local/robocasa` checks an existing source tree without downloading.

The command prints RoboCasa startup messages followed by a JSON result such as:

```json
{"instruction":"Close the fridge doors.","scene":"8:8","seed":42,"split":"target","steps":20,"success":false,"task":"robocasa/CloseFridge"}
```

`success` comes from RoboCasa's fridge-door rule. The bundled runner samples bounded random actions and holds base motion at zero; `false` is a valid smoke result, not an installation failure. `--steps` sets the action budget and `--seed` controls the reset and sampled actions. The process exits after the episode, so `kill.sh` is not needed. The task, asset origin, license, and limits are in the [benchmark guide](../benchmarks/Robocasa/README.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `Set MUJOCO_ROOT` or missing `libmujoco.so.3.3.1` | Set the absolute MuJoCo 3.3.1 root in `.env`, then rerun `./build.sh`. |
| RoboCasa setup prompt appears | Confirm `ROBOCASA_ROOT`; answer `y` only if you want the missing source, runtime, or assets downloaded. |
| Download interrupted | Rerun `./tools/robocasasetup.sh`; it reuses valid archives and resumes incomplete downloads. |
| RoboCasa exits with a Python traceback | Read the first error above the traceback; confirm the source and asset directories, then rerun setup. |
| `--scene` reports a missing executable | Run `./build.sh` and confirm `build/eos-mujoco-sim` exists. |
| Native socket or startup failure | Read `logs/dev/native/latest.log`; use `./kill.sh` for a process started by this launcher. |
| `--gui` fails on a headless host | Run with `--no-gui`; the benchmark and C++ tests do not require a desktop window. |

The benchmark runs in the foreground and writes its result to the terminal and `logs/dev/robocasa/latest.log`. Native output is under `logs/dev/native/latest.log`; timestamped files preserve earlier runs. The viewer has a corresponding `*-viewer.log`. Local logs are ignored by Git. For a managed deployment, find the current IsOS run and its first ready or failure event before changing the graph; see [build and run](README.md#isos-and-eos-deployment).

## Development GUI and local logs

Set `export SIM_PROFILE=dev` in this machine’s ignored `.env`. Run `./launch.sh --benchmark CloseFridge --steps 20` to see live RoboCasa camera frames; after the episode, press any key in the image window to close it. Pass `--no-gui` for a terminal-only run. `./launch.sh --scene navigation` opens a separate static MuJoCo XML viewer by default; `./kill.sh` stops the native process and viewer. The static viewer does not show live socket-simulator state.

Each local run has a timestamped log in Git-ignored `logs/dev/`. `logs/dev/robocasa/latest.log` and `logs/dev/native/latest.log` point to the most recent runs; the native viewer uses a matching `*-viewer.log`. The launcher checks for an active socket before clearing a stale one.
