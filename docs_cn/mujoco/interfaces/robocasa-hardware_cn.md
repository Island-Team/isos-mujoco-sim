# RoboCasa 机器人硬件核心接口

[RoboCasa 基准](../benchmarks/Robocasa/README_cn.md) · [English](../../../docs/mujoco/interfaces/robocasa-hardware.md)

Python `robocasa_core.Hardware` 管理调用方传入的固定版本 RoboCasa PandaOmron Gym 环境。目录使用 `robocasa` 层；组表示硬件功能，节点是稳定的可绑定端点。调用方负责创建环境、串行调用并关闭核心。此进程内接口没有认证或传输层。EOS 和 IsOS 包装尚未实现。

| 组 / 节点 ID | 命令 | 观测 |
| --- | --- | --- |
| `arm/right-arm` | 位置和旋转增量，各为 3 个 `[-1,1]` 归一化值 | 相对底座的末端位置和四元数 |
| `gripper/right-gripper` | 闭合：`0` 张开，`1` 闭合 | 夹爪关节位置 |
| `base/mobile-base` | 3 个 `[-1,1]` 归一化底盘运动值 | 底盘位置和四元数 |
| `torso/torso` | 1 个 `[-1,1]` 归一化躯干运动值 | 固定版本包装器不提供 |
| `camera/agentview-left`、`camera/agentview-right`、`camera/eye-in-hand` | 无 | RGB8 图像，高 × 宽 × 3 |

完整 ID 在每行前加 `robocasa/`。位置和旋转命令是控制器输入，不是米或弧度；由上游控制器解释。观测位置单位为米，姿态采用上游包装器的四元数顺序。核心构造时检查动作形状和必需观测键，不兼容的机器人配置会被拒绝。相机尺寸来自环境。目录描述此固定配置支持的端点；缺少必需端点时构造失败。

控制前调用 `reset(seed)`。`command_arm(position, rotation)`、`command_gripper(close)`、`command_base(motion)`、`command_torso(motion)` 和 `set_control_mode(mode)` 将值排队至一次 `step()`。控制模式为 `0` 或 `1`，原样传给 RoboCasa 的 `action.control_mode`；固定版本包装器将其映射到两种底盘模式。一步同时提交五个上游动作字段。未设置的运动为零；未设置的夹爪为张开，模式为 `0`。环境步进失败时队列也会先清空；再次控制前必须重置。`observe()` 和步进结果只包含复制的机器人状态和相机数组，不包含任务文字、奖励、成功结果或场景物体状态。`close()` 关闭环境，之后不能控制。

形状错误、非有限或越界运动值、非二值夹爪或模式、缺失观测以及重置前或关闭后调用都会抛出 `HardwareError`。RoboCasa 报告回合终止或截断时，最后一步仍返回机器人观测，后续控制必须先重置。上游环境异常会继续抛出，并使核心在重置前保持故障状态。此进程内接口没有截止时间、异步命令或物理停止保证；紧急停止策略应由所属控制层提供。

```python
hardware = Hardware(env)
hardware.reset(42)
hardware.command_arm([0, 0, 0], [0, 0, 0])
hardware.command_gripper(0)
robot = hardware.step()
frame = robot["eye-in-hand"]
hardware.close()
```

**目标设计 — 尚未实现：** RoboCasa 进程节点将管理环境生命周期，EOS 硬件节点通过受控适配器绑定稳定目录 ID。IsOS 包和图组合随后对接该进程契约。当前 C++ 场景目录及 EOS 模拟器 protobuf 不描述此核心。

保存命令及检查指定本地回合时，使用[记录与重放接口](robocasa-record_cn.md)。验证：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v` 执行桩单元测试；`PYTHONPATH=. .local/robocasa-venv/bin/python tests/robocasareplay.py` 执行两次固定种子的 `CloseFridge` 硬件重放。
