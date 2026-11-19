# EOS manipulator nodes

[Interface index](../../../README.md) · [Design](../../../../core/eos/hardware/manipulator.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/manipulator_cn.md)

The `0.2.8` candidate registers native joint-position and RoboCasa normalized Cartesian manipulators under `eos/hardware/manipulator`. Native `arm` binds `eos.hardware.manipulator.device@v0.2` to `arm-0`; RoboCasa `right-arm` binds `eos.hardware.manipulator.normalized_cartesian@v0.2` to `robocasa/arm/right-arm`.

## Ports and values

The native node has `command: joint_position_command@v0.2` and `observation: joint_state@v0.2`. A command requires exactly `joint_names` and `position_rad`: six unique names in the selected profile's order and six finite absolute positions in radians. The adapter checks the profile's absolute position limit (3.14 rad) and the service checks scene limits. The candidate does not advertise `max_joint_speed_rad_s`; its position controller has no qualified speed guarantee. State includes the same joint names, positions, velocities, and a simulation-clock sample in `robot_base`.

The RoboCasa node has `command: normalized_axes_command@v0.2`, `mode: control_mode_command@v0.2`, and `observation: pose_state@v0.2`. Its command requires exactly six `axes` names (`dx`, `dy`, `dz`, `droll`, `dpitch`, `dyaw`), finite values in `[-1,1]`, and integer `lease_ms` in 1–1000 bounded by the selected limit. These are dimensionless controller inputs. Its mode payload is exactly `{"mode":"0"}` or `{"mode":"1"}`. Each command executes one synchronous Gym step. A normalized command’s lease must cover the actual control timestep or it rejects before motion; this bounds simulation time and does not promise a wall-clock watchdog. Observation reports end-effector position and a unit `xyzw` quaternion in `robot_base` with a monotonic sample; no joint state is fabricated.

Command ports use `{owner:"isos",id:<data_type>,version:"1.0"}`. A parts Dispatcher selects one hardware input per part. Choose `command` or `mode` for this arm; binding the same hardware twice does not create two supported routes.

## Command payload example

```json
{
  "joint_names": [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint"
  ],
  "position_rad": [
    0.1,
    -0.2,
    0.1,
    0.0,
    0.0,
    0.0
  ]
}
```

## Admission, lifecycle, and compatibility

EOS validates the run, exact package and selected part before its Dispatcher releases a typed command. The plugin validates the standard payload again and maps it to the private service wire; it forwards no extra fields. Wrong frame, joint order, mode, payload, or unavailable service produces no successful acknowledgment. Commands carry owner-supplied run/revision and durable identity outside the payload. Stop closes admission and requires whole-robot proof; timeout or a missing proof remains unknown.

Exact pins through `0.2.7` retain their legacy plugin field names, contract metadata, and `state` outputs. The `0.2.8` candidate is a new package pin; saved graphs must select its `observation` outputs explicitly. The runtime owner keeps legacy translation for old metadata. Building or verifying the candidate does not publish or install a release.
