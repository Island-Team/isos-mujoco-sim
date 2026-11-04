# Q03 仿真器验证设计

[English](../../docs/mujoco/q03-qualification.md)

**状态：**归属方源码检查、Q03 final-17 选定源码重放及 Q04 final-5 合并后提交重放均已通过。独立 Q04 归档审查没有 P1/P2 发现。`v0.1.1` 标签已发布，后续五方发布资产重放通过了其既定 Q04/M5 关卡；详见[软件包发布记录](package-release_cn.md)和 [EOS Q04 验证记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)。仿真器拥有场景加载、确定性复位、物理、渲染、私有套接字及基准评分。EOS 拥有机器人侧路由。基准真实状态不得通过 EOS、EGIA 或界面暴露。

**Q03 所有者初始基线（2026-11-03）：**已实现 `tests/q03_socket_bench.py`、私有 `benchmark-reset` 工具及失败路径单元测试。此处是本机直接套接字证据，不等同于跨仓库安装重放或发布批准。初次完整输出保留在 Git 忽略的 `logs/test/20261103-q03-mujoco/`；最终渲染器探针软件包保存在 `logs/test/20261103-q03-mujoco-review-final/`；无碰撞的逐请求原始样本及六份子进程日志保存在 `logs/test/20261103-q03-mujoco-review-final-2/`。

## 固定输入与所有者检查

从已获取的 `master` 提交构建，使用 MuJoCo 3.16.0，记录编译器、CMake、CTest、库、源码及场景哈希。对受 Git 跟踪的 C++ 源码运行 `clang-format --dry-run --Werror`；运行 CMake 配置／构建及全部 CTest，再运行严格套接字／容量／Stop、场景、引擎及基准的定向测试。运行节点贡献契约用例，并在空输出目录构建新的 `island/mujoco-sim@0.1.1` 软件包。保存清单／归档 SHA-256，并在干净的 IsOS 主目录验证该包。把完整命令、输出及退出状态保存到忽略 Git 的 `logs/test/<run-id>/`，包括失败的尝试。

已安装的所有者重放必须选择目录中的两个场景，证明精确软件包和场景准入，读取一帧图像，通过 EOS 发送一次获准的底盘或机械臂命令，注入仿真器死亡，并观察当前运行的故障和受控 Stop／回收。保留选定图修订、运行 ID、软件包收据、子进程身份及跨仓库验证器结果。独立的 CTest 必需，但不能替代已安装重放。

## 初始套接字基线

