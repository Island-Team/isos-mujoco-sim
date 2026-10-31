# EOS-owned simulator socket contract

[中文](../../../docs_cn/mujoco/interfaces/socket_cn.md) · [Package descriptor](package.md) · [Design](../design.md)

**Identity and status.** The existing wire protocol is `2.0.0`; its number is a compatibility identity and does not set the package or graph release version. The simulator currently implements the framed Unix socket and operations below. The target checks for `node` device identity, `command_id` deduplication, explicit error codes and bounded stop progress are **not implemented yet**. EOS is the sole robot-side caller through its internal `mujoco-v2` adapter family; EGIA and IsosUI call EOS, never this socket. Benchmark RPC is separate and evaluator-only. The old gRPC simulator socket is documented as a retained legacy side chain in [simulator.md](simulator.md).

## Frame and common fields

The socket is an owner-only Unix stream (`0600`) under a private runtime directory. Each frame is `u32_le metadata_bytes | u32_le payload_bytes | UTF-8 JSON metadata | binary payload`; metadata is `1..65536` bytes and payload is `0..8388608` bytes. Requests have no binary payload. A malformed or oversized frame may close without response. A successful camera response carries JPEG bytes; other responses carry no binary payload. One connection currently handles one request. The target keeps this framing unchanged and adds semantic validation only.

| Field | Type / unit | Purpose and owner | Default / validation / compatibility |
| --- | --- | --- | --- |
| `version` | string | Simulator wire identity in every request/response | Required `"2.0.0"`; reject another value, retain the ID for existing callers. |
| `id` | nonempty string | Caller correlation ID, echoed in response | Required; bound length in target; old callers already send it. |
| `node` | nonempty string / simulator device ID | EOS adapter sends `adapter.settings.simulator_node` (`cam-0`, `base-0`, or `arm-0`) | Existing implementation ignores it; target matches the scene device ID and operation kind. EOS separately verifies the graph node to device mapping before sending. |
| `op` | enum string | Requested operation | Required; values in table below, unknown value returns an error. |
| `command_id` | nonempty string | Dispatcher admission identity for motion and stop | Existing implementation ignores it; target requires it for movement/stop, deduplicates per node and rejects conflicting replay. |
| `ok` | bool | Response success | Returned by simulator; false includes `error.message`. |
| `error.message` | string | Human-readable failure | Present on `ok:false`; target also returns stable `error.code`, additive for old readers. |
| `timestamp_ns` | finite number / simulated ns | Snapshot or frame time | Response; no caller default. Values are JSON numbers today, so consumers must not assume exact integer precision beyond the safe range. |
| `sequence` | nonnegative number / physics steps | Snapshot ordering | Response; nondecreasing within one simulator run. |
| `accepted` | bool | Operation-level admission/result | Response for health and motion/stop; `ok:false` wins if both occur. |

All numeric motion inputs must be finite. EOS checks graph identity, settings, device class, bounds, deadline and Dispatcher admission before calling the socket; the simulator independently checks numeric bounds and actual scene capability. Unknown optional response fields are ignored by old readers. A target error uses `{"ok":false,"error":{"code":"unsupported_operation","message":"unsupported operation"}}`; legacy readers still use `error.message`.

## Operations

| `op` | Additional request fields (type / unit) | Success fields (type / unit) | Validation and effect |
| --- | --- | --- | --- |
| `health` | none | `accepted: bool` | Reports live engine availability; target matches `node` to owner. |
| `camera_capture` | none | `format:"jpeg"`, `rgb_length:u32` bytes, `depth_available:false`, `width_px:u32`, `height_px:u32`, JPEG payload | Frame length equals `rgb_length`; target verifies camera node and bounded dimensions. |
| `base_observe` | none | `position_m:[f64;2]` m, `linear_velocity_m_s:[f64;2]` m/s, `yaw_rad:f64` rad, `angular_velocity_rad_s:f64` rad/s | Target verifies base node; values are a consistent engine snapshot. |
| `base_move` | `linear_x_m_s:f64` m/s, `linear_y_m_s:f64` m/s, `angular_z_rad_s:f64` rad/s, `valid_for_ms:f64` ms, `command_id:string` | `accepted:bool` | `valid_for_ms` in `(0,5000]`; scene limits apply, then base lease expires to stop. Target deduplicates accepted ID. |
| `manipulator_observe` | none | `joint_positions_rad:[f64;6]` rad, `joint_velocities_rad_s:[f64;6]` rad/s, `end_position_m:[f64;3]` m, `end_orientation_xyzw:[f64;4]` unit quaternion | Target verifies arm node; orientation order is x,y,z,w. |
| `manipulator_move` | `joint_positions_rad:[f64;6]` rad, `command_id:string` | `accepted:bool` | Exactly six finite targets within scene limits; target deduplicates accepted ID. |
| `stop` | `command_id:string` | `accepted:bool` | Stops base and arm; target makes stop idempotent, bounded and able to interrupt in-flight work. |

Example base request and success metadata (each preceded by its binary frame header):

```json
{"version":"2.0.0","id":"req-17","node":"base-0","op":"base_move","command_id":"cmd-17","linear_x_m_s":0.2,"linear_y_m_s":0.0,"angular_z_rad_s":0.0,"valid_for_ms":200.0}
```

```json
{"version":"2.0.0","id":"req-17","ok":true,"accepted":true,"timestamp_ns":100000000,"sequence":50}
```

Example target ownership failure (the current service does not yet enforce `node`):

```json
{"version":"2.0.0","id":"req-17","ok":false,"error":{"code":"node_mismatch","message":"node is not the declared base device"},"timestamp_ns":100000000,"sequence":50}
```

## Lifecycle and failures

EOS receives a verified executable/scene/socket from IsOS, starts the simulator as a direct child, waits for the socket and successful health, then makes declared adapters ready. A missing scene, incompatible protocol, malformed frame, unavailable camera or disconnected socket makes that adapter unavailable; EOS does not fabricate observations. On stop, EOS blocks new admissions, sends stop to active actuators with a bounded deadline, confirms or records failure, then terminates and reaps the child. The simulator removes its sockets on normal exit. An identical transport retransmission with the same `command_id` receives the prior result rather than repeating motion. EOS never automatically replays an uncertain released command; it reconciles from fresh state or requires an explicitly authorized new admission. A conflicting payload under the same ID fails. Stop is allowed during other work and is never queued behind an unbounded capture or move.
