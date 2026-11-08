# IsOS 管理的 MuJoCo 后端

下述 `0.1.2` 软件包是使用 MuJoCo 3.3.1 的本地开发候选，尚未发布；本页后面的历史 `0.1.1` 证据仍对应 MuJoCo 3.16.0。

**当前实现：** 本页记录现有包与集成路径。[包描述符与声明](../interfaces/package_cn.md)和[模拟器套接字](../interfaces/socket_cn.md)是本包拥有的字段契约；[设计](../architecture_cn.md)与 [TODO](../todo_cn.md)区分新的 0.x 目标。协议或已生成描述符文件名中的 `v2` 为兼容而保留；本主题页文件名不带版本后缀。

[English](../../../docs/mujoco/usage/isos-pkg.md)

从本地源码全新安装时，先设置 `MUJOCO_ROOT`，再运行 `isos pkg install --source /absolute/path/to/isos-mujoco-sim --allow-source-build`。IsOS 调用本仓库可执行的 `build.sh --output <空暂存目录>`，验证 `release.json` 和 `asset.tar.gz` 后安装包。包声明进程入口及通用场景和设备目录，IsOS 无需 MuJoCo 专用启动路径。随后验证并应用节点集，再明确运行或重启部署；仅安装包不会改变当前运行实例。