使用私有、仅所有者可访问的 v2 Unix 套接字，不启用 GUI。针对 `assets/scene.xml` 和 `assets/scenes/navigation/scene.xml`，分别启动三个全新的仿真器进程。使用直接启动的非托管基准进程（绝不作为 EOS 持有的托管子进程），提供私有、绝对且互不相同的 `--socket`、`--benchmark-socket`、`--v2-socket` 与 `--scene` 路径。例如：`build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`。每次进程预热前必须通过私有基准套接字成功执行 `Reset(seed=42)` 并记录响应；测量期间保持引擎暂停，不进行异步步进。使用软件包中仅含 EGL 的 `SimEngine::RenderCamera` 路径及 640×480 的 `cam-0` 捕获。套接字不输出运行时解析的渲染器身份；启用子进程的可选 EGL 上下文探针，从子进程日志记录运行时 EGL 供应商和 GL 渲染器，并在每次重复时断言实际 JPEG 格式、字节长度和图像尺寸。预热 20 次后，串行发送 200 次 `base_observe` 和 20 次 `camera_capture` 请求。记录每次单调时钟耗时、响应状态和字节数，以及每组操作测得的墙钟时长。逐进程和合并样本报告成功请求数／秒或帧数／秒、中位数（偶数样本取中间两数平均）及最近秩 p99（毫秒）；单独报告所有失败与超时。这只测量仿真器套接字，不代表 IsOS HTTP、EOS Dispatcher 或浏览器延迟。初始测量不形成性能目标。

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
python3 tools/build-backend-bundle.py --build-dir build-q03 --output logs/test/20261103-q03-mujoco-review-final/bundle
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/pick-place.json
python3 tests/q03_socket_bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scenes/navigation/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/navigation.json
```

格式修正后，全部 CTest 为 25/25，定向测试为 16/16；R05、R06 静态用例矩阵分别通过 31、48 项，节点贡献检查通过。初次格式检查在三个原有文件中出现 86 项诊断：`tests/smoke.cpp`、`src/service.cpp`、`src/gui.cpp`。单独的纯格式提交已修正，最终受 Git 跟踪的 C++ 格式检查通过。最终软件包为 `mujoco-sim-v0.1.1-linux-x86_64.tar.gz`，SHA-256 为 `05a9346db26f43510c1986ff7431038ae29197ac85300a2f1efd1211f3458fe6`。在这一初始归属方基线时，跨仓库 IsOS→EOS 安装重放尚待完成。

本机为 x86_64 Linux、GCC 13.3.0，使用已安装的 MuJoCo 3.16.0、软件包 EGL 渲染路径且无 GUI。`environment.json` 记录内核、工具版本、源码提交、二进制、场景、库和归档哈希。全部六个进程的运行时探针均报告 EGL 供应商 `NVIDIA` 和 GL 渲染器 `NVIDIA GeForce RTX 2080 Ti/PCIe/SSE2`。种子 42、暂停场景、每个场景三个新进程；每进程预热 20 次，再测量 200 次观察和 20 次图像采集。最终原始测量如下：

| 场景 | 操作 | 成功／失败 | 吞吐量 | 中位数 | p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| 抓取放置 | `base_observe` | 600/0 | 17,549 次／秒 | 0.054 毫秒 | 0.089 毫秒 |
| 抓取放置 | `camera_capture` | 60/0 | 716 帧／秒 | 1.261 毫秒 | 2.961 毫秒 |
| 导航 | `base_observe` | 600/0 | 18,033 次／秒 | 0.053 毫秒 | 0.074 毫秒 |
| 导航 | `camera_capture` | 60/0 | 731 帧／秒 | 1.262 毫秒 | 2.453 毫秒 |

吞吐量为成功次数除以各进程对应操作组的测量总时长。中位数取成功样本排序后的中点，p99 用最近秩。相同日志目录中的较早尝试结果不同，可能受到本机负载影响；此基线不设性能目标，也不作跨主机推断。每次重复分别记录成功的 `Reset(seed=42)`、观察到的 JPEG 探针尺寸，以及全部样本状态、字节数和超时标记。失败请求记录零个已接受的有效负载字节，摘要单独统计超时。可选的子进程日志在上下文创建后记录运行时 EGL 供应商与 GL 渲染器；套接字响应提供观察到的 JPEG 尺寸。日志文件名使用基准输出文件名，确保两个均名为 `scene.xml` 的场景各有独立日志。前一次运行因场景文件同名覆盖了子进程日志；其原始样本仍保留，但子进程日志由本次运行取代。数字只代表仿真器私有套接字。

### 选定安装归档证据（2026-11-03）

选定的 0.1.1 软件包记录 MuJoCo 源码提交 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`；`release.json` 必须继续保持这个精确来源身份。选定发布文件 SHA-256 为 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`，归档资产 SHA-256 为 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。EOS Q03 选定清单 SHA-256 为 `116aef2846750a96275645e4dec3021ad716ce6fb80b05c087a2ce377a74b990`；冻结评审主构建和案例构建收据 SHA-256 分别为 `977293e097779f636cb70bde9f3d5657bc9351b0b9f67534ca7beb41a97ef915` 和 `20b2dc444d4f90ca1e4cf4b8a2404893c53cd20de19a090ce02debf0c539ab5d`。

在封存的干净主目录重放中，IsOS 验证并安装该归档，选择 `pick-place` 场景和可用的相机、底盘、机械臂设备；EOS 将已验证的 MuJoCo 可执行程序作为直接子进程启动。真实的 640×480 相机帧到达 EOS、EGIA Vision 与浏览器观察。R06/A03 选定来源故障试验通过子进程死亡、Stop／回收及重启检查，没有重放结果不明的运动；最终部署 Stop 获确认，受管进程无存活者。六组选定案例和 `Q01_FULL_VERIFIED` 保存在 EOS 中忽略 Git 的 `logs/test/20261103-q03-selected-final-15/`。上文私有套接字基准仍是另一项固定负载测量。此次安装重放只覆盖本地模拟托管 Origin。在 final-15 关卡时，Q04 合并后提交评审和标签发布尚未执行。若更改软件包来源 HEAD，必须重新构建并验证 0.1.1 软件包。

### 最终选定源码与合并后提交的归档证据，2026-11-04

后续封存的 Q03 `20261103-q03-selected-final-17` 归档仍固定软件包源码 `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`、发布文件 SHA-256 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445` 和归档 SHA-256 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`。冻结选择清单 SHA-256 为 `35dd4e5aa4c209bf84935002a4eded756f3eb5a1c147b2fb12bd5d894e46b78a`；精确选定的 EOS 源码 `219f031bae9dbfc9d9f53f62c910b9e235bb2138` 上的验证器对全部六组返回 `Q01_FULL_VERIFIED`。独立 EOS 审核位于 `logs/test/20261104-q03-final17-independent-audit/`：选定源码验证通过，而较新检出因测试工具摘要变化被拒。上文 final-15 记录保留为历史证据。

Q04 `20261103-q04-merged-home-final-5` 的发布文件从已合并的 MuJoCo `master` `04b65882cd11b0aff8ce56473164691dbd662196` 重新构建。`release.json` 的 SHA-256 为 `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`，已安装归档的 SHA-256 为 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`；冻结的外部选择清单 SHA-256 为 `7f5cefa5b6521d42d28b88c916679f2b668ba93fd61bbcbbfed4bb8fcc722b87`。IsOS 在干净主目录中验证并安装精确软件包；EOS 将仿真器作为直接子进程启动，产生真实相机帧和受治理的底盘结果，随后在子进程终止与回收之前确认物理 Stop。选定的 R06/A03 故障与重启案例通过，没有重放结果不明的运动。完整选定验证器返回 `Q01_FULL_VERIFIED`；独立归档评审检查了 3,630 个封存文件，没有 P1/P2 发现。原始收据、事件、子进程证明和命令保存在 EOS 中忽略 Git 的 `logs/test/20261103-q04-merged-home-final-5/`。这是本地模拟托管 Origin 的重放，不代表已发布 `v0.1.1` 软件包或公网 HTTPS 部署；在该关卡时，发布收尾和标签仍未完成。
