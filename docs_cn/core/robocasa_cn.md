# RoboCasa 硬件与回放

[English](../../docs/core/robocasa.md) · [Docs](../README_cn.md)

Python 硬件 API 控制调用方拥有的一个 Gym 环境。打包工作进程拥有独立环境，按[私有服务契约](adapter_cn.md)串行处理请求。本地记录用于控制回放，评测计分保持私有。

## 发现机器人全身部件（0.2.8 候选）

托管 worker 使用 `[services.robocasa].robot`（默认 `PandaOmron`）构造原始 RoboCasa 环境，并使用 `robocasa_core.BodyHardware`，绕过上游固定的 PandaOmron Gym 字段转换器。一个世界包含一个机器人；控制器可以具有零个或多个机械臂和夹爪、可选底盘与躯干、选定的相机。下文的旧 `Hardware` API 和版本 1 PandaOmron 录制保持兼容。

发现过程读取实际复合控制器的动作切片、控制器类型、归一化输入与物理输出缩放、控制坐标系、关节名称/类型/局部轴以及可用相机。私有只读 `manifest` 操作和启动时的 `robot_manifest` 日志提供有界元数据，不暴露奖励、成功条件、物体或基准真值。每条动作只执行一次真实环境控制步；lease 必须覆盖该步，manifest 中记录 `command_step_ms`（已验证 PandaOmron 为 50 ms）。

支持已知 base/world 坐标系的六维笛卡尔增量机械臂、二值夹爪、三维平面底盘和单轴躯干。其他控制器（包括全身 IK、头部/腿部关节控制、绝对笛卡尔控制）会被忽略并产生有界警告。仅固定阻抗、固定版本的绝对 `JOINT_POSITION` 控制器使用未缩放的实测关节位置保持。未知绝对/中性控制语义或零输入缩放后非零的增量控制器，在推进物理前拒绝。这是控制器兼容性发现，不表示所有上游机器人都可使用当前安装的可选模型与资源加载。缺失可选观测不会丢弃其他部件，也不会补零。

机械臂状态读取真实末端 site 的位置和四元数，转换到声明坐标系；夹爪和躯干读取真实受控关节位置，移动关节使用米、转动关节使用弧度。躯干不再因为上游 Gym 转换器漏掉字段而缺失状态。只渲染显式选中的相机，渲染不推进物理。重复读取保留最近一次成功 reset/step 的 `simulation` 时钟采样时间，不伪造新物理测量。EOS 可在暂停世界使用有界接收新鲜度，不将仿真时钟当作主机时钟。

`tools/robot_graph.py` 从新建的选定环境生成 `{nodes, capabilities, members, robot_manifest, robot_manifest_digest}`。它生成一个全身 Dispatcher、精确硬件绑定、模型动作 schema、坐标系、单位、正方向、控制器缩放与中性动作。可选模式保留在 manifest 中；独立验证前不生成对应 Dispatcher 绑定。`members` 为 EOS 合并状态池标记观测源。它只是准备工具；需与 IsOS/EI session 和池声明组合，审阅后经 IsOS Apply，生成过程不授予动作权限。图中适配器固定 manifest SHA-256，控制器元数据不同会使 readiness 失败，避免陈旧控制说明静默控制不同机器人。改变机器人/控制器后须重新生成。

```sh
PYTHONPATH=. .local/robocasa-venv/bin/python tools/robot_graph.py \
  --robot PandaOmron --assets /absolute/path/to/robocasa/models/assets \
  --camera-size 256 --output /absolute/path/to/robot-fragment.json
```

固定 `PandaOmron` preset 是示例，不是发现机制。其他兼容全身应使用生成节点。0.2.8 候选托管配置必须包含 `robot`。session 中性动作不是 Stop 证明；独立 Stop 通道关闭准入并有界检查受控关节稳定，不能证明时返回 `unknown`。

<a id="robocasa-机器人硬件核心接口"></a>
## RoboCasa 机器人硬件核心接口

