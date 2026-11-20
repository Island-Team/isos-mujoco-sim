# Benchmark method and evaluator interface

[中文](../../docs_cn/core/benchmark_cn.md) · [Docs](../README.md)

The active task is upstream RoboCasa `CloseFridge`. Native pick-place and navigation remain compatibility fixtures. This page owns task provenance, success rules, limitations, and the private native evaluator RPC; task selection and display commands are in [start](../start.md).

<a id="robocasa-benchmark"></a>
## RoboCasa benchmark

The active benchmark is the upstream RoboCasa365 `CloseFridge` atomic task. The first local episode uses the official `robocasa/CloseFridge` Gym environment, target split, seed 42, and RoboCasa's own success check: the selected fridge door must be closed. The script in `tools/robocasahrun.py` takes 20 bounded random actions with base motion held at zero as a smoke baseline. Its result demonstrates environment launch and scoring, not a trained policy or a comparable leaderboard score. RoboCasa recommends 20 episodes per task for evaluation; retain seeds, assets, policy revision, and horizon when reporting a benchmark result.

`./launch.sh` runs this episode by default. It checks `ROBOCASA_ROOT` from `config/dev.toml` and then `.env`; an empty value resolves to ignored `.local/robocasa`. If source, runtime, or assets are missing, it asks before setup. `./launch.sh --robocasa --seed 42 --steps 20` makes the task and budget explicit. The setup helper pins RoboCasa source and robosuite revisions, installs a private Python 3.11 runtime, and downloads textures and general fixtures from the pinned official RoboCasa asset dataset plus the Lightwheel fixture and object archives from checksum-verified community mirrors. These files remain ignored under `.local/`. The Python runtime pins MuJoCo 3.3.1; the C++ build also targets 3.3.1.

RoboCasa source is [MIT licensed](https://github.com/robocasa/robocasa/blob/main/LICENSE); its [README](https://github.com/robocasa/robocasa#license) identifies assets and datasets as CC BY 4.0. The task implementation and success rule are in upstream `robocasa/environments/kitchen/atomic/kitchen_doors.py`. The [RoboCasa365 paper](https://robocasa.ai/assets/robocasa365_iclr26.pdf) describes the benchmark. Keep the downloaded asset attribution with any redistributed results or assets.

The former package-authored pick-and-place and navigation tasks are legacy simulator fixtures for compatibility tests and are not active benchmarks. Their private C++ benchmark RPC remains outside EOS and EGIA. RoboCasa runs in the upstream environment; the [Python robot hardware core](robocasa.md) controls and observes its PandaOmron robot in process, and [local records](robocasa.md) replay hardware commands for control testing. The package provides governed EOS hardware adapters; local smoke and hardware replay do not establish a complete EOS agent benchmark evaluation.

<a id="private-benchmark-rpc"></a>
## Private benchmark RPC

<a id="owner-caller-and-admission"></a>
### Owner, caller, and admission

This package implements `eos.mujoco.benchmark.v1.BenchmarkService` in [`proto/benchmark.proto`](../../proto/benchmark.proto). A trusted evaluator calls it over a separate owner-only Unix gRPC socket selected by `--benchmark-socket`. EOS, EGIA, and agents must never receive this socket or its ground truth. Managed strict children reject the benchmark listener. The service shares the direct-launch scene engine with the legacy simulator listener. The v1 protobuf identity is independent of package and control socket versions.

<a id="operations-and-fields"></a>
### Operations and fields

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

<a id="examples-errors-and-lifecycle"></a>
### Examples, errors, and lifecycle

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
