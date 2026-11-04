# Island 包发布

[English](../../docs/mujoco/package-release.md)

## `0.1.1` 发布版本 — 2026-11-04

**状态：**`v0.1.1` 已从准确的二进制构建源码 `04b65882cd11b0aff8ce56473164691dbd662196` 发布。重新下载的公开清单与归档摘要均与下文选定值一致。独立的干净 IsOS 主目录测试已验证并安装公开软件包、选择场景和设备、应用图、将 EOS 启动至就绪，并确认 Stop 与子进程回收。后续五方发布资产重放通过了既定 Q04/M5 关卡；具体范围与限制见下文。从较新的文档提交重新构建会产生新候选包，必须重新验证。

**操作员可见变化。** IsOS 可以验证并安装 `island/mujoco-sim@0.1.1`，列出两个场景及可用的相机、底盘、机械臂设备，预览 `sim-hardware` 节点集，并对选定图执行 Validate/Apply。EOS 将已验证仿真器作为直接子进程启动，读取真实相机帧，经 Dispatcher 准入运动，并在终止和回收子进程前确认物理 Stop。选定的干净主目录运行还覆盖子进程故障、受治理重启、软件包与边拒绝，以及显式图迁移。[Q03 验证记录](q03-qualification_cn.md)及 [EOS Q04 重放记录](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)说明范围和原始证据。

**兼容与迁移。** 此包采用 IsOS schema v4，面向图 `0.1.0` 和已注册的 `@v0.1` 类型。保留旧 `eos.process.mujoco@v1.0` 贡献供已验证的旧图读取；迁移须显式执行并检查修订。已发布的 `v1.0.1` 包使用退役图形态，属于另一版本。软件包要求操作员提供 MuJoCo 3.16.0 库；选定资产记录 Ubuntu 24.04、`glibc>=2.39` 和 x86_64。原生依赖规则见[软件包契约](interfaces/package_cn.md)。

**发布后的安装或升级。** 将 `MUJOCO_ROOT` 指向已安装的 MuJoCo 3.16.0 目录，按下文验证已发布清单和归档，再按[后端指南](backend_cn.md)安装或链接精确的 `0.1.1` 软件包，选择场景和设备，执行 Validate/Apply，启动 EOS。已保存的旧图在操作员请求迁移前保持原字节。

**已知范围。** 此次验证使用本地模拟托管 Origin 和 Ubuntu 24.04 原生资产；不证明公网 HTTPS 部署、其他架构或发行版、物理机器人切换或高频执行器通道。MuJoCo 仍是外部运行时依赖。软件包不向 EOS 或 EGIA 暴露基准真实状态。

### 已发布的精确字节与候选包检查

