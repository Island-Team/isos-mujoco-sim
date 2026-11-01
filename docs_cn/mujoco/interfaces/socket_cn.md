# MuJoCo 持有的模拟器套接字契约

[English](../../../docs/mujoco/interfaces/socket.md) · [包描述符](package_cn.md) · [设计](../design_cn.md)

**所有权、标识与状态。** 本包拥有模拟器套接字协议；EOS 拥有客户端适配器和直接子进程生命周期。 现有线协议为 `2.0.0`；它是兼容性标识，不决定包或图的发布版本。模拟器已实现下述分帧 Unix 套接字和操作。R05 管理模式已实现 `node` 设备身份检查、`command_id` 去重与稳定错误码；R06 已有所有者实现候选；独立审查及集成验收仍未完成。EOS 通过内部 `mujoco-v2` 适配器系列作为唯一机器人侧调用方；EGIA、IsosUI 只调用 EOS。Benchmark RPC 独立且仅供评测器使用。旧 gRPC 模拟器套接字是保留的历史侧链，见英文 [simulator.md](../../../docs/mujoco/interfaces/simulator.md)。

## 帧与通用字段

套接字位于私有运行目录，权限 `0600`。每帧为 `u32_le 元数据字节数 | u32_le 负载字节数 | UTF-8 JSON 元数据 | 二进制负载`；元数据为 `1..65536` 字节，负载为 `0..8388608` 字节。请求不带二进制负载。格式损坏或超限的帧可以直接断开。成功相机响应带 JPEG，其余响应无二进制负载。当前每个连接处理一个请求。严格模式保持帧格式，只增加语义验证。

**R05 管理模式：** IsOS 生成配置标识 EOS 管理的后端所用 P01 已验证包程序、场景和已应用图修订。EOS 从这种管理关系推导并传入 `--managed-strict-socket`；人工编写的图没有模式开关。该标志要求 `--v2-socket`，并拒绝 `--socket` 与 `--benchmark-socket`：这个受管理子进程既不能提供历史 `eos.simulator.v1.SimulatorService` 执行器监听器，也不能提供 benchmark 重置/步进监听器；EOS Dispatcher 是唯一执行器路线。独立的可信评测器可在受管理部署之外直接启动模拟器。不带标志的直接启动保留现有 `2.0.0` 帧格式及忽略 `node`、`command_id` 的行为，也保留历史 gRPC 与 benchmark 套接字；它是旧套接字模式，不能满足已应用 IsOS 图的就绪条件。这是启动策略，不是新线协议身份。未来若不兼容地改动帧格式或直接启动默认行为，必须使用新协议身份。

严格模式的成功 `health` 响应包含 `features:["strict-socket-v1"]` 和 `accepted:true`；旧直接模式不包含 `strict-socket-v1`。相机健康还会尝试真实渲染；EGL 或 JPEG 渲染失败时返回不带该特性的 `device_unavailable`。EOS 必须核对版本、回显的请求 ID、`ok`、`accepted` 和精确特性，之后才能宣告后端或任何 MuJoCo 适配器就绪；仅连接成功不足以证明就绪。特性缺失、畸形或自相矛盾时拒绝就绪，并终止、回收未就绪子进程。所有严格校验和历史监听器关闭前，子进程不得公告此特性。

受管理子进程从包拥有的 P02 目录 `tools/scene_catalog.py` 编译稳定设备 ID 与场景支持表，再与已加载 MuJoCo 模型的 profile 核对。模型提供六个命名关节的范围。EOS 必须传入已验证的场景路径，并核对已应用图选中的设备映射；子进程不能仅凭套接字请求推断图路径。

