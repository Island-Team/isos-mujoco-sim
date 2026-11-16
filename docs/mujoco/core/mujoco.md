# MuJoCo core design

[Design index](../README.md) · [Runtime control](../interfaces/control.md) · [Package contract](../interfaces/package.md)

The simulator core owns scene loading, deterministic reset, physics, rendering, and private benchmark scoring. IsOS verifies and configures an exact package service; EOS manages robot-side admission, health, and Stop. Native and RoboCasa services supply device data through private endpoints without exposing benchmark ground truth.