Python `robocasa_core.Hardware` 管理调用方传入的固定版本 RoboCasa PandaOmron Gym 环境。目录使用 `robocasa` 层；组表示硬件功能，节点是稳定的可绑定端点。调用方负责创建环境、串行调用并关闭核心。此进程内 API 没有认证或传输。打包后的 worker 经私有服务端点提供硬件；调用方及准入规则见[控制契约](adapter_cn.md)。

| 组 / 节点 ID | 命令 | 观测 |
| --- | --- | --- |
| `arm/right-arm` | 位置和旋转增量，各为 3 个 `[-1,1]` 归一化值 | 相对底座的末端位置和四元数 |
| `gripper/right-gripper` | 闭合：`0` 张开，`1` 闭合 | 夹爪关节位置 |
| `base/mobile-base` | 3 个 `[-1,1]` 归一化底盘运动值 | 底盘位置和四元数 |
| `torso/torso` | 1 个 `[-1,1]` 归一化躯干运动值 | 固定版本包装器不提供 |
| `camera/agentview-left`、`camera/agentview-right`、`camera/eye-in-hand` | 无 | RGB8 图像，高 × 宽 × 3 |

完整 ID 在每行前加 `robocasa/`。位置和旋转命令是控制器输入，不是米或弧度；由上游控制器解释。观测位置单位为米，姿态采用上游包装器的四元数顺序。核心构造时检查动作形状和必需观测键，不兼容的机器人配置会被拒绝。相机尺寸来自环境。目录描述此固定配置支持的端点；缺少必需端点时构造失败。

控制前调用 `reset(seed)`。`command_arm(position, rotation)`、`command_gripper(close)`、`command_base(motion)`、`command_torso(motion)` 和 `set_control_mode(mode)` 将值排队至一次 `step()`。控制模式为 `0` 或 `1`，原样传给 RoboCasa 的 `action.control_mode`；固定版本包装器将其映射到两种底盘模式。一步同时提交五个上游动作字段。未设置的运动为零；未设置的夹爪为张开，模式为 `0`。环境步进失败时队列也会先清空；再次控制前必须重置。`observe()` 和步进结果只包含复制的机器人状态和相机数组，不包含任务文字、奖励、成功结果或场景物体状态。`close()` 关闭环境，之后不能控制。

形状错误、非有限或越界运动值、非二值夹爪或模式、缺失观测以及重置前或关闭后调用都会抛出 `HardwareError`。RoboCasa 报告回合终止或截断时，最后一步仍返回机器人观测，后续控制必须先重置。上游环境异常会继续抛出，并使核心在重置前保持故障状态。此进程内接口没有截止时间、异步命令或物理停止保证；紧急停止策略应由所属控制层提供。

`control(device_id, payload)` 是通用的进程内控制入口，接收完整的 `robocasa/...` 设备 ID 和该设备自己的字段：机械臂的 `position` 与 `rotation`（或 `mode`）、夹爪的 `close`、底盘或躯干的 `motion`。它只读取支持的字段并忽略无关键。没有可用控制字段、机械臂字段不完整、设备未知或只读时抛出 `HardwareError`；支持字段的非法值仍按原有规则拒绝。`status(device_id)` 仅返回所选设备已测得字段的副本。固定版本包装器没有躯干测量，因此躯干状态报告不可用。相机状态返回所选 RGB8 图像；相机不支持控制。原有专用命令方法和 `observe()` 仍可使用。

```python
hardware = Hardware(env)
hardware.reset(42)
hardware.control("robocasa/arm/right-arm", {"position": [0, 0, 0], "rotation": [0, 0, 0]})
hardware.control("robocasa/gripper/right-gripper", {"close": 0})
hardware.step()
frame = hardware.status("robocasa/camera/eye-in-hand")["eye-in-hand"]
hardware.close()
```

本包提供由 IsOS 管理的隔离 RoboCasa worker 运行服务。EOS 硬件适配器通过受控服务端点绑定已声明的设备 ID。此进程内 `Hardware` API 仍用于本地测试；其 reset 和 step 不是代理接口。C++ 场景目录及 EOS 模拟器 protobuf 不描述 RoboCasa。

保存命令及检查指定本地回合时，使用[记录与重放接口](robocasa_cn.md)。验证：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasahardware.py' -v` 执行桩单元测试；`PYTHONPATH=. .local/robocasa-venv/bin/python tests/robocasareplay.py` 执行两次固定种子的 `CloseFridge` 硬件重放。