| 字段 | 类型／单位 | 用途与所有者 | 默认／验证／兼容 |
| --- | --- | --- | --- |
| `version` | 字符串 | 每次请求/响应的模拟器线协议标识 | 必填 `"2.0.0"`；其他值拒绝，现有调用方继续使用此 ID。 |
| `id` | 非空字符串／— | 调用方关联 ID，响应回显 | 必填；严格模式接受 1..128 个 UTF-8 字节，与 EOS Dispatcher ID 一致；旧直接模式保留现有非空字符串行为。 |
| `node` | 非空字符串／模拟器设备 ID | EOS 适配器发送 `adapter.settings.simulator_node`（`cam-0`、`base-0` 或 `arm-0`） | 旧直接模式忽略；严格模式要求精确匹配所选场景已验证目录中的设备 ID 与操作类别。EOS 发送前另行核对图节点、类别、所选场景和包锁定。 |
| `op` | 枚举字符串 | 请求操作 | 必填；下表列出有效值，未知操作报错。 |
| `command_id` | 非空字符串／— | 运动与停止的 Dispatcher 准入标识 | 旧直接模式忽略；严格模式要求运动/停止提供 1..128 个 UTF-8 字节，与 EOS Dispatcher ID 一致，按节点去重；健康、观察、拍摄不带此字段。旧直接模式继续忽略。 |
| `ok` | 布尔 | 响应成功状态 | 模拟器返回；false 时包含 `error.message`。 |
| `error.message` | 字符串 | 人可读失败原因 | `ok:false` 时出现；严格模式增加稳定的 `error.code`，旧读取方仍可读 message。 |
| `error.code` | 字符串枚举／— | 严格模式稳定失败标识 | 有界请求成功解析而返回 `ok:false` 时新增；值与优先顺序见下文。旧读取方仍可使用 `error.message`。 |
| `features` | 字符串数组／— | 健康能力证明 | 严格模式成功 `health` 包含必需成员 `strict-socket-v1`，未来可附加其他特性；旧模式不包含它。EOS 必须精确匹配该成员。 |
| `timestamp_ns` | 有限数／模拟纳秒 | 快照或画面时间 | 响应字段；当前用 JSON 数字，读取方不能假设超过安全范围仍精确。 |
| `sequence` | 非负数／物理步数 | 快照顺序 | 响应字段；同一次模拟器运行中不递减。 |
| `accepted` | 布尔 | 操作级准入/结果 | 健康、运动和停止响应；若 `ok:false`，以失败为准。 |

所有运动输入必须是解析后有限的 JSON 数字。严格模式底盘输入在引擎当前范围内：`linear_x_m_s`、`linear_y_m_s` 为 `[-1,1]`，`angular_z_rad_s` 为 `[-1.5,1.5]`，`valid_for_ms` 为 `(0,5000]`；场景可以进一步收紧。机械臂每个元素必须处于加载模型的对应关节范围内。EOS 调用前检查图身份、设置、设备类别、边界、期限及 Dispatcher 准入；模拟器再次检查实际场景能力。旧读取方忽略新增可选响应字段。严格模式错误形如 `{"ok":false,"error":{"code":"unsupported_operation","message":"unsupported operation"}}`；旧读取方仍使用 `error.message`。

严格校验顺序为：帧界限/JSON 解析、线协议版本和有界 `id`、已知 `op`、精确 `node` 与类别、必需的 `command_id`、有类型有限数字与场景限制，最后是幂等表和引擎下发。第一处失败决定稳定错误码：`invalid_request`、`unsupported_version`、`unsupported_operation`、`node_mismatch`、`invalid_command_id`、`invalid_movement`、`out_of_range`、`command_id_conflict`、`command_in_progress`、`command_capacity` 或 `device_unavailable`。畸形、截断或超限的帧可直接断开，因为其 `id` 不可信。`ok:false` 始终优先于 `accepted`，不代表物理完成。有界响应回显已解析的请求 `id`，无二进制负载。

