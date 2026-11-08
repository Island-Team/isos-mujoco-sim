# Private benchmark RPC

[Package overview](../README.md) · [Benchmark method](../benchmarks/Robocasa/README.md)

This package owns `eos.mujoco.benchmark.v1.BenchmarkService` in [`proto/benchmark.proto`](../../../proto/benchmark.proto). A trusted evaluator calls it over a separate owner-only Unix socket such as `<run>/benchmark.sock`. EOS and EGIA do not call it, and no agent should receive its ground truth. The service shares the selected scene engine with the EOS simulator service but has a different audience and access boundary.

`Reset` takes an unsigned 64-bit seed, restores the selected scene's deterministic initial state, and pauses real-time stepping. `Step` advances a requested number of fixed 2 ms steps, at most 100,000 per call. `SetPaused` switches real-time stepping on or off. `State` returns current sequence, elapsed simulated seconds, base pose, six arm joints, and scene ground truth. `Score` returns the scene's `navigation`, `grasp`, `placement`, `collisions`, and `elapsed_sim_s` values. The fields are stable across current scenes; inapplicable pick-and-place goals are false for navigation.

Protobuf JSON examples show field names and types; the transport is gRPC protobuf, not an HTTP JSON endpoint:

```json
{"seed":"42"}
{"ok":true,"sequence":"0","elapsedSimS":0.0,"baseXM":-1.2,"baseYM":0.0,"baseYawRad":0.0,"armJointsRad":[-1.5708,-1.5708,1.5708,-1.5708,-1.5708,0.0]}
```

The first object is `ResetRequest` and the second is an abbreviated `StateResponse`; protobuf JSON encodes `uint64` values as strings. A deterministic step request is `{"steps":200}` and returns another `StateResponse`. To resume a live episode, send `{"paused":false}`. `State` and `Score` use empty requests (`{}`). A score example is `{"navigation":true,"grasp":false,"placement":false,"collisions":0,"elapsedSimS":8.4}`; interpret it under the selected scene's rules in the [catalog](../benchmarks/Robocasa/README.md).

A reset failure sets `ok` false and supplies `error`, for example `{"ok":false,"error":"scene not loaded"}`. `Step` rejects more than 100,000 steps with gRPC `INVALID_ARGUMENT` and manual stepping while running with `FAILED_PRECONDITION`. Connection or server faults also surface as gRPC status errors. A score is meaningful only after a successful reset and an explicitly bounded episode.

**Related:** [Simulator RPC](simulator.md) · [Design](../architecture.md)
