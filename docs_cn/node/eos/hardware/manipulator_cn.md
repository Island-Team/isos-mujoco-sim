<a id="eos-机械臂节点"></a>
# hardware/manipulator 组

[接口目录](../../README_cn.md) · [设计](../../../core/adapter_cn.md) · [运行控制](../../../core/adapter_cn.md) · [English](../../../../docs/node/eos/hardware/manipulator.md)

`0.2.8` 候选在 `eos/hardware/manipulator` 注册原生关节位置和 RoboCasa 归一化笛卡尔机械臂。原生 `arm` 将 `eos.hardware.manipulator.device@v0.2` 绑定到 `arm-0`；RoboCasa `right-arm` 将 `eos.hardware.manipulator.normalized_cartesian@v0.2` 绑定到 `robocasa/arm/right-arm`。

<a id="端口与数值"></a>
### 端口与数值

原生节点包含 `command: joint_position_command@v0.2` 和 `observation: joint_state@v0.2`。命令必须且只能包含 `joint_names` 与 `position_rad`：按所选配置顺序排列的六个唯一名称，以及六个有限绝对位置（弧度）。适配器检查配置中的绝对位置限制（3.14 rad），服务检查场景限位。候选不声明 `max_joint_speed_rad_s`；其位置控制器没有经过资格验证的速度保证。状态包含相同关节名称、位置、速度及 `robot_base` 中使用仿真时钟的采样。

RoboCasa 节点包含 `command: normalized_axes_command@v0.2`、`mode: control_mode_command@v0.2` 和 `observation: pose_state@v0.2`。命令要求恰好六个 `axes` 名称（`dx`、`dy`、`dz`、`droll`、`dpitch`、`dyaw`）、`[-1,1]` 内有限数值及 1–1000 且不超过所选限制的整数 `lease_ms`。这些是无量纲控制器输入。模式载荷恰好为 `{"mode":"0"}` 或 `{"mode":"1"}`。每条命令执行一个同步 Gym 步。归一化命令的租期必须覆盖实际控制步长，否则在运动前拒绝；这约束仿真时间，不承诺墙钟看门狗。观测报告 `robot_base` 中的末端位置和单位 `xyzw` 四元数，采样使用单调时钟，不伪造关节状态。

命令端口采用 `{owner:"isos",id:<data_type>,version:"1.0"}`。部件 Dispatcher 为每个部件选择一个硬件输入。为此机械臂选择 `command` 或 `mode`；对同一硬件重复绑定不会产生两条受支持路线。

<a id="命令载荷示例"></a>
### 命令载荷示例

```json
{
  "joint_names": [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint"
  ],
  "position_rad": [
    0.1,
    -0.2,
    0.1,
    0.0,
    0.0,
    0.0
  ]
}
```

<a id="准入生命周期与兼容性"></a>
### 准入、生命周期与兼容性

EOS 校验运行、精确软件包及所选部件，再由 Dispatcher 放行类型化命令。插件再次验证标准载荷并映射到私有服务线路，不转发额外字段。坐标系、关节顺序、模式或载荷错误，以及服务不可用，都不会产生成功回执。命令在载荷之外携带所有者提供的运行／修订与持久身份。Stop 关闭准入并要求整机证明；超时或缺失证明仍为未知。

截至 `0.2.7` 的精确版本保留旧插件字段、契约元数据及 `state` 输出。`0.2.8` 候选使用新的软件包固定版本；保存图必须明确选择其 `observation` 输出。运行时所有者为旧元数据保留旧转换。构建或验证候选不等于发布或安装发行版。

## 载体、设置与可用性

所有端口使用 `in_process` 载体。适配器设置 `service_instance` 与 `device_id` 是必需字符串，必须匹配已验证包及所选设备，不会默认切换到其他服务。相机的尺寸、频率与限制见上文；执行器限值来自所选注册 profile。缺失设置、未知类型或不可用服务阻止准入或就绪。

节点类型不声明额外的 authored 设置。预设的硬件 profile 约束控制限值；适配器绑定不会替代 Dispatcher 准入。 预设 observation 上限为 50 Hz、65,536 字节；这是准入上限，不保证实时采样频率。
