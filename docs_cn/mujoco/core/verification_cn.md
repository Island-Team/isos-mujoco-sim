# 完整接口回放

[English](../../../docs/mujoco/core/verification.md) · [核心目录](README_cn.md) · [包契约](../interfaces/package_cn.md)

此回放分别检查原生仿真器与隔离的 RoboCasa 服务的硬件边界。测试复制 MJCF 并修改模型名称，同时保留有许可证的网格资源及声明的基准 profile。原生回放以严格模式和实时 X11 图形窗口启动软件包可执行文件，检查相机、底盘、机械臂和夹爪的健康及观测，拒绝越界运动，移动底盘、机械臂和夹爪，在伴随套接字上验证停止，拒绝过期运动，并确认子进程和套接字清理。测试自行退出。

```sh
python3 tests/full_interfaces.py build/eos-mujoco-sim assets/scene.xml \
  data/test/<run-id>/native --gui
```

RoboCasa 使用上游 Gym 环境，而非原生 C++ 引擎。测试固定厨房前，使用 `./tools/robocasasetup.sh --full` 安装固定版本的完整物体资源。三厨房测试分别在 `1:1`、`2:2`、`3:3` 记录三个有界动作，显示实时相机窗口，在最后一帧后自动关闭，再无窗口地重放相同动作并比较结果。文件保存在忽略目录 `data/test/`。

资源安装会在终端显示各压缩包的缓存、下载和解压状态。下载时约每五秒显示已接收字节数；服务器提供总长度时，还显示总量和百分比。下载中断后，若服务器支持字节范围请求，`.part` 文件可以续传。

```sh
python3 tests/full_robocasa.py .local/robocasa-venv/bin/python \
  tools/robocasahrun.py data/test/<run-id>/robocasa
```

在软件包边界，对固定到候选版本的原生和 RoboCasa 完整预设图及本地包 TOML 运行 IsOS `pkg check`。它重新构建并验证精确字节、应用每张图，检查已准入的观测和命令、拒绝、服务失败、停止及套接字清理。随后 `tests/package_logs.py <check-output>` 检查 IsOS 将各服务的就绪行捕获为 `package_service_output`，带有包标识、实例、输出流及运行 ID，并检查 EOS 日志使用同一运行 ID。JSONL 信封和持久日志池归 IsOS 所有；软件包只写入有界服务输出。相邻仓库可用时，参阅 IsOS [日志指南](https://github.com/Island-Team/isos-p/blob/master/docs/isos/core/logger.md)。

```sh
ISOS_AETHER_BIN_DIR=<isos-build-directory> isos pkg check \
  --source "$PWD" --version <candidate-version> --output <empty-output-directory> \
  --graph <native-graph.json> --graph <robocasa-graph.json> \
  --package-config <local-package.toml>
python3 tests/package_logs.py <check-output-directory>
```

## 本地验证，2026-11-16

原生自定义场景 GUI 回放通过并自动退出。使用 256 × 192 相机设置的原生和 RoboCasa 完整图在候选版本 `0.2.6` 上通过 IsOS `pkg check`；`tests/package_logs.py` 找到服务输出与 EOS 运行 ID 的对应记录。三厨房 GUI 记录和无窗口重放在 `1:1`、`2:2`、`3:3` 全部完成，每个厨房执行三个动作且摘要一致。这些有界动作没有完成 `CloseFridge` 任务；此回放验证启动、动作传递、确定性重放、GUI 自动退出及清理。完整本地输出位于忽略目录 `data/test/20261116-full-interfaces/`，其中包含 `robocasa-three-final/summary.json`。
