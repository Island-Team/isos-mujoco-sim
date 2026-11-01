# Documentation map

**First read:** [Build and run](usage.md) → [Core/layer/group/node catalog](catalog/README.md) → [Package and node contract](interfaces/package.md) → [MuJoCo-owned socket contract](interfaces/socket.md) → [Design and algorithms](design.md) → [Implementation TODO](todo.md). Current behavior and target design are labelled in each page.

[中文](../../docs_cn/mujoco/doc_index_cn.md)

- [IsOS managed v2 backend](backend.md): v2 bundle, framed EOS socket, and live GUI.

- [Usage](usage.md): build, direct launcher, scene viewer, current IsOS/EOS v2 graph setup, and verification.
- [Package release](package-release.md): local v2 candidate and historical v1.0.1 package-center publication.
- [Design](design.md): scene selection, engine ownership, EOS and EGIA boundaries, and package activation.
- [Benchmarks](benchmarks.md): task catalog, agent evaluation method, provenance, and adding a scene.
- [EOS simulator interface](interfaces/simulator.md): robot-facing private RPC consumed by EOS.
- [Benchmark interface](interfaces/benchmark.md): evaluator-only reset, clock, ground truth, and scoring RPC.
- [Island conventions](../island/conventions.v1.3.0.md): copied team rules applied by `AGENTS.md`.
