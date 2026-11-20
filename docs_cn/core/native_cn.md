# 原生模拟器与保留 RPC

[English](../../docs/core/native.md) · [Docs](../README_cn.md)

原生引擎加载包拥有的 MJCF、确定性重置、推进物理、渲染观察并计算仅评测器可见的真值。下方保留 gRPC 路线只用于直接启动；托管服务使用[适配器控制](adapter_cn.md)。

<a id="mujoco-核心设计"></a>
## MuJoCo 核心设计

模拟器核心负责场景加载、确定性复位、物理、渲染和私有评测评分。IsOS 校验并配置精确的软件包服务；EOS 管理机器人侧命令准入、健康检查和停止。原生服务与 RoboCasa 服务均通过私有端点向适配器提供数据，评测真实状态不通过这些端点暴露。

原生开发启动器与 IsOS 软件包都运行 `eos-mujoco-sim`。其直接模式套接字和受管理严格套接字共享一个来自 `src/mujoco/engine.h` 的 `SimEngine` 实例；独立的 `mujoco-core` 开发可执行文件也链接同一个 `mujoco_core` 库。套接字准入和生命周期不同，但场景加载、复位、步进、命令、状态快照、相机渲染和私有评分均由该核心负责。RoboCasa 在隔离的 Python 服务中使用上游 Gym 和 `robocasa_core.Hardware`，不调用原生 C++ `SimEngine` API。

2026-11-16 执行 `ctest --test-dir build -R '^(core-launch|launcher-lifecycle|strict-socket|strict-socket-navigation)$' --output-on-failure`，4/4 项通过，覆盖直接核心可执行文件、开发启动器和两个受管理原生场景。完整输出保存在忽略目录 `data/test/20261116-core-api-parity/ctest.log`。

<a id="历史模拟器-rpc"></a>
## 历史模拟器 RPC

<a id="归属调用方与准入"></a>
### 归属、调用方与准入

本包实现 [`proto/simulator.proto`](../../proto/simulator.proto) 中的 `eos.simulator.v1.SimulatorService`。EOS HAL 通过 `--socket` 指定的仅所有者可访问的本地 Unix gRPC 套接字调用；代理通过 EOS 的发现和 primitive 使用设备。直接启动可开放该监听器。受管理的 `--managed-strict-socket` 子进程拒绝 `--socket`，改用[帧格式控制接口](adapter_cn.md)。v1 protobuf 标识独立于软件包及套接字版本。

<a id="操作"></a>
### 操作

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

<a id="示例与生命周期"></a>
### 示例与生命周期

```json
{
  "deviceId": "base-0",
  "baseNavigateRelative": {
    "xM": 0.45,
    "yM": -1.3,
    "yawRad": 0.0,
    "footprintWidthM": 0.5,
    "footprintLengthM": 0.6
  }
}
```

```json
{
  "accepted": true
}
```

命令与设备不匹配时返回 `{"accepted":false,"errorCode":"unsupported_device_command"}`。底盘遥测请求为 `{"deviceId":"base-0","kind":"BASE"}`。相机响应中的 JPEG 字节在 protobuf JSON 中为 base64。复位和评分不属于本服务。Stop 或 halt 中断当前工作；连接失败、超时及引擎故障通过失败结果或 gRPC 状态返回。EOS 不应从历史路线推断物理停止证明。

## 场景加载与确定性重置

原生目录支持 `pick-place` 与 `navigation`，分别以唯一 MJCF numeric profile 标记 `eos_benchmark_pick_place_v1` 或 `eos_benchmark_navigation_v1` 识别。场景和资产路径必须位于已验证包内。暂存前目录检查相机、底盘、六关节机械臂与夹爪的必需元素；实际 MuJoCo 加载仍是运行时兼容检查。`tools/catalog.py` 拥有必需元素名和摘要验证。

`SimEngine::Reset(seed)` 清空 MuJoCo 状态，以确定性整数种子混合生成有界物体和障碍物变体，恢复底盘/机械臂/夹爪目标并清空回合计数。可重复性要求相同场景字节、种子、依赖版本和动作序列。原生样本使用 2 ms 物理步长；私有评测器 Reset 先暂停实时执行，再执行有界手工 Step。重置与私有计分都不是 EOS 硬件端口。新场景需要支持的 profile、确定性重置、定义的成功条件、来源与许可审查、真实加载/回放检查和可用 EOS 设备。
