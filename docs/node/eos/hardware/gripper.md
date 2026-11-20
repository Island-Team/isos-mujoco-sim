<a id="eos-gripper-node"></a>
# hardware/gripper group

[Interface index](../../README.md) · [Design](../../../core/adapter.md) · [Runtime control](../../../core/adapter.md) · [中文](../../../../docs_cn/node/eos/hardware/gripper_cn.md)

The `0.2.8` candidate registers `eos.hardware.gripper.binary@v0.2` in `eos/hardware/gripper`. Native `gripper` binds `gripper-0`; RoboCasa `hand` binds `robocasa/gripper/right-gripper`.

<a id="ports-and-values"></a>
### Ports and values

The optional `command` input uses `gripper_binary_command@v0.2` with exactly one required field: `action`, the string `open` or `close`. Booleans and legacy `close` fields are rejected at the standard adapter boundary. Its contract is `{owner:"isos",id:"gripper_binary_command@v0.2",version:"1.0"}`.

The `observation` output uses `gripper_state@v0.2`: a sample and named channels with finite values and explicit units. Native reports `opening` in percent with a simulation clock; RoboCasa reports `left_finger` and `right_finger` slide-joint positions in metres with a monotonic clock. Neither an acknowledgment nor an opening value proves grasp success. Observation is capped at 50 Hz and 65,536 bytes.

<a id="command-payload-example"></a>
### Command payload example

```json
{
  "action": "close"
}
```

<a id="admission-lifecycle-and-compatibility"></a>
### Admission, lifecycle, and compatibility

EOS validates the run, exact package and selected part before its Dispatcher releases a typed command. The plugin validates the standard payload again and maps it to the private service wire; it forwards no extra fields. Wrong frame, joint order, mode, payload, or unavailable service produces no successful acknowledgment. Commands carry owner-supplied run/revision and durable identity outside the payload. Stop closes admission and requires whole-robot proof; timeout or a missing proof remains unknown.

Exact pins through `0.2.7` retain their legacy plugin field names, contract metadata, and `state` outputs. The `0.2.8` candidate is a new package pin; saved graphs must select its `observation` outputs explicitly. The runtime owner keeps legacy translation for old metadata. Building or verifying the candidate does not publish or install a release.

## Carrier, settings, and availability

All ports use the `in_process` carrier. Adapter settings `service_instance` and `device_id` are required strings and must match the verified package and selected device; neither defaults to another service. Camera sizes, cadence, and limits are defined above; actuator limits come from the selected registered profile. Missing settings, unknown types, or an unavailable service block admission or readiness.

The node type declares no additional authored settings. Its preset hardware profile constrains control limits; adapter binding does not replace Dispatcher admission.