严格模式中的运动与 `stop` 在调用引擎前原子保留 `(node,command_id)`。指纹由操作名与规范化有类型值构成：解析为相等 `f64` 值的不同 JSON 数字写法视为相同，包括 `-0` 与 `0`；数组次序有意义。请求 `id` 只用于传输关联，不属于指纹。相同重发仅更换回显的请求 `id`，保留原操作结果的 `timestamp_ns` 与 `sequence`，不再次下发；同一有效键搭配不同指纹返回 `command_id_conflict`。并发相同重发可在有界期限内等待原请求，或返回 `command_in_progress`，绝不执行两次。已下发但结果不明时，存为不确定状态，绝不报告准入成功。每个键、指纹和终态/不确定结果均保留到子进程代际结束；不能通过按时过期或驱逐使同一子进程内的重发再次执行。运动表上限 65,536 条，另为停止表保留 4,096 条，使运动表已满不能占用停止容量。容量耗尽时下发前返回 `command_capacity` 并报告可处理故障；停止表也耗尽时拒绝新停止身份，EOS 须记录停止结果未知，并按 R06 升级处理。进程内去重不能取代 EOS 持久 Dispatcher 日志：子进程重启后，EOS 绝不自动重试结果不确定的已下发命令。

## 操作

| `op` | 额外请求字段（类型／单位） | 成功字段（类型／单位） | 验证与效果 |
| --- | --- | --- | --- |
| `health` | 无 | `accepted:bool`；严格模式另有 `features:["strict-socket-v1"]` | 报告引擎可用性；严格模式核对 `node` 是所选场景可用设备。EOS 发布就绪前探测每个已声明设备。 |
| `camera_capture` | 无 | `format:"jpeg"`、`rgb_length:u32` 字节、`depth_available:false`、`width_px:u32`、`height_px:u32`、JPEG 负载 | 帧长度等于 `rgb_length`；严格模式验证相机节点与有界尺寸。 |
| `base_observe` | 无 | `position_m:[f64;2]` m、`linear_velocity_m_s:[f64;2]` m/s、`yaw_rad:f64` rad、`angular_velocity_rad_s:f64` rad/s | 严格模式验证底盘节点；数值来自一致的引擎快照。 |
| `base_move` | `linear_x_m_s:f64` m/s、`linear_y_m_s:f64` m/s、`angular_z_rad_s:f64` rad/s、`valid_for_ms:f64` ms、`command_id:string` | `accepted:bool` | `valid_for_ms` 在 `(0,5000]`；受场景限制，租期后底盘停止。严格模式按 ID 去重。 |
| `manipulator_observe` | 无 | `joint_positions_rad:[f64;6]` rad、`joint_velocities_rad_s:[f64;6]` rad/s、`end_position_m:[f64;3]` m、`end_orientation_xyzw:[f64;4]` 单位四元数 | 严格模式验证机械臂节点；方向顺序为 x,y,z,w。 |
| `manipulator_move` | `joint_positions_rad:[f64;6]` rad、`command_id:string` | `accepted:bool` | 恰好六个有限目标且在场景边界内；严格模式按 ID 去重。 |
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

目标归属失败示例（受管理严格模式会检查 `node`）：

```json
{"version":"2.0.0","id":"req-17","ok":false,"error":{"code":"node_mismatch","message":"node is not the declared base device"},"timestamp_ns":100000000,"sequence":50}
```

## 生命周期与故障

EOS 从 IsOS 获得已验证的程序、场景和套接字，直接启动子进程，对每个声明的设备等待严格健康检查通过，再使声明的适配器可供观察。场景缺失、协议不兼容、帧损坏、相机不可用或断线都会使适配器不可用；EOS 不编造观察值。R06 仍须证明在终止并回收子进程前完成有界物理停止；R05 只证明未下发受管理运动时的子进程及套接字清理。模拟器正常退出时移除套接字。同一 `command_id` 的相同传输重发从目标去重存储取得旧结果，不重复运动。EOS 不自动重放结果不确定的已下发命令；它要从新状态核对，或要求一次明确授权的新准入。同一 ID 搭配冲突负载时报错。

## R06 受管理停止契约（设计目标）