冻结的 Q04 final-5 候选包由源码提交 `04b65882cd11b0aff8ce56473164691dbd662196` 构建。选定**输入** `release.json` 的 SHA-256 为 `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`；归档为 8,797,162 字节，SHA-256 为 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`。IsOS 安装后的清单是另一份字节流，不是发布输入。当前远端 `master` 之后仅增加文档；依照 IsOS 软件包来源校验要求，`v0.1.1` 必须解析到准确的构建源码。新标签首次发布时曾指向文档后代提交，随后立即修正；清单与归档字节未变。任何非文档改动都须重新构建、生成清单与摘要并重放干净主目录。

将封存的 Q04 `live/package-input/` 候选文件复制到 `/home` 下由操作员管理的目录后，运行并保留以下输出：

```sh
candidate=/home/ashex/release-candidates/mujoco-0.1.1
test "$(sha256sum "$candidate/release.json" | cut -d' ' -f1)" = c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096
test "$(sha256sum "$candidate/asset.tar.gz" | cut -d' ' -f1)" = bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4
test "$(stat -c %s "$candidate/asset.tar.gz")" = 8797162
python3 - "$candidate/release.json" <<'PY'
import json, sys
release = json.load(open(sys.argv[1], encoding="utf-8"))
asset = release["assets"][0]
assert (release["id"], release["version"], release["source_commit"]) == ("island/mujoco-sim", "0.1.1", "04b65882cd11b0aff8ce56473164691dbd662196")
assert (asset["sha256"], asset["size_bytes"], asset["libc"], asset["tested_ubuntu"]) == ("bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4", 8797162, "glibc>=2.39", ["24.04"])
assert "libmujoco.so.3.16.0" in asset["required_libraries"]
PY
mkdir -p "$candidate/inspect"
tar -xzf "$candidate/asset.tar.gz" -C "$candidate/inspect"
readelf -d "$candidate/inspect/bin/eos-mujoco-sim"
test -z "$(readelf -d "$candidate/inspect/bin/eos-mujoco-sim" | rg 'RPATH|RUNPATH')"
git diff --quiet 04b65882cd11b0aff8ce56473164691dbd662196 HEAD -- . ':(exclude)docs/**' ':(exclude)docs_cn/**'
```

最后一条命令比较已审查构建源码与当前的纯文档后代提交；已发布标签本身解析到构建源码。应对照目标主机检查 `readelf` 以及清单中的完整排序 `required_libraries` 列表，并在发布记录中保留选定 EOS [完整离线验证器命令](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md)及其 `Q01_FULL_VERIFIED` 输出。该记录还包含 CMake/CTest（26/26）与 3,630 个文件的归档审查。选定 Q04 资产须原字节上传；从较新提交重新构建并写入新的 `source_commit`，即使测试通过，也属于新候选包。

此次文档审查在已审查的 master 基础提交上重新运行 `git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror`、`cmake -S . -B logs/test/20261104-q04-release-notes/build -DMUJOCO_ROOT=<MuJoCo 3.16.0 根目录>`、`cmake --build logs/test/20261104-q04-release-notes/build -j4` 和 `ctest --test-dir logs/test/20261104-q04-release-notes/build --output-on-failure`：格式检查通过，CTest 为 26/26。R05/R06 静态用例矩阵分别通过 31/48 项，五项节点贡献测试、文档本地链接以及所复制选定清单／归档／ELF 检查均通过。完整本机输出位于 Git 忽略的 `logs/test/20261104-q04-release-notes/`；此次重跑检查当前源码，冻结的 Q04 归档仍是精确发布候选包。

### 发布后检查

首次公开下载检查已通过：`sha256sum` 返回选定清单摘要 `c421039…` 和归档摘要 `bb2862…`；归档有 56 个安全成员，远端 `v0.1.1^{}` 解析到 `04b65882cd11b0aff8ce56473164691dbd662196`。独立的干净主目录测试使用重新下载的字节、IsOS `c45011f`、公开 EOS 候选源码 `a4b66d3` 与 MuJoCo 3.16.0；软件包验证／安装、`pick-place` 预览、Validate/Apply、受管就绪和确认 Stop／回收均通过。完整本机输出位于 `/home/ashex/q04t/mujoco-public-smoke/`。这是首次使用已发布字节的初步测试。后续[五方发布资产重放](https://github.com/Island-Team/Island-eos/blob/master/docs_cn/island/q04-merged-qualification_cn.md)在干净 IsOS 主目录中使用已发布的 MuJoCo 归档，通过了发布资产的主路径、重启、迁移及 Stop 验证；另有单独封存的合并后提交六案例重放作为补充。发布关卡在其既定范围内已完成；发布资产重放没有呈现界面 Vision 帧，也没有测试公网 HTTPS Origin。

已发布的 `v0.1.1` 包包含精确的 `release.json` 清单和 `mujoco-sim-v0.1.1-linux-x86_64.tar.gz` 归档。将两份资源下载到 `/home` 下的新目录，对照上文核对 SHA-256 和归档大小，并检查公开标签目标、清单 `source_commit`、许可证、归档布局、ELF 依赖与发布 URL。上述安装／就绪／Stop 初步测试与后续 Q04/M5 发布资产重放，均已在各自记录的范围内通过。封存的 EOS `logs/test/20261104-public-five-assets-7/` 记录已发布资产字节、来源、现场观察、重启、迁移、Stop、独立评审及校验和清单。新的候选包或部署环境须使用新的运行 ID 重新验证。

```sh
download=/home/ashex/release-candidates/mujoco-0.1.1-public
mkdir -p "$download"
gh release download v0.1.1 --repo Island-Team/isos-mujoco-sim --dir "$download" --pattern release.json --pattern mujoco-sim-v0.1.1-linux-x86_64.tar.gz
sha256sum "$download/release.json" "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
stat -c '%s %n' "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
git ls-remote --tags origin refs/tags/v0.1.1
```

## Aether v2 节点候选包详情

`tools/build-backend-bundle.py` 生成本地 `island/mujoco-sim@0.1.1` 后端包、schema v4 `release.json` 和带校验值的归档。`node_contributions` 声明一个由包提供的模拟器进程类型、`mujoco-v2` 适配器系列，以及 `sim-hardware` 节点集。节点集使用通用 EOS 相机、底盘、机械臂、门和 primitive 绑定类型。每个硬件节点在设置中选择并固定 MuJoCo 适配器；通用类型不归该包所有。IsOS 在安装或链接时验证发布信息并展示节点；图预览与应用仍需操作员明确执行。`backend-v2.json` 继续单独描述可执行文件、场景、设备和 MuJoCo 库依赖。构建与验证步骤见 [后端指南](backend_cn.md)。

原生 `0.1.1` 候选包先运行 CMake/CTest 门，再执行 `tools/build-backend-bundle.py --build-dir <构建目录> --mujoco-root "$MUJOCO_ROOT" --output <空目录>`。构建工具暂存 CMake 安装后的程序，并在归档前检查它。审核 `assets[0].libc`、`tested_ubuntu`、`required_libraries`、归档摘要以及解压后 `readelf -d bin/eos-mujoco-sim` 的输出。当前 Ubuntu 24.04 主机记录 `glibc>=2.39` 和精确的 MuJoCo 3.16.0 SONAME。归档程序通过 IsOS 受管理启动时的 `LD_LIBRARY_PATH` 使用外部 MuJoCo 库。干净的 IsOS 管理式重定位与停止回放通过之前，不发布候选包。

## 先前发布版本

版本 1.0.1 已通过 GitHub Release 和 Island 包目录发布为 `island/mujoco-sim`。旧版 v0.1.0 使用旧目录模式；v1.0.1 使用 IsOS schema v4 清单。

`tools/build-package-release.py` 构建经过测试的 C++ 模拟器、场景资源、许可证和旧 EOS 配置模板，并生成供审核的归档及清单草稿。示例：

```sh
python3.12 tools/build-package-release.py --build-dir build --output dist
```

发布前需审核源代码、归档字节、许可证、SHA-256、依赖和 EOS 行为。候选清单记录 `ldd` 报告的 SONAME；`isos packages doctor` 检查运行时依赖。旧版激活包中的 `module.toml`、`eos.toml` 和 `binding.toml` 属于原 EOS 布局。MuJoCo 3.16.0 仍由操作员提供；可在 IsOS 管理的 EOS 节点 `launch.env` 中设置 `MUJOCO_ROOT`。变更二进制文件必须发布新版本。
