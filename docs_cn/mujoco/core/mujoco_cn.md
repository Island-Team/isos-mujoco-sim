# MuJoCo 核心设计

[设计目录](../README_cn.md) · [运行控制](../interfaces/control_cn.md) · [包契约](../interfaces/package_cn.md)

模拟器核心负责场景加载、确定性复位、物理、渲染和私有评测评分。IsOS 校验并配置精确的软件包服务；EOS 管理机器人侧命令准入、健康检查和停止。原生服务与 RoboCasa 服务均通过私有端点向适配器提供数据，评测真实状态不通过这些端点暴露。

原生开发启动器与 IsOS 软件包都运行 `eos-mujoco-sim`。其直接模式套接字和受管理严格套接字共享一个来自 `src/mujoco/engine.h` 的 `SimEngine` 实例；独立的 `mujoco-core` 开发可执行文件也链接同一个 `mujoco_core` 库。套接字准入和生命周期不同，但场景加载、复位、步进、命令、状态快照、相机渲染和私有评分均由该核心负责。RoboCasa 在隔离的 Python 服务中使用上游 Gym 和 `robocasa_core.Hardware`，不调用原生 C++ `SimEngine` API。

2026-11-16 执行 `ctest --test-dir build -R '^(core-launch|launcher-lifecycle|strict-socket|strict-socket-navigation)$' --output-on-failure`，4/4 项通过，覆盖直接核心可执行文件、开发启动器和两个受管理原生场景。完整输出保存在忽略目录 `data/test/20261116-core-api-parity/ctest.log`。
