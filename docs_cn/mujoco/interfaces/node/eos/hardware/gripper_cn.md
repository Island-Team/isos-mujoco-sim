# EOS 夹爪节点

[接口目录](../../../README_cn.md) · [设计](../../../../design/eos/hardware/gripper_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/hardware/gripper.md)

`eos.hardware.gripper.binary@v0.2` 开闭一个模拟夹爪。两种预设使用相同二值命令类型，但观察代表不同物理量。

| 预设 / 节点引用 | 设备 ID | 命令 | 状态 |
| --- | --- | --- | --- |
| `native/gripper` | `gripper-0` | 开闭原生场景夹爪 | `opening` 通道，0–100% |
| `robocasa/hand` | `robocasa/gripper/right-gripper` | 开闭 Panda 夹爪 | `left_finger`、`right_finger` 滑动关节通道，m |

## 端口和值

输入为 `command: gripper_binary_command@v0.2`，`payload.close` 是必需布尔值：`false` 打开，`true` 关闭。输出为 `state: gripper_state@v0.2`；`channels` 数组逐项给出 `name`、数值 `value` 和 `unit`。原生状态使用 `sample.clock:"simulation"`。RoboCasa 使用 `sample.clock:"monotonic"`，报告固定版本 Gym 包装层的两个关节位置。预设声明最大 50 Hz 观察频率和 65,536 字节负载。状态不表示抓取成功，也不识别所持物体。

EOS 发给适配器的准入命令：

```json
{
  "run_id": "run-7",
  "revision": "rev-2",
  "command_id": "grip-18",
  "stop_epoch": "0",
  "port": "command",
  "payload": {
    "close": true
  }
}
```

对于原生节点，`stop_epoch` 是健康检查或先前停止证明的当前令牌。EOS 提供运行屏障及命令 ID，代理不能直接调用私有服务。适配器通过 `command_result` 发出服务确认，并在请求观察时通过 `state` 发出状态。

## 准入、停止及失败

已验证的 `service_instance` 和准确 `device_id` 选择夹爪，均无回退值。EOS 经 Dispatcher 准入动作。原生控制检查代际和停止 epoch；两种服务在单个代际内去重命令 ID。`close` 非布尔、设备错误、运行过期或步进失败时拒绝动作。停止时 EOS 除底盘和机械臂证明外，还要求独立的 `gripper_stop:"stopped"`；RoboCasa 也要求躯干证明。夹爪证明缺失时结果为未知。此节点不能从命令确认推断物理抓取。线协议错误和期限见[运行控制](../../../control_cn.md)。