先构建模拟器，再生成本地 `island/mujoco-sim@0.1.2` 包：

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
mkdir -p "$HOME/tmp"
export TMPDIR="$HOME/tmp"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
python3 tests/nodes.py
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
```

构建目录与临时目录应放在空间充足的文件系统上，例如设置 `TMPDIR=/home/you/tmp` 和 `--build-dir /home/you/build-mujoco`。构建工具通过 CMake 安装程序，检查安装后的 ELF 依赖，并将原生 Ubuntu、glibc 和已解析库要求写入 `release.json`。在 Ubuntu 24.04 上，资源声明 `glibc>=2.39`、`tested_ubuntu:["24.04"]`，归档中没有构建主机的 RUNPATH。若构建工具未继承环境变量，用 `--mujoco-root "$MUJOCO_ROOT"` 显式指定根目录。链接或发布前检查 `readelf -d bin/eos-mujoco-sim` 以及清单中的资源要求。

包中包含 `bin/eos-mujoco-sim`、两个场景及其资源、`backend-v2.json` 和本地 schema v4 `release.json`。构建工具还会在包目录旁生成带 SHA-256 校验值的发布归档。后端描述文件声明 `mujoco-v2` 协议、`cam-0`、`base-0`、`arm-0` 设备 ID，以及外部 MuJoCo 3.3.1 库依赖。IsOS 在运行前验证可执行文件、场景、资源和库；安装包本身不会启用部署图。

发布清单中的 `node_contributions` 声明 `sim-hardware` 节点集、`mujoco-v2` 适配器系列和由包拥有的 `eos.process.mujoco@v0.1` 进程类型。新的 `0.1.0` 图预设有七个节点：该进程、EOS 通用相机/底盘/机械臂适配器、通用 `@v0.1` 底盘/机械臂 primitive 绑定，以及相机门。IsOS 初始图提供 `eos.dispatcher.control@v0.1`，包不重复添加。每个硬件实例在 `node.adapter.package` 固定 `island/mujoco-sim@0.1.2`，选择 `mujoco-v2` 并保存所选设备 ID。EOS 验证编译的工厂，Dispatcher 仍拥有命令准入。预设只组合草稿图，并非执行授权；它不包含未注册的旧 IsOS Vision 类型。IsOS 在 Apply 前验证包和图。详见[包贡献契约](../interfaces/package_cn.md#p02-声明与图边界)。

后端节点的 `settings.env` 可设置 `MUJOCO_GUI=1` 或 `MUJOCO_GUI=true`，在支持 X11 的主机上打开 `IsOS MuJoCo — live simulation` 窗口。窗口渲染来自同一个 `SimEngine` 的相机画面；默认不显示 GUI。若请求 GUI 但显示服务不可用，模拟器启动失败。`tools/view.sh` 仍用于独立的静态场景预览。

v2 Unix 套接字帧以八字节小端长度头开头，后接 JSON 元数据和可选 JPEG 负载。元数据上限为 64 KiB，负载上限为 8 MiB。请求包含 `version: "2.0.0"`、字符串 `id`、`node` 和 `op`；响应回显 ID 与版本，并返回 `ok` 或 `error.message`。

**R05 限定范围验收：** EOS 管理的严格子进程只接受帧格式 v2 套接字，拒绝历史 gRPC 机器人套接字与 benchmark 套接字。独立直接启动仍为旧客户端与可信评测保留这些套接字。固定版本的 IsOS → EOS → MuJoCo 回放验证了两个场景中相机、底盘和机械臂的严格健康检查、只读图像及状态、子进程和套接字清理。R06 所有者停止屏障已合并，限定范围跨所有者运动与停止回放通过；更完整的 R06 故障验收仍待完成。详见[所有者套接字契约](../interfaces/socket_cn.md)和 [R05 证据](../architecture_cn.md#r05-跨所有者验收)。

| 操作 | 请求字段 | 响应字段 |
| --- | --- | --- |
| `health` | 通用字段 | `accepted: bool` |
| `camera_capture` | 通用字段 | `format: "jpeg"`、`rgb_length: u32` 字节、`depth_available: false`、`width_px: u32`、`height_px: u32` 和 JPEG 负载 |
| `base_observe` | 通用字段 | `position_m: [f64; 2]`、`linear_velocity_m_s: [f64; 2]`、`yaw_rad: f64`、`angular_velocity_rad_s: f64` |
| `base_move` | `linear_x_m_s`、`linear_y_m_s`、`angular_z_rad_s: f64`，`valid_for_ms`，`command_id: string` | `accepted: bool`；租期结束后底盘停止 |
| `manipulator_observe` | 通用字段 | 六个关节位置、速度，以及末端位置和四元数 |
| `manipulator_move` | 六个关节目标和 `command_id: string` | `accepted: bool` |
| `stop` | `command_id: string` | `accepted: bool`；停止底盘和机械臂 |

`timestamp_ns` 是以纳秒为单位的模拟时间，`sequence` 是引擎步数。浮点数必须有限，运动边界由引擎强制执行。套接字权限为 `0600`，正常停止时会被移除。IsOS 验证包并把可执行文件及场景传给 EOS；EOS 将模拟器作为直接子进程启动，并使用硬件适配器连接套接字。限定范围的 R06 回放已证明两个场景在终止和回收前完成物理停止；R05 清理结果本身不能证明这一点。

## 验证

2026-10-30 的现有基线在 Ubuntu 和 MuJoCo 3.3.1 上通过了十个 CTest 用例。`tests/v2.py` 覆盖 JPEG 捕获、底盘运动、六关节命令、安全停止和套接字清理。GUI 检查还验证了可见窗口、运动后像素变化，以及显示服务不可用时的启动失败。完整日志保存在本地 `logs/test/2026-10-30-v2-live/`。新增节点声明可用 `python3 tests/nodes.py` 检查，并需通过 IsOS 与 EOS 的完整图准入及运行集成测试。

2026-10-30，旧版六节点预设及端口元数据通过 `python3 tests/nodes.py` 的四个测试。`python3 tools/bundle.py --build-dir build --output logs/test/20261030-general-interfaces/bundle-r3` 成功生成当时的发布候选包，`ctest --test-dir build --output-on-failure` 的十个模拟器测试全部通过。完整本地输出保存在 `logs/test/20261030-general-interfaces/`。当时的八节点预设也用相同的 Python 命令检查；2026-10-31 的模拟器基线十个测试通过，日志在 `logs/test/20261031-generic-device-preset/`。

随后，独立的 IsOS 目录链接旧版 `bundle-r3`，使用场景和套接字参数预览 `sim-hardware`，并通过 EOS `aether-profile` 验证生成的图。该预览添加六个节点，只在当时四个 MuJoCo 类型上保留包引用，并报告三个由 IsOS 管理的进程。复现细节见 `logs/test/20261030-general-interfaces/graph-preview.log`。后续 EOS 与 IsOS 的通用设备及 primitive 契约已支持新的七节点预设；详见 R05 跨所有者验收。

## 软件包 0.1.2 检查（2026-10-31）

`python3 tests/nodes.py`、`python3 tests/release.py` 和 `ctest --test-dir build --output-on-failure` 通过（10 项模拟器测试）。`python3 tools/bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` 暂存的软件包在发行清单与描述文件中均报告 `0.1.2`。描述文件 schema 和套接字协议保持 `2.0.0`。输出位于忽略 Git 的 `logs/test/20261031-version-alignment/`。
