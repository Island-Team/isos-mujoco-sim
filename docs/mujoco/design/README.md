# Node, layer, and group design

[中文](../../../docs_cn/mujoco/design/README_cn.md) · [Architecture](../architecture.md) · [Usage](../usage/README.md)

This directory describes the MuJoCo package's EOS type placement and the behavior of its process node. The [layer catalog](layers/README.md) leads to the [process layer](layers/process/README.md), [MuJoCo group](layers/process/groups/mujoco/README.md), and [simulator node](layers/process/groups/mujoco/nodes/simulator.md). The node page describes lifecycle and state transitions; the [package contract](../interfaces/package.md) and [socket contract](../interfaces/socket.md) own exact fields and wire behavior.

Cross-component activation, command ordering, and qualification live in [architecture](../architecture.md). Operator steps live in the [dev](../usage/dev.md) and [IsOS package](../usage/isos-pkg.md) guides.
