<a id="eos-底盘节点"></a>
# hardware/base 组

[接口目录](../../README_cn.md) · [设计](../../../core/adapter_cn.md) · [运行控制](../../../core/adapter_cn.md) · [English](../../../../docs/node/eos/hardware/base.md)

`0.2.8` 候选在 `eos/hardware/base` 注册原生 `eos.hardware.base.device@v0.2` 与 RoboCasa `eos.hardware.base.normalized_axes@v0.2` 类型。原生预设将 `drive` 绑定到 `base-0`；RoboCasa 预设将 `mobile` 绑定到 `robocasa/base/mobile-base`。

<a id="端口与数值"></a>
### 端口与数值

两个节点都有可选的进程内 `command` 输入及 `observation` 输出。原生输入使用 `base_twist_command@v0.2`，RoboCasa 输入使用 `normalized_axes_command@v0.2`。命令端口采用 `{owner:"isos",id:<data_type>,version:"1.0"}`，Dispatcher 的具名端口继承完整输入契约。

| 原生字段 | 类型／单位 | 含义与验证 |
| --- | --- | --- |
| `frame_id` | 字符串／— | 必需为 `base_link`，匹配所选配置的机体命令坐标系。 |
| `vx_m_s`、`vy_m_s` | 有限数值／m/s | 必需机体坐标系速度；向量模须符合 `max_linear_m_s`（预设为 1.0）。 |
| `yaw_rate_rad_s` | 有限数值／rad/s | 必需偏航速率；预设绝对值不超过 1.5。 |
| `lease_ms` | 整数／ms | 必需为 1–1000，且不超过所选运动限制。原生服务按仿真时间使运动到期。 |

RoboCasa 必须包含且仅包含 `axes:{x,y,yaw}`，数值有限且位于 `[-1,1]`，并提供从 1 到所选限制（至多 1000）的整数 `lease_ms`。这些是无量纲控制器输入。每条命令执行一个同步 Gym 步。租期必须覆盖所选环境的实际控制步长；过短时在运动前拒绝。这是仿真时间界限，不声明自主运动循环或墙钟看门狗。

原生观测使用 `base_state@v0.2`：世界坐标系平面位姿、机体坐标系线速度及偏航速率。RoboCasa 观测使用 `pose_state@v0.2`，包含世界坐标系位置及单位 `xyzw` 四元数。采样标识源时间、时钟、序号和坐标系；原生时钟为 `simulation`，RoboCasa 为 `monotonic`。节点不从其他表示伪造速度。

<a id="命令载荷示例"></a>
### 命令载荷示例

```json
{
  "frame_id": "base_link",
  "vx_m_s": 0.2,
  "vy_m_s": 0.0,
  "yaw_rate_rad_s": 0.05,
  "lease_ms": 100
}
```

<a id="准入生命周期与兼容性"></a>
### 准入、生命周期与兼容性

EOS 校验运行、精确软件包及所选部件，再由 Dispatcher 放行类型化命令。插件再次验证标准载荷并映射到私有服务线路，不转发额外字段。坐标系、关节顺序、模式或载荷错误，以及服务不可用，都不会产生成功回执。命令在载荷之外携带所有者提供的运行／修订与持久身份。Stop 关闭准入并要求整机证明；超时或缺失证明仍为未知。

截至 `0.2.7` 的精确版本保留旧插件字段、契约元数据及 `state` 输出。`0.2.8` 候选使用新的软件包固定版本；保存图必须明确选择其 `observation` 输出。运行时所有者为旧元数据保留旧转换。构建或验证候选不等于发布或安装发行版。

## 载体、设置与可用性

所有端口使用 `in_process` 载体。适配器设置 `service_instance` 与 `device_id` 是必需字符串，必须匹配已验证包及所选设备，不会默认切换到其他服务。相机的尺寸、频率与限制见上文；执行器限值来自所选注册 profile。缺失设置、未知类型或不可用服务阻止准入或就绪。

节点类型不声明额外的 authored 设置。预设的硬件 profile 约束控制限值；适配器绑定不会替代 Dispatcher 准入。 预设 observation 上限为 50 Hz、65,536 字节；这是准入上限，不保证实时采样频率。
