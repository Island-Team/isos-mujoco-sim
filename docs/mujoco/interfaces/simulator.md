# EOS simulator RPC

[Package overview](../README.md) · [Design](../design.md)

This page documents the retained v1 gRPC side chain. The current IsOS/EOS v2 runtime uses the framed owner-only socket documented in [the backend guide](../backend.md). For the v1 route, EOS owns `eos.simulator.v1.SimulatorService`; this package pins its protobuf in [`proto/simulator.proto`](../../../proto/simulator.proto). EOS's HAL is the caller on an owner-only local Unix socket such as `<run>/simulator.sock`. Agents do not call this socket directly. The executable still supports this socket alongside its v2 socket and private benchmark socket.

The service has `Health`, `Execute`, `ReadTelemetry`, and `ReadCameraFrame`. Requests address an EOS-configured device ID. The MuJoCo profile exposes base, arm, gripper, and camera; it does not advertise gimbal, microphone, speaker, or `arm.pick`. `Execute` accepts one command in its protobuf `oneof`. For motion, `accepted: true` means the measured target was reached; a stop or halt interrupts active work. Unsupported devices, commands, invalid targets, or unavailable simulation produce an unsuccessful response or gRPC error. EOS applies finite deadlines and maps the result to its agent-facing primitive acknowledgment.

A minimal base command and result in protobuf JSON form are:

```json
{"deviceId":"base-0","baseNavigateRelative":{"xM":0.45,"yM":-1.3,"yawRad":0.0,"footprintWidthM":0.5,"footprintLengthM":0.6}}
```

```json
{"accepted":true}
```

The `base-0` device ID matches the current EOS MuJoCo profile; agents should use the ID they discover. A mismatched device and command returns `{"accepted":false,"errorCode":"unsupported_device_command"}`. A telemetry read uses `{"deviceId":"base-0","kind":"BASE"}` and returns `available` plus the typed `base` message, including position and velocity in metres, radians, and seconds. A camera read uses `cam-0` and returns JPEG bytes, dimensions, a source timestamp, and state when a frame is available. JPEG bytes appear base64-encoded in protobuf JSON.

The copied protobuf is tied to the EOS-owned source at `../Island-eos/share/contracts/eos/external/simulator/simulator.proto`. A contract change must be coordinated with EOS, including its runtime and configuration tests. Scene-specific goal truth and scores remain on the [benchmark RPC](benchmark.md).

**Related:** [Usage](../usage.md) · [Benchmark RPC](benchmark.md)
