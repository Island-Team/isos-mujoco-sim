# EOS torso node

[Interface index](../../../README.md) · [Design](../../../../design/eos/hardware/torso.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/torso_cn.md)

`eos.hardware.torso.normalized_axes@v0.2` exists in the **RoboCasa robot** preset as `robocasa/lift`, bound to `robocasa/torso/torso`. The native robot preset has no torso node. This node commands the PandaOmron torso lift through a normalized controller input; it does not publish a measured torso position.

## Port and command

The optional in-process event input is `command: normalized_axes_command@v0.2`. Its `payload.axes` object has exactly one finite number, `lift`, in `[-1,1]`. This is a dimensionless controller input, not metres or m/s. An accepted command advances one Gym step. The preset advertises `max_velocity_lease_ms:1000` for admission. There is no `state` or other observation output, and the worker does not fabricate one.

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "lift-18",
  "port": "command",
  "payload": {
    "axes": {
      "lift": 0.25
    }
  }
}
```

EOS supplies the run/revision fence and command ID; the adapter emits a `command_result` acknowledgment. An agent can request torso movement only through EOS's admitted capability. It cannot read torso position from this node. Other RoboCasa nodes can still provide their own observations.

## Admission, Stop, and failure

`service_instance:"robocasa"` and `device_id:"robocasa/torso/torso"` bind the exact service and device. IsOS verifies the package and service configuration; EOS checks health and Dispatcher admission. Invalid axes, a stale run, unavailable service, or failed Gym step rejects control. The worker deduplicates command IDs within one generation and faults after a failed step. Stop fences later commands and requires `torso_stop:"stopped"` as part of the whole-robot proof; missing proof is unknown. See [runtime control](../../../control.md) for the private service contract.
