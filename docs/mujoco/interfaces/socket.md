# MuJoCo-owned simulator socket contract

[中文](../../../docs_cn/mujoco/interfaces/socket_cn.md) · [Package descriptor](package.md) · [Design](../design.md)

**Ownership, identity and status.** This package owns the simulator socket protocol; EOS owns the client adapter and direct-child lifecycle. The existing wire protocol is `2.0.0`; its number is a compatibility identity and does not set the package or graph release version. The simulator currently implements the framed Unix socket and operations below. R05 managed mode enforces `node` device identity, `command_id` deduplication and stable errors. R06 bounded preemptive stop progress remains open. EOS is the sole robot-side caller through its internal `mujoco-v2` adapter family; EGIA and IsosUI call EOS, never this socket. Benchmark RPC is separate and evaluator-only. The old gRPC simulator socket is documented as a retained legacy side chain in [simulator.md](simulator.md).

## Frame and common fields

The socket is an owner-only Unix stream (`0600`) under a private runtime directory. Each frame is `u32_le metadata_bytes | u32_le payload_bytes | UTF-8 JSON metadata | binary payload`; metadata is `1..65536` bytes and payload is `0..8388608` bytes. Requests have no binary payload. A malformed or oversized frame may close without response. A successful camera response carries JPEG bytes; other responses carry no binary payload. One connection currently handles one request. Strict mode keeps this framing unchanged and adds semantic validation only.

**R05 managed mode:** IsOS generated configuration identifies the P01-verified package executable, scene and applied graph revision for an EOS-managed backend. EOS derives and passes `--managed-strict-socket` for that backend; the authored graph contains no mode switch. The flag requires `--v2-socket` and rejects `--socket` and `--benchmark-socket`: neither the historical `eos.simulator.v1.SimulatorService` actuator listener nor the benchmark reset/step listener may exist in this managed child. This leaves EOS Dispatcher as the only actuator route. A separate trusted evaluator may use a direct launch outside the managed deployment. A direct launch without the flag retains the present `2.0.0` framing and optional/ignored `node` and `command_id` behavior, including the historical gRPC and benchmark sockets. It is the legacy socket mode and cannot satisfy readiness for an applied IsOS graph. This is a launch policy, not a new wire identity. Incompatible future framing or direct-launch changes require a new protocol identity.

In strict mode a successful `health` response includes `features:["strict-socket-v1"]` and `accepted:true`; direct legacy mode has no `strict-socket-v1` feature. EOS checks the version, echoed request ID, `ok`, `accepted` and exact feature before declaring the backend or any MuJoCo adapter ready. Merely connecting to the socket is insufficient. A missing, malformed or contradictory feature fails readiness, and EOS terminates/reaps the unready child. The child never claims this feature until all strict checks and legacy-listener suppression are active.

The managed child compiles stable device IDs and scene support from the package-owned P02 catalog in `tools/scene_catalog.py`, then matches the device to the profile of the loaded MuJoCo model. The model supplies the six named joint ranges. EOS must supply the verified scene path and check the applied graph's selected device mapping; the child cannot infer an authored graph path from a socket request.

