# EOS 持有的模拟器套接字契约

[English](../../../docs/mujoco/interfaces/socket.md) · [包描述符](package_cn.md) · [设计](../design_cn.md)

**标识与状态。** 现有线协议为 `2.0.0`；它是兼容性标识，不决定包或图的发布版本。模拟器已实现下述分帧 Unix 套接字和操作。对 `node` 的设备身份检查、`command_id` 去重、稳定错误码及有界停止推进属于**尚未实现的目标**。EOS 通过内部 `mujoco-v2` 适配器系列作为唯一机器人侧调用方；EGIA、IsosUI 只调用 EOS。Benchmark RPC 独立且仅供评测器使用。旧 gRPC 模拟器套接字是保留的历史侧链，见英文 [simulator.md](../../../docs/mujoco/interfaces/simulator.md)。

## 帧与通用字段

套接字位于私有运行目录，权限 `0600`。每帧为 `u32_le 元数据字节数 | u32_le 负载字节数 | UTF-8 JSON 元数据 | 二进制负载`；元数据为 `1..65536` 字节，负载为 `0..8388608` 字节。请求不带二进制负载。格式损坏或超限的帧可以直接断开。成功相机响应带 JPEG，其余响应无二进制负载。当前每个连接处理一个请求。目标保持帧格式，只增加语义验证。

| 字段 | 类型／单位 | 用途与所有者 | 默认／验证／兼容 |
| --- | --- | --- | --- |
| `version` | 字符串 | 每次请求/响应的模拟器线协议标识 | 必填 `"2.0.0"`；其他值拒绝，现有调用方继续使用此 ID。 |
| `id` | 非空字符串 | 调用方关联 ID，响应回显 | 必填；目标限制长度；旧调用方已发送。 |
| `node` | 非空字符串／模拟器设备 ID | EOS 适配器发送 `adapter.settings.simulator_node`（`cam-0`、`base-0` 或 `arm-0`） | 当前实现忽略；目标检查场景设备 ID 与操作种类。EOS 在发送前另行验证图节点到设备的映射。 |
| `op` | 枚举字符串 | 请求操作 | 必填；下表列出有效值，未知操作报错。 |
| `command_id` | 非空字符串 | 运动与停止的 Dispatcher 准入标识 | 当前实现忽略；目标要求运动/停止必须提供，按节点去重并拒绝冲突重放。 |
| `ok` | 布尔 | 响应成功状态 | 模拟器返回；false 时包含 `error.message`。 |
| `error.message` | 字符串 | 人可读失败原因 | `ok:false` 时出现；目标增加稳定的 `error.code`，旧读取方仍可读 message。 |
| `timestamp_ns` | 有限数／模拟纳秒 | 快照或画面时间 | 响应字段；当前用 JSON 数字，读取方不能假设超过安全范围仍精确。 |
| `sequence` | 非负数／物理步数 | 快照顺序 | 响应字段；同一次模拟器运行中不递减。 |
| `accepted` | 布尔 | 操作级准入/结果 | 健康、运动和停止响应；若 `ok:false`，以失败为准。 |

所有运动数字必须有限。EOS 调用前检查图身份、设置、设备类别、边界、期限及 Dispatcher 准入；模拟器再次检查数字边界与实际场景能力。旧读取方忽略新增的可选响应字段。目标错误形如 `{"ok":false,"error":{"code":"unsupported_operation","message":"unsupported operation"}}`；旧读取方仍使用 `error.message`。

## 操作

| `op` | 额外请求字段（类型／单位） | 成功字段（类型／单位） | 验证与效果 |
| --- | --- | --- | --- |
| `health` | 无 | `accepted:bool` | 报告引擎可用性；目标核对 node 归属。 |
| `camera_capture` | 无 | `format:"jpeg"`、`rgb_length:u32` 字节、`depth_available:false`、`width_px:u32`、`height_px:u32`、JPEG 负载 | 帧长度等于 `rgb_length`；目标验证相机节点与有界尺寸。 |
| `base_observe` | 无 | `position_m:[f64;2]` m、`linear_velocity_m_s:[f64;2]` m/s、`yaw_rad:f64` rad、`angular_velocity_rad_s:f64` rad/s | 目标验证底盘节点；数值来自一致的引擎快照。 |
| `base_move` | `linear_x_m_s:f64` m/s、`linear_y_m_s:f64` m/s、`angular_z_rad_s:f64` rad/s、`valid_for_ms:f64` ms、`command_id:string` | `accepted:bool` | `valid_for_ms` 在 `(0,5000]`；受场景限制，租期后底盘停止。目标按 ID 去重。 |
| `manipulator_observe` | 无 | `joint_positions_rad:[f64;6]` rad、`joint_velocities_rad_s:[f64;6]` rad/s、`end_position_m:[f64;3]` m、`end_orientation_xyzw:[f64;4]` 单位四元数 | 目标验证机械臂节点；方向顺序为 x,y,z,w。 |
| `manipulator_move` | `joint_positions_rad:[f64;6]` rad、`command_id:string` | `accepted:bool` | 恰好六个有限目标且在场景边界内；目标按 ID 去重。 |
| `stop` | `command_id:string` | `accepted:bool` | 停止底盘和机械臂；目标实现幂等、有界且可中断进行中工作。 |

底盘请求及成功元数据示例（每段前都要有二进制帧头）：

```json
{"version":"2.0.0","id":"req-17","node":"base-0","op":"base_move","command_id":"cmd-17","linear_x_m_s":0.2,"linear_y_m_s":0.0,"angular_z_rad_s":0.0,"valid_for_ms":200.0}
```

```json
{"version":"2.0.0","id":"req-17","ok":true,"accepted":true,"timestamp_ns":100000000,"sequence":50}
```

目标归属失败示例（当前服务尚未检查 `node`）：

```json
{"version":"2.0.0","id":"req-17","ok":false,"error":{"code":"node_mismatch","message":"node is not the declared base device"},"timestamp_ns":100000000,"sequence":50}
```

## 生命周期与故障

EOS 从 IsOS 获得已验证的程序、场景和套接字，直接启动子进程，等待套接字及健康检查成功，再使声明的适配器就绪。场景缺失、协议不兼容、帧损坏、相机不可用或断线都会使适配器不可用；EOS 不编造观察值。停止时 EOS 阻止新准入，用有界期限向活动执行器发送 stop，确认或记录失败，再终止并回收子进程。模拟器正常退出时移除套接字。同一 `command_id` 的相同传输重发从目标去重存储取得旧结果，不重复运动。EOS 不自动重放结果不确定的已下发命令；它要从新状态核对，或要求一次明确授权的新准入。同一 ID 搭配冲突负载时报错。Stop 可中断其他工作，不得排在无界的拍摄或运动之后。
