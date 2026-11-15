# EOS 硬件节点：torso

[设计](../../../../design/eos/hardware/torso_cn.md) · [包契约](../../../package_cn.md) · [运行控制](../../../control_cn.md)

这些节点由 EOS 拥有，MuJoCo 包提供经过验证的 `isos_node_v2` 适配器。IsOS 验证精确包版本和服务实例后才能启动；EOS 负责准入、运行和停止。

| 类型 ID | 能力 | 输入端口 | 输出端口 | 安全适配器 |
| --- | --- | --- | --- | --- |
| `eos.hardware.torso.normalized_axes@v0.2` | `normalized_axes` | `command: normalized_axes_command@v0.2` | — | `torso_normalized_axes` |

所有端口为进程内事件，端口 `required:false`。命令数据由 EOS 按图声明的类型和 Dispatcher 策略准入；观察值不包含 benchmark 奖励或成功信息。配置字段 `service_instance` 与 `device_id` 是必需的字符串，无默认值，分别选择已验证服务实例及其设备。未知设备、服务、包版本或命令失败时节点不可用；EOS 不重放结果未知的动作。

原生服务使用 JPEG；RoboCasa 服务使用 RGB8。具体负载、取值范围、单位、停止证明、错误码和期限由[运行控制契约](../../../control_cn.md)定义。服务进程终止后，EOS 使端口不可用；重新运行需要新的代际。
