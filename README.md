# EOS MuJoCo benchmark simulator

The 0.x integration design starts at [first use](docs/mujoco/usage.md), then [package contract](docs/mujoco/interfaces/package.md), [socket contract](docs/mujoco/interfaces/socket.md), [algorithms](docs/mujoco/design.md), and [TODO](docs/mujoco/todo.md). Target behavior is distinguished from the current simulator.

[中文](README_cn.md)

[GitHub repository](https://github.com/Island-Team/isos-mujoco-sim)

This independent C++ package runs robotic benchmark scenes in MuJoCo. EOS connects to its simulator socket and exposes normal robot discovery, observations, and primitives to agents such as EGIA. A trusted evaluator alone connects to the separate benchmark socket for seeded resets, manual stepping, ground truth, and scores.

The catalog starts with [pick and place](assets/scene.xml) and [navigation](assets/scenes/navigation/scene.xml). Select one scene at process startup with `--scene` for direct runs or in the IsOS v2 graph for managed runs. Read the [documentation map](docs/mujoco/doc_index.md) for setup, benchmark methods, interfaces, model provenance, and the path for adding a scene.

For the IsOS/EOS 2.0.0 graph and framed socket path, use the
[v2 backend guide](docs/mujoco/backend.md). It stages a local backend
bundle with `tools/build-backend-bundle.py`. Set `MUJOCO_GUI=1` in the IsOS
backend node environment to view the running simulator's live state.

## Quick start

For the current IsOS/EOS deployment, build and link a local `island/mujoco-sim@0.1.1` bundle, preview its `sim-hardware` node set, and apply the resulting shared graph. IsOS verifies the package and scene; EOS starts the simulator as its direct child. See the [v2 backend guide](docs/mujoco/backend.md) and [package usage](docs/mujoco/usage.md). MuJoCo 3.16.0 remains an operator-provided dependency through `MUJOCO_ROOT`. The published v1.0.1 release is a separate legacy package; see [release history](docs/mujoco/package-release.md).

The following source build is useful for development and direct runs.

Requires C++20, CMake 3.22+, MuJoCo 3.16.0, protobuf, gRPC, and libjpeg. Copy [.env.example](.env.example) to the ignored `.env`, set `MUJOCO_ROOT` to your actual MuJoCo installation directory, then source it before building. The directory must contain `include/mujoco/mujoco.h`, `lib/libmujoco.so`, `bin/compile`, and `bin/simulate`.

```sh
. ./.env
: "${MUJOCO_ROOT:?Set MUJOCO_ROOT to your installed MuJoCo 3.16.0 directory}"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
```

For a standalone background run, `launch.sh` uses the configured scene and creates owner-only sockets under `.run/mujoco/`. It loads the local `.env` automatically; `kill.sh` stops only processes started by this launcher. Copy [launch.conf.example](launch.conf.example) to the ignored `launch.conf` to change defaults.

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

Use `--scene navigation` for the navigation task or `--gui` to open a separate MuJoCo viewer of the selected XML. The viewer does not display the running simulator's live state. For a direct run, pass absolute paths; the second socket is private to the evaluator.

```sh
build/eos-mujoco-sim \
  --socket /tmp/eos-simulator.sock \
  --benchmark-socket /tmp/eos-benchmark.sock \
  --scene "$PWD/assets/scene.xml"
```

Use `tools/scene-view.sh --scene "$PWD/assets/scene.xml"` for an interactive MuJoCo preview, or add `--check` for a headless model-loading check. `build/benchmark-eval` runs a timed private episode while the agent acts through EOS. See [usage](docs/mujoco/usage.md) for EOS launch, the navigation scene, and evaluator flags.

## License

Original package code and documentation are [Apache-2.0](LICENSE). Imported Menagerie models retain their [UR5e](assets/menagerie/universal_robots_ur5e/LICENSE) and [Robotiq 2F-85](assets/menagerie/robotiq_2f85/LICENSE) licenses. Keep the [model provenance](assets/MODELS.md) and source licenses with redistributed assets. MuJoCo is installed separately.
