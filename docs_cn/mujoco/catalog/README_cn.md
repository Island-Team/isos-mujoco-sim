# MuJoCo 贡献节点目录

[English](../../../docs/mujoco/catalog/README.md) · [首次使用](../usage_cn.md) · [包契约](../interfaces/package_cn.md)

**目标设计。** IsOS 目录将精确验证的 `island/mujoco-sim@0.1.1` 贡献放在 **EOS core → process layer → MuJoCo group → simulator node**。先读[进程节点](../layers/process/groups/mujoco/nodes/simulator_cn.md)，再读包与套接字契约。本包拥有该进程类型和场景/设备选项数据。通用相机、底盘、机械臂、控制及 gate 类型由 EOS 或 IsOS 拥有，并由 `sim-hardware` 节点集组合。节点集是可预览安装模板，并非新的运行时类型。

首次使用顺序：安装或链接精确包、预览节点集、选择场景与设备 ID、校验并应用图修订、等待 EOS 健康状态、读取当前运行第一条就绪或故障事件。图保存 ID 与包锁定；IsOS 解析验证路径并通过生成配置传给 EOS。[使用指南](../usage_cn.md)的直接启动方式不代表已应用图。
