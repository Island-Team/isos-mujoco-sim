# Private benchmark RPC

[Interface index](README.md) · [Simulator RPC](simulator.md) · [Benchmark method](../benchmarks/Robocasa/README.md) · [中文](../../../docs_cn/mujoco/interfaces/benchmark_cn.md)

## Owner, caller, and admission

This package implements `eos.mujoco.benchmark.v1.BenchmarkService` in [`proto/benchmark.proto`](../../../proto/benchmark.proto). A trusted evaluator calls it over a separate owner-only Unix gRPC socket selected by `--benchmark-socket`. EOS, EGIA, and agents must never receive this socket or its ground truth. Managed strict children reject the benchmark listener. The service shares the direct-launch scene engine with the legacy simulator listener. The v1 protobuf identity is independent of package and control socket versions.

## Operations and fields

| RPC | Request fields: type / unit | Response | Validation and default |
| --- | --- | --- | --- |
| `Reset` | `seed`: uint64 / — | `StateResponse` | Restores deterministic initial state and pauses real-time stepping; omitted seed is protobuf zero. |
| `Step` | `steps`: uint32 / fixed 2 ms steps | `StateResponse` | `1..100000`; requires paused manual stepping. |
| `State` | empty | `StateResponse` | Reads current state without advancing. |
| `Score` | empty | `ScoreResponse` | Reads scene success and collision scoring after reset. |
| `SetPaused` | `paused`: bool / — | `StateResponse` | `true` pauses; omitted value is protobuf `false`. |

| Response field | Type / unit | Meaning and compatibility |
| --- | --- | --- |
| `ok`, `error` | bool, string / — | State operation result and human error; `error` is empty on success. |
| `sequence`, `elapsedSimS` | uint64 / steps, double / s | Deterministic step count and simulated time. Proto JSON encodes uint64 as a string. |
| `baseXM`, `baseYM`, `baseYawRad` | double / m, m, rad | Ground-truth base pose. |
| `armJointsRad` | repeated double / rad | Six joint positions. |
| `objectHeldId` | string / — | Held object identity; empty when none. |
| `objectPositionM`, `gripperPinchPositionM` | repeated double / m | World xyz positions. |
| `obstacle0PositionM`, `obstacle1PositionM` | repeated double / m | World xy positions. |
| `navigation`, `grasp`, `placement` | bool / — | Scene success predicates; inapplicable goals remain false. |
| `collisions`, `elapsedSimS` | uint32 / count, double / s | Collision count and elapsed time in `ScoreResponse`. |

## Examples, errors, and lifecycle

These are individual protobuf JSON messages; the transport is gRPC protobuf:

```json
{
  "seed": "42"
}
```

```json
{
  "ok": true,
  "sequence": "0",
  "elapsedSimS": 0.0,
  "baseXM": -1.2,
  "baseYM": 0.0,
  "baseYawRad": 0.0,
  "armJointsRad": [
    -1.5708,
    -1.5708,
    1.5708,
    -1.5708,
    -1.5708,
    0.0
  ]
}
```

A bounded step request is `{"steps":200}`. `State` and `Score` use `{}`. A score result can be `{"navigation":true,"grasp":false,"placement":false,"collisions":0,"elapsedSimS":8.4}`. A reset failure returns `{"ok":false,"error":"scene not loaded"}`. More than 100,000 steps returns gRPC `INVALID_ARGUMENT`; stepping while real-time execution is active returns `FAILED_PRECONDITION`. Transport and server failures use gRPC status errors. A score is meaningful only after successful reset and a bounded episode. Keep these values on the trusted evaluator path.
