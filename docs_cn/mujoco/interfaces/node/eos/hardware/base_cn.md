# EOS 底盘节点

[接口目录](../../../README_cn.md) · [设计](../../../../core/eos/hardware/base_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/hardware/base.md)

底盘节点代表一个模拟移动底盘。**原生机器人**预设提供速度控制及平面状态；**RoboCasa 机器人**预设提供归一化控制轴及世界坐标位姿。操作员在 IsOS 选择预设和服务配置；健康检查和 Dispatcher 准入通过后，代理只看到 EOS 公布的能力。

| 预设 / 节点引用 | 类型与绑定设备 | 能做什么 | 报告什么 |
| --- | --- | --- | --- |
| `native/drive` | `eos.hardware.base.device@v0.2` → `base-0` | `body_velocity`：有租期的有界平面速度 | `base_state@v0.2`：x/y（m）、偏航角（rad）、x/y 速度（m/s）及偏航角速度（rad/s） |
| `robocasa/mobile` | `eos.hardware.base.normalized_axes@v0.2` → `robocasa/base/mobile-base` | `normalized_axes`：x、y、yaw 控制器输入 | `pose_state@v0.2`：世界坐标位置（m）及 `xyzw` 四元数 |

## 端口和值

两种类型都有名为 `command` 的可选进程内事件输入和名为 `state` 的可选事件输出。原生输入类型是 `base_twist_command@v0.2`；`payload` 含有限值 `linear_x_m_s`、`linear_y_m_s`（均为 `[-1,1]` m/s）、`angular_z_rad_s`（`[-1.5,1.5]` rad/s）和正数 `valid_for_ms`（引擎上限 5000 ms）。预设声明 `max_velocity_lease_ms:1000`，所以 EOS 采用更严格的租期。租期届满后模拟器停止底盘。原生 `state` 是所选场景快照，`sample.clock:"simulation"`。

RoboCasa 输入类型为 `normalized_axes_command@v0.2`；`payload.axes` 恰好包含 `x`、`y`、`yaw`，每个都是 `[-1,1]` 内的有限数。这些是控制器输入，不是 m/s 或 rad/s。每条准入命令令 worker 执行一个 Gym 步。位姿包含 `sample.clock:"monotonic"`、`sample.frame_id:"world"`、`position_m:[x,y,z]` 和 `orientation_xyzw:[x,y,z,w]`；不声称测得底盘速度。两种预设均声明最大 50 Hz 观察频率及 65,536 字节状态负载。

EOS 准入后的 RoboCasa 命令示例：

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "move-18",
  "port": "command",
  "payload": {
    "axes": {
      "x": 0.2,
      "y": 0.0,
      "yaw": -0.1
    }
  }
}
```

EOS 提供运行/修订屏障和命令标识；代理不直接调用插件或服务套接字。适配器在 `command_result` 发出确认，并在 EOS 请求时通过 `state` 发出观察。[运行控制契约](../../../control_cn.md)定义准确服务线协议与错误码。

## 准入、生命周期及失败

适配器用经过验证的 `service_instance`（`native` 或 `robocasa`）和准确 `device_id` 绑定节点，均无后备值。IsOS 配置服务，EOS 检查健康并经 Dispatcher 准入，再由适配器发送命令。原生服务要求当前代际和停止 epoch。同一服务代际内重复的命令 ID 不会再次执行动作。停止时 EOS 关闭准入，要求包含底盘、机械臂和夹爪的全机器人证明；RoboCasa 还要求躯干证明。证明缺失或失败时结果为 `unknown`。过期运行、错误设备、无效负载、服务不可用或步进失败时不伪造状态，EOS 保持节点不可用或报告命令失败。新 Run 建立新服务代际。
