# 评测方法与评测器接口

[English](../../docs/core/benchmark.md) · [Docs](../README_cn.md)

当前任务为上游 RoboCasa `CloseFridge`，原生抓放与导航保留为兼容样本。本页拥有任务来源、成功规则、限制及私有原生评测 RPC；任务选择和显示命令见[开始使用](../start_cn.md)。

<a id="robocasa-基准"></a>
## RoboCasa 基准

当前基准采用上游 RoboCasa365 的 `CloseFridge` 原子任务。首次本地回合使用官方 `robocasa/CloseFridge` Gym 环境、target 划分、种子 42 和 RoboCasa 自身的成功判定：选定的冰箱门必须关闭。`tools/robocasahrun.py` 在底盘运动为零的条件下执行 20 个有界随机动作，作为启动冒烟基线。结果只证明环境启动与评分，并不代表训练策略或可与排行榜比较的成绩。正式评测按 RoboCasa 建议每任务运行 20 回合，并记录种子、资源、策略版本和时长。

默认运行 `./launch.sh` 即启动此回合。脚本从`config/dev.toml` 读取 `ROBOCASA_ROOT`，然后由 `.env` 覆盖；空值使用忽略的 `.local/robocasa`。若源码、运行环境或资源缺失，启动脚本先询问再设置。`./launch.sh --robocasa --seed 42 --steps 20` 可显式指定任务预算。设置脚本固定 RoboCasa 与 robosuite 源码版本、安装私有 Python 3.11 环境，并从固定版本的官方 RoboCasa 资源数据集下载纹理和通用装置资源，再从经过校验和验证的社区镜像下载 Lightwheel 装置与物体资源。这些文件位于忽略的 `.local/`。Python 运行环境及 C++ 构建均使用 MuJoCo 3.3.1。

RoboCasa [源码采用 MIT 许可](https://github.com/robocasa/robocasa/blob/main/LICENSE)；其 [README](https://github.com/robocasa/robocasa#license) 说明资源与数据集采用 CC BY 4.0。任务实现和成功规则位于上游 `robocasa/environments/kitchen/atomic/kitchen_doors.py`。[RoboCasa365 论文](https://robocasa.ai/assets/robocasa365_iclr26.pdf) 描述基准。再分发资源或结果时应保留资源署名。

原有自行设计的抓取放置和导航任务仅作为历史模拟器兼容性测试场景，不再是当前基准。其私有 C++ 基准 RPC 仍不通过 EOS 或 EGIA 暴露。RoboCasa 在上游环境中运行；[Python 机器人硬件核心](robocasa_cn.md)在进程内控制并观测 PandaOmron 机器人，[本地记录](robocasa_cn.md)可重放硬件命令以测试控制逻辑。本包已提供受治理的 EOS 硬件适配器；本地冒烟与硬件回放不能证明完整的 EOS 代理评测。

<a id="私有评测-rpc"></a>
## 私有评测 RPC

<a id="归属调用方与准入"></a>
### 归属、调用方与准入

本包实现 [`proto/benchmark.proto`](../../proto/benchmark.proto) 的 `eos.mujoco.benchmark.v1.BenchmarkService`。可信评测器通过 `--benchmark-socket` 指定的独立、仅所有者可访问的 Unix gRPC 套接字调用。EOS、EGIA 和代理不得获得该套接字或真实状态。受管理严格模式拒绝评测监听器。直接启动时，本服务与历史模拟器监听器共用场景引擎。v1 protobuf 标识独立于包及控制套接字版本。

<a id="操作与字段"></a>
### 操作与字段

| RPC | 请求字段：类型 / 单位 | 响应 | 验证与默认值 |
| --- | --- | --- | --- |
| `Reset` | `seed`：uint64 / — | `StateResponse` | 确定性复位并暂停实时步进；缺省为 protobuf 零值。 |
| `Step` | `steps`：uint32 / 固定 2 ms 步 | `StateResponse` | `1..100000`；要求暂停实时步进。 |
| `State` | 空 | `StateResponse` | 不推进状态。 |
| `Score` | 空 | `ScoreResponse` | 复位后读取场景成功条件和碰撞评分。 |
| `SetPaused` | `paused`：bool / — | `StateResponse` | `true` 暂停；缺省为 protobuf `false`。 |

| 响应字段 | 类型 / 单位 | 含义与兼容 |
| --- | --- | --- |
| `ok`、`error` | bool、string / — | 状态操作结果及错误信息；成功时错误为空。 |
| `sequence`、`elapsedSimS` | uint64 / 步、double / s | 确定性步数和模拟时间；protobuf JSON 把 uint64 编码为字符串。 |
| `baseXM`、`baseYM`、`baseYawRad` | double / m、m、rad | 底盘真实位姿。 |
| `armJointsRad` | double 数组 / rad | 六关节位置。 |
| `objectHeldId` | string / — | 当前抓取物体；无物体时为空。 |
| `objectPositionM`、`gripperPinchPositionM` | double 数组 / m | 世界坐标 xyz。 |
| `obstacle0PositionM`、`obstacle1PositionM` | double 数组 / m | 世界坐标 xy。 |
| `navigation`、`grasp`、`placement` | bool / — | 场景成功条件；不适用时为 `false`。 |
| `collisions`、`elapsedSimS` | uint32 / 次、double / s | `ScoreResponse` 的碰撞数和时长。 |

<a id="示例错误与生命周期"></a>
### 示例、错误与生命周期

以下为单条 protobuf JSON 消息，实际传输是 gRPC protobuf：

```json
{
  "seed": "42"
}
```

```json
{
  "ok": true,
  "sequence": "0",
  "elapsedSimS": 0.0,
  "baseXM": -1.2,
  "baseYM": 0.0,
  "baseYawRad": 0.0,
  "armJointsRad": [
    -1.5708,
    -1.5708,
    1.5708,
    -1.5708,
    -1.5708,
    0.0
  ]
}
```

有限步进请求为 `{"steps":200}`；`State` 和 `Score` 使用 `{}`。评分示例为 `{"navigation":true,"grasp":false,"placement":false,"collisions":0,"elapsedSimS":8.4}`。复位失败时返回 `{"ok":false,"error":"scene not loaded"}`。超过 100000 步返回 gRPC `INVALID_ARGUMENT`；实时运行时手动步进返回 `FAILED_PRECONDITION`。传输与服务故障使用 gRPC 状态。评分只有在成功复位和有界回合后才有意义；这些值始终留在可信评测路径。
