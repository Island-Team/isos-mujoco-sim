# MuJoCo contributed node catalog

[中文](../../../docs_cn/mujoco/catalog/README_cn.md) · [First use](../usage.md) · [Package contract](../interfaces/package.md)

**Target design.** The IsOS catalog exposes the exact verified `island/mujoco-sim@0.1.1` contribution under **EOS core → process layer → MuJoCo group → simulator node**. Start with [the process node](../layers/process/groups/mujoco/nodes/simulator.md), then the package and socket contracts. This package owns that process type and its scene/device option data. Generic camera, base, manipulator, control and gate types remain owned by EOS or IsOS and are composed by the `sim-hardware` node set. A node set is a previewable installation template, not a new runtime type.

The operator installs or links the exact package, previews the node set, chooses scene and device IDs, validates and applies a graph revision, waits for EOS health, then reads the current run's first ready or failure event. The graph stores IDs and package pins; verified paths are resolved by IsOS and passed to EOS as generated config. Direct simulator launch remains documented in [usage](../usage.md) and does not imply an applied graph.
