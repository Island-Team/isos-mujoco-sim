# MuJoCo 核心

[English](../../../docs/mujoco/core/README.md) · [MuJoCo 指南](../README_cn.md) · [公开接口](../interfaces/README_cn.md)

这些页面说明仿真器实现、基准行为与 EOS 集成。[接口文档](../interfaces/README_cn.md)拥有公开字段和兼容规则；[开始使用指南](../start/README_cn.md)给出操作顺序。

| 页面 | 范围 |
| --- | --- |
| [完整接口回放](verification_cn.md) | 自定义场景、三厨房回放、软件包检查与日志关联。 |
| [架构](architecture_cn.md) | 源码归属、运行数据流与验证证据。 |
| [仿真器](mujoco_cn.md) | 场景加载、物理、渲染与运行服务设计。 |
| [RoboCasa 基准](benchmark_cn.md) | 当前任务、来源、评分与限制。 |
| [EOS 进程](eos/process/mujoco_cn.md) | 历史进程节点声明。 |
| [EOS 硬件](eos/hardware/camera_cn.md) | 相机、底盘、机械臂、夹爪与躯干设计页。 |
| [交互角色](interaction-nodes_cn.md) | 目标图路由设计。 |

## 文档验证

2026-11-16 调整目录后，`python3 tests/fixtures/strict_socket/check.py` 通过 31 个 R05 用例，`python3 tests/fixtures/strict_stop_lane/check.py` 通过 48 个 R06 用例。相对 Markdown 链接检查未发现缺失目标。完整检查输出保存在忽略目录 `data/test/20261116-docs-isos-layout/`。
