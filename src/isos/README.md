# IsOS package wrapper

`eos-mujoco-sim` is the native package entrypoint. `main.cpp` validates launch arguments; `adapter.cpp` serves the managed v2 socket and strict stop lane; `service.cpp` serves direct-launch legacy gRPC and private benchmark endpoints. The wrapper calls `mujoco_core` through `engine.h`. The v0.2.1 package declares this as an IsOS-owned runtime service, activated when its hardware nodes appear in the applied graph. Older v0.2.0 graphs retain the EOS-owned process node. Benchmark ground truth is never exposed through EOS hardware.

The [backend guide](../../docs/mujoco/usage/isos-pkg.md) describes installation and managed readiness. The [socket contract](../../docs/mujoco/interfaces/socket.md) defines the wire behavior. Direct development launch through this binary remains available with `--socket`, `--benchmark-socket`, and `--scene`.
