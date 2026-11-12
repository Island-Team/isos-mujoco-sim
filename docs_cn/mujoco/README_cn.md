# MuJoCo 基准软件包

[完整硬件软件包契约](interfaces/full-hardware_cn.md)说明下个发行候选版及 IsOS 管理的服务。

模拟器在进程启动时加载场景，为 EOS 执行机器人命令并渲染观测；可信评测器通过独立的私有服务读取评分真值。EGIA 等智能体通过 EOS 的发现、资源和原语进行交互。

当前基准采用上游 RoboCasa `CloseFridge`；抓取放置与导航场景保留为 C++ 模拟器兼容性测试场景。先阅读[首次运行指南](usage/dev_cn.md)，再按[基准说明](benchmarks/Robocasa/README_cn.md)检查范围与验证。[MuJoCo 核心](../../src/mujoco/README.md)负责场景加载、物理、渲染和评分；[IsOS 软件包包装层](../../src/isos/README.md)负责面向 EOS 的进程和套接字端点。开发时可直接运行 `build/mujoco-core`；软件包入口保持为 `build/eos-mujoco-sim`。具体操作见[使用指南](usage/README_cn.md)。

[English](../../docs/mujoco/README.md)
