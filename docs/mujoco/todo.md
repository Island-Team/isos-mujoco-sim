# MuJoCo 0.1.1 integration TODO

Track implementation in [MuJoCo package 0.1.1](https://github.com/Island-Team/isos-mujoco-sim/milestone/1), with the shared [M2 verified inputs](https://github.com/Island-Team/Island-eos/milestone/2), [M3 governed execution](https://github.com/Island-Team/Island-eos/milestone/3) and [M5 qualification](https://github.com/Island-Team/Island-eos/milestone/5) gates. The sequence below is the required dependency order.

[中文](../../docs_cn/mujoco/todo_cn.md) · [Design](design.md) · [Socket contract](interfaces/socket.md)

1. Add a nonblank description and selector metadata to the contributed process type and its scene setting. Publish `@v0.1` types only when IsOS/EOS catalog readers accept them; preserve `@v1.0` aliases and the installed schema-v4 package identity. Ensure the descriptor options are derived from verified scene/device assets.
2. Add managed strict-socket launch and health feature confirmation while preserving legacy direct-launch `2.0.0` semantics. In strict mode, enforce socket `node` as a simulator device ID with operation/device matching, and EOS graph-to-device mapping, finite typed inputs, stable additive error codes, and bounded request IDs. Add `(node, command_id)` idempotency with conflicting-replay rejection and bounded retention. Keep framing and wire version `2.0.0` unchanged.
3. Make stop preempt an in-flight move or slow capture, respect a finite deadline, and acknowledge both base and arm; EOS must stop admitted actuators before child termination. Test identical transport retransmission, uncertain-outcome non-replay, duplicate movement, conflicting replay, unsupported node/device, malformed and oversized frames, unavailable GUI, child crash, and cleanup.
4. Emit shared sanitized JSONL startup, readiness, fault and stop events with run/node/correlation IDs. Do not log JPEG frames or secrets. Test rotation/cursor behavior through IsOS and first-failure discovery in the UI.
5. Run `python3 tests/node_contributions.py`, `python3 tests/release.py`, `ctest --test-dir build --output-on-failure`, and IsOS → EOS → MuJoCo → EGIA integration tests for success, failure and safe stop. Save full output under `logs/test/<run-id>/`; record reproducible commands, environment, results and limitations. Only then consider publication of `v0.1.1`; retain historical tags.

The existing C++ simulator is the package implementation and is **not** EOS's unused legacy `src/eos/` runtime. Its current gRPC simulator service remains a legacy compatibility side chain until last-caller review shows it is removable.
