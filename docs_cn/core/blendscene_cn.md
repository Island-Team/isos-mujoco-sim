# Blender 场景转换器（blendscene）

[English](../../docs/core/blendscene.md) · [文档](../README_cn.md)

`tools/blendscene.py` 把任意 Blender `.blend` 文件转换成可运行的 MuJoCo 小车导航场景：带纹理的可视网格、结构性碰撞外壳，以及内嵌的差速驱动小车。仓库里跟踪的 `assets/car_scene` 就是该工具的一个输出（由作者的 `0001.blend` 生成）；流水线本身与具体场景无关。

## 环境要求

- 一个装有 `mujoco` 3.3.1、`numpy`、`Pillow` 的 Python。仓库的 `.car-venv` 即可（Windows 下是 `scripts/` 布局，Linux 下是 `bin/`）。
- Blender 4.3.x，按 `--blender PATH`、`BLENDER_EXE` 环境变量、`PATH` 的顺序查找。只有导出和 analyze 阶段需要 Blender，其余步骤没有它也能跑。

## 快速开始

```sh
.car-venv/Scripts/python tools/blendscene.py building.blend        # -> assets/building_scene/
.car-venv/Scripts/python tools/blendscene.py run                   # 交互式 WASD 查看器
```

`build` 依次执行完整流水线：

1. **导出** — 无头 Blender 载荷（`tools/blendscene_export.py`）复制可见网格、烘焙世界变换、按主材质合并对象为 `meshes/vis_<材质>.obj`（附 MTL 与解包纹理），把最大的结构写成 `collision/col_NNNN.obj`，并输出 `manifest.json`。Blender 即使载荷抛异常也退出 `0`，因此编排器还要求 manifest 是新写入且可解析的。
2. **打包** — `tools/blendscene_pack.py` 就地把 OBJ 转成 MuJoCo 二进制 MSH，把非 PNG 的 `map_Kd` 图转成 PNG（MuJoCo 只加载 PNG），并裁掉 MuJoCo 永远不会读的贴图。
3. **构建** — `tools/blendscene_build.py` 由 manifest 和 MTL 生成 `scene.xml`，内嵌小车、导出的点光源、安全地板和 `eos_benchmark_car_navigation_v1` profile 标记。
4. **出生点** — 首次构建时，`tools/blendscene_spawn.py` 用射线检测找一个开阔出生点和最远开阔目标点，并据此重建 XML。

Blender 和 MuJoCo 都是 z 轴朝上的右手系，坐标原样传递。源模型里的地板必须有厚度——零体积的可视网格无法通过 MuJoCo 编译。

## 命令参考

| 命令 | 用途 |
| --- | --- |
| `build <model.blend> [-o DIR]` | 完整流水线；默认输出 `assets/<blend文件名>_scene` |
| `analyze <model.blend> [--out FILE]` | 通过 Blender 输出场景统计（单位、包围盒、材质） |
| `spawn <scene_dir> [--force]` | 刻意重算 `spawn.json` |
| `run [SCENE]` | 交互式 WASD 查看器（默认 `assets/car_scene/scene.xml`） |
| `drive [SCENE]` | 无头脚本化驾驶检查；小车疑似翻车时退出码为 `1` |
| `render [SCENE] [--recolor]` | 离屏渲染 + 接触报告；`--recolor` 用于诊断渲染过暗 |

常用的 `build` 参数：`--unit-scale`、`--collision-min-size`、`--max-collision`（导出调优），`--spawn X,Y[,Z]` 与 `--goal X,Y`（直接固定端点而不做射线搜索），`--respawn`（重算出生点），`--no-export`（复用现有 manifest），`--skip-pack`，`--drive`/`--render`（构建后顺带验证），`--blender PATH`。出生点搜索参数（`--window`、`--center`、`--spawn-inset`、`--seed`、`--trials`、`--clearance`、`--floor-z`）默认从 manifest 包围盒推导。

## 场景目录布局

```
assets/<名称>_scene/
  scene.xml       # 生成的 MJCF；给定下列输入时输出是确定的
  manifest.json   # 导出摘要：包围盒、可视组、碰撞列表、灯光、材质
  spawn.json      # {"pos": [x, y, z], "goal": [x, y]}
  meshes/         # 二进制 MSH + MTL + PNG 纹理   （不入 git）
  collision/      # 二进制 MSH 碰撞外壳            （不入 git）
```

`meshes/` 与 `collision/` 这两个重型目录被 gitignore（`/assets/*_scene/meshes/`、`/assets/*_scene/collision/`），改以 release 资源包形式分发，见下一节。输入不变时重新生成会得到逐字节一致的 `scene.xml`；`<mujoco model>` 的名字由目录名推导，所以不要重命名已有的场景目录。

## 分发资源包

`tools/blendscene_assets.py` 为网格不入 git 的场景提供与 RoboCasa 源码获取同模式的分发：

```sh
python tools/blendscene_assets.py check       # 网格是否就位？
python tools/blendscene_assets.py download    # 下载 + sha256 校验 + 解压
python tools/blendscene_assets.py pack        # 重新导出后重建 dist/<zip>
```

每个场景的固定信息（release tag、压缩包名、URL、sha256）放在脚本顶部的 `SCENES` 注册表里；`CAR_SCENE_ASSETS_URL` 和 `CAR_SCENE_ASSETS_SHA256` 环境变量可覆盖。全新 clone 先执行 `download` 再 `ctest -R engine-car-test`，否则测试会带着同样的提示快速失败。重新导出后：递增该场景的版本号，`pack`，把 zip 上传到对应 release tag，并把打印出的 sha256 贴进注册表。不要对已发布的版本重复 pack——zip 元数据会改变摘要。

## 再生成与出生点稳定性

`spawn.json` 只由出生点阶段写入，已存在的文件在没有 `--force`/`--respawn` 时绝不覆盖。这是刻意设计：`tests/engine_car.cpp` 断言了烘焙进已跟踪场景的出生点位姿，重新搜索会得到另一个（依然有效的）出生点，并在测试更新之前一直打破该断言。重新导出时使用与当前生成相同的 Blender 版本；`manifest.json` 出现顺序重排类的 diff 是红旗，不是噪音。

## 引擎契约

小车的几何参数（轮半径 `0.08` m、轮距 `0.36` m、最大轮速 `15` rad/s）和所有引擎侧名字（`car`、`car_root`、`wheel_{left,right}_spin`、`{left,right}_wheel_motor`、`robot_camera`、`navigation_goal`、profile 标记）硬编码在 `tools/blendscene_build.py` 中，必须与 `src/mujoco/engine.cpp` 里的常量（`kCarWheelRadius` 等）保持一致。修改它们是一次跨构建器、引擎、测试的同步编辑；交互式查看器则直接从加载的模型推导轮几何。

## 验证

- `ctest -R engine-car-test` —— C++ 侧 profile、出生点位姿、驾驶/导航不变量（需要已下载的网格）。
- `.car-venv/Scripts/python tools/blendscene.py drive` —— 无头运动检查。
- `.car-venv/Scripts/python tools/blendscene.py render` —— 离屏渲染输出到 `.run/`。
- 从 blend 重建一个已跟踪场景并要求 `git status` 干净——回环不允许改动任何已跟踪文件。
