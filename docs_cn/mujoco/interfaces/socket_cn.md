# MuJoCo 持有的模拟器套接字契约

[English](../../../docs/mujoco/interfaces/socket.md) · [包描述符](package_cn.md) · [设计](../design_cn.md)

**所有权、标识与状态。** 本包拥有模拟器套接字协议；EOS 拥有客户端适配器和直接子进程生命周期。 现有线协议为 `2.0.0`；它是兼容性标识，不决定包或图的发布版本。模拟器已实现下述分帧 Unix 套接字和操作。对 `node` 的设备身份检查、`command_id` 去重、稳定错误码及有界停止推进属于**尚未实现的目标**。EOS 通过内部 `mujoco-v2` 适配器系列作为唯一机器人侧调用方；EGIA、IsosUI 只调用 EOS。Benchmark RPC 独立且仅供评测器使用。旧 gRPC 模拟器套接字是保留的历史侧链，见英文 [simulator.md](../../../docs/mujoco/interfaces/simulator.md)。

## 帧与通用字段

套接字位于私有运行目录，权限 `0600`。每帧为 `u32_le 元数据字节数 | u32_le 负载字节数 | UTF-8 JSON 元数据 | 二进制负载`；元数据为 `1..65536` 字节，负载为 `0..8388608` 字节。请求不带二进制负载。格式损坏或超限的帧可以直接断开。成功相机响应带 JPEG，其余响应无二进制负载。当前每个连接处理一个请求。目标保持帧格式，只增加语义验证。

**目标设计——尚未实现（R05）：** IsOS 生成配置标识 EOS 管理的后端所用 P01 已验证包程序、场景和已应用图修订。EOS 从这种管理关系推导并传入 `--managed-strict-socket`；人工编写的图没有模式开关。该标志要求 `--v2-socket`，并拒绝 `--socket` 与 `--benchmark-socket`：这个受管理子进程既不能提供历史 `eos.simulator.v1.SimulatorService` 执行器监听器，也不能提供 benchmark 重置/步进监听器；EOS Dispatcher 是唯一执行器路线。独立的可信评测器可在受管理部署之外直接启动模拟器。不带标志的直接启动保留现有 `2.0.0` 帧格式及忽略 `node`、`command_id` 的行为，也保留历史 gRPC 与 benchmark 套接字；它是旧套接字模式，不能满足已应用 IsOS 图的就绪条件。这是启动策略，不是新线协议身份。未来若不兼容地改动帧格式或直接启动默认行为，必须使用新协议身份。

严格模式的成功 `health` 响应包含 `features:["strict-socket-v1"]` 和 `accepted:true`；旧直接模式不包含 `strict-socket-v1`。EOS 必须核对版本、回显的请求 ID、`ok`、`accepted` 和精确特性，之后才能宣告后端或任何 MuJoCo 适配器就绪；仅连接成功不足以证明就绪。特性缺失、畸形或自相矛盾时拒绝就绪，并终止、回收未就绪子进程。所有严格校验和历史监听器关闭前，子进程不得公告此特性。

