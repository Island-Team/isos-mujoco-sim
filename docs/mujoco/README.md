# MuJoCo benchmark package

The simulator loads one scene at process startup, executes robot commands and renders observations for EOS, and reports evaluation truth through a separate private service. EOS remains independent of MuJoCo. EGIA and other agents interact through EOS discovery, resources, and primitives; the evaluator controls episodes and reads scores.

The active benchmark is upstream RoboCasa `CloseFridge`; the former pick-and-place and navigation scenes remain as C++ simulator compatibility fixtures. Start with the [first-run guide](usage/start.md), then use the [benchmark method](benchmarks.md) and [documentation map](doc_index.md) for scope and verification.

The [MuJoCo core](../../src/mujoco/README.md) owns scene loading, physics, rendering, and scoring. The [IsOS package wrapper](../../src/isos/README.md) owns the EOS-facing process and socket endpoints. The core can be run directly for development with `build/mujoco-core`; the packaged entrypoint remains `build/eos-mujoco-sim`.
