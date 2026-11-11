# MuJoCo 模拟器进程节点

[English](../../../../../docs/mujoco/design/process/mujoco/simulator.md) · [目录](../../README_cn.md) · [包字段](../../../interfaces/package_cn.md) · [套接字契约](../../../interfaces/socket_cn.md)

**当前软件包类型。** v0.2.0 源码候选在 `core=eos`、`layer=process`、`group=mujoco` 贡献 `eos.process.mujoco.simulator@v0.2`，实现类型为 `managed_process`。当前 `sim-hardware` 预设只含进程与一个 JPEG 相机；底盘和机械臂仍在资源目录中，但在执行器 Stop 证明完成前不得用于托管执行。历史 0.1.x 软件包保留原有读取路径。注册的 `NodeType.description`：“作为 EOS 拥有的子进程启动一个已验证 MuJoCo 场景，只提供图中声明的仿真设备。”实例描述独立记录本次部署用途。

## 首次使用行为

1. IsOS 验证精确包收据、可执行文件、场景资源、设备映射及外部 MuJoCo 库；给出带描述和不可用原因的稳定场景/设备选项。操作者选择 ID，不填写路径。
2. IsOS 校验 `sim-hardware` 预览并应用修订。EOS 不修改图，解析已验证的 `mujoco-v2` 动态库并直接启动经验证的模拟器子进程。
3. 套接字健康及声明设备检查通过后节点才就绪。JPEG 相机适配器是独立的 EOS 节点实例；此进程节点不能绕过 dispatcher 准入。
4. 失败时状态保留不可用节点及原因。日志先显示本次运行第一条就绪/故障事件，再按节点路径和关联 ID 过滤。
5. 关闭时 EOS 先关闭准入并请求 R06 物理停止，再终止和回收子进程。未获确认的停止记录为结果不确定；限定范围的 R06 重放已确认底盘与机械臂分别获确认。

## 算法与兼容

选择顺序为：精确收据 → 摘要/路径验证 → 描述符验证 → 选项解析 → 图校验 → 子进程启动 → 套接字健康 → 适配器激活。更换场景需要新图修订和子进程重启。套接字 `2.0.0`、描述符 `2.0.0`、release schema `0.2.0` 与 `mujoco-v2` 适配器名是独立兼容身份。未知未来图或类型版本给出版本诊断；旧图仅在显式且校验修订后迁移。命令去重与停止顺序见[集成设计](../../../architecture_cn.md)。