本节只扩展 `--managed-strict-socket`。线协议仍为 `2.0.0`；帧格式、操作名、直接启动行为及 R05 的 `(node,command_id)` 全代际保留不变。受管理子进程在现有 `--v2-socket` 路径后追加 ASCII 字面后缀 `.stop`，得到仅所有者可访问的停止套接字；图和启动参数均不新增套接字字段。两个路径须连 NUL 终止符一起符合 `sockaddr_un.sun_path`：主套接字路径最多 102 字节，才能使 `.stop` 后缀及终止符放入 108 字节。路径过长时以 `socket_path_too_long` 启动失败；任一路径绑定或权限设置失败时，启动也须失败并清理两个自有套接字文件。两者均在既有私有运行目录中使用 `0600`；EOS 推导同一路径，仅在直接子进程回收后清理旧的自有文件。直接启动不创建伴随停止套接字。

停止套接字有独立的监听器／分类器，只接受原有分帧 `health` 与 `stop` 操作；其他已解析操作在引擎下发前返回 `unsupported_operation`。该套接字上的 `health` 校验精确的底盘或机械臂场景设备 ID，并且仅在停止通道、引擎写入屏障、底盘／机械臂分别确认和取消路径全部启用时，返回 `ok:true,accepted:true,features:["strict-socket-v1","strict-stop-v1"]`。主套接字上的执行器健康响应只有在伴随监听器就绪后才增加 `strict-stop-v1` 成员。两个健康路径都返回本子进程相同的全新 `generation_id`；无法取得 128 个随机位时，受管理启动在公告特性前失败。EOS 在公开运动能力或终态停止屏障前，须检查每个已声明执行器的两个特性、探测停止套接字并比较代际 ID。仅有 `strict-socket-v1` 仍足以证明 R05 只读就绪。该特性证明可用能力，不代表之后某次停止成功。

严格模式的 `stop` 仍是整机请求，即使 `node` 为 `base-0` 或 `arm-0`；`node` 仍是 R05 去重键的一部分。新准入的停止屏蔽本子进程代际中所有先前运动。主套接字为 R05 兼容仍接受 `stop`，但当普通入口槽全部占用时，只有伴随套接字上的停止具有 R06 入口保证；EOS 必须使用伴随路径。受管理 `base_move`、`manipulator_move` 请求增加两个必填前提字段：当前 `generation_id` 和 `stop_epoch`。前者来自健康响应，是每个子进程新的随机 128 位身份，用精确 32 位小写十六进制 ASCII 编码。缺失或不匹配代际在日志预留与引擎下发前返回 `stale_generation`。后者是非空规范 ASCII 十进制字符串，无符号及前导零，初始值例外为 `"0"`；缺失或畸形 epoch 返回 `stop_fenced`。EOS 缓存健康代际，在新子进程内从 epoch `"0"` 开始，只在停止完整证明后更新。伴随套接字的 `stop` 请求也须携带当前代际 ID，防止上代延迟请求影响新子进程。R05 兼容的主套接字 `stop` 接受缺失代际 ID，保留既有日志语义；EOS 不用它执行 R06。直接启动和只读操作忽略新请求字段。停止响应增加下列字段；通过校验且成功在停止日志中预留的请求必须返回，包括部分／未知结果及相同请求的已存储重发；损坏请求或预留前拒绝不带这些字段。

| 字段 | 类型／单位 | 用途与校验 |
| --- | --- | --- |
| `base_stop` | 枚举字符串／— | 只能是 `"stopped"` 或 `"unknown"`；`stopped` 表示底盘租期已失效、零驱动和当前位置保持目标已在一个引擎步提交，屏障之前的运动之后不能再写底盘目标。仅有命令接受回执不够。 |
| `arm_stop` | 枚举字符串／— | 只能是 `"stopped"` 或 `"unknown"`；`stopped` 表示六轴目标已替换为观察到的保持位置，屏障之前的运动之后不能再写机械臂目标。这证明终态命令保持，不保证残余物理速度在数学上为零。 |
| `generation_id` | 32 位小写十六进制 ASCII 字符／子进程身份 | 每个受管理子进程全新随机 128 位值，由主套接字和伴随套接字的 `health` 及严格停止结果返回。受管理运动和伴随停止请求须携带精确当前值。它是身份检查，不是授权密钥或图修订。缺失／错误值在下发前返回 `stale_generation`。 |
| `stop_epoch` | 非空十进制字符串／子进程内代际计数 | 单调递增的引擎屏障标识，首次停止前为 `"0"`，第一次准入停止为 `"1"`；同一子进程内不得复用。只允许 ASCII 数字，无符号与前导零，`"0"` 例外。受管理运动请求须携带当前值作为前提；停止响应返回新值，相同重发返回原值。它用于关联证据，不是图修订或跨进程序号。 |

