# 从源码首次运行

[MuJoCo 文档](../README_cn.md) · [构建与运行](README_cn.md) · [RoboCasa 基准](../benchmarks/Robocasa/README_cn.md) · [English](../../../docs/mujoco/usage/dev.md)

本指南包含两条本地流程。`./launch.sh` 在前台运行当前上游 RoboCasa `CloseFridge` 冒烟回合。`./build.sh` 构建本仓库的 C++ MuJoCo 核心及 IsOS/EOS 软件包包装层，并在下载前询问后准备 RoboCasa；`./launch.sh --scene ...` 在后台启动该兼容性模拟器。RoboCasa 环境目前尚未连接 EOS。将 C++ 包安装到 IsOS 时，使用[受管理后端指南](isos-pkg_cn.md)。

## 前提条件

在 Linux 上从仓库根目录执行命令。RoboCasa 设置需要 `git`、`wget`、`uv`、Python 3.11，以及下载源码和资源所需的网络连接。私有 Python 环境位于 `.local/robocasa-venv`。首次下载包含多个较大的归档，请确认仓库所在磁盘有足够空间。

C++ 构建需要 **MuJoCo 3.3.1** 安装目录、C++20 编译器、CMake 3.22 或更新版本、protobuf、gRPC、libjpeg，以及供构建工具使用的 Python 3。`MUJOCO_ROOT` 应指向绝对路径，其下需有 `include/mujoco/mujoco.h`、`lib/libmujoco.so.3.3.1`、`bin/compile` 和 `bin/simulate`。RoboCasa 的私有 Python 环境会安装自己的 MuJoCo 3.3.1 软件包；原生库路径供本仓库的 C++ 构建和包装层使用。

## 配置本地路径

根目录的 [`config.toml`](../../../config.toml) 提供仓库级默认值，并指定 [`config/benchmarks/robocasa.toml`](../../../config/benchmarks/robocasa.toml) 作为基准配置。把示例文件复制为忽略的 `.env`，再设置本机的 MuJoCo 路径。同名 `.env` 赋值覆盖 `config.toml`。将机器特定路径保存在 `.env`，避免写入仓库。

```sh
cp .env.example .env
# 编辑 .env 并设置实际的绝对路径，例如：
# export MUJOCO_ROOT=/opt/mujoco-3.3.1
```

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| `MUJOCO_ROOT` | 空；在 `.env` 中设置 | 原生构建、查看器和 IsOS 软件包 |
| `SIM_PROFILE` | `isos-pkg`；本机设置 `dev` | 构建和启动模式 |
| `DEV_GUI` | `true` | dev 模式的默认 GUI |
| `ROBOCASA_ROOT` | 空，即 `.local/robocasa` | RoboCasa 源码和解压后的资源 |
| `BENCHMARK_CONFIG` | `config/benchmarks/robocasa.toml` | 根目录 `config.toml` 选择的基准配置文件 |
| `BENCHMARK_TASK` | `CloseFridge` | 默认的 RoboCasa 注册任务 |
| `BENCHMARK_SPLIT` | `target` | 任务划分：`target`、`pretrain` 或 `all` |
| `BENCHMARK_SCENE` | 空；在划分内随机选择 | 固定的厨房 `layout:style` 组合 |
| `BENCHMARK_SEED` | `42` | 重置与随机动作的种子 |
| `BENCHMARK_STEPS` | `20` | 冒烟动作数上限 |
| `BENCHMARK_CAMERA` | `robot0_agentview_left` | GUI 显示的相机视角 |
| `BENCHMARK_CAMERA_WIDTH`、`BENCHMARK_CAMERA_HEIGHT` | 各 `256` | 实际渲染的观测像素 |
| `BENCHMARK_GUI_WIDTH` | `768` | GUI 显示宽度，保持宽高比 |
| `SIM_EXECUTABLE` | `build/eos-mujoco-sim` | `--scene` 启动器 |
| `SIM_SCENE` | `assets/scene.xml` | 原生启动器的默认场景 |
| `SIM_RUN_DIR` | `.run/mujoco` | 原生套接字、日志和进程记录 |
| `SIM_GUI` | `false` | 独立原生场景查看器 |
| `SIM_MANUAL_STEP` | `false` | 原生模拟器的初始步进模式 |

表中除 `MUJOCO_ROOT` 外的路径均可相对于仓库根目录。若要把 RoboCasa 源码放到别处，在 `config.toml` 设置 `ROBOCASA_ROOT`，或在 `.env` 添加 `export ROBOCASA_ROOT=/absolute/path/to/robocasa`。Python 环境和 robosuite 源码仍位于本仓库忽略的 `.local/` 目录。

表中的 `BENCHMARK_*` 值来自所选基准 TOML 文件的 `[task]`、`[camera]` 和 `[gui]`。根目录的 `BENCHMARK_CONFIG` 指定该文件；可在 `config.toml` 修改路径以使用另一份纳入版本控制的预设。`.env` 赋值覆盖基准文件中的值，单次命令参数再覆盖 `.env`。

