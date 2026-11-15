# EOS manipulator nodes

[Interface index](../../../README.md) · [Design](../../../../design/eos/hardware/manipulator.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/manipulator_cn.md)

These nodes control the robot arm. The native preset uses six MuJoCo joint targets. The RoboCasa preset uses six normalized end-effector controller axes and a separate control-mode input. Their commands and observations have different units and must not be interchanged.

| Preset / node ref | Type and bound device | Commands | Observation |
| --- | --- | --- | --- |
| `native/arm` | `eos.hardware.manipulator.device@v0.2` → `arm-0` | `joint_positions`: six joint positions in rad | `joint_state@v0.2`: six names, positions in rad, velocities in rad/s |
| `robocasa/right-arm` | `eos.hardware.manipulator.normalized_cartesian@v0.2` → `robocasa/arm/right-arm` | `normalized_cartesian`: translation and rotation axes; `mode`: control mode | `pose_state@v0.2`: end-effector pose relative to `robot_base` |

## Ports and values

The native type has `command: joint_position_command@v0.2` and `state: joint_state@v0.2`. The command carries six finite `joint_positions_rad` targets within the selected model's joint ranges. The preset advertises `max_joint_position_rad:3.14` and `max_joint_speed_rad_s:1.0`; EOS applies its admission policy before the simulator validates scene limits. The state names are `shoulder_pan_joint`, `shoulder_lift_joint`, `elbow_joint`, `wrist_1_joint`, `wrist_2_joint`, and `wrist_3_joint`, in that order. Its sample clock is `simulation`.

The RoboCasa type has `command: normalized_axes_command@v0.2`, `mode: control_mode_command@v0.2`, and `state: pose_state@v0.2`. The `command` payload has exactly six finite `axes` values named `dx`, `dy`, `dz`, `droll`, `dpitch`, and `dyaw`, each in `[-1,1]`. These are upstream controller inputs, not metres or radians. The `mode` payload has `mode:0` or `mode:1`; it selects the pinned RoboCasa controller mode. Each accepted input advances one Gym step. State carries `position_m:[x,y,z]` and a unit `orientation_xyzw:[x,y,z,w]`, with `sample.frame_id:"robot_base"` and `sample.clock:"monotonic"`. There is no joint-state output from this RoboCasa type. Observation is capped at 50 Hz and 65,536 bytes.

An admitted RoboCasa arm command looks like:

```json
{"run_id":"run-7","revision":"rev-2","command_id":"arm-18","port":"command","payload":{"axes":{"dx":0.1,"dy":0.0,"dz":0.0,"droll":0.0,"dpitch":0.0,"dyaw":0.0}}}
```

EOS constructs the run fence and command identity. The adapter emits an acknowledgment on `command_result` and requested state on `state`; agents cannot address the private worker socket.

## Admission, lifecycle, and failure

The exact `service_instance` and `device_id` settings bind the node to the verified preset. EOS checks health and Dispatcher admission before calling the adapter. The native service checks the current generation and stop epoch; both services deduplicate command IDs in one generation. Invalid shape, nonfinite axes, out-of-range targets, wrong mode, stale run/revision, or service failure rejects control. On Stop, EOS closes admission and requires whole-robot proof; an unproved arm stop is `unknown` even if the process exits. The RoboCasa worker faults after a failed Gym step and requires a new run rather than silently continuing. See [runtime control](../../../control.md) for wire errors and deadlines.
