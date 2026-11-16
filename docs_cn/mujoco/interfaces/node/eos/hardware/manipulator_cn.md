# EOS 机械臂节点

[接口目录](../../../README_cn.md) · [设计](../../../../core/eos/hardware/manipulator_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/hardware/manipulator.md)

这两种节点控制机器人手臂。原生预设使用六个 MuJoCo 关节目标；RoboCasa 预设使用六个归一化末端控制轴及独立控制模式输入。两者的命令与观察单位不同，不能互换。

| 预设 / 节点引用 | 类型与设备 | 命令 | 观察 |
| --- | --- | --- | --- |
| `native/arm` | `eos.hardware.manipulator.device@v0.2` → `arm-0` | `joint_positions`：六关节位置（rad） | `joint_state@v0.2`：六个名称、位置（rad）及速度（rad/s） |
| `robocasa/right-arm` | `eos.hardware.manipulator.normalized_cartesian@v0.2` → `robocasa/arm/right-arm` | `normalized_cartesian`：平移及旋转轴；`mode`：控制模式 | `pose_state@v0.2`：相对 `robot_base` 的末端位姿 |

## 端口和值

原生类型有 `command: joint_position_command@v0.2` 和 `state: joint_state@v0.2`。命令包含选定模型关节范围内的六个有限 `joint_positions_rad` 目标。预设声明 `max_joint_position_rad:3.14` 和 `max_joint_speed_rad_s:1.0`；EOS 先执行准入策略，模拟器再检查场景边界。状态中的关节顺序为 `shoulder_pan_joint`、`shoulder_lift_joint`、`elbow_joint`、`wrist_1_joint`、`wrist_2_joint`、`wrist_3_joint`；采样时钟为 `simulation`。

RoboCasa 类型有 `command: normalized_axes_command@v0.2`、`mode: control_mode_command@v0.2` 和 `state: pose_state@v0.2`。`command` 的 `axes` 恰好包含 `dx`、`dy`、`dz`、`droll`、`dpitch`、`dyaw` 六个有限值，每个在 `[-1,1]`。这些是上游控制器输入，不是米或弧度。`mode` 负载含 `mode:0` 或 `mode:1`，选择固定版本的 RoboCasa 控制模式。每条被接受的输入推进一个 Gym 步。状态包含 `position_m:[x,y,z]`、单位四元数 `orientation_xyzw:[x,y,z,w]`、`sample.frame_id:"robot_base"` 和 `sample.clock:"monotonic"`。此 RoboCasa 类型不输出关节状态。最大观察频率为 50 Hz，负载上限为 65,536 字节。

EOS 准入后的 RoboCasa 手臂命令示例：

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "arm-18",
  "port": "command",
  "payload": {
    "axes": {
      "dx": 0.1,
      "dy": 0.0,
      "dz": 0.0,
      "droll": 0.0,
      "dpitch": 0.0,
      "dyaw": 0.0
    }
  }
}
```

EOS 构造运行屏障及命令标识。适配器在 `command_result` 发出确认，在 `state` 发出请求的状态；代理无法直接访问私有 worker 套接字。

## 准入、生命周期及失败

准确 `service_instance` 与 `device_id` 将节点绑定到已验证预设。EOS 检查健康和 Dispatcher 准入后调用适配器。原生服务检查当前代际及停止 epoch；两种服务都在单个代际内去重命令 ID。无效形状、非有限控制轴、越界目标、错误模式、过期运行/修订或服务失败均拒绝控制。停止时 EOS 关闭准入并要求全机器人证明；即使进程退出，未经证明的机械臂停止仍为 `unknown`。RoboCasa worker 在 Gym 步进失败后进入故障状态，需要新的运行。线协议错误和期限见[运行控制](../../../control_cn.md)。
