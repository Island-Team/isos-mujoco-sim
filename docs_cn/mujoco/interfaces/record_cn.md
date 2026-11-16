# RoboCasa 本地硬件记录与重放

[硬件核心](robocasa_cn.md) · [RoboCasa 基准](../core/benchmark_cn.md) · [English](../../../docs/mujoco/interfaces/record.md)

`EpisodeRecorder` 将一次 PandaOmron 硬件回合写为带版本的本地 JSON 记录。`load_record(path)` 选择并校验本地文件；`replay_record(hardware, record)` 用记录的种子重置新环境，按顺序执行各组命令，并在重置后和每一步检查机器人状态。调用方拥有环境和文件路径。这是没有网络传输或认证的进程内测试接口。

版本 `1` 的顶层字段严格为 `version`、`layer`、`profile`、`task`、`split`、`seed`、`camera_width`、`camera_height`、`initial_state` 和 `steps`。`layer` 为 `robocasa`，`profile` 为 `PandaOmron`。`steps` 是有序的 `{command,state}` 数组。命令可包含 `arm:{position,rotation}`、`gripper`、`base`、`torso` 和 `mode`；缺失组采用硬件核心的中性值。运动数组和二值字段遵循[硬件契约](robocasa_cn.md)的形状和范围。每个状态包含 `gripper_qpos`（2）、`base_position`（3）、`base_rotation`（4）、`end_effector_position_relative`（3）和 `end_effector_rotation_relative`（4），数值使用上游观测单位。记录不包含图像、任务文字、奖励、成功结果或装置真值。

`EpisodeRecorder.reset()` 清空之前的步骤并保存初始机器人状态。各组命令方法通过 `Hardware` 校验；`step()` 只保存成功执行的命令和返回的机器人状态。`save(path)` 要求目标目录已存在，并原子替换选定文件。`load_record` 拒绝未知字段或版本、错误形状或数值、超过 10,000 步以及超过 8 MB 的文件。默认重放以绝对容差 `1e-5`、相对容差零比较状态，报告首次差异的步骤和字段。由于 GPU 驱动可能影响渲染，不比较 RGB 像素。重放差异是测试证据，不是基准分数或物理安全证明。

```sh
./launch.sh --record-demo
./launch.sh --replay-record examples/robocasa/hardware-demo.json
```

仓库中的演示记录使用 `CloseFridge`、target 划分、种子 42、64×64 相机，以及两步覆盖机械臂、夹爪、底盘、躯干和控制模式的命令。`--demo` 会覆盖指定路径；若要保留仓库示例，请使用其他本地路径。`--replay` 只读取调用方指定的路径，并按记录中的身份信息创建新 RoboCasa 环境。记录不含资源或源码哈希，因此重现性依赖本地固定版本的 RoboCasa 与资源集。基准评测元数据和评分仍留在私有基准路径。

## 本地记录配置
在 `config/benchmarks/robocasa.toml` 的 `[record]` 中设置 `enabled`（布尔值，默认 `false`）和 `path`（非空路径，默认 `.run/hardware-record.json`）。相对路径按仓库根目录解析；`.env` 中导出的 `BENCHMARK_RECORD_ENABLED` 与 `BENCHMARK_RECORD_PATH` 覆盖它们。`./launch.sh --record-demo` 使用配置路径；`--record-demo FILE` 仅覆盖本次路径。关闭时写入请求失败；`--replay-record FILE` 仍可读取现有记录。默认路径的父目录按私有权限创建，写入文件受 `0077` umask 保护。

```sh
./launch.sh --record-demo
./launch.sh --replay-record .run/hardware-record.json
```

验证：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasarecord.py' -v` 覆盖本地保存、加载、选定记录重放、错误记录和状态偏差。上面的 CLI 命令用真实环境验证演示记录。
