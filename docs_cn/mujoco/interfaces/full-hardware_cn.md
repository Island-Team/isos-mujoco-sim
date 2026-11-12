# 完整机器人硬件软件包（v0.2.1 候选版）

`island/mujoco-sim@0.2.1` 提供“原生机器人”和“RoboCasa 机器人”两套设备预设。节点是普通 EOS 硬件节点，分别位于 camera、base、manipulator、gripper 和 torso 分组。预设没有进程节点。IsOS 只启动已选节点引用的软件包服务，并管理子进程及日志，再把私有服务端点交给 EOS。EOS 通过 `isos_node_v2` 加载已验证的 `libmujoco-eos-node.so`，所有执行器命令均由 Dispatcher 准入。

原生预设提供 `cam-0`、`base-0`、`arm-0` 和 `gripper-0`。严格套接字支持 JPEG 图像、SI 单位底盘状态与速度命令、六关节状态与位置命令、夹爪开度与开合命令、带代际隔离的命令，以及分别报告底盘、机械臂和夹爪结果的全机器人停止证明。场景为 `pick-place` 或 `navigation`；路径由软件包已验证的场景资源提供。

RoboCasa 预设提供三路 RGB8 相机、移动底盘、右臂、右夹爪及躯干。Python Gym 环境运行于 IsOS 管理的子进程，EOS 不加载 Python。底盘位姿采用世界坐标系，末端执行器位姿相对于 `robot_base`；两者的四元数顺序均为 `xyzw`。Panda 夹爪两个滑动关节通道使用米。工作进程串行执行步进，在同一代际内去重命令 ID；步进失败后拒绝继续控制。停止操作先隔离排队命令、清除运动和模式状态，再执行中性运动步进，直到夹爪保持的通道稳定。服务缓存与本次运行绑定的结果，使每个已选执行器都能取得同一证明；步进失败或夹爪不稳定时报告 `unknown`。躯干不伪造位置观测。基准奖励与成功真值不会作为硬件数据暴露。

`config/package-config.json` 为通用 IsOS 软件包配置界面声明中英文标签和说明。`config/package.toml` 提供 `[package]`、`[host]`、`[services.native]` 和 `[services.robocasa]`。已选原生服务需要本地 MuJoCo 3.3.1 目录；已选 RoboCasa 服务需要本地资源及明确选定的 Python 解释器。这些大型主机资源不随软件包下载。路径属于本地部署配置，不属于图节点设置。每个硬件适配器通过 `service_instance` 选择服务；IsOS 在 Apply 与 Run 时解析它。

构建命令为 `./build.sh --output 绝对路径的空目录 --version 0.2.1`。只有两套预设都通过 IsOS `pkg check` 回放，包括拒绝、崩溃、日志和停止场景，候选版才可发布。已发布的 v0.2.0 记录及其进程节点图保持不变。

[English](../../../docs/mujoco/interfaces/full-hardware.md) · [软件包详情](package_cn.md) · [套接字](socket_cn.md)
