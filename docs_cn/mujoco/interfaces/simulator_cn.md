# 历史模拟器 RPC

[接口目录](README_cn.md) · [运行控制](control_cn.md) · [私有评测 RPC](benchmark_cn.md) · [English](../../../docs/mujoco/interfaces/simulator.md)

## 归属、调用方与准入

本包实现 [`proto/simulator.proto`](../../../proto/simulator.proto) 中的 `eos.simulator.v1.SimulatorService`。EOS HAL 通过 `--socket` 指定的仅所有者可访问的本地 Unix gRPC 套接字调用；代理通过 EOS 的发现和 primitive 使用设备。直接启动可开放该监听器。EOS 管理的 `--managed-strict-socket` 子进程拒绝 `--socket`，改用[帧格式控制接口](control_cn.md)。v1 protobuf 标识独立于软件包及套接字版本。

## 操作

| RPC | 输入 | 输出 | 验证与失败 |
| --- | --- | --- | --- |
| `Health` | `deviceId`：非空设备 ID，无默认值 | `available`：布尔值 | 未知或不可用设备返回 `false`。 |
| `Execute` | `deviceId` 和恰好一个 `command` 变体 | `accepted`；拒绝时的 `errorCode` | 不支持的设备或命令、非有限值、越界目标、不可用引擎均拒绝；EOS 设置有限期限。 |
| `ReadTelemetry` | `deviceId`；本配置支持 `ARM`、`BASE`、`GRIPPER` | `available` 和匹配的 `arm`、`base`、`gripper` 数据 | 类型与设备不匹配或引擎不可用时返回不可用。 |
| `ReadCameraFrame` | `deviceId`，如 `cam-0` | `available`、尺寸、时间戳、`jpeg`、`state` | 渲染器不可用或设备错误时返回不可用。 |

本配置支持底盘、机械臂、夹爪和相机，不声明云台、麦克风、扬声器或 `arm.pick`。共享 protobuf 包含更多命令与遥测变体；仅有定义不代表当前设备支持。proto3 标量缺失时使用 protobuf 零值；EOS 在调用前检查已声明能力及命令。

| 字段族 | 类型 / 单位 | 含义及兼容 |
| --- | --- | --- |
| `baseNavigateRelative.xM`、`yM`、`yawRad` | double / m、m、rad | 相对底盘目标，须为有限值并符合场景边界。 |
| `footprintWidthM`、`footprintLengthM` | double / m | 碰撞检查的正数占地尺寸。 |
| `armMoveJ.positionsRad` | double 数组 / rad | 模型范围内的六关节目标。 |
| `armMoveL.positionM`、`orientationXyzw` | double 数组 / m、单位四元数 | 三个位置值及四个四元数值。 |
| `baseDrive.linearXMS`、`linearYMS`、`angularZRadS` | double / m/s、m/s、rad/s | 连续底盘指令。 |
| `gripperMove.close`、`forceN` | bool、double / —、N | 夹爪目标及力。 |
| `arm`、`base`、`gripper` 遥测 | 类型化 protobuf / SI 单位 | 当前机器人状态；oneof 与请求类别匹配。 |
| `CameraState.sequence`、`sceneRevision` | uint64 / 步、修订 | 快照顺序；protobuf JSON 把 uint64 编码为字符串。 |

准确字段、枚举值和 protobuf JSON 名称以 `proto/simulator.proto` 为准。修改时须同步 EOS 所有者文件 `../Island-eos/share/contracts/eos/external/simulator/simulator.proto`。

## 示例与生命周期

```json
{"deviceId":"base-0","baseNavigateRelative":{"xM":0.45,"yM":-1.3,"yawRad":0.0,"footprintWidthM":0.5,"footprintLengthM":0.6}}
```

```json
{"accepted":true}
```

命令与设备不匹配时返回 `{"accepted":false,"errorCode":"unsupported_device_command"}`。底盘遥测请求为 `{"deviceId":"base-0","kind":"BASE"}`。相机响应中的 JPEG 字节在 protobuf JSON 中为 base64。复位和评分不属于本服务。Stop 或 halt 中断当前工作；连接失败、超时及引擎故障通过失败结果或 gRPC 状态返回。EOS 不应从历史路线推断物理停止证明。
