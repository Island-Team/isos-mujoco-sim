# IsOS package wrapper

`eos-mujoco-sim` is the package entrypoint. `main.cpp` validates launch arguments; `adapter.cpp` serves the managed EOS v2 socket and strict stop lane; `service.cpp` serves direct-launch legacy gRPC and private benchmark endpoints. The wrapper calls `mujoco_core` through `engine.h`. IsOS manages the package and EOS owns the child process and its simulator contract; this directory does not expose benchmark ground truth through EOS.

The [backend guide](../../docs/mujoco/usage/isos-pkg.md) describes installation and managed readiness. The [socket contract](../../docs/mujoco/interfaces/socket.md) defines the wire behavior. Direct development launch through this binary remains available with `--socket`, `--benchmark-socket`, and `--scene`.
