# EOS base nodes

[Interface index](../../../README.md) · [Design](../../../../design/eos/hardware/base.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/base_cn.md)

A base node represents one simulated mobile base. The **Native robot** preset offers velocity control and a planar state; the **RoboCasa robot** preset offers normalized controller axes and a world-frame pose. An operator selects the preset and service configuration in IsOS; an agent sees only the capabilities EOS publishes after health and Dispatcher admission.

| Preset / node ref | Type and bound device | What it can do | What it reports |
| --- | --- | --- | --- |
| `native/drive` | `eos.hardware.base.device@v0.2` → `base-0` | `body_velocity`: bounded planar velocity with a lease | `base_state@v0.2`: x/y in m, yaw in rad, x/y velocity in m/s, yaw rate in rad/s |
| `robocasa/mobile` | `eos.hardware.base.normalized_axes@v0.2` → `robocasa/base/mobile-base` | `normalized_axes`: x, y, yaw controller inputs | `pose_state@v0.2`: world position in m and `xyzw` quaternion |

## Ports and values

Both types have an optional in-process event input named `command` and an optional event output named `state`. The native input is `base_twist_command@v0.2`; its `payload` supplies finite `linear_x_m_s` and `linear_y_m_s` in `[-1,1]`, `angular_z_rad_s` in `[-1.5,1.5]`, and a positive `valid_for_ms` no greater than the engine's 5000 ms bound. The preset advertises `max_velocity_lease_ms:1000`, so EOS admission uses the tighter limit. The simulator stops the base when the lease expires. The native state is a snapshot from the selected MuJoCo scene, with `sample.clock:"simulation"`.

The RoboCasa input is `normalized_axes_command@v0.2`; `payload.axes` has exactly `x`, `y`, and `yaw`, each a finite number in `[-1,1]`. They are controller inputs, not m/s or rad/s. Each admitted command makes the worker take one Gym step. Its pose uses `sample.clock:"monotonic"`, `sample.frame_id:"world"`, `position_m:[x,y,z]`, and `orientation_xyzw:[x,y,z,w]`. It does not claim a measured base velocity. Both presets cap advertised observation rate at 50 Hz and state payload size at 65,536 bytes.

For example, after EOS has admitted a RoboCasa command, its adapter receives this envelope:

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "move-18",
  "port": "command",
  "payload": {
    "axes": {
      "x": 0.2,
      "y": 0.0,
      "yaw": -0.1
    }
  }
}
```

EOS supplies the run/revision fence and command identity; agents do not call the plugin or service socket directly. The adapter emits a `command_result` event with the service acknowledgment and emits observations on `state` when EOS requests them. The [runtime control contract](../../../control.md) owns the exact service wire and error codes.

## Admission, lifecycle, and failure

The adapter binds `service_instance` (`native` or `robocasa`) and the exact `device_id` from the verified preset; neither has a fallback. IsOS configures the service, EOS checks health and admits movement through its Dispatcher, then the adapter sends the command. The native service requires the current generation and stop epoch. A duplicate command ID cannot release movement twice within one service generation. On Stop, EOS closes admission and requires whole-robot proof including base, arm, and gripper; RoboCasa also requires torso proof. A missing or failed proof remains `unknown`. A stale run, wrong device, malformed payload, unavailable service, or failed step produces no fabricated state; EOS keeps the node unavailable or reports the command failure. A new Run creates a new service generation.
