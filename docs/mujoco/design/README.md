# Node, layer, and group design

[中文](../../../docs_cn/mujoco/design/README_cn.md) · [Architecture](../architecture.md) · [Usage](../start/README.md)

The [MuJoCo core](core/mujoco.md) owns scene and runtime service design. The [EOS process node](eos/process/mujoco.md) records the historical 0.2.0 declaration. Current hardware node designs are grouped under [camera](eos/hardware/camera.md), [base](eos/hardware/base.md), [manipulator](eos/hardware/manipulator.md), [gripper](eos/hardware/gripper.md), and [torso](eos/hardware/torso.md). The [interaction role mapping](interaction-nodes.md) describes a target design for future graph routes. The [interface index](../interfaces/README.md) owns exact fields.
