# EOS 进程节点：MuJoCo

[设计](../../../../design/eos/process/mujoco_cn.md) · [包声明](../../../package_cn.md) · [运行控制](../../../control_cn.md)

历史 `0.2.0` 包声明 `eos.process.mujoco.simulator@v0.2`。IsOS 验证场景资源与精确包版本；EOS 使用 `mujoco-v2` 生命周期适配器启动子进程。新硬件包使用服务声明，不在预设中放入进程节点。

| 设置 | 类型 / 单位 | 用途及验证 | 默认 |
| --- | --- | --- | --- |
| `scene` | string / — | Stable verified scene ID; required | none |
| `socket` | string / path | Owner-only Unix socket; required | none |
| `env` | string table / — | Child environment references | empty |
| `start_timeout_ms` | positive integer / ms | Readiness deadline | owner policy |

严格健康检查失败、场景不符或服务退出时，节点不可用。停止前 EOS 关闭命令准入并确认停止证明，然后回收子进程。
