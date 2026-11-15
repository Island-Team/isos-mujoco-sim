# EOS hardware design: base

[Node interface](../../../interfaces/node/eos/hardware/base.md) · [Core design](../../core/mujoco.md)

IsOS verifies the package and service configuration. EOS publishes ports only after the service is healthy and the selected device matches. Actuator commands pass Dispatcher admission; Stop closes admission and checks the service proof. Missing proof remains an unknown outcome.
