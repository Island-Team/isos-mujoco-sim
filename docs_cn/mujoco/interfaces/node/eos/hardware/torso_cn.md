# EOS 躯干节点

[接口目录](../../../README_cn.md) · [设计](../../../../design/eos/hardware/torso_cn.md) · [运行控制](../../../control_cn.md) · [English](../../../../../../docs/mujoco/interfaces/node/eos/hardware/torso.md)

`eos.hardware.torso.normalized_axes@v0.2` 只在 **RoboCasa 机器人**预设中出现，节点引用为 `robocasa/lift`，设备为 `robocasa/torso/torso`。原生机器人预设没有躯干节点。它通过归一化控制器输入指挥 PandaOmron 躯干升降，不发布实测躯干位置。

## 端口和命令

可选进程内事件输入为 `command: normalized_axes_command@v0.2`。`payload.axes` 恰好含一个有限数 `lift`，范围 `[-1,1]`。它是无量纲控制器输入，不是米或 m/s。接受命令后执行一个 Gym 步。预设为准入声明 `max_velocity_lease_ms:1000`。没有 `state` 或其他观察输出，worker 不伪造观察。

```json
{"run_id":"run-7","revision":"rev-2","command_id":"lift-18","port":"command","payload":{"axes":{"lift":0.25}}}
```

EOS 提供运行/修订屏障和命令 ID；适配器发出 `command_result` 确认。代理只能通过 EOS 已准入的能力请求躯干运动，不能从此节点读取位置。其他 RoboCasa 节点仍可提供各自观察。

## 准入、停止及失败

`service_instance:"robocasa"` 与 `device_id:"robocasa/torso/torso"` 绑定准确服务和设备。IsOS 验证包和服务配置；EOS 检查健康与 Dispatcher 准入。控制轴无效、运行过期、服务不可用或 Gym 步进失败时拒绝动作。worker 在单个代际内去重命令 ID，步进失败后进入故障状态。停止隔离后续命令，并要求全机器人证明中的 `torso_stop:"stopped"`；证明缺失时结果未知。私有服务契约见[运行控制](../../../control_cn.md)。