受管理运动及伴随停止请求示例（每段仍有原来的帧头）：

```json
{"version":"2.0.0","id":"move-req-1","node":"base-0","op":"base_move","command_id":"cmd-1","generation_id":"00112233445566778899aabbccddeeff","stop_epoch":"0","linear_x_m_s":0.2,"linear_y_m_s":0.0,"angular_z_rad_s":0.0,"valid_for_ms":200.0}
```

```json
{"version":"2.0.0","id":"stop-req-1","node":"base-0","op":"stop","command_id":"stop-cmd-1","generation_id":"00112233445566778899aabbccddeeff"}
```

只有 `base_stop` 与 `arm_stop` 都是 `"stopped"`，才返回 `ok:true,accepted:true`。任一是 `"unknown"` 时，返回 `ok:false,accepted:false,error.code:"stop_outcome_unknown"`，同时保留分别得到的证明和屏障标识。超时、引擎故障、断连或崩溃都可能使任一结果未知；没有响应时，EOS 必须视两者均未知，无论子进程实际状态如何。预留前拒绝沿用 R05 校验／容量错误码，没有停止证明。已下发但被取消的运动返回 `ok:false,accepted:false,error.code:"command_interrupted"`；日志保留该失败结果，相同重发返回原结果。`command_interrupted` 本身不是停止证明。`stop_outcome_unknown`、`command_interrupted`、`stop_fenced` 与 `stale_generation` 是严格模式的新增稳定错误码，直接启动错误不变。停止响应的既有 `timestamp_ns` 与 `sequence` 必须在保持目标提交**之后**采样；相同重发除传输 `id` 外，所有结果字段均不变。

**R05 重发优先顺序：** 常规请求、版本、节点、有类型数值、代际及规范 epoch 语法验证后，服务从操作名、规范化有类型值**及请求中的 `stop_epoch`**计算运动指纹。在与日志键预留、停止屏障递增共用的同步边界内，先查询既有 `(node,command_id)`。相同键与指纹即使在当前 epoch 已增加后，仍返回已存储的终态或不确定结果；进行中的相同重发返回 `command_in_progress`，负载或 epoch 改变则返回 `command_id_conflict`。重发绝不再次下发。仅对**新键**比较当前 epoch；旧值返回 `stop_fenced`，当前值才可预留并进入引擎写入复核。这样在拒绝延迟新命令的同时保留 R05 相同重发及冲突语义。错误的子进程代际即使重启后数字 epoch 一样，也先返回 `stale_generation`。EOS 仍不得自动重发结果不确定的已下发命令。


停止通道从完整有效停止帧读入起，以单调时钟计算 **1000 ms** 截止，届时必须提交底盘／机械臂证明或返回 `stop_outcome_unknown`。每条连接从 accept 起，读取帧头和元数据最多 **250 ms**，包括服务端队列中的等待时间；已接受连接把接受时刻和绝对截止时间一同传给工作线程。主监听器有最多 32 个普通工作槽及 8 个入口槽；**全部八个都被部分帧占用，也不能占用伴随停止监听器**。伴随监听器有三个专属停止入口工作线程、仅所有者可访问的待连接队列、按先进先出顺序分配工作线程、相同的每连接 250 ms 读取期限，以及一个预留停止执行槽。若此前恰有两个部分帧占用入口，且没有其他排队者，第三个工作线程可在有效停止已连接后的自身 **250 ms** 入口期限内完成分类，满足公布的 **500 ms** 分类上界。若三个较早的部分帧占满入口，后续排队帧可能在分类前过期；EOS 此时将停止视为未知。只有读完完整有效停止帧后，1000 ms 执行预算才开始。若连接本身失败，或仅所有者可访问的待连接队列被其他客户占满，EOS 外层连接期限到期，停止结果为未知。普通工作不能占用伴随槽。停止执行器在调度有效停止前不能等待普通运动或相机工作线程。普通工作超额须在引擎下发前拒绝或断开。运动日志容量不能占用停止日志容量。EOS 自身还须对连接、完整帧读写和子进程终止设置外层期限；准确的 EOS 外层预算待 EOS 设计审查确定。固定执行线程可能在 1000 ms 响应期限后完成引擎操作；超时或部分结果仍保留为 `stop_outcome_unknown`，即使之后引擎操作成功，本代子进程的新运动仍被禁止。伴随健康检查从缓存读取身份与特性，不获取引擎互斥锁。停止预留时会取消活动旧 JPEG 流；成功停止须等待其发布闸门，而期限内仍阻塞的流使停止结果为未知。任何超时不得解释为成功停止。

