# IsOS MuJoCo simulator

A MuJoCo simulator package for IsOS and EOS, with a local RoboCasa benchmark workflow.

[中文](README_cn.md) · [Start here](docs/mujoco/start/README.md) · [Interfaces](docs/mujoco/interfaces/README.md) · [Design](docs/mujoco/core/README.md)

| Path | What it runs | Current scope |
| --- | --- | --- |
| RoboCasa | Upstream `CloseFridge` in a private Python environment | Local smoke episode and replayable PandaOmron hardware records |
| Native simulator | C++ MuJoCo scene engine and IsOS package wrapper | `pick-place` and `navigation` compatibility scenes; EOS-facing devices and private benchmark RPC |

EOS owns robot-facing admission and its simulator child. Benchmark scoring stays on the trusted evaluator path and is not exposed to EOS or agents. The RoboCasa smoke runner is separate from EOS agent evaluation.

## Quick start

On Linux, install MuJoCo **3.3.1**, a C++20 compiler, CMake 3.22+, protobuf, gRPC, libjpeg, Python 3.11, `git`, `wget`, and `uv`. Set `MUJOCO_ROOT` to an installation containing `include/mujoco/mujoco.h`, `lib/libmujoco.so.3.3.1`, `bin/compile`, and `bin/simulate`.

```sh
cp .env.example .env
# Edit .env and set: export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
./launch.sh --benchmark CloseFridge --seed 42 --steps 20 --no-gui
```

The default `SIM_PROFILE=isos-pkg` builds the native targets. Set `export SIM_PROFILE=dev` in `.env` when you want `./build.sh` to prepare the local RoboCasa source, assets, and Python environment. Setup asks before downloading missing assets. The benchmark emits JSON with task, scene, camera, seed, action count, instruction, and success. Its bounded random actions make `success: false` a valid smoke result. See the [first-run guide](docs/mujoco/start/dev.md) for dependencies, configuration, GUI behavior, and troubleshooting.

## Select and inspect

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --list-scenes
./launch.sh --scene pick-place --no-gui
./kill.sh
```

`config.toml` selects the benchmark config at `config/benchmarks/robocasa.toml`; `.env` overrides matching values and command flags override both. The native wrapper starts in the background and prints its owner-only sockets and log path. `./kill.sh` stops the process recorded by the launcher. See the [task selection guide](docs/mujoco/core/benchmark.md) and [native runtime guide](docs/mujoco/start/dev.md).

## Record hardware control

Set `[record].enabled = true` and `[record].path` in `config/benchmarks/robocasa.toml`, or export `BENCHMARK_RECORD_ENABLED=true` and `BENCHMARK_RECORD_PATH` in `.env`. Recording is off by default. The hardware demo writes a versioned local JSON record; replay checks robot state after each step. It does not record benchmark reward, success, or images.

```sh
./launch.sh --record-demo
./launch.sh --replay-record .run/hardware-record.json
```

The selected path is relative to this repository unless absolute. `--record-demo FILE` overrides the configured path for one run. See the [record contract](docs/mujoco/interfaces/record.md) for format and limits.

## Package with IsOS

Build a package asset with `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY`, then verify and install the exact release in IsOS. EOS loads the package adapter and manages the simulator child; IsOS owns package verification and graph admission. The [package guide](docs/mujoco/start/isos-pkg.md) contains the commands and stop procedure. The [documentation overview](docs/mujoco/README.md) maps source ownership, interfaces, design, provenance, and verification.

[GitHub repository](https://github.com/Island-Team/isos-mujoco-sim)
