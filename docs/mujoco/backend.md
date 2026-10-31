# IsOS managed MuJoCo backend

**Current implementation:** This page records the existing bundle and integration path. [Package descriptor and contributions](interfaces/package.md) and [simulator socket](interfaces/socket.md) are the owner-specific field contracts; [design](design.md) and [TODO](todo.md) distinguish the new 0.x target. The `v2` in a protocol or generated descriptor filename is retained for compatibility; this topic page has no version suffix.

[中文](../../docs_cn/mujoco/backend_cn.md)

Build the simulator and stage a local `island/mujoco-sim@0.1.1` bundle:

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.16.0
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
python3 tests/node_contributions.py
python3 tools/build-backend-bundle.py --output /absolute/path/to/mujoco-v2-bundle
isos pkg link island/mujoco-sim 0.1.1 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
```

The bundle contains an actual executable at `bin/eos-mujoco-sim`, the two
supported scenes and their model assets, `backend-v2.json`, and a local schema v4 `release.json`. The builder writes a checksummed release archive beside the bundle. The descriptor
declares the `mujoco-v2` protocol, `cam-0`, `base-0`, and `arm-0` device IDs,
and the external MuJoCo 3.16.0 library requirement. IsOS verifies the scene,
assets, executable, and library before run and supplies the library directory
to the child process. Package installation alone does not activate a graph.

The release's `node_contributions` declares a `sim-hardware` node set and the `mujoco-v2` adapter family. The EOS-owned simulator process is the sole package-contributed node type at `eos/process/mujoco/simulator`. Generic hardware types place one device at each of `eos/hardware/camera/front`, `eos/hardware/base/drive`, and `eos/hardware/manipulator/arm`. Each device selects `mujoco-v2` in its adapter settings and pins `island/mujoco-sim@0.1.1` there; its generic node type has no package pin. The adapter family declares supported device classes and exact primitive versions, while EOS verifies that a compiled factory actually exists. The set adds `base.velocity@1.0.0` and `arm.movej@1.0.0` binding nodes under `eos/dispatcher/base` and `eos/dispatcher/manipulator`; their typed command outputs connect to the selected device nodes. The shared dispatcher service remains the admission and safety owner. The camera connects to the EOS gate under `eos/interface/gate`, which supplies the default input to `isos/ui/panel/vision`. IsOS catalogs the set after install or link; preview binds the scene and owner-only socket, resolves symbolic references, and validates the resulting shared graph. The preset edits the draft graph only. Vision can select another active compatible gate at runtime without changing the default edge.

The backend node's `settings.env` can contain `MUJOCO_GUI=1` or
`MUJOCO_GUI=true`. This opens an X11 window titled `IsOS MuJoCo — live
simulation` while EOS owns the simulator child. It renders camera frames from the
same `SimEngine` instance controlled by the v2 socket and benchmark socket.
The default is headless. A desktop with an accessible `DISPLAY` is required;
an unavailable display makes the simulator fail at startup. The independent
`tools/scene-view.sh` viewer remains a static scene preview.

The v2 socket uses an eight-byte little-endian frame header followed by JSON
metadata and an optional JPEG payload. Metadata is capped at 64 KiB; payload
is capped at 8 MiB. The request must include `version: "2.0.0"`, a string
`id`, `node`, and `op`. The response echoes ID and version and supplies `ok`
or `error.message`. Operations refer to the live state:

| Operation | Request fields | Response fields |
| --- | --- | --- |
| `health` | none | `accepted: bool` |
| `camera_capture` | none | `format: "jpeg"`, `rgb_length: u64` bytes, `depth_available: false`, `width_px: u32`, `height_px: u32`, JPEG payload |
| `base_observe` | none | `position_m: [f64; 2]`, `linear_velocity_m_s: [f64; 2]`, `yaw_rad: f64`, `angular_velocity_rad_s: f64` |
| `base_move` | `linear_x_m_s: f64`, `linear_y_m_s: f64`, `angular_z_rad_s: f64`, `valid_for_ms: f64` in `(0, 5000]`, `command_id: string` | `accepted: bool`; drive expires after `valid_for_ms` simulated time |
| `manipulator_observe` | none | `joint_positions_rad: [f64; 6]`, `joint_velocities_rad_s: [f64; 6]`, `end_position_m: [f64; 3]`, `end_orientation_xyzw: [f64; 4]` |
| `manipulator_move` | `joint_positions_rad: [f64; 6]`, `command_id: string` | `accepted: bool` |
| `stop` | `command_id: string` | `accepted: bool`; holds base and arm |

`timestamp_ns` is simulated time in nanoseconds and `sequence` is the engine
step count. Values are finite and movement bounds are enforced by the engine.
The v2 socket is owner-only (`0600`) and removed on normal shutdown. IsOS verifies the package and passes the executable and scene to EOS. EOS starts the simulator as its direct child, connects its hardware adapters as socket clients, and stops admitted actuators before terminating the simulator.

## Verification

On 2026-10-30, `cmake --build build -j4` and all ten CTest cases passed on
Ubuntu with MuJoCo 3.16.0. `tests/v2.py` exercised real JPEG capture, base
motion, six-joint command, safe stop, and socket cleanup. With
`MUJOCO_GUI=1` and `DISPLAY=:0`, `xwininfo` reported a visible 640×480
window. A v2 base command moved observed base x from -1.20 m to -0.951 m;
XWD captures of that window had different pixel hashes. The unavailable GUI
test confirmed startup failure removes every socket. The commands and full
output are in `logs/test/2026-10-30-v2-live/{build,ctest,bundle,gui}.log`;
XWD captures are in that same directory. Reproduce the visual check with
`python3 tests/gui.py build/eos-mujoco-sim assets/scene.xml
logs/test/2026-10-30-v2-live` on a desktop with X11 access.

The earlier six-node preset and port metadata passed `python3 tests/node_contributions.py` (four tests) on 2026-10-30. `python3 tools/build-backend-bundle.py --build-dir build --output logs/test/20261030-general-interfaces/bundle-r3` staged that release candidate, and `ctest --test-dir build --output-on-failure` passed all ten simulator tests. Complete local output is in `logs/test/20261030-general-interfaces/`. The current eight-node preset is checked with the same Python command; its baseline simulator suite passed ten tests on 2026-10-31 in `logs/test/20261031-generic-device-preset/`.

An isolated IsOS home linked the previous `bundle-r3`, previewed `sim-hardware` with a scene and socket, and validated the resulting graph through EOS `aether-profile`. That preview added six nodes, kept package pins only on the four former MuJoCo types, and reported three IsOS-owned processes. Reproduction details are in `logs/test/20261030-general-interfaces/graph-preview.log`. The new preset requires the updated generic device and primitive contracts in EOS and IsOS.

## Package version 0.1.1 check (2026-10-31)

`python3 tests/node_contributions.py`, `python3 tests/release.py`, and `ctest --test-dir build --output-on-failure` passed (10 simulator tests). `python3 tools/build-backend-bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` staged a bundle whose release and descriptor report package `0.1.1`. Descriptor schema and socket protocol remain `2.0.0`. Output is in ignored `logs/test/20261031-version-alignment/`.
