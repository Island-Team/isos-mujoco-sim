# MuJoCo core

[中文](../../../docs_cn/mujoco/core/README_cn.md) · [MuJoCo guide](../README.md) · [Public interfaces](../interfaces/README.md)

These pages explain the simulator implementation, benchmark behavior, and EOS integration. The [interfaces](../interfaces/README.md) own public fields and compatibility rules; the [start guides](../start/README.md) give the operating sequence.

| Page | Scope |
| --- | --- |
| [Architecture](architecture.md) | Source ownership, runtime data flow, and verification evidence. |
| [Simulator](mujoco.md) | Scene loading, physics, rendering, and runtime service design. |
| [RoboCasa benchmark](benchmark.md) | Active task, provenance, scoring, and limits. |
| [EOS process](eos/process/mujoco.md) | Historical process node declaration. |
| [EOS hardware](eos/hardware/camera.md) | Camera, base, manipulator, gripper, and torso design pages. |
| [Interaction roles](interaction-nodes.md) | Target graph route design. |

## Documentation verification

On 2026-11-16, `python3 tests/fixtures/strict_socket/check.py` passed 31 R05 cases and `python3 tests/fixtures/strict_stop_lane/check.py` passed 48 R06 cases after the layout change. A local relative Markdown link scan found zero missing targets. Complete check output is under ignored `data/test/20261116-docs-isos-layout/`.
