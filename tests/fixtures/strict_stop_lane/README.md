# R06 strict stop lane design fixtures

`cases.json` freezes the [MuJoCo owner socket contract](../../../docs/mujoco/interfaces/socket.md#r06-managed-stop-contract-design-target). It is a design matrix, not a claim that the current C++ server passes. Runtime CTest must exercise every case ID with a controllable engine stub and the real pick-place and navigation scenes where applicable. The harness should record each case's exact result and elapsed monotonic time in `logs/test/<run-id>/`, then an independent reviewer compares it with this matrix.

The `fence` cases require a deterministic barrier at engine command commit, not timing-only sleeps. `stop_result` cases independently inject base and arm failures. `capture` cases block EGL/JPEG after a snapshot to prove the stop path does not need the render lock. `lifecycle` cases verify timeout, crash, force-reap, socket cleanup, and restart without replay of an uncertain old command. EOS owns its Dispatcher fence, outer deadline and stop-before-terminate evidence; IsOS owns reverse dependent process shutdown. Direct-launch cases preserve historical `2.0.0` behavior.

Run `python3 tests/fixtures/strict_stop_lane/check.py` for static fixture and EN/CN contract checks. This does not establish runtime stop safety.
