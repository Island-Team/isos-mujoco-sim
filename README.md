# IsOS MuJoCo simulator

This package supplies native MuJoCo and RoboCasa hardware services. IsOS verifies and configures packages, applies graphs, and supervises selected services; EOS owns robot command admission, device health, and Stop proof. Benchmark truth remains evaluator-only.

[中文](README_cn.md) · [Documentation](docs/README.md) · [Detailed start guide](docs/start.md) · [Node groups](docs/node/README.md)

## Quick start

Linux native builds need MuJoCo **3.3.1**, a C++20 compiler, CMake 3.22+, protobuf, gRPC, and libjpeg. RoboCasa preparation also needs Python 3.11, Git, `wget`, and `uv`. See [start](docs/start.md) for full prerequisites, Windows RoboCasa operation, and configuration precedence.

```sh
cp .env.example .env
# Edit .env and set: export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
./launch.sh --benchmark CloseFridge --seed 42 --steps 20 --no-gui
```

The build prepares native targets and the local RoboCasa environment, asking before downloading missing assets. Bounded random actions can return `success: false` in a valid smoke run; this is not an agent policy score.

For a local native run, use `./launch.sh --scene pick-place --no-gui` and finish with `./kill.sh`. Task selection, cameras, recording/replay, managed deployment, and recovery are in the [detailed guide](docs/start.md). See [package](docs/package.md) for declarations and qualification rules, and [architecture](docs/architecture.md) for current data flow.
