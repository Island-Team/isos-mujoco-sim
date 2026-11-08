# RoboCasa benchmark

[Package overview](../../README.md) · [Usage](../../usage/README.md) · [中文](../../../../docs_cn/mujoco/benchmarks/Robocasa/README_cn.md)

The active benchmark is the upstream RoboCasa365 `CloseFridge` atomic task. The first local episode uses the official `robocasa/CloseFridge` Gym environment, target split, seed 42, and RoboCasa's own success check: the selected fridge door must be closed. The script in `tools/robocasahrun.py` takes 20 bounded random actions with base motion held at zero as a smoke baseline. Its result demonstrates environment launch and scoring, not a trained policy or a comparable leaderboard score. RoboCasa recommends 20 episodes per task for evaluation; retain seeds, assets, policy revision, and horizon when reporting a benchmark result.

`./launch.sh` runs this episode by default. It checks `ROBOCASA_ROOT` from root `config.toml` and then `.env`; an empty value resolves to ignored `.local/robocasa`. If source, runtime, or assets are missing, it asks before setup. `./launch.sh --robocasa --seed 42 --steps 20` makes the task and budget explicit. The setup helper pins RoboCasa source and robosuite revisions, installs a private Python 3.11 runtime, and downloads textures and general fixtures from the pinned official RoboCasa asset dataset plus the Lightwheel fixture and object archives from checksum-verified community mirrors. These files remain ignored under `.local/`. The Python runtime pins MuJoCo 3.3.1; the C++ build also targets 3.3.1.

RoboCasa source is [MIT licensed](https://github.com/robocasa/robocasa/blob/main/LICENSE); its [README](https://github.com/robocasa/robocasa#license) identifies assets and datasets as CC BY 4.0. The task implementation and success rule are in upstream `robocasa/environments/kitchen/atomic/kitchen_doors.py`. The [RoboCasa365 paper](https://robocasa.ai/assets/robocasa365_iclr26.pdf) describes the benchmark. Keep the downloaded asset attribution with any redistributed results or assets.

The former package-authored pick-and-place and navigation tasks are legacy simulator fixtures for compatibility tests and are not active benchmarks. Their private C++ benchmark RPC remains outside EOS and EGIA. RoboCasa runs in the upstream environment; the [Python robot hardware core](../../interfaces/robocasa-hardware.md) controls and observes its PandaOmron robot in process, and [local records](../../interfaces/robocasa-record.md) replay hardware commands for control testing. EOS agent control still requires a governed adapter before it can be claimed as an end-to-end EOS evaluation.

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

Set `[task].name`, `split`, `scene`, `seed`, and `steps` in `config/benchmarks/robocasa.toml` to change shared defaults. Root `config.toml` selects this file with `BENCHMARK_CONFIG`. The ignored `.env` can override each value with `export BENCHMARK_TASK=...` and similar assignments, including `export BENCHMARK_SCENE=1:1`. Command-line flags override both. Run `./launch.sh` for the configured benchmark or `./launch.sh --native` for the configured native `SIM_SCENE`. `--show-config` prints the effective selection. The JSON result records the actual kitchen `scene` as `layout:style`. The upstream horizon is task metadata; this runner's `--steps` is a shorter smoke budget and does not claim a full evaluation episode.

The checked-in [RoboCasa preset](../../../../config/benchmarks/robocasa.toml) groups the task selection, camera observation, and GUI display settings. To use another checked-in preset, set `BENCHMARK_CONFIG` in root `config.toml` to its path. The loader rejects missing sections, missing fields, unknown fields, and wrong TOML types before starting a run.

## Camera and display configuration

RoboCasa provides three RGB views: `robot0_agentview_left`, `robot0_agentview_right`, and `robot0_eye_in_hand`. `BENCHMARK_CAMERA` selects the view shown in the dev GUI; it does not remove the other camera observations. `BENCHMARK_CAMERA_WIDTH` and `BENCHMARK_CAMERA_HEIGHT` set the rendered observation size (64–2048 pixels each; default 256×256). Changing them affects image pixels and runtime, so record them with a benchmark result. `BENCHMARK_GUI_WIDTH` scales the displayed window only (256–3840 pixels; default 768); it preserves the observation resolution and image aspect ratio. The result JSON records the camera and rendered dimensions.

Set `[camera]` and `[gui]` values in `config/benchmarks/robocasa.toml`, override them with the corresponding `BENCHMARK_*` variables in `.env`, or use one-run flags:

```sh
./launch.sh --benchmark CloseFridge --camera robot0_agentview_right --gui-width 960
./launch.sh --benchmark CloseFridge --camera-width 512 --camera-height 512 --gui-width 960
```

The first command enlarges the window while retaining 256×256 benchmark observations. The second renders 512×512 observations and uses more GPU time and memory. Use `--no-gui` to run without a window.

## Local verification

On 2026-11-08, `./launch.sh --robocasa --seed 42 --steps 20` completed twice with the same task instruction, 20 steps, and `success: false`. This confirms the upstream task loads and its success rule is queried; it does not establish an agent policy score. The C++ MuJoCo 3.3.1 build passed 27/27 CTest cases.
