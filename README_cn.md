# IsOS MuJoCo 模拟器

本包提供原生 MuJoCo 与 RoboCasa 硬件服务。IsOS 验证和配置包、Apply 图并监督所选服务；EOS 拥有机器人命令准入、设备健康和 Stop 证明。评测真值仅供可信评测器使用。

[English](README.md) · [文档](docs_cn/README_cn.md) · [详细开始指南](docs_cn/start_cn.md) · [节点组](docs_cn/node/README_cn.md)

## 快速开始

Linux 原生构建需要 MuJoCo **3.3.1**、C++20 编译器、CMake 3.22+、protobuf、gRPC 和 libjpeg；RoboCasa 准备还需要 Python 3.11、Git、`wget` 与 `uv`。完整依赖、Windows RoboCasa 操作与配置覆盖规则见[开始使用](docs_cn/start_cn.md)。

```sh
cp .env.example .env
# 编辑 .env，设置：export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
./build.sh
ctest --test-dir build --output-on-failure
./launch.sh --benchmark CloseFridge --seed 42 --steps 20 --no-gui
```

构建脚本准备原生目标及本地 RoboCasa 环境，缺少资产时会询问后下载。有界随机动作得到 `success: false` 仍是有效冒烟结果，不代表代理策略成绩。

本地原生运行使用 `./launch.sh --scene pick-place --no-gui`，结束时运行 `./kill.sh`。任务选择、相机、记录回放、托管部署与恢复见[详细指南](docs_cn/start_cn.md)。发布声明与验收规则见[软件包](docs_cn/package_cn.md)，当前数据流见[架构](docs_cn/architecture_cn.md)。
