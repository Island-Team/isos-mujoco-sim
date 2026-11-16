# 私有评测 RPC

[接口目录](README_cn.md) · [模拟器 RPC](simulator_cn.md) · [基准方法](../core/benchmark_cn.md) · [English](../../../docs/mujoco/interfaces/benchmark.md)

## 归属、调用方与准入

本包实现 [`proto/benchmark.proto`](../../../proto/benchmark.proto) 的 `eos.mujoco.benchmark.v1.BenchmarkService`。可信评测器通过 `--benchmark-socket` 指定的独立、仅所有者可访问的 Unix gRPC 套接字调用。EOS、EGIA 和代理不得获得该套接字或真实状态。受管理严格模式拒绝评测监听器。直接启动时，本服务与历史模拟器监听器共用场景引擎。v1 protobuf 标识独立于包及控制套接字版本。

## 操作与字段

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

## 示例、错误与生命周期

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
