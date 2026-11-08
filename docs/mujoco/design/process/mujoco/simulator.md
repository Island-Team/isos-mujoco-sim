# MuJoCo simulator process node

[中文](../../../../../docs_cn/mujoco/design/process/mujoco/simulator_cn.md) · [Catalog](../../README.md) · [Package fields](../../../interfaces/package.md) · [Socket contract](../../../interfaces/socket.md)

**Current package type.** The published `0.1.1` release and local `0.1.2` candidate use this process placement. Placement is `core=eos`, `layer=process`, `group=mujoco`; the new registered type uses `@v0.1`, with the `@v1.0` alias retained for legacy reads. R05 strict child readiness passed scoped cross-owner qualification; the MuJoCo R06 stop lane merged and scoped managed movement/stop replay passed; broader R06 qualification remains open. Registered `NodeType.description`: “Starts one verified MuJoCo scene as an EOS-owned simulator child and supplies only the graph-declared simulated devices.” The instance `description` records this deployment's purpose and remains separate. The exact field types, defaults, validation and compatibility belong to [the package descriptor](../../../interfaces/package.md), IsOS's graph contract and EOS's node-profile contract.

## First-use behavior

1. IsOS verifies the exact package receipt, executable, scene assets, device map and external MuJoCo library. It presents stable scene/device options with descriptions and unavailable reasons; the operator selects IDs rather than paths.
2. IsOS validates the `sim-hardware` preview and applies a revision. EOS reads the graph without mutation, resolves its compiled `mujoco-v2` adapter and starts the verified simulator as its direct child.
3. The node becomes ready only after socket health and declared device checks. Camera, base and manipulator adapters are separate EOS node instances; this process node cannot bypass their dispatcher admission.
4. On failure, retain the unavailable node and reason in status. Open logs at this run's first ready/failure event, then filter by node path and correlation ID.
5. On shutdown, EOS closes admission and requests the R06 physical stop before terminating and reaping the child. It records an unacknowledged stop as an unknown outcome; the scoped R06 replay confirmed separate base and arm acknowledgments.

## Algorithm and compatibility

Package selection is exact receipt → digest/path verification → descriptor validation → option resolution → graph validation → child spawn → socket health → adapter activation. A scene change requires a new graph revision and child restart. The socket `2.0.0`, descriptor `2.0.0`, release schema v4 and `mujoco-v2` adapter name are independent compatibility identities. Unknown future graph or type versions fail with a version diagnostic; old saved graphs are not rewritten until explicit revision-checked migration. See [integration design](../../../architecture.md) for command deduplication and stop ordering.