<a id="robocasa-本地硬件记录与重放"></a>
## RoboCasa 本地硬件记录与重放

`EpisodeRecorder` 将一次 PandaOmron 硬件回合写为带版本的本地 JSON 记录。`load_record(path)` 选择并校验本地文件；`replay_record(hardware, record)` 用记录的种子重置新环境，按顺序执行各组命令，并在重置后和每一步检查机器人状态。调用方拥有环境和文件路径。这是没有网络传输或认证的进程内测试接口。

版本 `1` 的顶层字段严格为 `version`、`layer`、`profile`、`task`、`split`、`seed`、`camera_width`、`camera_height`、`initial_state` 和 `steps`。`layer` 为 `robocasa`，`profile` 为 `PandaOmron`。`steps` 是有序的 `{command,state}` 数组。命令可包含 `arm:{position,rotation}`、`gripper`、`base`、`torso` 和 `mode`；缺失组采用硬件核心的中性值。运动数组和二值字段遵循[硬件契约](robocasa_cn.md)的形状和范围。每个状态包含 `gripper_qpos`（2）、`base_position`（3）、`base_rotation`（4）、`end_effector_position_relative`（3）和 `end_effector_rotation_relative`（4），数值使用上游观测单位。记录不包含图像、任务文字、奖励、成功结果或装置真值。

`EpisodeRecorder.reset()` 清空之前的步骤并保存初始机器人状态。各组命令方法通过 `Hardware` 校验；`step()` 只保存成功执行的命令和返回的机器人状态。`save(path)` 要求目标目录已存在，并原子替换选定文件。`load_record` 拒绝未知字段或版本、错误形状或数值、超过 10,000 步以及超过 8 MB 的文件。默认重放以绝对容差 `1e-5`、相对容差零比较状态，报告首次差异的步骤和字段。由于 GPU 驱动可能影响渲染，不比较 RGB 像素。重放差异是测试证据，不是基准分数或物理安全证明。

```sh
./launch.sh --record-demo
./launch.sh --replay-record examples/robocasa/hardware-demo.json
```

仓库中的演示记录使用 `CloseFridge`、target 划分、种子 42、64×64 相机，以及两步覆盖机械臂、夹爪、底盘、躯干和控制模式的命令。`--demo` 会覆盖指定路径；若要保留仓库示例，请使用其他本地路径。`--replay` 只读取调用方指定的路径，并按记录中的身份信息创建新 RoboCasa 环境。记录不含资源或源码哈希，因此重现性依赖本地固定版本的 RoboCasa 与资源集。基准评测元数据和评分仍留在私有基准路径。

<a id="本地记录配置"></a>
### 本地记录配置
在 `config/benchmarks/robocasa.toml` 的 `[record]` 中设置 `enabled`（布尔值，默认 `false`）和 `path`（非空路径，默认 `.run/hardware-record.json`）。相对路径按仓库根目录解析；`.env` 中导出的 `BENCHMARK_RECORD_ENABLED` 与 `BENCHMARK_RECORD_PATH` 覆盖它们。`./launch.sh --record-demo` 使用配置路径；`--record-demo FILE` 仅覆盖本次路径。关闭时写入请求失败；`--replay-record FILE` 仍可读取现有记录。默认路径的父目录按私有权限创建，写入文件受 `0077` umask 保护。

```sh
./launch.sh --record-demo
./launch.sh --replay-record .run/hardware-record.json
```

验证：`PYTHONPATH=. .local/robocasa-venv/bin/python -m unittest discover -s tests -p 'robocasarecord.py' -v` 覆盖本地保存、加载、选定记录重放、错误记录和状态偏差。上面的 CLI 命令用真实环境验证演示记录。

生成观测适配器显式配置采集频率（`frequency_hz`：全身状态10Hz、相机30Hz）；`observation.max_rate_hz` 只是上限，不是采集时钟。仅控制部件不添加采集计时器。Stop 允许24个中性步消除初始瞬态，仍要求受控关节连续两次变化不超过1e-4；不会把旧 unknown 结果改成已证明停止。
