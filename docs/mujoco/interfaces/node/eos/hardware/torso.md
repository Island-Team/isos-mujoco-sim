# EOS torso node

[Interface index](../../../README.md) · [Design](../../../../core/eos/hardware/torso.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/hardware/torso_cn.md)

The `0.2.8` candidate registers `eos.hardware.torso.normalized_axes@v0.2` in `eos/hardware/torso`. Only RoboCasa contributes this device: `lift` binds `robocasa/torso/torso`.

## Port and command

The optional `command` input uses `normalized_axes_command@v0.2`. The payload requires exactly `axes` and `lease_ms`. The axes object contains exactly one finite `lift` in `[-1,1]`; the lease is an integer from 1 to the selected limit (at most 1000 ms). There is no default, and unknown fields reject. These are dimensionless controller inputs. One accepted command executes one synchronous Gym step. Its lease must cover the actual control timestep or it rejects before motion; this bounds simulation time without advertising autonomous motion or a wall-clock watchdog. The port contract is `{owner:"isos",id:"normalized_axes_command@v0.2",version:"1.0"}`.

This node has no observation port and does not fabricate a torso position. Its private `command_result` acknowledgment is returned to the owner, outside graph routing.

## Command payload example

```json
{
  "axes": {
    "lift": 0.25
  },
  "lease_ms": 100
}
```

## Admission, lifecycle, and compatibility

EOS validates the run, exact package and selected part before its Dispatcher releases a typed command. The plugin validates the standard payload again and maps it to the private service wire; it forwards no extra fields. Wrong frame, joint order, mode, payload, or unavailable service produces no successful acknowledgment. Commands carry owner-supplied run/revision and durable identity outside the payload. Stop closes admission and requires whole-robot proof; timeout or a missing proof remains unknown.

Exact pins through `0.2.7` retain their legacy plugin field names, contract metadata, and `state` outputs. The `0.2.8` candidate is a new package pin; saved graphs must select its `observation` outputs explicitly. The runtime owner keeps legacy translation for old metadata. Building or verifying the candidate does not publish or install a release.
