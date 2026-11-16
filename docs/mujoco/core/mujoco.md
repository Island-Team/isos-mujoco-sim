# MuJoCo core design

[Design index](../README.md) · [Runtime control](../interfaces/control.md) · [Package contract](../interfaces/package.md)

The simulator core owns scene loading, deterministic reset, physics, rendering, and private benchmark scoring. IsOS verifies and configures an exact package service; EOS manages robot-side admission, health, and Stop. Native and RoboCasa services supply device data through private endpoints without exposing benchmark ground truth.

The native developer launcher and the IsOS package both execute `eos-mujoco-sim`. Its direct sockets and managed strict socket share one `SimEngine` instance from `src/mujoco/engine.h`; the separate `mujoco-core` developer executable also links the same `mujoco_core` library. Socket admission and lifecycle differ, while scene loading, reset, stepping, commands, snapshots, camera rendering, and private scoring remain in that core. RoboCasa uses upstream Gym and `robocasa_core.Hardware` in an isolated Python service; it does not call the native C++ `SimEngine` API.

On 2026-11-16, `ctest --test-dir build -R '^(core-launch|launcher-lifecycle|strict-socket|strict-socket-navigation)$' --output-on-failure` passed 4/4 tests, covering the direct core executable, developer launcher, and both managed native scenes. Complete output is under ignored `data/test/20261116-core-api-parity/ctest.log`.
