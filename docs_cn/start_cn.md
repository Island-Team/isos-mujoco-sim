# 构建与运行模拟器

[English](../docs/start.md) · [Docs](README_cn.md)

先完成下方源码构建，再选择本地 RoboCasa 回合或原生兼容场景。托管部署见 [IsOS 部署](#managed-deployment)。本页拥有操作流程；节点与服务字段的精确定义由链接的参考页拥有。

<a id="从源码首次运行"></a>
## 从源码首次运行

本指南包含两条本地流程。`./launch.sh` 在前台运行当前上游 RoboCasa `CloseFridge` 冒烟回合。`./build.sh` 构建本仓库的 C++ MuJoCo 核心及 IsOS/EOS 软件包包装层，并在下载前询问后准备 RoboCasa；`./launch.sh --scene ...` 在后台启动该兼容性模拟器。本地 RoboCasa 冒烟运行器直接调用 Gym；打包后的 RoboCasa worker 通过独立的 `robocasa_core.Hardware` API 向 EOS 提供设备。软件包路径见[受管理后端指南](start_cn.md)。

<a id="前提条件"></a>
## 前提条件

Linux 命令从仓库根目录执行。RoboCasa Python 冒烟运行也支持 Windows PowerShell，使用 `tools/robocasasetup.ps1` 和 `tools/robocasarun.ps1`；C++ 构建和原生启动器仍是 Linux 流程。RoboCasa 设置需要 `git`、`uv`、Python 3.11，以及下载源码和资源所需的网络连接。私有 Python 环境位于 `.local/robocasa-venv`。首次下载包含多个较大的归档，请确认仓库所在磁盘有足够空间。

Windows 上先安装 Python 3.11、Git for Windows 和 `uv`，再从仓库根目录打开 PowerShell 运行。运行器使用 MuJoCo GLFW 后端，默认打开图形窗口；`-NoGui` 关闭图像窗口（渲染相机仍需要支持 OpenGL 的桌面会话）。设置 `$env:ROBOCASA_ROOT` 可更换源码和资源目录。其他任务或固定厨房场景需要较大的完整资源集时使用 `-Full`。

```powershell
.\tools\robocasasetup.ps1
.\tools\robocasarun.ps1 -Task CloseFridge -Seed 42 -Steps 20
# 不打开图像窗口：
.\tools\robocasarun.ps1 -Task CloseFridge -Seed 42 -Steps 20 -NoGui
```

若 PowerShell 阻止本地脚本，仅对当前进程放行：`Set-ExecutionPolicy -Scope Process Bypass`。

C++ 构建需要 **MuJoCo 3.3.1** 安装目录、C++20 编译器、CMake 3.22 或更新版本、protobuf、gRPC、libjpeg，以及供构建工具使用的 Python 3。`MUJOCO_ROOT` 应指向绝对路径，其下需有 `include/mujoco/mujoco.h`、`lib/libmujoco.so.3.3.1`、`bin/compile` 和 `bin/simulate`。RoboCasa 的私有 Python 环境会安装自己的 MuJoCo 3.3.1 软件包；原生库路径供本仓库的 C++ 构建和包装层使用。

<a id="配置本地路径"></a>
## 配置本地路径

开发配置 [`config/dev.toml`](../config/dev.toml) 提供仓库级默认值，并指定 [`config/benchmarks/robocasa.toml`](../config/benchmarks/robocasa.toml) 作为基准配置。把示例文件复制为忽略的 `.env`，再设置本机的 MuJoCo 路径。同名 `.env` 赋值覆盖 `config/dev.toml`。将机器特定路径保存在 `.env`，避免写入仓库。

```sh
cp .env.example .env
# 编辑 .env 并设置实际的绝对路径，例如：
# export MUJOCO_ROOT=/opt/mujoco-3.3.1
```

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| `MUJOCO_ROOT` | 空；在 `.env` 中设置 | 开发构建和查看器 |
| `DEV_GUI` | `true` | 开发启动的默认 GUI |
| `ROBOCASA_ROOT` | 空，即 `.local/robocasa` | RoboCasa 源码和解压后的资源 |
| `BENCHMARK_CONFIG` | `config/benchmarks/robocasa.toml` | `config/dev.toml` 选择的基准配置文件 |
| `BENCHMARK_TASK` | `CloseFridge` | 默认的 RoboCasa 注册任务 |
| `BENCHMARK_SPLIT` | `target` | 任务划分：`target`、`pretrain` 或 `all` |
| `BENCHMARK_SCENE` | 空；在划分内随机选择 | 固定的厨房 `layout:style` 组合 |
| `BENCHMARK_SEED` | `42` | 重置与随机动作的种子 |
| `BENCHMARK_STEPS` | `20` | 冒烟动作数上限 |
| `BENCHMARK_CAMERA` | `robot0_agentview_left` | GUI 显示的相机视角 |
| `BENCHMARK_CAMERA_WIDTH`、`BENCHMARK_CAMERA_HEIGHT` | `1920` 和 `1080` | 实际渲染的观测像素 |
| `BENCHMARK_GUI_WIDTH` | `1920` | GUI 显示宽度，保持宽高比 |
| `BENCHMARK_RECORD_ENABLED` | `false` | 允许 `--record-demo` 写入本地硬件记录 |
| `BENCHMARK_RECORD_PATH` | `.run/hardware-record.json` | 默认本地记录文件 |
| `SIM_EXECUTABLE` | `build/eos-mujoco-sim` | `--scene` 启动器 |
| `SIM_SCENE` | `assets/scene.xml` | 原生启动器的默认场景 |
| `SIM_RUN_DIR` | `.run/mujoco` | 原生套接字、日志和进程记录 |
| `SIM_GUI` | `false` | 独立原生场景查看器 |
| `SIM_MANUAL_STEP` | `false` | 原生模拟器的初始步进模式 |

包部署使用独立的 [`config/package.toml`](../config/package.toml)；其中的主机路径和服务选择不继承开发配置或 `.env`。表中除 `MUJOCO_ROOT` 外的路径均可相对于仓库根目录。若要把 RoboCasa 源码放到别处，在 `config/dev.toml` 设置 `ROBOCASA_ROOT`，或在 `.env` 添加 `export ROBOCASA_ROOT=/absolute/path/to/robocasa`。Python 环境和 robosuite 源码仍位于本仓库忽略的 `.local/` 目录。

受管理源码包构建时，环境变量 `MUJOCO_ROOT` 优先于 `[host].mujoco_root`。两者都为空时，构建会使用本仓库现有的 `.local/mujoco-3.3.1`，因此 IsOS 可重建干净的源码检出，而无需在受版本控制的配置中写入本机路径。

软件包模式复用被 Git 忽略的 `.local/package-build/` CMake 构建树。运行 `python3 tests/archive.py` 验证归档确定性。

运行 `python3 tests/config_modes.py` 可检查两个配置边界：修改软件包选择不会改变 `./launch.sh --show-config` 的结果，而开发设置及 `.env` 不会改变软件包构建所选的 MuJoCo 根目录。

表中的 `BENCHMARK_*` 值来自所选基准 TOML 文件的 `[task]`、`[camera]`、`[gui]` 和 `[record]`。根目录的 `BENCHMARK_CONFIG` 指定该文件；可在 `config/dev.toml` 修改路径以使用另一份纳入版本控制的预设。`.env` 赋值覆盖基准文件中的值，单次命令参数再覆盖 `.env`。

<a id="ubuntu-2204-构建"></a>
## Ubuntu 22.04 构建

默认原生构建保持不变。在 Ubuntu 22.04、glibc 2.35 和 Python 3.11 或更新版本的环境中，选择可选的 `ubuntu22` CMake 预设。仅此配置检查主机构建基线及打包 ELF 的 glibc 需求，并拒绝交叉编译。该配置的开发和打包构建使用独立的 `.local/package-build-ubuntu22` 目录，默认构建保留原有目录。

```sh
export MUJOCO_ROOT="$HOME/.local/opt/mujoco-3.3.1"
cmake --preset ubuntu22 -DPython3_EXECUTABLE="$(python3 -c 'import sys; print(sys.executable)')"
cmake --build --preset ubuntu22 --parallel 4
ctest --preset ubuntu22
MUJOCO_BUILD_PROFILE=ubuntu22 ./build.sh --output "$PWD/data/test/ubuntu22-package/profile-asset" --version 0.2.8
```

请使用实际 MuJoCo 路径及空输出目录，测试通过后再打包。0.2.8 仍为候选版本，正式发布遵循[包契约](package_cn.md)。

<a id="构建和运行原生模拟器"></a>
## 构建和运行原生模拟器

设置 `MUJOCO_ROOT` 后，构建全部目标、准备 RoboCasa 并运行 C++ 测试：

```sh
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`./build.sh` 将原生程序输出到 `build/`。开发构建还会检查 RoboCasa 源码、Python 环境和资源。若有缺失，下载前会先询问；拒绝下载时原生程序已构建，但完整设置尚未完成，脚本退出。`mujoco-core` 可供开发时直接加载场景并推进引擎；`eos-mujoco-sim` 是面向 IsOS/EOS 的包装层。测试覆盖场景加载、回放、渲染、套接字、包生成和停止行为。CMake 的 MuJoCo 检查失败通常意味着 `MUJOCO_ROOT` 指向了其他版本，或目录缺少所需头文件、库或工具。

若不经过 IsOS 检查兼容性包装层，运行：

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

启动器在后台启动 `build/eos-mujoco-sim`，并报告模拟器及私有 benchmark 套接字路径。默认的仅所有者可访问运行目录是 `.run/mujoco/`；启动失败时读取 `logs/dev/native/latest.log`。`./kill.sh` 仅停止该启动器记录的进程。运行 `./launch.sh --list-scenes` 可查看软件包拥有的原生场景 ID 和 XML 路径。其他场景可用 `--scene navigation` 或 XML 路径。在配置中设置 `SIM_SCENE` 后，可运行 `./launch.sh --native` 使用默认值。`--gui` 打开独立的静态 MuJoCo 查看器，需要图形显示环境；它不展示运行中模拟器的实时状态。若启动时使用 `--run-dir PATH`，停止时也要向 `kill.sh` 传入相同路径。

这些原生场景属于兼容性测试场景。构建包、安装、图校验、就绪检查、日志和受管理停止见 [IsOS 部署](#managed-deployment)。使用所选包的精确候选版本；托管硬件运行不会将 RoboCasa 冒烟回合变成 EOS 基准评测。

<a id="运行首个-robocasa-任务"></a>
## 运行首个 RoboCasa 任务

先列出并选择已注册任务，也可先查看生效的默认值：

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
```

任务列表显示类型、上游时长和本仓库是否完成本地冒烟验证。`--list-kitchens` 显示所选划分的厨房布局与风格候选组合；具体任务可能排除其中一些组合；target 划分使用 `1:1` 至 `10:10` 的配对场景。不传 `--kitchen-scene` 时，由 RoboCasa 在划分内选择场景。`--list-benchmarks --split all` 列出全部已注册 RoboCasa 任务；`--filter TEXT` 只缩小输出，不修改配置。随附资源集已验证 RoboCasa 按种子选择场景时的 `CloseFridge`。选择其他任务或固定厨房场景时，脚本会在下载完整物体资源前询问；压缩文件约 8 GB，解压还需额外空间。拒绝下载不影响首个任务资源。完成完整设置后，可用 `./launch.sh --benchmark CloseFridge --kitchen-scene 1:1 --steps 20` 选择固定 target 场景。在 `config/benchmarks/robocasa.toml` 的 `[task]` 中设置共享默认值，或在 `.env` 作本地覆盖。单次运行的命令行参数优先于两者。

```sh
./launch.sh --robocasa --seed 42 --steps 20
```

不带参数的 `./launch.sh` 运行同一任务和默认参数。若未通过 `./build.sh` 完成设置，启动器会检查 RoboCasa 源码、Python 环境和资源；下载前提示 `Download and set up ...? [y/N]`。输入 `y`，安装到 `ROBOCASA_ROOT` 或本地默认目录。输入 `N` 则退出，不启动回合。后续运行复用已下载的源码和资源。决定下载后，也可直接运行 `./tools/robocasasetup.sh`；`python3 tools/robocasasource.py check --path .local/robocasa` 只检查现有源码，不下载。

命令先输出 RoboCasa 启动信息，最后输出类似 JSON：

```json
{"instruction":"Close the fridge doors.","scene":"8:8","seed":42,"split":"target","steps":20,"success":false,"task":"robocasa/CloseFridge"}
```

`--gui-exit-ms 300` 在最后一帧显示 300 毫秒后关闭窗口，无需按键。`--record-actions PATH` 保存采样动作序列；`--replay-actions PATH` 在相同任务、数据分组、场景和种子下重用该序列。使用[完整接口回放](development_cn.md)测试三个固定厨房场景及自动关闭窗口。

`success` 来自 RoboCasa 的冰箱门判定规则。随附运行器采样有界随机动作，并将底盘运动置零；`false` 是有效的冒烟结果，不代表安装失败。`--steps` 指定动作预算，`--seed` 控制重置与动作采样。回合结束后进程自行退出，无需运行 `kill.sh`。任务、资源来源、许可和限制见[基准指南](core/benchmark_cn.md)。

<a id="列出并选择任务"></a>
## 列出并选择任务

```sh
./launch.sh --show-config
./launch.sh --list-benchmarks --filter Fridge
./launch.sh --list-kitchens
./launch.sh --benchmark CloseFridge --split target --seed 42 --steps 20
./launch.sh --list-scenes
./launch.sh --scene navigation --no-gui
```

基准列表取自固定版本的 RoboCasa 任务注册表。默认显示有 `target` 数据集条目的任务；使用 `--split pretrain` 或 `--split all` 查看其他集合。每行包含上游回合时长和本地资源状态。`--list-kitchens` 显示厨房布局与风格候选组合；具体任务可能排除某些组合。target 划分使用 `1:1` 至 `10:10` 的配对场景；不传 `--kitchen-scene` 时，RoboCasa 按种子选择场景。`CloseFridge` 已通过冒烟验证。选择其他已注册任务或固定厨房场景需要完整物体资源。启动器和默认 `./build.sh` 会在配置的选择需要这些资源时先询问；压缩文件约 8 GB，解压还需额外空间。拒绝下载不影响首个任务设置。也可显式运行 `./tools/robocasasetup.sh --full`。更广的目录已在上游注册，但尚未逐任务完成冒烟验证。原生场景列表取自软件包拥有的目录，显示两个兼容性场景 ID。

在 `config/benchmarks/robocasa.toml` 的 `[task]` 中设置 `name`、`split`、`scene`、`seed` 和 `steps`，可修改共享默认值。`config/dev.toml` 通过 `BENCHMARK_CONFIG` 指向该文件。被忽略的 `.env` 可用 `export BENCHMARK_TASK=...` 等赋值覆盖，也可设置 `export BENCHMARK_SCENE=1:1`。命令行参数优先于两者。运行 `./launch.sh` 使用配置的基准，或运行 `./launch.sh --native` 使用配置的原生 `SIM_SCENE`。`--show-config` 输出生效的选择。JSON 结果会以 `layout:style` 记录实际厨房 `scene`。上游时长是任务元数据；此运行器的 `--steps` 是较短的冒烟预算，不表示完成正式评测回合。

纳入版本控制的 [RoboCasa 预设](../config/benchmarks/robocasa.toml) 将任务选择、相机观测和 GUI 显示设置分组。要使用另一份预设，可在`config/dev.toml` 将 `BENCHMARK_CONFIG` 设为其路径。启动前，加载器会拒绝缺失的分组或字段、未知字段以及错误的 TOML 类型。

<a id="相机和显示配置"></a>
## 相机和显示配置

RoboCasa 提供三个 RGB 视角：`robot0_agentview_left`、`robot0_agentview_right` 和 `robot0_eye_in_hand`。`BENCHMARK_CAMERA` 选择 dev 图形窗口显示的视角，不会移除其他相机观测。`BENCHMARK_CAMERA_WIDTH` 和 `BENCHMARK_CAMERA_HEIGHT` 指定实际渲染的观测尺寸（每边 64–2048 像素，检入预设默认 1920×1080）。修改它们会影响图像像素和运行耗时，因此报告基准结果时应记录。`BENCHMARK_GUI_WIDTH` 只缩放显示窗口（256–3840 像素，检入预设默认 1920），保持观测分辨率及画面宽高比。结果 JSON 记录相机和渲染尺寸。

可在 `config/benchmarks/robocasa.toml` 的 `[camera]` 和 `[gui]` 中设置这些值，再由 `.env` 的对应 `BENCHMARK_*` 变量覆盖，或使用单次命令参数：

```sh
./launch.sh --benchmark CloseFridge --camera robot0_agentview_right --gui-width 960
./launch.sh --benchmark CloseFridge --camera-width 512 --camera-height 512 --gui-width 960
```

使用检入预设时，第一条命令在宽 960 像素的窗口中显示 1920×1080 观测。第二条将观测改为 512×512，并以宽 960 像素显示；渲染像素数少于预设。使用 `--no-gui` 可关闭窗口。

<a id="本地硬件记录"></a>
## 本地硬件记录

`config/benchmarks/robocasa.toml` 中的 `[record].enabled` 默认 `false`；`[record].path` 默认 `.run/hardware-record.json`。启用后，`./launch.sh --record-demo` 在该路径写入两步 PandaOmron 硬件记录，`./launch.sh --replay-record FILE` 检查指定记录。记录用于硬件控制测试，不包含基准奖励、成功信息、任务文本或图像。格式与重放限制见[记录接口](core/robocasa_cn.md)。

<a id="当前-028-硬件候选"></a>
## 当前 0.2.8 硬件候选

当前源码为未发布 `0.2.8` 候选，采用 schema `0.2.1`、`isos_node_v2`、七种硬件类型和两个由 IsOS 监督的服务。精确声明与发布条件见[软件包](package_cn.md)。

<a id="managed-deployment"></a>
## IsOS 部署

先构建并测试，再暂存未发布候选。清单与所有图包锁定必须使用同一精确版本；源码候选不等于已发布版本。

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh --output /absolute/empty/candidate-directory --version 0.2.8
isos pkg verify /absolute/empty/candidate-directory/release.json /absolute/empty/candidate-directory/mujoco-sim-v0.2.8-linux-x86_64.tar.gz
isos pkg install --source /absolute/path/to/isos-mujoco-sim --version 0.2.8 --allow-source-build
isos pkg configure island/mujoco-sim@0.2.8 --service native
# 选择另一服务：
isos pkg configure island/mujoco-sim@0.2.8 --service robocasa
```

归档名以 `release.json` 的实际声明为准。原生服务需要所选 MuJoCo 安装；RoboCasa 需要配置的 Python 解释器与资产。Apply 前检查并保存包配置。交互式 RoboCasa 配置在路径缺失时提供安装选项；拒绝后仍可手工配置。

在 IsOS 选择包的 Native robot 或 RoboCasa robot 节点集。执行器命令输入经过 EOS parts Dispatcher 绑定，并填写相机尺寸。验证图、Apply 修订，再 Run。安装与 Apply 都不启动部署。IsOS 只启动所选服务并将端点传给 EOS；EOS 检查设备健康后才使端口就绪。参见[包声明](package_cn.md)与[节点组](node/README_cn.md)。

排查前先找到当前运行及其第一条就绪或失败事件。IsOS 将服务 stdout/stderr 捕获为 `package_service_output`；使用运行 ID 和服务实例关联 EOS 记录。进程运行或套接字存在不足以证明设备就绪。修复宿主路径、包字节不匹配或渲染不可用后，再重试准入。

通过 IsOS 请求部署 Stop。EOS 先关闭运动准入并检查整机服务证明，IsOS 再终止其服务子进程。证明缺失或回复丢失仍为未知；进程退出不能证明安全停止。不要自动重发结果不确定的已下发命令。修复服务并获得新的准入后再运动。本地 `./kill.sh` 只控制开发启动器，不控制托管部署。

升级时选择并验证新的精确包锁定，检查端口与配置变化，重新 Validate、Apply 后启动新运行。重建同一未发布候选后也须再次 Apply，以绑定新的已验证库摘要。恢复过程中保留未解决的命令与 Stop 结果。[开发指南](development_cn.md)提供发布验收命令；[变更记录](changelog_cn.md)保留历史候选与迁移说明。

<a id="开发界面和本地日志"></a>
## 开发界面和本地日志

运行 `./launch.sh --benchmark CloseFridge --steps 20` 可在图像窗口查看 RoboCasa 当前回合的相机画面；回合结束后在图像窗口按任意键关闭。`--no-gui` 关闭图形窗口。运行 `./launch.sh --scene navigation` 会默认打开独立的静态 MuJoCo XML 查看器，`./kill.sh` 停止原生进程及查看器。后者不显示套接字模拟器的实时状态。

每次本地运行的日志保存在被 Git 忽略的 `logs/dev/`。`logs/dev/robocasa/latest.log` 和 `logs/dev/native/latest.log` 指向最近的运行文件；原生查看器日志使用同一时间戳的 `*-viewer.log`。启动器检查活跃套接字后自动清理遗留套接字。

<a id="故障排查"></a>
## 故障排查

| 现象 | 检查方法 |
| --- | --- |
| `Set MUJOCO_ROOT` 或缺少 `libmujoco.so.3.3.1` | 在 `.env` 中设置绝对的 MuJoCo 3.3.1 根目录，再运行 `./build.sh`。 |
| 出现 RoboCasa 设置提示 | 核对 `ROBOCASA_ROOT`；仅在希望下载缺少的源码、运行环境或资源时输入 `y`。 |
| 下载中断 | 再运行 `./tools/robocasasetup.sh`；脚本复用有效归档并续传未完成下载。 |
| RoboCasa 输出 Python 回溯 | 先读回溯上方的第一条错误，检查源码和资源目录，再运行设置脚本。 |
| `--scene` 提示可执行文件不存在 | 运行 `./build.sh`，确认 `build/eos-mujoco-sim` 存在。 |
| 原生套接字或启动失败 | 读取 `logs/dev/native/latest.log`；对该启动器启动的进程使用 `./kill.sh`。 |
| 无图形界面的主机上 `--gui` 失败 | 使用 `--no-gui`；基准和 C++ 测试均不要求桌面窗口。 |

RoboCasa 基准在前台运行，结果输出到终端。原生启动器将日志写到选定的运行目录。对于受管理部署，修改图之前先找到当前 IsOS 运行及其首条就绪或失败事件；参见[构建与运行](start_cn.md)。

0.2.8 候选配置需要 `[services.robocasa].robot = "PandaOmron"`（或已安装的其他兼容模型），并使用[全身发现准备工具](core/robocasa_cn.md)重新生成硬件/控制片段。旧录制运行器仍专用于 PandaOmron。

托管机器人图：在相机节点设置中调整分辨率（默认 1280 × 720）、JPEG 质量和采样频率。只将独立自由相机接到人类 Vision；agent 相机接到 Vision pool 供模型读取。详见 [相机接口](node/eos/hardware/camera_cn.md)。
