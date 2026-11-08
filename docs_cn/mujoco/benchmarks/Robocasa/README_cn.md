# RoboCasa 基准

[English](../../../../docs/mujoco/benchmarks/Robocasa/README.md) · [使用指南](../../usage/README_cn.md)

当前基准采用上游 RoboCasa365 的 `CloseFridge` 原子任务。首次本地回合使用官方 `robocasa/CloseFridge` Gym 环境、target 划分、种子 42 和 RoboCasa 自身的成功判定：选定的冰箱门必须关闭。`tools/robocasahrun.py` 在底盘运动为零的条件下执行 20 个有界随机动作，作为启动冒烟基线。结果只证明环境启动与评分，并不代表训练策略或可与排行榜比较的成绩。正式评测按 RoboCasa 建议每任务运行 20 回合，并记录种子、资源、策略版本和时长。

默认运行 `./launch.sh` 即启动此回合。脚本从根目录 `config.toml` 读取 `ROBOCASA_ROOT`，然后由 `.env` 覆盖；空值使用忽略的 `.local/robocasa`。若源码、运行环境或资源缺失，启动脚本先询问再设置。`./launch.sh --robocasa --seed 42 --steps 20` 可显式指定任务预算。设置脚本固定 RoboCasa 与 robosuite 源码版本、安装私有 Python 3.11 环境，并从固定版本的官方 RoboCasa 资源数据集下载纹理和通用装置资源，再从经过校验和验证的社区镜像下载 Lightwheel 装置与物体资源。这些文件位于忽略的 `.local/`。Python 运行环境及 C++ 构建均使用 MuJoCo 3.3.1。

RoboCasa [源码采用 MIT 许可](https://github.com/robocasa/robocasa/blob/main/LICENSE)；其 [README](https://github.com/robocasa/robocasa#license) 说明资源与数据集采用 CC BY 4.0。任务实现和成功规则位于上游 `robocasa/environments/kitchen/atomic/kitchen_doors.py`。[RoboCasa365 论文](https://robocasa.ai/assets/robocasa365_iclr26.pdf) 描述基准。再分发资源或结果时应保留资源署名。

原有自行设计的抓取放置和导航任务仅作为历史模拟器兼容性测试场景，不再是当前基准。其私有 C++ 基准 RPC 仍不通过 EOS 或 EGIA 暴露。RoboCasa 在上游环境中运行；[Python 机器人硬件核心](../../interfaces/robocasa-hardware_cn.md)在进程内控制并观测 PandaOmron 机器人，[本地记录](../../interfaces/robocasa-record_cn.md)可重放硬件命令以测试控制逻辑。EOS 代理控制仍需受控适配器，完成之前不能称为 EOS 端到端评测。

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

在 `config/benchmarks/robocasa.toml` 的 `[task]` 中设置 `name`、`split`、`scene`、`seed` 和 `steps`，可修改共享默认值。根目录 `config.toml` 通过 `BENCHMARK_CONFIG` 指向该文件。被忽略的 `.env` 可用 `export BENCHMARK_TASK=...` 等赋值覆盖，也可设置 `export BENCHMARK_SCENE=1:1`。命令行参数优先于两者。运行 `./launch.sh` 使用配置的基准，或运行 `./launch.sh --native` 使用配置的原生 `SIM_SCENE`。`--show-config` 输出生效的选择。JSON 结果会以 `layout:style` 记录实际厨房 `scene`。上游时长是任务元数据；此运行器的 `--steps` 是较短的冒烟预算，不表示完成正式评测回合。

纳入版本控制的 [RoboCasa 预设](../../../../config/benchmarks/robocasa.toml) 将任务选择、相机观测和 GUI 显示设置分组。要使用另一份预设，可在根目录 `config.toml` 将 `BENCHMARK_CONFIG` 设为其路径。启动前，加载器会拒绝缺失的分组或字段、未知字段以及错误的 TOML 类型。

## 相机和显示配置

RoboCasa 提供三个 RGB 视角：`robot0_agentview_left`、`robot0_agentview_right` 和 `robot0_eye_in_hand`。`BENCHMARK_CAMERA` 选择 dev 图形窗口显示的视角，不会移除其他相机观测。`BENCHMARK_CAMERA_WIDTH` 和 `BENCHMARK_CAMERA_HEIGHT` 指定实际渲染的观测尺寸（每边 64–2048 像素，默认 256×256）。修改它们会影响图像像素和运行耗时，因此报告基准结果时应记录。`BENCHMARK_GUI_WIDTH` 只缩放显示窗口（256–3840 像素，默认 768），保持观测分辨率及画面宽高比。结果 JSON 记录相机和渲染尺寸。

可在 `config/benchmarks/robocasa.toml` 的 `[camera]` 和 `[gui]` 中设置这些值，再由 `.env` 的对应 `BENCHMARK_*` 变量覆盖，或使用单次命令参数：

```sh
./launch.sh --benchmark CloseFridge --camera robot0_agentview_right --gui-width 960
./launch.sh --benchmark CloseFridge --camera-width 512 --camera-height 512 --gui-width 960
```

第一条命令放大窗口，基准观测仍为 256×256；第二条渲染 512×512 观测，消耗更多 GPU 时间和显存。使用 `--no-gui` 可关闭窗口。

## 本地验证

2026-11-08，`./launch.sh --robocasa --seed 42 --steps 20` 连续运行两次，均返回相同的任务说明、20 步和 `success: false`。这证明上游任务可加载且成功规则被调用，但不构成代理策略成绩。使用 MuJoCo 3.3.1 的 C++ 构建通过了全部 27 项 CTest。
