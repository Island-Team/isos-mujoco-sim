# MuJoCo 0.1.1 集成 TODO

实施跟踪见 [MuJoCo 包 0.1.1](https://github.com/Island-Team/isos-mujoco-sim/milestone/1)，并纳入共享 [M2 已验证输入](https://github.com/Island-Team/Island-eos/milestone/2)、[M3 受治理执行](https://github.com/Island-Team/Island-eos/milestone/3) 和 [M5 集成验收](https://github.com/Island-Team/Island-eos/milestone/5)。下列步骤按依赖顺序完成。

[English](../../docs/mujoco/todo.md) · [设计](design_cn.md) · [套接字契约](interfaces/socket_cn.md)

**进度，2026-11-02：** 第 2 项已在固定版本的 MuJoCo、EOS 和 IsOS 上通过限定范围的 R05 所有者验收；详见[跨所有者证据](design_cn.md#r05-跨所有者验收)。第 3 项的抢占式物理停止与实时受管理运动，以及第 4–5 项的完整日志与发布验收仍待完成。R05 结果不意味着已发布 `v0.1.1` 标签。

1. 为贡献的进程类型及其场景设置增加非空描述和选择器元数据。只有 IsOS/EOS 目录读取方支持后才发布 `@v0.1` 类型；保留 `@v1.0` 别名和已安装 schema-v4 包身份。描述符选项必须来自已验证场景/设备资源。
2. 增加受管理的严格套接字启动与健康特性确认，同时保留直接启动的旧 `2.0.0` 语义。在严格模式下检查套接字 `node` 模拟器设备 ID 与操作/设备匹配，并在 EOS 检查图到设备的映射、有限有类型输入、向后兼容的稳定错误码、有界请求 ID。按 `(node, command_id)` 实现幂等，拒绝冲突重放并限制保留量。保持分帧格式与线协议 `2.0.0` 不变。
3. Stop 可抢占进行中的运动或慢速拍摄，遵守有限期限，并确认底盘与机械臂；EOS 必须在终止子进程前停止已准入执行器。测试相同传输重发、结果不确定时不自动重放、重复运动、冲突重放、不支持的节点/设备、损坏或超长帧、GUI 不可用、子进程崩溃和清理。
4. 按共享格式记录经净化的 JSONL 启动、就绪、故障与停止事件，包含运行/节点/关联 ID；不记录 JPEG 帧或秘密。通过 IsOS 测试轮转/游标与 UI 中首次故障查找。
5. 运行 `python3 tests/node_contributions.py`、`python3 tests/release.py`、`ctest --test-dir build --output-on-failure` 和 IsOS → EOS → MuJoCo → EGIA 成功、故障与安全停止集成测试。完整输出存于 `logs/test/<run-id>/`，记录可复现命令、环境、结果与限制。之后才考虑发布 `v0.1.1`；保留历史标签。

现有 C++ 模拟器是本包实现，**不是** EOS 无用的旧 `src/eos/` 运行时。其现有 gRPC 模拟器服务在最后调用方审查证明可移除前仍是历史兼容侧链。
