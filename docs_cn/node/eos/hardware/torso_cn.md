<a id="eos-躯干节点"></a>
# hardware/torso 组

[接口目录](../../README_cn.md) · [设计](../../../core/adapter_cn.md) · [运行控制](../../../core/adapter_cn.md) · [English](../../../../docs/node/eos/hardware/torso.md)

`0.2.8` 候选在 `eos/hardware/torso` 注册 `eos.hardware.torso.normalized_axes@v0.2`。仅 RoboCasa 提供此设备：`lift` 绑定 `robocasa/torso/torso`。

<a id="端口与命令"></a>
### 端口与命令

可选 `command` 输入使用 `normalized_axes_command@v0.2`。载荷必须且只能包含 `axes` 和 `lease_ms`。轴对象恰好包含一个 `[-1,1]` 内的有限 `lift`；租期为从 1 到所选限制（至多 1000 ms）的整数。没有默认值，未知字段被拒绝。这些是无量纲控制器输入。一条获准命令执行一个同步 Gym 步。租期必须覆盖实际控制步长，否则在运动前拒绝；这约束仿真时间，不声明自主运动或墙钟看门狗。端口契约为 `{owner:"isos",id:"normalized_axes_command@v0.2",version:"1.0"}`。

此节点没有观测端口，不伪造躯干位置。私有 `command_result` 回执在图路由之外返回所有者。

<a id="命令载荷示例"></a>
### 命令载荷示例

```json
{
  "axes": {
    "lift": 0.25
  },
  "lease_ms": 100
}
```

<a id="准入生命周期与兼容性"></a>
### 准入、生命周期与兼容性

EOS 校验运行、精确软件包及所选部件，再由 Dispatcher 放行类型化命令。插件再次验证标准载荷并映射到私有服务线路，不转发额外字段。坐标系、关节顺序、模式或载荷错误，以及服务不可用，都不会产生成功回执。命令在载荷之外携带所有者提供的运行／修订与持久身份。Stop 关闭准入并要求整机证明；超时或缺失证明仍为未知。

截至 `0.2.7` 的精确版本保留旧插件字段、契约元数据及 `state` 输出。`0.2.8` 候选使用新的软件包固定版本；保存图必须明确选择其 `observation` 输出。运行时所有者为旧元数据保留旧转换。构建或验证候选不等于发布或安装发行版。

## 载体、设置与可用性

所有端口使用 `in_process` 载体。适配器设置 `service_instance` 与 `device_id` 是必需字符串，必须匹配已验证包及所选设备，不会默认切换到其他服务。相机的尺寸、频率与限制见上文；执行器限值来自所选注册 profile。缺失设置、未知类型或不可用服务阻止准入或就绪。

节点类型不声明额外的 authored 设置。预设的硬件 profile 约束控制限值；适配器绑定不会替代 Dispatcher 准入。
