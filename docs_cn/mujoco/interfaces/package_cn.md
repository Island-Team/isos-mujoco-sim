# MuJoCo 包描述符与节点声明

[English](../../../docs/mujoco/interfaces/package.md) · [套接字](socket_cn.md) · [包发布](../package-release_cn.md)

**所有权与状态。** 本仓库拥有 MuJoCo 专用 `backend-v2.json` 描述符和 schema v4 `release.json` 中的 `node_contributions`。IsOS 拥有通用发布清单 schema、注册表验证、节点图和 `/node-options` API。`tools/build-backend-bundle.py` 已能生成包；下述选择器与 `@v0.1` 声明属于目标设计。即使新建图格式为 `0.1.0`，`backend-v2.json`、schema `2.0.0`、协议名 `mujoco-v2` 和套接字线协议 `2.0.0` 仍是兼容性标识。

## 当前描述符字段

| 字段 | 类型／单位 | 用途／所有者 | 默认、验证和兼容 |
| --- | --- | --- | --- |
| `schema_version` | 字符串 | 描述符解析标识／本包 | 必填 `2.0.0`；IsOS 拒绝未知主版本，并保留此标识。 |
| `package.id`, `package.version` | 字符串 | 精确包锁定／本包 | 必填 `island/mujoco-sim`、`0.1.1`；须匹配已验证收据。 |
| `entrypoint` | 相对路径 | 模拟器程序／本包 | 必填 `bin/eos-mujoco-sim`；IsOS 检查其在已验证包内且可执行。 |
| `protocol` | 字符串 | EOS 适配器工厂标识／本包与 EOS | 必填 `mujoco-v2`；EOS 必须有匹配的编译工厂。 |
| `scenes[] .id` | 唯一字符串 | 稳定场景选择值／本包 | 当前 `pick-place`、`navigation`；图不存路径。 |
| `scenes[] .path` | 相对路径 | 场景 MJCF 与资源／本包 | 必须在已验证包内解析为可读的受支持场景；禁止遍历和符号链接逃逸。 |
| `devices.camera`, `.base`, `.manipulator` | 字符串 | 模拟器设备 ID／本包 | 当前 `cam-0`、`base-0`、`arm-0`；适配器设置使用精确 ID。 |
| `runtime.mujoco_version` | 字符串 | 外部 MuJoCo ABI 要求／本包 | `3.16.0`；IsOS 启动前检查库和程序兼容性。 |
| `runtime.environment_variable` | 字符串 | 安装根目录输入／本包 | `MUJOCO_ROOT`；不能把未验证程序路径或秘密写入图。 |
| `runtime.library` | 相对路径 | 安装根目录下所需动态库／本包 | `lib/libmujoco.so.3.16.0`；IsOS 启动前验证。 |

通用 `release.json` 字段（ID、版本、校验值、架构、源码、许可证、资源）遵循 IsOS 包契约。本包贡献一个进程节点类型、`mujoco-v2` 适配器系列和 `sim-hardware` 节点集。包只拥有模拟器进程类型；相机、底盘、机械臂、门、primitive 绑定和 Vision 类型仍归 EOS 或 IsOS。实例的 `description` 描述配置好的实例；目标注册进程的 `NodeType.description` 描述可复用类型。当前 sidecar 没有类型描述，发布新 sidecar 前由 IsOS 提供规定的兼容默认。

## 选择器契约呈现

目标 sidecar 把 `scene` 标记为包场景选择器，把硬件 `device_id` 标记为包设备选择器。IsOS 根据精确安装收据及当前图锁定解析选项，不使用任意用户路径。每项返回稳定 ID、标签、描述、可用性和原因；已保存但不存在或不可用的 ID 在 UI 中仍可见，但阻止 Apply。验证后选择 `pick-place` 对应 `assets/scene.xml`，`navigation` 对应 `assets/scenes/navigation/scene.xml`。设备选项受注册硬件种类和描述符设备映射限制。其他包资源将来可使用相同机制；本次不定义 EGIA tensor 执行。

匹配的 EOS 与 IsOS 读取方能够接收后，新声明使用 `@v0.1` 节点 ID。旧 `@v1.0` ID 仍能按原有行为读取；IsOS 不静默改写已应用图。schema v4 收据及其内容校验值保持不可变。二进制或场景变更需要新包版本。

## 故障示例

若选择 `scene="navigation"`，但其资源验证失败，IsOS 返回带原因的不可用场景选项，图不能 Apply。EOS 不用未经验证的路径启动子进程。若包已安装但缺少所需 MuJoCo 库，安装记录可以保留，但运行就绪为 false；UI 显示库问题和精确包锁定。
