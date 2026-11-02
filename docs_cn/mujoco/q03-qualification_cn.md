# Q03 仿真器验证设计

[English](../../docs/mujoco/q03-qualification.md)

**状态：**所有者实现候选稿；跨仓库发布证据尚未完成。仿真器拥有场景加载、确定性复位、物理、渲染、私有套接字及基准评分。EOS 拥有机器人侧路由。基准真实状态不得通过 EOS、EGIA 或界面暴露。

**Q03 所有者初始基线（2026-11-03）：**已实现 `tests/q03_socket_bench.py`、私有 `benchmark-reset` 工具及失败路径单元测试。此处是本机直接套接字证据，不等同于跨仓库安装重放或发布批准。完整输出、逐请求原始样本、子进程日志、软件包和哈希保存在 Git 忽略的 `logs/test/20261103-q03-mujoco/`。

## 固定输入与所有者检查

从已获取的 `master` 提交构建，使用 MuJoCo 3.16.0，记录编译器、CMake、CTest、库、源码及场景哈希。对受 Git 跟踪的 C++ 源码运行 `clang-format --dry-run --Werror`；运行 CMake 配置／构建及全部 CTest，再运行严格套接字／容量／Stop、场景、引擎及基准的定向测试。运行节点贡献契约用例，并在空输出目录构建新的 `island/mujoco-sim@0.1.1` 软件包。保存清单／归档 SHA-256，并在干净的 IsOS 主目录验证该包。把完整命令、输出及退出状态保存到忽略 Git 的 `logs/test/<run-id>/`，包括失败的尝试。

已安装的所有者重放必须选择目录中的两个场景，证明精确软件包和场景准入，读取一帧图像，通过 EOS 发送一次获准的底盘或机械臂命令，注入仿真器死亡，并观察当前运行的故障和受控 Stop／回收。保留选定图修订、运行 ID、软件包收据、子进程身份及跨仓库验证器结果。独立的 CTest 必需，但不能替代已安装重放。

## 初始套接字基线

使用私有、仅所有者可访问的 v2 Unix 套接字，不启用 GUI。针对 `assets/scene.xml` 和 `assets/scenes/navigation/scene.xml`，分别启动三个全新的仿真器进程。使用直接启动的非托管基准进程（绝不作为 EOS 持有的托管子进程），提供私有、绝对且互不相同的 `--socket`、`--benchmark-socket`、`--v2-socket` 与 `--scene` 路径。例如：`build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`。每次进程预热前必须通过私有基准套接字成功执行 `Reset(seed=42)` 并记录响应；测量期间保持引擎暂停，不进行异步步进。固定软件包 EGL 渲染器与 640×480 的 `cam-0` 捕获，并在每次重复时断言实际渲染器及图像尺寸。预热 20 次后，串行发送 200 次 `base_observe` 和 20 次 `camera_capture` 请求。记录每次单调时钟耗时、响应状态和字节数，以及每组操作测得的墙钟时长。逐进程和合并样本报告成功请求数／秒或帧数／秒、中位数（偶数样本取中间两数平均）及最近秩 p99（毫秒）；单独报告所有失败与超时。这只测量仿真器套接字，不代表 IsOS HTTP、EOS Dispatcher 或浏览器延迟。初始测量不形成性能目标。

测试工具须对套接字不可用、畸形响应、超时、场景错误和子进程意外退出明确失败；定向测试须覆盖这些路径。独立代理在实现前审查本设计，并在合入 MuJoCo `master` 前审查工具、证据及 PR。Q03 跨仓库摘要记录最终精确提交；Q04 负责发布与标签。
## 可重现的所有者证据

在仓库根目录设置 `MUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`，依次执行：

```sh
git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror
cmake -S . -B build-q03 -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build-q03 -j4
ctest --test-dir build-q03 --output-on-failure
ctest --test-dir build-q03 -R 'strict-socket|strict-capacity|strict-stop|v2-socket|benchmark-eval|engine-test|scene-catalog|bundle-catalog|q03-socket' --output-on-failure
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tests/node_contributions.py
python3 tools/build-backend-bundle.py --build-dir build-q03 --output logs/test/20261103-q03-mujoco/bundle
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco/pick-place-final.json
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scenes/navigation/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco/navigation-final.json
```

初次全部 CTest 为 25/25，通过定向测试 16/16；R05、R06 静态用例矩阵分别通过 31、48 项，节点贡献检查通过。初次格式检查在三个原有文件中出现 86 项诊断：`tests/smoke.cpp`、`src/service.cpp`、`src/gui.cpp`。其格式修正将在基准实现提交后作为单独的纯格式提交，并须在合并前重检。软件包为 `mujoco-sim-v0.1.1-linux-x86_64.tar.gz`，SHA-256 为 `3aa0393883b02bb577ee7b6c408eff1fa4803df543723b9faaa3cdcb80b0c94f`。跨仓库 IsOS→EOS 安装重放仍待完成。

本机为 x86_64 Linux、GCC 13.3.0，使用已安装的 MuJoCo 3.16.0、软件包 EGL 渲染路径且无 GUI。`environment.json` 记录内核、工具版本、源码提交、二进制、场景、库和归档哈希。种子 42、暂停场景、每个场景三个新进程；每进程预热 20 次，再测量 200 次观察和 20 次图像采集。最终原始测量如下：

| 场景 | 操作 | 成功／失败 | 吞吐量 | 中位数 | p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| 抓取放置 | `base_observe` | 600/0 | 17,128 次／秒 | 0.054 毫秒 | 0.099 毫秒 |
| 抓取放置 | `camera_capture` | 60/0 | 757 帧／秒 | 1.209 毫秒 | 2.459 毫秒 |
| 导航 | `base_observe` | 600/0 | 17,917 次／秒 | 0.054 毫秒 | 0.075 毫秒 |
| 导航 | `camera_capture` | 60/0 | 791 帧／秒 | 1.200 毫秒 | 2.041 毫秒 |

吞吐量为成功次数除以各进程对应操作组的测量总时长。中位数取成功样本排序后的中点，p99 用最近秩。相同日志目录中的初次尝试较慢，可能受到本机负载影响；此基线不设性能目标，也不作跨主机推断。每次重复分别记录成功的 `Reset(seed=42)`、EGL 图像探针、640×480 尺寸及全部样本状态。数字只代表仿真器私有套接字。
