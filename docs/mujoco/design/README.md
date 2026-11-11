# Node, layer, and group design

[中文](../../../docs_cn/mujoco/design/README_cn.md) · [Architecture](../architecture.md) · [Usage](../usage/README.md)

This package contributes one EOS process type: **EOS core → process layer → MuJoCo group → simulator node**. The [process layer](process.md) and [MuJoCo group](process/mujoco.md) lead to the [simulator node](process/mujoco/simulator.md), which describes lifecycle, readiness, and stop behavior. IsOS selects an exact verified package and the scene and device IDs; EOS owns the child process.

The current `sim-hardware` node set combines this package-owned process type with one generic EOS JPEG camera. Base and manipulator remain cataloged resources; managed execution waits for actuator Stop proof. A node set is a previewable installation template, not a runtime type. The graph stores IDs and package pins; IsOS resolves verified paths in generated configuration. See the [package contract](../interfaces/package.md) and [socket contract](../interfaces/socket.md) for exact fields. Operator steps are in the [dev](../usage/dev.md) and [IsOS package](../usage/isos-pkg.md) guides.
