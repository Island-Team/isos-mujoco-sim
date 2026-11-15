# EOS gripper node

[Interface index](../../../README.md) · [Design](../../../../design/eos/hardware/gripper.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/gripper_cn.md)

`eos.hardware.gripper.binary@v0.2` opens or closes one simulated gripper. Both presets expose the same binary command type, but their observations describe different physical quantities.

| Preset / node ref | Device ID | Command | State |
| --- | --- | --- | --- |
| `native/gripper` | `gripper-0` | Open or close the native scene gripper | `opening` channel, 0–100% |
| `robocasa/hand` | `robocasa/gripper/right-gripper` | Open or close the Panda gripper | `left_finger` and `right_finger` slide-joint channels, m |

## Ports and values

The input is `command: gripper_binary_command@v0.2`; `payload.close` is a required boolean. `false` opens and `true` closes. The output is `state: gripper_state@v0.2`; its `channels` array gives each channel's `name`, numeric `value`, and `unit`. Native state uses `sample.clock:"simulation"`. RoboCasa state uses `sample.clock:"monotonic"` and reports the two joint positions from the pinned Gym wrapper. The preset advertises a maximum 50 Hz observation rate and 65,536-byte payload. The state does not claim grasp success or identify held objects.

An admitted command sent by EOS to the adapter is:

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "grip-18",
  "stop_epoch": "0",
  "port": "command",
  "payload": {
    "close": true
  }
}
```

For a native node, `stop_epoch` is the current token proved by health or a prior Stop. EOS supplies the run fence and command ID; agents do not call the private service. The adapter emits a service acknowledgment on `command_result` and requested observations on `state`.

## Admission, Stop, and failure

The verified `service_instance` and exact `device_id` select the gripper; neither has a fallback. EOS admits the action through its Dispatcher. Native control checks generation and stop epoch; both services deduplicate a command ID within one generation. A nonboolean `close`, wrong device, stale run, or failed step rejects the action. On Stop, EOS requires a separate `gripper_stop:"stopped"` result alongside base and arm proof; RoboCasa also requires torso proof. A missing gripper proof remains unknown. This node cannot infer physical grasp from a command acknowledgment. See [runtime control](../../../control.md) for wire errors and deadlines.
