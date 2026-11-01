# MuJoCo simulator process node

[中文](../../../../../../../docs_cn/mujoco/layers/process/groups/mujoco/nodes/simulator_cn.md) · [Catalog](../../../../../catalog/README.md) · [Package fields](../../../../../interfaces/package.md) · [Socket contract](../../../../../interfaces/socket.md)

**0.x target, not yet released.** Placement is `core=eos`, `layer=process`, `group=mujoco`; the new registered type uses `@v0.1`, with the `@v1.0` alias retained for legacy reads. R05 strict child readiness passed scoped cross-owner qualification; R06 physical stop and managed movement remain open. Registered `NodeType.description`: “Starts one verified MuJoCo scene as an EOS-owned simulator child and supplies only the graph-declared simulated devices.” The instance `description` records this deployment's purpose and remains separate. The exact field types, defaults, validation and compatibility belong to [the package descriptor](../../../../../interfaces/package.md), IsOS's graph contract and EOS's node-profile contract.

## First-use behavior

1. IsOS verifies the exact package receipt, executable, scene assets, device map and external MuJoCo library. It presents stable scene/device options with descriptions and unavailable reasons; the operator selects IDs rather than paths.
2. IsOS validates the `sim-hardware` preview and applies a revision. EOS reads the graph without mutation, resolves its compiled `mujoco-v2` adapter and starts the verified simulator as its direct child.
3. The node becomes ready only after socket health and declared device checks. Camera, base and manipulator adapters are separate EOS node instances; this process node cannot bypass their dispatcher admission.
4. On failure, retain the unavailable node and reason in status. Open logs at this run's first ready/failure event, then filter by node path and correlation ID.
5. R06 must close admission and physically stop admitted actuators before terminating and reaping the child. An unacknowledged stop must be recorded as failure, not as successful shutdown; the R05 cleanup replay did not release managed movement.

## Algorithm and compatibility

Package selection is exact receipt → digest/path verification → descriptor validation → option resolution → graph validation → child spawn → socket health → adapter activation. A scene change requires a new graph revision and child restart. The socket `2.0.0`, descriptor `2.0.0`, release schema v4 and `mujoco-v2` adapter name are independent compatibility identities. Unknown future graph or type versions fail with a version diagnostic; old saved graphs are not rewritten until explicit revision-checked migration. See [integration design](../../../../../design.md) for command deduplication and stop ordering.
