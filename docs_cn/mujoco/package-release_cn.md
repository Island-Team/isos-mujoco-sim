# Island 包发布

[English](../../docs/mujoco/package-release.md)

## Aether v2 节点候选包

`tools/build-backend-bundle.py` 生成本地 `island/mujoco-sim@0.1.1` 后端包、schema v4 `release.json` 和带校验值的归档。`node_contributions` 声明一个由包提供的模拟器进程类型、`mujoco-v2` 适配器系列，以及 `sim-hardware` 节点集。节点集使用通用 EOS 相机、底盘、机械臂、门和 primitive 绑定类型，并添加 IsOS Vision 面板。每个硬件节点在设置中选择并固定 MuJoCo 适配器；通用类型不归该包所有。IsOS 在安装或链接时验证发布信息并展示节点；图预览与应用仍需操作员明确执行。`backend-v2.json` 继续单独描述可执行文件、场景、设备和 MuJoCo 库依赖。构建与验证步骤见 [后端指南](backend_cn.md)。

## 先前发布版本

版本 1.0.1 已通过 GitHub Release 和 Island 包目录发布为 `island/mujoco-sim`。旧版 v0.1.0 使用旧目录模式；v1.0.1 使用 IsOS schema v4 清单。

`tools/build-package-release.py` 构建经过测试的 C++ 模拟器、场景资源、许可证和旧 EOS 配置模板，并生成供审核的归档及清单草稿。示例：

```sh
python3.12 tools/build-package-release.py --build-dir build --output dist
```

发布前需审核源代码、归档字节、许可证、SHA-256、依赖和 EOS 行为。候选清单记录 `ldd` 报告的 SONAME；`isos packages doctor` 检查运行时依赖。旧版激活包中的 `module.toml`、`eos.toml` 和 `binding.toml` 属于原 EOS 布局。MuJoCo 3.16.0 仍由操作员提供；可在 IsOS 管理的 EOS 节点 `launch.env` 中设置 `MUJOCO_ROOT`。变更二进制文件必须发布新版本。
