<a id="eos-torso-node"></a>
# hardware/torso group

[Interface index](../../README.md) · [Design](../../../core/adapter.md) · [Runtime control](../../../core/adapter.md) · [中文](../../../../docs_cn/node/eos/hardware/torso_cn.md)

The `0.2.8` candidate registers `eos.hardware.torso.normalized_axes@v0.2` in `eos/hardware/torso`. Only RoboCasa contributes this device: `lift` binds `robocasa/torso/torso`.

<a id="port-and-command"></a>
### Port and command

The optional `command` input uses `normalized_axes_command@v0.2`. The payload requires exactly `axes` and `lease_ms`. The axes object contains exactly one finite `lift` in `[-1,1]`; the lease is an integer from 1 to the selected limit (at most 1000 ms). There is no default, and unknown fields reject. These are dimensionless controller inputs. One accepted command executes one synchronous Gym step. Its lease must cover the actual control timestep or it rejects before motion; this bounds simulation time without advertising autonomous motion or a wall-clock watchdog. The port contract is `{owner:"isos",id:"normalized_axes_command@v0.2",version:"1.0"}`.

The `observation` output uses `joint_channels@v0.1`: the standard sample metadata plus `channels` containing actual joint `name`, finite `value`, and `unit` (`m` for prismatic or `rad` for hinge). It reads the selected controller's real joint position; absent or unsupported measurements remain unavailable. The port contract is `{owner:"eos",id:"joint_channels@v0.1",version:"0.1"}`. It shares the hardware profile observation rate and payload bounds. Its frame is joint-local. Its private `command_result` acknowledgment is returned to the owner, outside graph routing.

<a id="command-payload-example"></a>
### Command payload example

```json
{
  "axes": {
    "lift": 0.25
  },
  "lease_ms": 100
}
```

<a id="admission-lifecycle-and-compatibility"></a>
### Admission, lifecycle, and compatibility

EOS validates the run, exact package and selected part before its Dispatcher releases a typed command. The plugin validates the standard payload again and maps it to the private service wire; it forwards no extra fields. Wrong frame, joint order, mode, payload, or unavailable service produces no successful acknowledgment. Commands carry owner-supplied run/revision and durable identity outside the payload. Stop closes admission and requires whole-robot proof; timeout or a missing proof remains unknown.

Exact pins through `0.2.7` retain their legacy plugin field names, contract metadata, and `state` outputs. The `0.2.8` candidate is a new package pin; saved graphs must select its `observation` outputs explicitly. The runtime owner keeps legacy translation for old metadata. Building or verifying the candidate does not publish or install a release.

## Carrier, settings, and availability

All ports use the `in_process` carrier. Adapter settings `service_instance` and `device_id` are required strings and must match the verified package and selected device; neither defaults to another service. Camera sizes, cadence, and limits are defined above; actuator limits come from the selected registered profile. Missing settings, unknown types, or an unavailable service block admission or readiness.

The node type declares no additional authored settings. Its preset hardware profile constrains control limits; adapter binding does not replace Dispatcher admission.
