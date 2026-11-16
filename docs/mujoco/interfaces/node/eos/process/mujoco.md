# Historical EOS MuJoCo process node

[Interface index](../../../README.md) · [Design](../../../../core/eos/process/mujoco.md) · [Package declaration](../../../package.md) · [Runtime control](../../../control.md) · [中文](../../../../../../docs_cn/mujoco/interfaces/node/eos/process/mujoco_cn.md)

`eos.process.mujoco.simulator@v0.2` belongs to the historical `0.2.0` `sim-hardware` set. It starts one verified MuJoCo scene as an EOS-owned child and provides the private service used by that set's JPEG camera. It is a process lifecycle node, not an agent control or observation port. Current full hardware presets contain device nodes and let IsOS start their selected runtime service implicitly; they do not include this process node.

## Placement and settings

The node is `core:eos`, `layer:process`, `group:mujoco`, `kind:software`, with `process` lifecycle and capability. The set includes this node and `native/front` camera. The process type itself has no input or output ports.

| Setting | Type / unit | What the operator selects | Validation and default |
| --- | --- | --- | --- |
| `scene` | string / stable ID | `pick-place` or `navigation` from the verified package catalog | Required; no resolved path in the graph; default in the set is `pick-place`. |
| `socket` | string / private Unix path | EOS-owner endpoint for the child | Required; no type default. |
| `env` | string table / — | Child environment references | Optional; empty when absent. |
| `start_timeout_ms` | positive integer / ms | Time allowed for child readiness | Optional in the type; EOS policy applies if absent. |

IsOS verifies the exact package receipt, scene XML digest, selected scene ID, and host MuJoCo library. EOS resolves `bin/eos-mujoco-sim` and the scene path from that verified package, then launches `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}` with its `mujoco-v2` lifecycle adapter. The operator does not write an executable path or benchmark socket into the node.

## Readiness and Stop

The child must open its owner-only socket and pass strict health for the graph-declared devices before EOS publishes readiness. A missing scene, wrong library, unhealthy camera render, incompatible protocol, or child exit leaves the node unavailable with a reason; socket existence alone is insufficient. EOS closes command admission before Stop, asks the companion stop lane for whole-robot proof, records an unknown outcome if proof is missing, and reaps the child. A scene change requires a new graph revision and child restart. The simulator cannot expose benchmark reset or score through this managed node. See the [runtime control contract](../../../control.md) for frames, errors, and deadlines.
