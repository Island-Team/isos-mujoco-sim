# RoboCasa 机器人硬件核心接口

[RoboCasa 基准](../benchmarks/Robocasa/README_cn.md) · [English](../../../docs/mujoco/interfaces/robocasa.md)

Python `robocasa_core.Hardware` 管理调用方传入的固定版本 RoboCasa PandaOmron Gym 环境。目录使用 `robocasa` 层；组表示硬件功能，节点是稳定的可绑定端点。调用方负责创建环境、串行调用并关闭核心。此进程内 API 没有认证或传输。打包后的 worker 经私有服务端点提供硬件；调用方及准入规则见[控制契约](control_cn.md)。

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

`control(device_id, payload)` 是通用的进程内控制入口，接收完整的 `robocasa/...` 设备 ID 和该设备自己的字段：机械臂的 `position` 与 `rotation`（或 `mode`）、夹爪的 `close`、底盘或躯干的 `motion`。它只读取支持的字段并忽略无关键。没有可用控制字段、机械臂字段不完整、设备未知或只读时抛出 `HardwareError`；支持字段的非法值仍按原有规则拒绝。`status(device_id)` 仅返回所选设备已测得字段的副本。固定版本包装器没有躯干测量，因此躯干状态报告不可用。相机状态返回所选 RGB8 图像；相机不支持控制。原有专用命令方法和 `observe()` 仍可使用。

```python
hardware = Hardware(env)
hardware.reset(42)
hardware.control("robocasa/arm/right-arm", {"position": [0, 0, 0], "rotation": [0, 0, 0]})
hardware.control("robocasa/gripper/right-gripper", {"close": 0})
hardware.step()
frame = hardware.status("robocasa/camera/eye-in-hand")["eye-in-hand"]
hardware.close()
```

本包提供由 IsOS 管理的隔离 RoboCasa worker 运行服务。EOS 硬件适配器通过受控服务端点绑定已声明的设备 ID。此进程内 `Hardware` API 仍用于本地测试；其 reset 和 step 不是代理接口。C++ 场景目录及 EOS 模拟器 protobuf 不描述 RoboCasa。

保存命令及检查指定本地回合时，使用[记录与重放接口](record_cn.md)。验证：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v` 执行桩单元测试；`PYTHONPATH=. .local/robocasa-venv/bin/python tests/robocasareplay.py` 执行两次固定种子的 `CloseFridge` 硬件重放。