| Field | Type / unit | Purpose and owner | Default / validation / compatibility |
| --- | --- | --- | --- |
| `version` | string | Simulator wire identity in every request/response | Required `"2.0.0"`; reject another value, retain the ID for existing callers. |
| `id` | nonempty string / — | Caller correlation ID, echoed in response | Required; strict mode accepts 1..128 UTF-8 bytes, matching EOS Dispatcher IDs; legacy direct mode retains its existing nonempty-string behavior. |
| `node` | nonempty string / simulator device ID | EOS adapter sends `adapter.settings.simulator_node` (`cam-0`, `base-0`, or `arm-0`) | Legacy direct mode ignores it; strict mode requires the exact device ID present in the selected scene's verified catalog and the operation's device kind. EOS separately verifies graph node, kind, selected scene and package pin before sending. |
| `op` | enum string | Requested operation | Required; values in table below, unknown value returns an error. |
| `command_id` | nonempty string / — | Dispatcher admission identity for motion and stop | Legacy direct mode ignores it; strict mode requires 1..128 UTF-8 bytes for movement/stop, matching EOS Dispatcher IDs and deduplicates per node. It is absent for health, observation and capture. Legacy direct mode retains ignored behavior. |
| `ok` | bool | Response success | Returned by simulator; false includes `error.message`. |
| `error.message` | string | Human-readable failure | Present on `ok:false`; strict mode also returns stable `error.code`, additive for old readers. |
| `error.code` | string enum / — | Stable strict-mode failure identity | Added only on `ok:false` where a bounded request was parsed; values and precedence are below. Old readers continue to use `error.message`. |
| `features` | string array / — | Health capability proof | Strict `health` success contains the required feature `strict-socket-v1`; additional future feature names may appear. Legacy health omits it. EOS requires the exact member. |
| `timestamp_ns` | finite number / simulated ns | Snapshot or frame time | Response; no caller default. Values are JSON numbers today, so consumers must not assume exact integer precision beyond the safe range. |
| `sequence` | nonnegative number / physics steps | Snapshot ordering | Response; nondecreasing within one simulator run. |
| `accepted` | bool | Operation-level admission/result | Response for health and motion/stop; `ok:false` wins if both occur. |

All numeric motion inputs must be JSON numbers and finite after parsing. Strict base components lie within the engine's current limits: `linear_x_m_s` and `linear_y_m_s` in `[-1,1]`, `angular_z_rad_s` in `[-1.5,1.5]`, and `valid_for_ms` in `(0,5000]`; the scene may impose tighter limits. Every manipulator element must lie within the loaded model's named joint range. EOS checks graph identity, settings, device class, bounds, deadline and Dispatcher admission before calling the socket; the simulator independently checks actual scene capability. Unknown optional response fields are ignored by old readers. A strict error uses `{"ok":false,"error":{"code":"unsupported_operation","message":"unsupported operation"}}`; legacy readers still use `error.message`.

Strict validation is ordered: frame bounds/JSON parsing, wire version and bounded `id`, known `op`, exact `node` and kind, required `command_id`, typed finite fields and scene limits, then idempotency and engine release. The first failed check determines the stable code: `invalid_request`, `unsupported_version`, `unsupported_operation`, `node_mismatch`, `invalid_command_id`, `invalid_movement`, `out_of_range`, `command_id_conflict`, `command_in_progress`, `command_capacity`, or `device_unavailable`. A malformed, short or oversized frame may close without response because its `id` is untrusted. `ok:false` always wins over `accepted`; it never communicates physical completion. A bounded response echoes the parsed request `id` and has no binary payload.

For strict motion and `stop`, atomically reserve `(node,command_id)` before an engine call. Its fingerprint is the operation and canonical typed values: numeric JSON spellings with equal parsed `f64` values are identical, including `-0` and `0`; array order is significant. Request `id` is transport correlation, not part of this fingerprint. An identical duplicate returns the stored operation result with its own echoed request `id` and does not release again. A different fingerprint under the same live key returns `command_id_conflict`. A concurrent identical duplicate may await the original within a bounded request deadline or return `command_in_progress`; it never executes twice. A release with no known result is stored as uncertain and never reported as accepted success. Retain every key, fingerprint and terminal/uncertain result for the entire child generation; no time expiry or eviction can permit same-child replay. Bound the movement table to 65,536 entries and reserve a separate 4,096-entry stop table so movement saturation cannot consume stop capacity. At capacity, return `command_capacity` before release and report an actionable fault; an exhausted stop table also rejects a new stop identity and requires EOS to record unknown stop and escalate under R06. This process-local dedup does not replace the EOS durable Dispatcher journal: after a child restart, EOS must never automatically retry a released command whose outcome was uncertain.

## Operations

