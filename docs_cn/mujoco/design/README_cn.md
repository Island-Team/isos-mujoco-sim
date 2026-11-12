# 节点、层与组设计

[English](../../../docs/mujoco/design/README.md) · [架构](../architecture_cn.md) · [使用指南](../usage/README_cn.md)

本包贡献一个 EOS 进程类型：**EOS core → process layer → MuJoCo group → simulator node**。[进程层](process_cn.md)和 [MuJoCo 组](process/mujoco_cn.md)通往[模拟器节点](process/mujoco/simulator_cn.md)，说明生命周期、就绪和停止行为。IsOS 选择精确验证的软件包以及场景和设备 ID；EOS 拥有子进程。

当前 `sim-hardware` 节点集组合本包拥有的进程类型和一个 EOS 通用 JPEG 相机。底盘和机械臂仍在资源目录中；托管执行须等待执行器 Stop 证明。节点集是可预览的安装模板，而非运行时类型。图保存 ID 和软件包固定版本；IsOS 在生成的配置中解析已验证路径。精确字段见[包契约](../interfaces/package_cn.md)和[套接字契约](../interfaces/socket_cn.md)。操作步骤见 [dev 指南](../usage/dev_cn.md)与 [IsOS 包指南](../usage/isos-pkg_cn.md)。