## 构建和运行原生模拟器

设置 `MUJOCO_ROOT` 后，构建全部目标、准备 RoboCasa 并运行 C++ 测试：

```sh
./build.sh
ctest --test-dir build --output-on-failure
build/mujoco-core --scene "$PWD/assets/scene.xml" --seed 42 --steps 20
```

`./build.sh` 将原生程序输出到 `build/`。`SIM_PROFILE=dev` 时，还会检查 RoboCasa 源码、Python 环境和资源。若有缺失，下载前会先询问；拒绝下载时原生程序已构建，但完整设置尚未完成，脚本退出。`mujoco-core` 可供开发时直接加载场景并推进引擎；`eos-mujoco-sim` 是面向 IsOS/EOS 的包装层。测试覆盖场景加载、回放、渲染、套接字、包生成和停止行为。CMake 的 MuJoCo 检查失败通常意味着 `MUJOCO_ROOT` 指向了其他版本，或目录缺少所需头文件、库或工具。

若不经过 IsOS 检查兼容性包装层，运行：

```sh
./launch.sh --scene pick-place --no-gui
./kill.sh
```

启动器在后台启动 `build/eos-mujoco-sim`，并报告模拟器及私有 benchmark 套接字路径。默认的仅所有者可访问运行目录是 `.run/mujoco/`；启动失败时读取 `logs/dev/native/latest.log`。`./kill.sh` 仅停止该启动器记录的进程。运行 `./launch.sh --list-scenes` 可查看软件包拥有的原生场景 ID 和 XML 路径。其他场景可用 `--scene navigation` 或 XML 路径。在配置中设置 `SIM_SCENE` 后，可运行 `./launch.sh --native` 使用默认值。`--gui` 打开独立的静态 MuJoCo 查看器，需要图形显示环境；它不展示运行中模拟器的实时状态。若启动时使用 `--run-dir PATH`，停止时也要向 `kill.sh` 传入相同路径。

这些原生场景属于兼容性测试场景。构建包、安装、图校验、就绪检查、日志和受管理停止见 [IsOS/EOS 后端指南](isos-pkg_cn.md)。该路径使用精确的 `island/mujoco-sim@0.1.2` 本地候选包，不会将 RoboCasa 冒烟回合变成 EOS 基准评测。

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

`SIM_PROFILE=dev` 时，不带参数的 `./launch.sh` 运行同一任务和默认参数。若未通过 `./build.sh` 完成设置，启动器会检查 RoboCasa 源码、Python 环境和资源；下载前提示 `Download and set up ...? [y/N]`。输入 `y`，安装到 `ROBOCASA_ROOT` 或本地默认目录。输入 `N` 则退出，不启动回合。后续运行复用已下载的源码和资源。决定下载后，也可直接运行 `./tools/robocasasetup.sh`；`python3 tools/robocasasource.py check --path .local/robocasa` 只检查现有源码，不下载。

命令先输出 RoboCasa 启动信息，最后输出类似 JSON：

```json
{"instruction":"Close the fridge doors.","scene":"8:8","seed":42,"split":"target","steps":20,"success":false,"task":"robocasa/CloseFridge"}
```

`success` 来自 RoboCasa 的冰箱门判定规则。随附运行器采样有界随机动作，并将底盘运动置零；`false` 是有效的冒烟结果，不代表安装失败。`--steps` 指定动作预算，`--seed` 控制重置与动作采样。回合结束后进程自行退出，无需运行 `kill.sh`。任务、资源来源、许可和限制见[基准指南](../benchmarks/Robocasa/README_cn.md)。

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

RoboCasa 基准在前台运行，结果输出到终端。原生启动器将日志写到选定的运行目录。对于受管理部署，修改图之前先找到当前 IsOS 运行及其首条就绪或失败事件；参见[构建与运行](README_cn.md#isos-与-eos-部署)。

## 开发界面和本地日志

在本机被忽略的 `.env` 中设置 `export SIM_PROFILE=dev`。运行 `./launch.sh --benchmark CloseFridge --steps 20` 可在图像窗口查看 RoboCasa 当前回合的相机画面；回合结束后在图像窗口按任意键关闭。`--no-gui` 关闭图形窗口。运行 `./launch.sh --scene navigation` 会默认打开独立的静态 MuJoCo XML 查看器，`./kill.sh` 停止原生进程及查看器。后者不显示套接字模拟器的实时状态。

每次本地运行的日志保存在被 Git 忽略的 `logs/dev/`。`logs/dev/robocasa/latest.log` 和 `logs/dev/native/latest.log` 指向最近的运行文件；原生查看器日志使用同一时间戳的 `*-viewer.log`。启动器检查活跃套接字后自动清理遗留套接字。
