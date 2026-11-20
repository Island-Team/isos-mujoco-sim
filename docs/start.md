# Build and run the simulator

[中文](../docs_cn/start_cn.md) · [Docs](README.md)

Start with a source build below, then select a local RoboCasa episode or native compatibility scene. For a managed deployment, follow [IsOS deployment](#managed-deployment). This guide owns operating procedures; exact node and service fields remain in their linked references.

<a id="first-run-from-source"></a>
## First run from source

This guide has two local workflows. `./launch.sh` runs the active upstream RoboCasa `CloseFridge` smoke episode in the foreground. `./build.sh` builds this repository's C++ MuJoCo core and IsOS/EOS package wrapper, then prepares RoboCasa after asking before any needed download; `./launch.sh --scene ...` starts that compatibility simulator in the background. The local RoboCasa smoke runner calls Gym directly; the packaged RoboCasa worker exposes the separate `robocasa_core.Hardware` API to EOS. Use the [managed backend guide](start.md) for the package path.

<a id="prerequisites"></a>
## Prerequisites

Run the shell commands from the repository root on Linux. RoboCasa's Python smoke runner also supports Windows PowerShell through `tools/robocasasetup.ps1` and `tools/robocasarun.ps1`; the C++ build and native launcher remain Linux workflows. The RoboCasa setup uses `git`, `uv`, Python 3.11, and a network connection for its source and asset downloads. It creates a private Python environment under `.local/robocasa-venv`. The initial download includes several large archives, so ensure the checkout has enough free disk space.

On Windows, install Python 3.11, Git for Windows, and `uv`, then run these commands from the repository root in PowerShell. The runner uses MuJoCo's GLFW backend and opens a GUI by default; `-NoGui` runs without the image window (a desktop/OpenGL-capable session is still needed for camera rendering). Set `$env:ROBOCASA_ROOT` to use a different source/assets directory. `-Full` fetches the larger asset collection needed by other tasks or fixed kitchen scenes.

```powershell
.\tools\robocasasetup.ps1
.\tools\robocasarun.ps1 -Task CloseFridge -Seed 42 -Steps 20
# Or run without the image window:
.\tools\robocasarun.ps1 -Task CloseFridge -Seed 42 -Steps 20 -NoGui
```

If PowerShell blocks local scripts, allow them for the current process only with `Set-ExecutionPolicy -Scope Process Bypass`.

The C++ build requires a MuJoCo **3.3.1** installation, a C++20 compiler, CMake 3.22 or newer, protobuf, gRPC, libjpeg, and Python 3 for build tooling. Set `MUJOCO_ROOT` to an absolute directory containing `include/mujoco/mujoco.h`, `lib/libmujoco.so.3.3.1`, `bin/compile`, and `bin/simulate`. RoboCasa's private Python environment installs its own MuJoCo 3.3.1 package; the native library path is for this repository's C++ build and wrapper.

<a id="configure-local-paths"></a>
## Configure local paths

The development [`config/dev.toml`](../config/dev.toml) holds repository-wide defaults and selects [`config/benchmarks/robocasa.toml`](../config/benchmarks/robocasa.toml) for benchmark settings. Copy the sample file to the ignored `.env` and set your local MuJoCo path. Each matching `.env` assignment overrides `config/dev.toml`. Keep machine-specific paths in `.env` so they do not enter the repository.

```sh
cp .env.example .env
# Edit .env and set your actual absolute path, for example:
# export MUJOCO_ROOT=/opt/mujoco-3.3.1
```

| Key | Default | Used by |
| --- | --- | --- |
| `MUJOCO_ROOT` | Empty; set it in `.env` | Development build and viewer |
| `DEV_GUI` | `true` | GUI default for development |
| `ROBOCASA_ROOT` | Empty, meaning `.local/robocasa` | RoboCasa source and extracted assets |
| `BENCHMARK_CONFIG` | `config/benchmarks/robocasa.toml` | Benchmark file selected by `config/dev.toml` |
| `BENCHMARK_TASK` | `CloseFridge` | Default registered RoboCasa task |
| `BENCHMARK_SPLIT` | `target` | Task set: `target`, `pretrain`, or `all` |
| `BENCHMARK_SCENE` | Empty; random scene in the split | Fixed kitchen `layout:style` pair |
| `BENCHMARK_SEED` | `42` | Reset and random action seed |
| `BENCHMARK_STEPS` | `20` | Maximum smoke actions |
| `BENCHMARK_CAMERA` | `robot0_agentview_left` | GUI camera view |
| `BENCHMARK_CAMERA_WIDTH`, `BENCHMARK_CAMERA_HEIGHT` | `1920` and `1080` | Rendered observation pixels |
| `BENCHMARK_GUI_WIDTH` | `1920` | GUI display width; preserves aspect ratio |
| `BENCHMARK_RECORD_ENABLED` | `false` | Enables `--record-demo` to write a local hardware record |
| `BENCHMARK_RECORD_PATH` | `.run/hardware-record.json` | Default local record file |
| `SIM_EXECUTABLE` | `build/eos-mujoco-sim` | `--scene` launcher |
| `SIM_SCENE` | `assets/scene.xml` | Native launcher default scene |
| `SIM_RUN_DIR` | `.run/mujoco` | Native sockets, log, and process record |
| `SIM_GUI` | `false` | Separate native scene viewer |
| `SIM_MANUAL_STEP` | `false` | Native simulator initial stepping |

Package deployment uses the separate [`config/package.toml`](../config/package.toml); its host paths and service selectors do not inherit this file or `.env`. Paths in the table other than `MUJOCO_ROOT` can be relative to the repository root. To place the RoboCasa checkout elsewhere, set `ROBOCASA_ROOT` in `config/dev.toml` or add `export ROBOCASA_ROOT=/absolute/path/to/robocasa` to `.env`. The Python environment and robosuite checkout still live under this repository's ignored `.local/` directory.

For a managed source package build, `MUJOCO_ROOT` in the environment takes precedence over `[host].mujoco_root`. When both are empty, the build uses an existing `.local/mujoco-3.3.1` in this checkout. This lets IsOS rebuild a clean source checkout without storing a machine-specific path in tracked configuration.

Package mode reuses the ignored `.local/package-build/` CMake tree. Run `python3 tests/archive.py` to verify archive determinism.

Run `python3 tests/config_modes.py` to check both configuration boundaries: package selector edits leave `./launch.sh --show-config` unchanged, while development settings and `.env` leave the package build's selected MuJoCo root unchanged.

The `BENCHMARK_*` rows come from `[task]`, `[camera]`, `[gui]`, and `[record]` in the selected benchmark TOML file. The root `BENCHMARK_CONFIG` path selects that file; edit it in `config/dev.toml` to use a different checked-in benchmark preset. `.env` assignments override the loaded benchmark values, and one-run flags override `.env`.

<a id="ubuntu-2204-builds"></a>
## Ubuntu 22.04 builds

The default native build is unchanged. Select the optional `ubuntu22` CMake preset on an Ubuntu 22.04 host with glibc 2.35 and Python 3.11 or newer. Only this profile checks the host baseline and validates the packaged ELF glibc requirements. Cross-compilation is rejected. Its development and package builds share an isolated `.local/package-build-ubuntu22` directory; default builds retain their original directories.

```sh
export MUJOCO_ROOT="$HOME/.local/opt/mujoco-3.3.1"
cmake --preset ubuntu22 -DPython3_EXECUTABLE="$(python3 -c 'import sys; print(sys.executable)')"
cmake --build --preset ubuntu22 --parallel 4
ctest --preset ubuntu22
MUJOCO_BUILD_PROFILE=ubuntu22 ./build.sh --output "$PWD/data/test/ubuntu22-package/profile-asset" --version 0.2.8
```

Use the actual MuJoCo path and an empty output directory; package only after tests pass. Version 0.2.8 remains a candidate. Publication follows the [package contract](package.md).

<a id="build-and-run-the-native-simulator"></a>
## Build and run the native simulator

After setting `MUJOCO_ROOT`, build all targets, prepare RoboCasa, and run the C++ tests:

```sh
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`./build.sh` writes native binaries to `build/`. It also checks the RoboCasa source, Python runtime, and assets. If any are missing, it asks before downloading; declining leaves the native binaries built but exits before full setup completes. `mujoco-core` loads and steps the engine directly for development; `eos-mujoco-sim` is the IsOS/EOS-facing wrapper. The tests exercise scene loading, replay, rendering, sockets, package generation, and stop behavior. A failed CMake MuJoCo check usually means `MUJOCO_ROOT` points to another version or a directory without the required headers, library, or tools.

To inspect the compatibility wrapper without IsOS, run:

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

The launcher starts `build/eos-mujoco-sim` in the background and reports its simulator and private benchmark socket paths. The default owner-only run directory is `.run/mujoco/`; read `logs/dev/native/latest.log` if startup fails. `./kill.sh` stops the process recorded by this launcher. Run `./launch.sh --list-scenes` to see the package-owned native scene IDs and XML paths. For another scene, use `--scene navigation` or an XML path. Set `SIM_SCENE` in configuration and run `./launch.sh --native` to use that default. `--gui` opens a separate static MuJoCo viewer and requires a display; it does not show the running simulator's live state. If you pass `--run-dir PATH` to `launch.sh`, pass the same path to `kill.sh`.

These native scenes are compatibility fixtures. For package construction, installation, graph validation, readiness, logging, and managed stop, continue with the [IsOS deployment](#managed-deployment). Use the exact selected package candidate; a managed hardware run does not turn the RoboCasa smoke episode into an EOS benchmark.

<a id="run-the-first-robocasa-task"></a>
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

Bare `./launch.sh` runs the configured task with its live camera GUI and holds the final frame until a key is pressed in the image window. Use `--no-gui` for a terminal-only run. If setup was not completed by `./build.sh`, the launcher checks for RoboCasa source, the Python runtime, and assets. It asks `Download and set up ...? [y/N]` before fetching anything; answer `y` to install at `ROBOCASA_ROOT` or the local default. A `N` answer exits without starting an episode. Subsequent runs reuse the downloaded source and assets. The setup can also be run explicitly with `./tools/robocasasetup.sh` after deciding to download; `python3 tools/robocasasource.py check --path .local/robocasa` checks an existing source tree without downloading.

The command prints RoboCasa startup messages followed by a JSON result such as:

```json
{"instruction":"Close the fridge doors.","scene":"8:8","seed":42,"split":"target","steps":20,"success":false,"task":"robocasa/CloseFridge"}
```

`--gui-exit-ms 300` closes the GUI 300 ms after the final frame instead of waiting for a key. `--record-actions PATH` stores the sampled action sequence; `--replay-actions PATH` reuses it for the same task, split, scene, and seed. Use the [full interface replay](development.md) to exercise three fixed kitchens with bounded GUI exit.

`success` comes from RoboCasa's fridge-door rule. The bundled runner samples bounded random actions and holds base motion at zero; `false` is a valid smoke result, not an installation failure. `--steps` sets the action budget and `--seed` controls the reset and sampled actions. The process exits after the episode, so `kill.sh` is not needed. The task, asset origin, license, and limits are in the [benchmark guide](core/benchmark.md).

<a id="list-and-select-a-task"></a>
## List and select a task

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
./launch.sh --list-scenes
./launch.sh --scene navigation --no-gui
```

The benchmark list comes from the pinned RoboCasa task registry. By default it shows the tasks that have a `target` dataset entry; use `--split pretrain` or `--split all` to see other sets. Each row includes the upstream episode horizon and a local asset status. `--list-kitchens` shows kitchen layout and style candidates; individual tasks may exclude a candidate. The target split uses paired scenes `1:1` through `10:10`; omit `--kitchen-scene` for RoboCasa's seeded scene choice. `CloseFridge` is the verified smoke task. Other registered tasks or a fixed kitchen scene need the full object collections. The launcher and default `./build.sh` ask before downloading about 8 GB compressed plus extraction when the configured selection needs them; a declined download leaves the first-task setup intact. Full asset setup can also be requested explicitly with `./tools/robocasasetup.sh --full`. This broader catalog is registered upstream but is not yet smoke verified task by task. The native scene list comes from the package-owned catalog and shows the two compatibility scene IDs.

Set `[task].name`, `split`, `scene`, `seed`, and `steps` in `config/benchmarks/robocasa.toml` to change shared defaults. Root `config/dev.toml` selects this file with `BENCHMARK_CONFIG`. The ignored `.env` can override each value with `export BENCHMARK_TASK=...` and similar assignments, including `export BENCHMARK_SCENE=1:1`. Command-line flags override both. Run `./launch.sh` for the configured benchmark or `./launch.sh --native` for the configured native `SIM_SCENE`. `--show-config` prints the effective selection. The JSON result records the actual kitchen `scene` as `layout:style`. The upstream horizon is task metadata; this runner's `--steps` is a shorter smoke budget and does not claim a full evaluation episode.

The checked-in [RoboCasa preset](../config/benchmarks/robocasa.toml) groups the task selection, camera observation, and GUI display settings. To use another checked-in preset, set `BENCHMARK_CONFIG` in `config/dev.toml` to its path. The loader rejects missing sections, missing fields, unknown fields, and wrong TOML types before starting a run.

<a id="camera-and-display-configuration"></a>
## Camera and display configuration

RoboCasa provides three RGB views: `robot0_agentview_left`, `robot0_agentview_right`, and `robot0_eye_in_hand`. `BENCHMARK_CAMERA` selects the view shown in the dev GUI; it does not remove the other camera observations. `BENCHMARK_CAMERA_WIDTH` and `BENCHMARK_CAMERA_HEIGHT` set the rendered observation size (64–2048 pixels each; checked-in default 1920×1080). Changing them affects image pixels and runtime, so record them with a benchmark result. `BENCHMARK_GUI_WIDTH` scales the displayed window only (256–3840 pixels; checked-in default 1920); it preserves the observation resolution and image aspect ratio. The result JSON records the camera and rendered dimensions.

Set `[camera]` and `[gui]` values in `config/benchmarks/robocasa.toml`, override them with the corresponding `BENCHMARK_*` variables in `.env`, or use one-run flags:

```sh
./launch.sh --benchmark CloseFridge --camera robot0_agentview_right --gui-width 960
./launch.sh --benchmark CloseFridge --camera-width 512 --camera-height 512 --gui-width 960
```

With the checked-in preset, the first command displays 1920×1080 observations in a 960-pixel-wide window. The second changes observation resolution to 512×512 and displays it at width 960; it renders fewer pixels than the preset. Use `--no-gui` to run without a window.

<a id="local-hardware-records"></a>
## Local hardware records

`[record].enabled` in `config/benchmarks/robocasa.toml` defaults to `false`; `[record].path` defaults to `.run/hardware-record.json`. After enabling, `./launch.sh --record-demo` writes a two-step PandaOmron hardware record to that path, and `./launch.sh --replay-record FILE` checks a selected record. These records exercise hardware control and contain no benchmark reward, success, task text, or images. The [record interface](core/robocasa.md) owns the format and replay limits.

<a id="current-028-hardware-candidate"></a>
## Current 0.2.8 hardware candidate

The current source is unpublished candidate `0.2.8`, using schema `0.2.1`, `isos_node_v2`, seven hardware types, and two IsOS-supervised services. Exact declarations and publication gates are in [package](package.md).

<a id="managed-deployment"></a>
## IsOS deployment

Build and test before staging an unpublished candidate. Use the exact version in the manifest and every graph package pin; a source candidate is not a published release.

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh --output /absolute/empty/candidate-directory --version 0.2.8
isos pkg verify /absolute/empty/candidate-directory/release.json /absolute/empty/candidate-directory/mujoco-sim-v0.2.8-linux-x86_64.tar.gz
isos pkg install --source /absolute/path/to/isos-mujoco-sim --version 0.2.8 --allow-source-build
isos pkg configure island/mujoco-sim@0.2.8 --service native
# For the other service:
isos pkg configure island/mujoco-sim@0.2.8 --service robocasa
```

Use the archive basename actually declared in `release.json`. The native service needs the selected MuJoCo installation; RoboCasa needs its configured Python interpreter and assets. Review and save package configuration before Apply. Interactive RoboCasa configuration offers setup when paths are absent; declining leaves manual configuration available.

Select the package's Native robot or RoboCasa robot node set in IsOS. Bind actuator command inputs through an EOS parts Dispatcher and supply the selected camera sizes. Validate the graph, Apply its revision, then Run. Installation and Apply do not start a deployment. IsOS starts only selected services and passes their endpoints to EOS; EOS checks device health before making ports ready. See [package declarations](package.md) and [node groups](node/README.md).

Find the current run and its first ready or failure event before debugging. IsOS captures service stdout/stderr as `package_service_output`; correlate these records with EOS using the run ID and service instance. A running process or existing socket does not prove device readiness. Fix missing host paths, incompatible package bytes, or unavailable rendering before retrying admission.

Request deployment Stop through IsOS. EOS closes movement admission and checks whole-robot service proof before IsOS terminates its service children. Missing proof or a lost reply remains unknown; process exit alone is not a confirmed safe stop. Do not retry an uncertain released command automatically. Repair the failed service and obtain fresh admission before movement. Local `./kill.sh` controls the developer launcher, not managed deployments.

For upgrades, select and verify a new exact package pin, review node port and configuration changes, Validate and Apply again, then start the new run. If rebuilding the same unpublished candidate, Apply again to bind the new verified library digest. Preserve unresolved command and Stop results during recovery. Release qualification commands are in [development](development.md); historical candidates and migrations are in [changelog](changelog.md).

<a id="development-gui-and-local-logs"></a>
## Development GUI and local logs

Run `./launch.sh --benchmark CloseFridge --steps 20` to see live RoboCasa camera frames; after the episode, press any key in the image window to close it. Pass `--no-gui` for a terminal-only run. `./launch.sh --scene navigation` opens a separate static MuJoCo XML viewer by default; `./kill.sh` stops the native process and viewer. The static viewer does not show live socket-simulator state.

Each local run has a timestamped log in Git-ignored `logs/dev/`. `logs/dev/robocasa/latest.log` and `logs/dev/native/latest.log` point to the most recent runs; the native viewer uses a matching `*-viewer.log`. The launcher checks for an active socket before clearing a stale one.

<a id="troubleshooting"></a>
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

The benchmark runs in the foreground and writes its result to the terminal and `logs/dev/robocasa/latest.log`. Native output is under `logs/dev/native/latest.log`; timestamped files preserve earlier runs. The viewer has a corresponding `*-viewer.log`. Local logs are ignored by Git. For a managed deployment, find the current IsOS run and its first ready or failure event before changing the graph; see [build and run](start.md).