| 字段 | 类型／单位 | 用途与所有者 | 默认／验证／兼容 |
| --- | --- | --- | --- |
| `version` | 字符串 | 每次请求/响应的模拟器线协议标识 | 必填 `"2.0.0"`；其他值拒绝，现有调用方继续使用此 ID。 |
| `id` | 非空字符串／— | 调用方关联 ID，响应回显 | 必填；严格模式接受 1..128 个 UTF-8 字节，与 EOS Dispatcher ID 一致；旧直接模式保留现有非空字符串行为。 |
| `node` | 非空字符串／模拟器设备 ID | EOS 适配器发送 `adapter.settings.simulator_node`（`cam-0`、`base-0` 或 `arm-0`） | 当前实现忽略；严格模式要求精确匹配所选场景已验证目录中的设备 ID 与操作类别。EOS 发送前另行核对图节点、类别、所选场景和包锁定。 |
| `op` | 枚举字符串 | 请求操作 | 必填；下表列出有效值，未知操作报错。 |
| `command_id` | 非空字符串／— | 运动与停止的 Dispatcher 准入标识 | 当前实现忽略；严格模式要求运动/停止提供 1..128 个 UTF-8 字节，与 EOS Dispatcher ID 一致，按节点去重；健康、观察、拍摄不带此字段。旧直接模式继续忽略。 |
| `ok` | 布尔 | 响应成功状态 | 模拟器返回；false 时包含 `error.message`。 |
| `error.message` | 字符串 | 人可读失败原因 | `ok:false` 时出现；目标增加稳定的 `error.code`，旧读取方仍可读 message。 |
| `error.code` | 字符串枚举／— | 严格模式稳定失败标识 | 有界请求成功解析而返回 `ok:false` 时新增；值与优先顺序见下文。旧读取方仍可使用 `error.message`。 |
| `features` | 字符串数组／— | 健康能力证明 | 严格模式成功 `health` 包含必需成员 `strict-socket-v1`，未来可附加其他特性；旧模式不包含它。EOS 必须精确匹配该成员。 |
| `timestamp_ns` | 有限数／模拟纳秒 | 快照或画面时间 | 响应字段；当前用 JSON 数字，读取方不能假设超过安全范围仍精确。 |
| `sequence` | 非负数／物理步数 | 快照顺序 | 响应字段；同一次模拟器运行中不递减。 |
| `accepted` | 布尔 | 操作级准入/结果 | 健康、运动和停止响应；若 `ok:false`，以失败为准。 |

所有运动输入必须是解析后有限的 JSON 数字。严格模式底盘输入在引擎当前范围内：`linear_x_m_s`、`linear_y_m_s` 为 `[-1,1]`，`angular_z_rad_s` 为 `[-1.5,1.5]`，`valid_for_ms` 为 `(0,5000]`；场景可以进一步收紧。机械臂每个元素必须处于加载模型的对应关节范围内。EOS 调用前检查图身份、设置、设备类别、边界、期限及 Dispatcher 准入；模拟器再次检查实际场景能力。旧读取方忽略新增可选响应字段。目标错误形如 `{"ok":false,"error":{"code":"unsupported_operation","message":"unsupported operation"}}`；旧读取方仍使用 `error.message`。

严格校验顺序为：帧界限/JSON 解析、线协议版本和有界 `id`、已知 `op`、精确 `node` 与类别、必需的 `command_id`、有类型有限数字与场景限制，最后是幂等表和引擎下发。第一处失败决定稳定错误码：`invalid_request`、`unsupported_version`、`unsupported_operation`、`node_mismatch`、`invalid_command_id`、`invalid_movement`、`out_of_range`、`command_id_conflict`、`command_in_progress`、`command_capacity` 或 `device_unavailable`。畸形、截断或超限的帧可直接断开，因为其 `id` 不可信。`ok:false` 始终优先于 `accepted`，不代表物理完成。有界响应回显已解析的请求 `id`，无二进制负载。

严格模式中的运动与 `stop` 在调用引擎前原子保留 `(node,command_id)`。指纹由操作名与规范化有类型值构成：解析为相等 `f64` 值的不同 JSON 数字写法视为相同，包括 `-0` 与 `0`；数组次序有意义。请求 `id` 只用于传输关联，不属于指纹。相同重发以新请求 `id` 回显旧操作结果，不再次下发；同一有效键搭配不同指纹返回 `command_id_conflict`。并发相同重发可在有界期限内等待原请求，或返回 `command_in_progress`，绝不执行两次。已下发但结果不明时，存为不确定状态，绝不报告准入成功。每个键、指纹和终态/不确定结果均保留到子进程代际结束；不能通过按时过期或驱逐使同一子进程内的重发再次执行。运动表上限 65,536 条，另为停止表保留 4,096 条，使运动表已满不能占用停止容量。容量耗尽时下发前返回 `command_capacity` 并报告可处理故障；停止表也耗尽时拒绝新停止身份，EOS 须记录停止结果未知，并按 R06 升级处理。进程内去重不能取代 EOS 持久 Dispatcher 日志：子进程重启后，EOS 绝不自动重试结果不确定的已下发命令。

