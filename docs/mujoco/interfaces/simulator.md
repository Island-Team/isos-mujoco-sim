# Legacy simulator RPC

[Interface index](README.md) · [Runtime control](control.md) · [Private benchmark RPC](benchmark.md) · [中文](../../../docs_cn/mujoco/interfaces/simulator_cn.md)

## Owner, caller, and admission

This package implements `eos.simulator.v1.SimulatorService` from [`proto/simulator.proto`](../../../proto/simulator.proto). The EOS HAL is the caller on an owner-only local Unix gRPC socket selected by `--socket`; agents use EOS discovery and primitives. A direct launch can expose this listener. An EOS-managed `--managed-strict-socket` child rejects `--socket` and uses the [framed control interface](control.md). This retained v1 protobuf identity is independent of package and socket versions.

## Operations

| RPC | Input | Output | Validation and failure |
| --- | --- | --- | --- |
| `Health` | `deviceId`: nonempty device ID, no default | `available`: boolean | Unknown or unavailable device yields `false`. |
| `Execute` | `deviceId` and exactly one `command` variant | `accepted`: boolean; `errorCode`: string on rejection | Unsupported device/command, nonfinite or out-of-range target, or unavailable engine rejects. EOS supplies a finite deadline. |
| `ReadTelemetry` | `deviceId`; `kind`: `ARM`, `BASE`, or `GRIPPER` for this profile | `available` and one typed `arm`, `base`, or `gripper` message | Mismatched kind/device or unavailable engine returns unavailable. |
| `ReadCameraFrame` | `deviceId` such as `cam-0` | `available`, `widthPx`, `heightPx`, `sourceTimestampNs`, `jpeg`, `state` | Unavailable renderer or wrong device returns unavailable. |

The profile supports base, arm, gripper, and camera. It does not advertise gimbal, microphone, speaker, or `arm.pick`. The protobuf defines more command and telemetry variants for shared EOS compatibility; definition alone does not make a capability available. Caller inputs have no implicit device default. Proto3 scalar omission uses protobuf zero values; EOS must validate requested capability and command before invoking this service.

| Field family | Type / unit | Meaning and compatibility |
| --- | --- | --- |
| `baseNavigateRelative.xM`, `yM`, `yawRad` | double / m, m, rad | Relative base target; finite and within the selected scene. |
| `baseNavigateRelative.footprintWidthM`, `footprintLengthM` | double / m | Positive robot footprint for collision checking. |
| `armMoveJ.positionsRad` | repeated double / rad | Six joint targets within model limits. |
| `armMoveL.positionM`, `orientationXyzw` | repeated double / m, unit quaternion | Three position values and four quaternion values. |
| `baseDrive.linearXMS`, `linearYMS`, `angularZRadS` | double / m/s, m/s, rad/s | Continuous base command; use the exact protobuf JSON spellings. |
| `gripperMove.close`, `forceN` | bool, double / —, N | Requested gripper state and force. |
| `arm`, `base`, `gripper` telemetry | typed protobuf / SI units | Current robot state; selected oneof matches the requested kind. |
| `CameraState.sequence`, `sceneRevision` | uint64 / steps, revision | Snapshot ordering; protobuf JSON encodes uint64 as strings. |

The exact field set, enum values, and protobuf JSON spelling are in `proto/simulator.proto`. The simulator and EOS copy at `../Island-eos/share/contracts/eos/external/simulator/simulator.proto` must change together.

## Examples and lifecycle

A protobuf JSON command and result:

```json
{"deviceId":"base-0","baseNavigateRelative":{"xM":0.45,"yM":-1.3,"yawRad":0.0,"footprintWidthM":0.5,"footprintLengthM":0.6}}
```

```json
{"accepted":true}
```

A mismatched command returns `{"accepted":false,"errorCode":"unsupported_device_command"}`. `ReadTelemetry` for the base sends `{"deviceId":"base-0","kind":"BASE"}`. A camera response carries JPEG bytes as base64 in protobuf JSON. Reset and scoring are outside this service. Stop or halt interrupts active work; a connection failure, deadline, or engine fault is an unsuccessful result or gRPC status error. EOS must not infer physical stop proof from this retained route.
