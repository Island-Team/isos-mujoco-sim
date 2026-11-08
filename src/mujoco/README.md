# MuJoCo core

`mujoco_core` owns scene loading, deterministic reset, physics, rendering, and scoring. Its public C++ interface is `engine.h`. It has no EOS protobuf or IsOS package dependency. `mujoco-core` is a direct development executable: it loads a scene, resets to a seed, advances a chosen number of physics steps, and prints the resulting sequence and simulation time.

The [simulator overview](../../docs/mujoco/README.md) describes scene behavior and verification. Run `build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20` after building.