## 操作

| `op` | 额外请求字段（类型／单位） | 成功字段（类型／单位） | 验证与效果 |
| --- | --- | --- | --- |
| `health` | 无 | `accepted:bool`；严格模式另有 `features:["strict-socket-v1"]` | 报告引擎可用性；严格模式核对 `node` 是所选场景可用设备。EOS 发布就绪前探测每个已声明设备。 |
| `camera_capture` | 无 | `format:"jpeg"`、`rgb_length:u32` 字节、`depth_available:false`、`width_px:u32`、`height_px:u32`、JPEG 负载 | 帧长度等于 `rgb_length`；目标验证相机节点与有界尺寸。 |
| `base_observe` | 无 | `position_m:[f64;2]` m、`linear_velocity_m_s:[f64;2]` m/s、`yaw_rad:f64` rad、`angular_velocity_rad_s:f64` rad/s | 目标验证底盘节点；数值来自一致的引擎快照。 |
| `base_move` | `linear_x_m_s:f64` m/s、`linear_y_m_s:f64` m/s、`angular_z_rad_s:f64` rad/s、`valid_for_ms:f64` ms、`command_id:string` | `accepted:bool` | `valid_for_ms` 在 `(0,5000]`；受场景限制，租期后底盘停止。目标按 ID 去重。 |
| `manipulator_observe` | 无 | `joint_positions_rad:[f64;6]` rad、`joint_velocities_rad_s:[f64;6]` rad/s、`end_position_m:[f64;3]` m、`end_orientation_xyzw:[f64;4]` 单位四元数 | 目标验证机械臂节点；方向顺序为 x,y,z,w。 |
| `manipulator_move` | `joint_positions_rad:[f64;6]` rad、`command_id:string` | `accepted:bool` | 恰好六个有限目标且在场景边界内；目标按 ID 去重。 |
| `stop` | `command_id:string` | `accepted:bool` | 严格模式接受 `node` 为所选场景目录中的底盘或机械臂设备 ID（当前为 `base-0` 或 `arm-0`），并执行现有整机底盘与机械臂停止。R05 对此请求去重；`accepted` 只表示当前引擎调用结果，不是分别完成的物理确认。R06 再实现专用停止通道、有界中断及底盘/机械臂各自确认。 |

严格模式健康证明元数据示例（每段前都要有二进制帧头）：

```json
{"version":"2.0.0","id":"req-health-1","node":"base-0","op":"health"}
```

```json
{"version":"2.0.0","id":"req-health-1","ok":true,"accepted":true,"features":["strict-socket-v1"],"timestamp_ns":100000000,"sequence":50}
```

底盘请求及成功元数据示例：

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

EOS 从 IsOS 获得已验证的程序、场景和套接字，直接启动子进程，等待套接字及健康检查成功，再使声明的适配器就绪。场景缺失、协议不兼容、帧损坏、相机不可用或断线都会使适配器不可用；EOS 不编造观察值。停止时 EOS 阻止新准入，用有界期限向活动执行器发送 stop，确认或记录失败，再终止并回收子进程。模拟器正常退出时移除套接字。同一 `command_id` 的相同传输重发从目标去重存储取得旧结果，不重复运动。EOS 不自动重放结果不确定的已下发命令；它要从新状态核对，或要求一次明确授权的新准入。同一 ID 搭配冲突负载时报错。

**R06 停止调度仍待实现：** move 或 capture 仍在执行时，监听器必须接受第二条连接，解析有界帧并将 `stop` 送到专用控制通道。该通道须使活动运动租期失效，分别返回底盘与机械臂确认或不确定结果；EOS 只能在停止期限后终止、回收子进程。拍摄与运动工作线程须观察取消。每条连接仍只处理一个请求。R05 严格特性并不证明 R06 的停止保证。
