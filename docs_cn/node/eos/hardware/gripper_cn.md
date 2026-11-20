<a id="eos-夹爪节点"></a>
# hardware/gripper 组

[接口目录](../../README_cn.md) · [设计](../../../core/adapter_cn.md) · [运行控制](../../../core/adapter_cn.md) · [English](../../../../docs/node/eos/hardware/gripper.md)

`0.2.8` 候选在 `eos/hardware/gripper` 注册 `eos.hardware.gripper.binary@v0.2`。原生 `gripper` 绑定 `gripper-0`；RoboCasa `hand` 绑定 `robocasa/gripper/right-gripper`。

<a id="端口与数值"></a>
### 端口与数值

可选 `command` 输入使用 `gripper_binary_command@v0.2`，恰好一个必需字段 `action`，值为字符串 `open` 或 `close`。标准适配器边界拒绝布尔值及旧 `close` 字段。端口契约为 `{owner:"isos",id:"gripper_binary_command@v0.2",version:"1.0"}`。

`observation` 输出使用 `gripper_state@v0.2`：采样及具有有限数值和明确单位的具名通道。原生使用仿真时钟，报告以百分比计的 `opening`；RoboCasa 使用单调时钟，报告以米计的 `left_finger` 和 `right_finger` 滑动关节位置。回执或开度均不能证明抓取成功。观测上限为 50 Hz 和 65,536 字节。

<a id="命令载荷示例"></a>
### 命令载荷示例

```json
{
  "action": "close"
}
```

<a id="准入生命周期与兼容性"></a>
### 准入、生命周期与兼容性

EOS 校验运行、精确软件包及所选部件，再由 Dispatcher 放行类型化命令。插件再次验证标准载荷并映射到私有服务线路，不转发额外字段。坐标系、关节顺序、模式或载荷错误，以及服务不可用，都不会产生成功回执。命令在载荷之外携带所有者提供的运行／修订与持久身份。Stop 关闭准入并要求整机证明；超时或缺失证明仍为未知。

截至 `0.2.7` 的精确版本保留旧插件字段、契约元数据及 `state` 输出。`0.2.8` 候选使用新的软件包固定版本；保存图必须明确选择其 `observation` 输出。运行时所有者为旧元数据保留旧转换。构建或验证候选不等于发布或安装发行版。

## 载体、设置与可用性

所有端口使用 `in_process` 载体。适配器设置 `service_instance` 与 `device_id` 是必需字符串，必须匹配已验证包及所选设备，不会默认切换到其他服务。相机的尺寸、频率与限制见上文；执行器限值来自所选注册 profile。缺失设置、未知类型或不可用服务阻止准入或就绪。

节点类型不声明额外的 authored 设置。预设的硬件 profile 约束控制限值；适配器绑定不会替代 Dispatcher 准入。