| `op` | Additional request fields (type / unit) | Success fields (type / unit) | Validation and effect |
| --- | --- | --- | --- |
| `health` | none | `accepted: bool`; strict mode also `features:["strict-socket-v1"]` | Reports live engine availability; strict mode matches `node` to an available scene device. EOS probes each declared device before publishing readiness. |
| `camera_capture` | none | `format:"jpeg"`, `rgb_length:u32` bytes, `depth_available:false`, `width_px:u32`, `height_px:u32`, JPEG payload | Frame length equals `rgb_length`; strict mode verifies camera node and bounded dimensions. |
| `base_observe` | none | `position_m:[f64;2]` m, `linear_velocity_m_s:[f64;2]` m/s, `yaw_rad:f64` rad, `angular_velocity_rad_s:f64` rad/s | Strict mode verifies base node; values are a consistent engine snapshot. |
| `base_move` | `linear_x_m_s:f64` m/s, `linear_y_m_s:f64` m/s, `angular_z_rad_s:f64` rad/s, `valid_for_ms:f64` ms, `command_id:string` | `accepted:bool` | `valid_for_ms` in `(0,5000]`; scene limits apply, then base lease expires to stop. Strict mode deduplicates the ID. |
| `manipulator_observe` | none | `joint_positions_rad:[f64;6]` rad, `joint_velocities_rad_s:[f64;6]` rad/s, `end_position_m:[f64;3]` m, `end_orientation_xyzw:[f64;4]` unit quaternion | Strict mode verifies arm node; orientation order is x,y,z,w. |
| `manipulator_move` | `joint_positions_rad:[f64;6]` rad, `command_id:string` | `accepted:bool` | Exactly six finite targets within scene limits; target deduplicates accepted ID. |
| `stop` | `command_id:string` | `accepted:bool` | Strict mode accepts `node` equal to the selected scene catalog's base or manipulator device ID (currently `base-0` or `arm-0`) and applies the existing whole-robot base-and-arm stop. R05 deduplicates this request; `accepted` only reports the current engine call, not dual physical acknowledgment. R06 adds the dedicated stop lane, bounded interruption and separate base/arm acknowledgment. |

Strict health proof metadata (each preceded by its binary frame header):

```json
{"version":"2.0.0","id":"req-health-1","node":"base-0","op":"health"}
```

```json
{"version":"2.0.0","id":"req-health-1","ok":true,"accepted":true,"features":["strict-socket-v1"],"timestamp_ns":100000000,"sequence":50}
```

Example base request and success metadata:

```json
{"version":"2.0.0","id":"req-17","node":"base-0","op":"base_move","command_id":"cmd-17","linear_x_m_s":0.2,"linear_y_m_s":0.0,"angular_z_rad_s":0.0,"valid_for_ms":200.0}
```

```json
{"version":"2.0.0","id":"req-17","ok":true,"accepted":true,"timestamp_ns":100000000,"sequence":50}
```

Example strict ownership failure:

```json
{"version":"2.0.0","id":"req-17","ok":false,"error":{"code":"node_mismatch","message":"node is not the declared base device"},"timestamp_ns":100000000,"sequence":50}
```

## Lifecycle and failures

EOS receives a verified executable/scene/socket from IsOS, starts the simulator as a direct child, waits for the socket and successful health, then makes declared adapters ready. A missing scene, incompatible protocol, malformed frame, unavailable camera or disconnected socket makes that adapter unavailable; EOS does not fabricate observations. On stop, EOS blocks new admissions, sends stop to active actuators with a bounded deadline, confirms or records failure, then terminates and reaps the child. The simulator removes its sockets on normal exit. An identical transport retransmission with the same `command_id` receives the prior result rather than repeating motion. EOS never automatically replays an uncertain released command; it reconciles from fresh state or requires an explicitly authorized new admission. A conflicting payload under the same ID fails.

**R06 stop scheduling remains open after R05:** The listener must accept a second connection while a move or capture is in flight, parse a bounded frame and route `stop` to a dedicated control lane. That lane must invalidate active movement leases, return separate base and arm acknowledgment or an unknown outcome, and allow EOS to terminate/reap only after its stop deadline. Capture and motion workers must observe cancellation. One request per connection remains true. R05's strict feature does not certify this R06 stop guarantee.
