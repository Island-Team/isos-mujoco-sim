# 开发与验证软件包

[English](../docs/development.md) · [Docs](README_cn.md)

使用 C++20、根目录 CMake 与格式配置。`src/mujoco/` 拥有原生场景引擎，`src/isos/` 拥有原生服务，`src/plugin/` 拥有 EOS 适配器；`robocasa_core/` 与 `tools/robocasa_worker.py` 拥有 Python 硬件边界和独立服务。`tools/nodes.py` 与 `tools/bundle.py` 声明并打包两个服务。

## 开发流程

从已确认集成目标创建聚焦的 `fix/`、`test/`、`docs/` 或 `refactor/` 分支，保留无关改动。公共行为变化时，同步更新所属节点、包或核心契约、实现、样本、示例及双语文档。独立审查、PR、测试分支、合并和清理遵循[共享发布规则](conventions.v2.0.0_cn.md#变更与发布流程)；本地检查不发布软件包。

新增设备或场景时先定义问题与支持能力，再更新 `tools/catalog.py` 或 `tools/nodes.py`、服务处理、适配器转换、包配置和所属参考页。保持 EOS Dispatcher 准入与 Stop 证明、精确版本身份、原生/RoboCasa 设备隔离及评测隐私。移除组件前检查构建、安装包、运行时和测试调用方。

## 常规检查

使用实际 MuJoCo 安装路径，将完整命令输出保存到忽略目录 `data/test/<run-id>/`。Ubuntu 22.04 构建配置及宿主要求见[开始使用](start_cn.md#ubuntu-2204-构建)。

```sh
cmake -S . -B build -DMUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
cmake --build build -j4
ctest --test-dir build --output-on-failure
python3 tests/catalogtest.py
python3 tests/nodes.py
python3 tests/release.py
python3 tests/config_modes.py
python3 tests/build_env.py
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tools/check_docs.py --all
git diff --check
```

按根目录配置，对修改的 C++ 文件运行 `clang-format --dry-run --Werror`。Python 硬件变化需要桩单元测试：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v`；记录回放变化使用 `robocasarecord.py`，私有工作进程使用 `robocasaworker.py`。标准负载变化还需用所选 IsOS profile 程序和已构建插件运行 `tests/eos_contracts.py`。在变化的真实边界检查成功、拒绝、服务失败与 Stop。上方完整回放依赖已准备的模拟环境，只能证明其声明范围。

文档检查器验证双语树、根指南、源码 README 和样本 README 的相对文件及章节锚点。纯文档变化运行它、两个固定设计检查及相关声明检查；目录迁移不代表新运行时或发布验收。移动共享规范时保持其与对应上游版本逐字节一致。

## 文档重构验证 2026 年 11 月 20 日

运行上方文档检查、R05/R06 固定设计检查、`tests/catalogtest.py`、`tests/nodes.py`、`tests/release.py`、`tests/config_modes.py`、`tests/build_env.py` 和 `git diff --check` 均通过。链接检查覆盖 46 个 Markdown 文件，损坏相对链接为零；双语各 19 页，路径镜像一致，共享规范仅移动、字节未变。R05/R06 分别检查 31/48 个固定案例；目录、节点、发布、配置测试分别通过 8/17/1/2 项，构建环境隔离检查通过。`python3 -m py_compile tools/check_docs.py tests/fixtures/strict_socket/check.py tests/fixtures/strict_stop_lane/check.py` 也通过。完整命令和输出位于忽略目录 `data/test/20261120-docs-rewrite/`。本次只验证文档与声明边界，没有重新执行 CTest、真实 Gym 或托管包验收，也不发布软件包。

<a id="完整接口回放"></a>
## 完整接口回放

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

<a id="interaction-route-todo"></a>
## 交互路线验收 TODO

**目标设计——尚未实现。** 本任务依赖 IsOS 与 EOS 实现版本化交互声明和路线准入。

- [ ] 绑定所有者精确支持的交互声明，不从套接字操作推断角色。
- [ ] 扩展组合所有者回放，将捕获帧传给已准入订阅路线，并在捕获进行中 Stop。使用 `python3 tests/full_interfaces.py build/eos-mujoco-sim assets/scene.xml data/test/<run-id>/native --gui` 作为现有服务边界基线，再加入所有者路线断言；此基线本身不证明未来路线。
- [ ] 拒绝不可用服务、过期运行/修订、错误设备、无效帧、阻塞消费者和缺失路线；确认运动仍须 Dispatcher 准入，结果不确定的命令不会换新 ID 重放。
- [ ] 描述路线已支持前，同步双语文档并保存完整跨所有者证据。

## 机器人全身候选验证，2026 年 11 月 22 日

使用 `PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robotbody.py' -v` 验证多臂发现、缺失观测、躯干实测米制通道、未知绝对控制、缩放后非零的中性动作拒绝和 Stop 门控；原硬件与 worker 套件仍须通过。`tools/robot_graph.py` 从真实控制器 manifest 生成图片段。

准备好的固定运行时中，PandaOmron 成功读取七个设备（三相机、机械臂、夹爪、底盘、躯干），提交四种控制并验证重复 ID 不重复执行，独立 Stop 边界返回 `stopped`。Release 构建和 35 项 CTest 全部通过，包含原生插件、严格 socket 与 Stop。固定底座 `Panda` 无法加载当前厨房：上游 reset 要求 `mobilebase0_joint_mobile_yaw`，因此不声明为已验证配置。多臂桩测试不代表所有上游机器人及未安装模型/IK 依赖均已验证。完整日志及生成 manifest 位于忽略目录 `data/test/20261122-body/`。源码软件包构建仅为未发布本地候选，已安装 EOS/EI 验证另行进行。

`python3 tests/plugin_body.py build/libmujoco-eos-node.so` 额外验证原生适配器边界：躯干米/弧度混合通道、重复名称与无效单位拒绝、manifest 摘要变化导致 readiness 拒绝。
