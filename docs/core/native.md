# Native simulator and retained RPC

[中文](../../docs_cn/core/native_cn.md) · [Docs](../README.md)

The native engine loads package-owned MJCF, resets deterministically, steps physics, renders observations, and computes evaluator-only truth. The retained gRPC route below is available only on direct launches; managed services use [adapter control](adapter.md).

<a id="mujoco-core-design"></a>
## MuJoCo core design

The simulator core owns scene loading, deterministic reset, physics, rendering, and private benchmark scoring. IsOS verifies and configures an exact package service; EOS manages robot-side admission, health, and Stop. Native and RoboCasa services supply device data through private endpoints without exposing benchmark ground truth.

The native developer launcher and the IsOS package both execute `eos-mujoco-sim`. Its direct sockets and managed strict socket share one `SimEngine` instance from `src/mujoco/engine.h`; the separate `mujoco-core` developer executable also links the same `mujoco_core` library. Socket admission and lifecycle differ, while scene loading, reset, stepping, commands, snapshots, camera rendering, and private scoring remain in that core. RoboCasa uses upstream Gym and `robocasa_core.Hardware` in an isolated Python service; it does not call the native C++ `SimEngine` API.

On 2026-11-16, `ctest --test-dir build -R '^(core-launch|launcher-lifecycle|strict-socket|strict-socket-navigation)$' --output-on-failure` passed 4/4 tests, covering the direct core executable, developer launcher, and both managed native scenes. Complete output is under ignored `data/test/20261116-core-api-parity/ctest.log`.

<a id="legacy-simulator-rpc"></a>
## Legacy simulator RPC

<a id="owner-caller-and-admission"></a>
### Owner, caller, and admission

This package implements `eos.simulator.v1.SimulatorService` from [`proto/simulator.proto`](../../proto/simulator.proto). The EOS HAL is the caller on an owner-only local Unix gRPC socket selected by `--socket`; agents use EOS discovery and primitives. A direct launch can expose this listener. A managed `--managed-strict-socket` child rejects `--socket` and uses the [framed control interface](adapter.md). This retained v1 protobuf identity is independent of package and socket versions.

<a id="operations"></a>
### Operations

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

<a id="examples-and-lifecycle"></a>
### Examples and lifecycle

A protobuf JSON command and result:

```json
{
  "deviceId": "base-0",
  "baseNavigateRelative": {
    "xM": 0.45,
    "yM": -1.3,
    "yawRad": 0.0,
    "footprintWidthM": 0.5,
    "footprintLengthM": 0.6
  }
}
```

```json
{
  "accepted": true
}
```

A mismatched command returns `{"accepted":false,"errorCode":"unsupported_device_command"}`. `ReadTelemetry` for the base sends `{"deviceId":"base-0","kind":"BASE"}`. A camera response carries JPEG bytes as base64 in protobuf JSON. Reset and scoring are outside this service. Stop or halt interrupts active work; a connection failure, deadline, or engine fault is an unsuccessful result or gRPC status error. EOS must not infer physical stop proof from this retained route.

## Scene loading and deterministic reset

The native catalog supports `pick-place` and `navigation`, identified by exactly one MJCF numeric profile marker: `eos_benchmark_pick_place_v1` or `eos_benchmark_navigation_v1`. Scene and asset paths must remain within the verified package. The catalog checks required camera, base, six-joint arm, and gripper elements before staging; the real MuJoCo loader remains the runtime compatibility check. `tools/catalog.py` owns the required element names and digest validation.

`SimEngine::Reset(seed)` clears MuJoCo state, derives bounded object and obstacle variants from deterministic integer seed mixing, restores base/arm/gripper targets, and clears episode accounting. Repeatability requires the same scene bytes, seed, dependency versions, and action sequence. Native fixtures use 2 ms physics timesteps; private evaluator Reset pauses real-time execution before bounded manual Step. Neither reset nor private scoring is exposed as an EOS hardware port. New scenes need a supported profile, deterministic reset, a defined success condition, source attribution and license review, real load/replay checks, and usable EOS-visible devices.
