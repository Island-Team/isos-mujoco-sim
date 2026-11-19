# EOS base nodes

[Interface index](../../../README.md) · [Design](../../../../core/eos/hardware/base.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/base_cn.md)

The `0.2.8` candidate registers the native `eos.hardware.base.device@v0.2` and RoboCasa `eos.hardware.base.normalized_axes@v0.2` types in `eos/hardware/base`. The native preset binds `drive` to `base-0`; the RoboCasa preset binds `mobile` to `robocasa/base/mobile-base`.

## Ports and values

Both nodes have an optional in-process `command` input and an `observation` output. The native input uses `base_twist_command@v0.2`; the RoboCasa input uses `normalized_axes_command@v0.2`. Command ports use `{owner:"isos",id:<data_type>,version:"1.0"}`. Their named Dispatcher ports inherit the complete input contract.

| Native field | Type / unit | Meaning and validation |
| --- | --- | --- |
| `frame_id` | string / — | Required `base_link`, matching the selected profile's body command frame. |
| `vx_m_s`, `vy_m_s` | finite number / m/s | Required body-frame velocities; vector magnitude must fit `max_linear_m_s` (1.0 in the preset). |
| `yaw_rate_rad_s` | finite number / rad/s | Required yaw rate; absolute value ≤1.5 in the preset. |
| `lease_ms` | integer / ms | Required 1–1000, bounded by the selected movement limit. The native service expires motion in simulation time. |

RoboCasa requires exactly `axes:{x,y,yaw}` with finite values in `[-1,1]` and integer `lease_ms` from 1 to the selected limit (at most 1000). These are dimensionless controller inputs. A command advances one synchronous Gym step. The lease must cover the selected environment’s actual control timestep; a shorter lease rejects before motion. This is a simulation-time bound, without an autonomous motion loop or wall-clock watchdog.

The native observation uses `base_state@v0.2`: world-frame planar pose, body-frame linear velocities, and yaw rate. The RoboCasa observation uses `pose_state@v0.2` with a world-frame position and unit `xyzw` quaternion. The sample identifies source time, clock, sequence, and frame; native time is `simulation`, RoboCasa time is `monotonic`. Neither node fabricates a velocity from the other representation.

## Command payload example

```json
{
  "frame_id": "base_link",
  "vx_m_s": 0.2,
  "vy_m_s": 0.0,
  "yaw_rate_rad_s": 0.05,
  "lease_ms": 100
}
```

## Admission, lifecycle, and compatibility

EOS validates the run, exact package and selected part before its Dispatcher releases a typed command. The plugin validates the standard payload again and maps it to the private service wire; it forwards no extra fields. Wrong frame, joint order, mode, payload, or unavailable service produces no successful acknowledgment. Commands carry owner-supplied run/revision and durable identity outside the payload. Stop closes admission and requires whole-robot proof; timeout or a missing proof remains unknown.

Exact pins through `0.2.7` retain their legacy plugin field names, contract metadata, and `state` outputs. The `0.2.8` candidate is a new package pin; saved graphs must select its `observation` outputs explicitly. The runtime owner keeps legacy translation for old metadata. Building or verifying the candidate does not publish or install a release.
