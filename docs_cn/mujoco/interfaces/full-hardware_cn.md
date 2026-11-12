# 完整机器人硬件软件包（下个发行候选版）

下个 `island/mujoco-sim` 发行包声明七种 EOS 硬件类型，并提供“原生机器人”和“RoboCasa 机器人”两套设备预设。每个实例以精确软件包版本同时锁定类型所有者和适配器所有者。这些类型位于 EOS 硬件层的 camera、base、manipulator、gripper 和 torso 分组；其他软件包可选择不同的层和分组。预设没有进程节点。IsOS 只启动已选节点引用的软件包服务，并管理子进程及日志，再把私有服务端点交给 EOS。EOS 通过 `isos_node_v2` 加载已验证的 `libmujoco-eos-node.so`，所有执行器命令均由 Dispatcher 准入。

原生预设提供 `cam-0`、`base-0`、`arm-0` 和 `gripper-0`。严格套接字支持 JPEG 图像、SI 单位底盘状态与速度命令、六关节状态与位置命令、夹爪开度与开合命令、带代际隔离的命令，以及分别报告底盘、机械臂和夹爪结果的全机器人停止证明。夹爪观测包含以百分比为单位、名为 `opening` 的通道。场景为 `pick-place` 或 `navigation`；路径由软件包已验证的场景资源提供。

RoboCasa 预设提供三路 RGB8 相机、移动底盘、右臂、右夹爪及躯干。Python Gym 环境运行于 IsOS 管理的子进程，并禁用字节码写入，以保持已验证的软件包字节不变；EOS 不加载 Python。观测时间戳使用已声明的主机 `monotonic` 时钟。底盘位姿采用世界坐标系，末端执行器位姿相对于 `robot_base`；两者的四元数顺序均为 `xyzw`。Panda 夹爪两个滑动关节通道使用米。工作进程串行执行步进，在同一代际内去重命令 ID；步进失败后拒绝继续控制。停止操作先隔离排队命令、清除运动和模式状态，再执行中性运动步进，直到夹爪保持的通道稳定。服务缓存与本次运行绑定的结果，使每个已选执行器都能取得同一证明；步进失败或夹爪不稳定时报告 `unknown`。躯干不伪造位置观测。基准奖励与成功真值不会作为硬件数据暴露。

`config/package-config.json` 为通用 IsOS 软件包配置界面声明中英文标签和说明。`config/package.toml` 提供 `[package]`、`[host]`、`[services.native]` 和 `[services.robocasa]`。已选原生服务需要本地 MuJoCo 3.3.1 目录；已选 RoboCasa 服务需要本地资源及明确选定的 Python 解释器。这些大型主机资源不随软件包下载。路径属于本地部署配置，不属于图节点设置。每个硬件适配器通过 `service_instance` 选择服务；IsOS 在 Apply 与 Run 时解析它。

RoboCasa 服务配置还要求 `[services.robocasa]` 中的整数 `camera_width` 和 `camera_height`。模板默认均为 64，允许范围均为 64–512 像素。经过验证的服务交接将其作为 `ISOS_ROBOCASA_CAMERA_WIDTH` 和 `ISOS_ROBOCASA_CAMERA_HEIGHT` 传入；工作进程在创建 Gym 环境前验证两者，并将所得尺寸用于全部三路相机观测。尺寸修改在下次运行时生效。已安装的 `0.2.2` 软件包仍固定为 64 × 64；需使用新版本软件包、导入更新后的配置并更新图中的精确版本锁定，才能启用此字段。

RoboCasa 工作进程的私有 `observe` 回复在元数据中携带 `width_px` 和 `height_px`，套接字负载恰好包含 `width_px × height_px × 3` 字节的 RGB8 数据。元数据仍限制为 64 KiB，负载限制为 8 MiB。状态观测继续使用 JSON `values` 回复。插件在发送图中的类型化帧前验证准确尺寸和字节数。

使用 `./build.sh --output 绝对路径的空目录 --version 0.2.3` 或更高的未使用版本构建候选版。已发布的 v0.2.0、v0.2.1 和 v0.2.2 标签保持不变。只有两套预设都通过 IsOS `pkg check` 回放，包括拒绝、崩溃、日志和停止场景，候选版才可发布。

2026-11-13，`0.2.3` 源码候选版使用 IsOS PR #504 的 EOS 命令确认修复，通过隔离的 `isos pkg check`。设置 `ISOS_AETHER_BIN_DIR` 指向已修复的 EOS 可执行文件，并提供本机 EI 与 MuJoCo 路径，然后运行 `isos pkg check --source <本源码目录> --version 0.2.3 --output <空证据目录> --graph <锁定 0.2.3 的 RoboCasa 完整预设图> --graph <锁定 0.2.3 的原生完整预设图> --package-config <本机 package.toml>`。256 × 192 和 512 × 512 两种配置均通过静态验证、原生 ABI、所有者准入、托管观测／控制／日志及两套预设的确认停止；RoboCasa 三路相机帧均报告请求的尺寸。准确命令、输入、`check.json`、所有者交换和完整构建日志保存在被 Git 忽略的 `data/test/2026-11-13-camera-size/`；候选归档 SHA-256 为 `58e3d9fa8d45345d5fe9a0da5f804d016bc6fbddbcb08fcceeece32d92c0bf6f`。发布和更新图中的精确版本锁定仍需另外执行。

[English](../../../docs/mujoco/interfaces/full-hardware.md) · [软件包详情](package_cn.md) · [套接字](socket_cn.md)
