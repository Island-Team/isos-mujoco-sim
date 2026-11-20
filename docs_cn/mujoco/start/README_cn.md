# 按流程开始

[English](../../../docs/mujoco/start/README.md)

按运行方式选择指南：[dev 指南](dev_cn.md)说明源码构建、RoboCasa 冒烟运行、原生场景检查和直接启动；[IsOS 包指南](isos-pkg_cn.md)说明软件包构建、图准入、严格就绪、受治理命令和停止。[RoboCasa 基准页](../core/benchmark_cn.md)记录当前任务与评分范围。

当前 schema `0.2.2` 硬件候选包支持 `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY`，省略 `--version` 时使用源码候选版本。Apply 前准备共享服务配置，并保留预设提供的两个相机尺寸值。参见[软件包契约](../interfaces/package_cn.md#当前包装器准入schema-022)。