停止通道预留有效请求时，递增引擎 `stop_epoch`，关闭旧运动写入门。每个运动携带请求中的 `stop_epoch`；引擎在与底盘驱动或机械臂目标写入共用的短命令状态锁内，把它与当前 epoch 比对。停止通道先递增 epoch 并使两个运动租期失效，再采样并保持两个设备。屏障前已解析或排队、但之后才到达引擎的运动不能写目标：日志已预留则返回并保留 `command_interrupted`，**新键**在预留前拒绝则返回 `stop_fenced`。停止确认后才到达的延迟**新帧**也带旧令牌，必须返回 `stop_fenced`；相同旧键的重发按上面的 R05 规则返回原日志结果。若运动先进入短写入段，停止等待它退出，随后覆盖目标；覆盖后才能确认。成功停止后，不得出现屏障前延迟写入。EOS 在非锁存控制停止后明确准入的新运动携带已证明的新令牌，可以执行；紧急关闭时由 EOS 关闭新准入。套接字只有所有者可用，自身不授予执行器权限。

相机在短命令状态锁内取得有界、不可变的场景／数据快照，随后在独立有界工作线程与渲染上下文中渲染，不占用该锁。停止取消排队拍摄，并屏蔽进行中拍摄的负载发布。如果 EGL/JPEG 无法中断，停止仍须到达引擎；拍摄可报 `device_unavailable` 或断开，EOS 在外层期限后强制回收子进程。子进程不得让仍可访问已销毁模型／数据的工作线程脱离管理。受管理子进程 GUI 不可用时须启动失败、清理套接字且不公告 `strict-stop-v1`。子进程崩溃、引擎卡住或停止日志满时，EOS 记录未知停止；IsOS/EOS 保留可见故障事件，不宣称完成安全停止。

成功停止响应元数据示例（仍有原来的帧头）：

```json
{"version":"2.0.0","id":"stop-req-1","ok":true,"accepted":true,"base_stop":"stopped","arm_stop":"stopped","generation_id":"00112233445566778899aabbccddeeff","stop_epoch":"1","timestamp_ns":100000000,"sequence":50}
```

部分证明示例；EOS 仍须在有界升级后终止并回收子进程，整体结果为未知：

```json
{"version":"2.0.0","id":"stop-req-2","ok":false,"accepted":false,"base_stop":"stopped","arm_stop":"unknown","generation_id":"00112233445566778899aabbccddeeff","stop_epoch":"2","error":{"code":"stop_outcome_unknown","message":"arm stop outcome unknown"},"timestamp_ns":102000000,"sequence":51}
```

R06 设计与负面样本见[固定用例](../../../tests/fixtures/strict_stop_lane/README.md)。本分支的 MuJoCo 所有者实现候选通过 24/24 项 CTest；[设计证据与可复现命令](../design_cn.md#r06-停止通道设计目标)记录其范围。三个入口工作线程的契约变更还需独立设计复审；EOS 公开运动或将目标视为集成现状之前，仍需独立实现审查与跨所有者物理安全停止验收。
