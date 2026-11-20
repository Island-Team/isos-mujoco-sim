# Release history and qualification records

[中文](../docs_cn/changelog_cn.md) · [Docs](README.md)

These records retain historical package declarations, process-node behavior, design proposals, and checks at their recorded versions and dates. Old commands, owner relationships, dependency versions, and statements such as “current” or “remaining” inside a historical record apply to that record only. Use [start](start.md), [package](package.md), and [architecture](architecture.md) for the present service model. Candidate qualification does not publish a release; source, package, graph, node, ABI, and socket versions are independent.

<a id="standard-hardware-contract-verification-2026-11-19"></a>
### Standard hardware contract verification (2026-11-19)

The `0.2.8` source candidate registers all seven hardware types against the current EOS catalog. Its standard command contracts are inherited by the parts Dispatcher. Native and RoboCasa command graphs and a separate RoboCasa mode binding validate; unassigned hardware and direct skill-to-hardware bypasses reject. The plugin accepts standard payloads, checks required fields, frames, joint order, limits, and leases, and performs private wire translation. The owner selects unchanged standard forwarding from the registered input contract while retaining legacy package translation.

Reproduce with `cmake --build build -j4`, `ctest --test-dir build --output-on-failure -j4`, `python3 tests/nodes.py`, and `python3 tests/eos_contracts.py --eos-profile <current-IsOS-checkout>/target/debug/aether-profile --plugin build/libmujoco-eos-node.so`. The interop script requires Python `jsonschema`. Build the candidate with `python3 tools/bundle.py --build-dir build --mujoco-root <local-3.3.1-root> --output <empty-directory>`; its default version is `0.2.8`. Check the resulting manifest and archive with `isos pkg verify <release.json> <archive>`. Complete commands and output are under ignored `data/test/20261119-standard-hardware/`.

The checks passed: 35 CTest cases, 17 node declaration tests, nine graph admission cases, nine standard payload schemas, 12 RoboCasa worker tests, and 13 hardware tests. A real EOS owner → parts Dispatcher → plugin → native service replay completed base, arm, and gripper commands and observations, rejected a wrong Dispatcher identity, and confirmed Stop. RoboCasa adapter calls use a stub service in these boundary tests; this does not qualify a new full Gym deployment or publish the candidate. Old exact package pins retain their declarations and payload handling.

The camera adapter assigns a separate publication sequence to each camera instance. Repeated observations of a cached RoboCasa image therefore remain deliverable to inference nodes that reject replayed source sequences; the simulator command/state sequence stays private. After installing changed source at the same unpublished `0.2.8` version, Apply the graph again so its verified library digest matches the rebuilt package. The camera [interface](node/eos/hardware/camera.md) defines the counter and cached-image limitation.

On 2026-11-19, `cmake --build .local/package-build --target mujoco-eos-node -j2`, `ctest --test-dir .local/package-build -R '^eos-node-plugin' --output-on-failure`, and `clang-format --dry-run --Werror src/plugin/node.cpp` passed. The four plugin boundary tests cover two native and RoboCasa camera publications while the stub's simulator state sequence remains fixed, malformed RGB payload rejection, commands, service failure, and Stop. Complete output is in ignored `data/test/20261119-camera-sample-sequence/`. These source checks do not publish a package release.

<a id="historical-020-process-candidate"></a>
### Historical 0.2.0 process candidate

The historical default built `island/mujoco-sim@0.2.0`. `./build.sh --output <absolute-empty-directory> --version 0.2.x` selects an unpublished patch candidate; each published fix receives a new patch version. The release uses `isos.package@v1` schema `0.2.0` and contributes the `mujoco-v2` adapter family through `lib/libmujoco-eos-node.so`. The manifest records its SHA-256 in both `adapters` and `node_contributions.libraries`; the exact archive pins the same bytes. The output directory preserves the manifest asset basename, such as `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`. Archive entries are path sorted with zero owner and timestamps, and gzip mtime is zero; repeated archives of fixed payload bytes have the same digest. `python3 tests/archive.py` checks this boundary. `bin/eos-mujoco-sim` remains the verified supervised child. The library exports `isos_node_v1` with create/start/input/health/stop/destroy, consumes the admitted node's `adapter.settings`, probes `strict-socket-v1`, and translates camera, base, and manipulator observations into generic `@v0.2` payloads. It accepts only `{"op":"observe"}` input; it rejects direct movement. The historical `sim-hardware` set contains only the simulator process and JPEG camera (12 MiB observation JSON cap), with `jpeg` capability. Base and manipulator remain in the resource catalog but outside managed graphs until actuator Stop proof is complete. EOS must own Dispatcher admission and physical stop proof before a command set may be published.

For `isos pkg check --source`, export `MUJOCO_ROOT` to the local 3.3.1 installation; the explicit environment value takes precedence over `[host].mujoco_root` in `config/package.toml`; the package build does not load development `.env`. `python3 tests/build_env.py` verifies this build input boundary without downloading anything. The manifest bounds IsOS compatibility to `[0.2.3,0.3.0)` and requires IsOS `package-process-v1` plus EOS `native-plugin-v1`; the release check still records the exact qualified IsOS build. The `.so` is a Linux C++/protobuf binary and requires the IsOS host's ABI table plus matching runtime libraries. Building the file alone does not establish compatibility: IsOS checks the manifest and digest, EOS checks the ABI and callbacks, and managed qualification checks the simulator child, data schemas, readiness, and Stop. Other platforms and in-process Python remain future work; Python may use a supervised process interface. `python3 tests/plugin.py <built-lib>` exercises strict health, observation, movement rejection, and Stop against a stub. The older `0.1.2` notes below are historical candidate evidence, not instructions for the current hardware candidate.

On the 2026-11-11 Linux x86_64 qualification host, the real MuJoCo 3.3.1 build passed all 29 CTest cases, including the native adapter, package catalog, strict socket, camera failure, Stop, and scene viewer checks. Set `MUJOCO_ROOT=<absolute MuJoCo 3.3.1 root>` for the build and the package process host input. When launching IsOS, also set `LD_LIBRARY_PATH="$MUJOCO_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"` so the EOS-owned simulator child can load `libmujoco.so.3.3.1`; the package archive does not contain that library. The checked `0.2.0` source candidate passed `isos pkg check --source ... --version 0.2.0 --graph ...` with managed Run, camera observation, logs, and Stop. Complete local build and CTest output is under ignored `data/test/20261111-real-mujoco/`; IsOS qualification evidence is recorded by its own check output. This is source qualification evidence, not a claim that a GitHub release is already published.

<a id="historical-012-candidate-notes"></a>
### Historical 0.1.2 candidate notes

The `0.1.2` bundle below is a local development candidate using MuJoCo 3.3.1. It is not a published release; historical `0.1.1` evidence later on this page remains tied to MuJoCo 3.16.0.

**Current implementation:** This page records the existing bundle and integration path. [Package descriptor and contributions](package.md) and [simulator socket](core/adapter.md) are the owner-specific field contracts; [architecture](architecture.md) explains integration and [remaining qualification](#remaining-qualification) records the open checks. The `v2` in a protocol or generated descriptor filename is retained for compatibility; this topic page has no version suffix.

[中文](../docs_cn/start_cn.md)

For a fresh local source install, set `MUJOCO_ROOT` and run `isos pkg install --source /absolute/path/to/isos-mujoco-sim --allow-source-build`. IsOS invokes this repository's executable `build.sh --output <empty-staging-directory>`, verifies `release.json` and the manifest-named archive, then installs the package. The package declares its process entrypoint and generic scene/device catalog; IsOS does not need a MuJoCo-specific launch path. Validate and Apply the node set, then explicitly Run or Restart the deployment. Installation alone does not change an active run.

Build the simulator and stage a local `island/mujoco-sim@0.1.2` bundle:

```sh
export MUJOCO_ROOT=/absolute/path/to/mujoco-3.3.1
mkdir -p "$HOME/tmp"
export TMPDIR="$HOME/tmp"
cmake -S . -B build -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build -j
ctest --test-dir build --output-on-failure
python3 tests/nodes.py
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
```

Keep build and temporary directories on a filesystem with enough space, for example `TMPDIR=/home/you/tmp` and `--build-dir /home/you/build-mujoco`. The builder installs the executable through CMake, checks its installed ELF dependencies, and records the native Ubuntu, glibc and resolved library requirements in `release.json`. On Ubuntu 24.04 the asset claims `glibc>=2.39` and `tested_ubuntu:["24.04"]`; the archive has no build-host RUNPATH. Use `--mujoco-root "$MUJOCO_ROOT"` when the root is not exported to the builder. Inspect `readelf -d bin/eos-mujoco-sim` and the release asset before linking or publishing.

The bundle contains an actual executable at `bin/eos-mujoco-sim`, the two
supported scenes and their model assets, `backend-v2.json`, and a local schema v4 `release.json`. The builder writes a checksummed release archive beside the bundle. The descriptor
declares the `mujoco-v2` protocol, `cam-0`, `base-0`, and `arm-0` device IDs,
and the external MuJoCo 3.3.1 library requirement. IsOS verifies the scene,
assets, executable, and library before run and supplies the library directory
to the child process. Package installation alone does not activate a graph.

The release's `node_contributions` declares the `sim-hardware` set, `mujoco-v2` adapter family, and package-owned `eos.process.mujoco.simulator@v0.2` process type. The `0.2.1` set adds that process plus general EOS camera, base, and manipulator `device@v0.2` instances. Each hardware node pins `island/mujoco-sim@0.1.2` in `node.adapter.package` and selects its stable device ID. This first set is observation-only: it declares no Dispatcher command binding or camera gate. IsOS verifies the release, then validates a composed graph at preview and Apply; EOS readiness and Stop require a separately tested owner runtime. See the [package contribution contract](#p02-contribution-and-graph-boundary).

The backend node's `settings.env` can contain `MUJOCO_GUI=1` or
`MUJOCO_GUI=true`. This opens an X11 window titled `IsOS MuJoCo — live
simulation` while EOS owns the simulator child. It renders camera frames from the
same `SimEngine` instance controlled by the v2 socket and benchmark socket.
The default is headless. A desktop with an accessible `DISPLAY` is required;
an unavailable display makes the simulator fail at startup. The independent
`tools/view.sh` viewer remains a static scene preview.

**R05 scoped qualification:** an EOS-managed strict child accepts only the framed v2 socket and rejects the historical gRPC robot and benchmark sockets. A separate direct launch retains those sockets for legacy clients and trusted evaluation. The pinned IsOS → EOS → MuJoCo replay proved strict health for the declared camera, base and arm in both scenes, read-only capture and observations, and child/socket cleanup. The R06 owner stop fence merged, and scoped cross-owner movement and stop replay passed; broader R06 failure qualification remains open. See the [owning socket contract](core/adapter.md) and [R05 evidence](#r05-cross-owner-qualification).

The v2 socket uses an eight-byte little-endian frame header followed by JSON
metadata and an optional JPEG payload. Metadata is capped at 64 KiB; payload
is capped at 8 MiB. The request must include `version: "2.0.0"`, a string
`id`, `node`, and `op`. The response echoes ID and version and supplies `ok`
or `error.message`. Operations refer to the live state:

| Operation | Request fields | Response fields |
| --- | --- | --- |
| `health` | none | `accepted: bool` |
| `camera_capture` | none | `format: "jpeg"`, `rgb_length: u32` bytes, `depth_available: false`, `width_px: u32`, `height_px: u32`, JPEG payload |
| `base_observe` | none | `position_m: [f64; 2]`, `linear_velocity_m_s: [f64; 2]`, `yaw_rad: f64`, `angular_velocity_rad_s: f64` |
| `base_move` | `linear_x_m_s: f64`, `linear_y_m_s: f64`, `angular_z_rad_s: f64`, `valid_for_ms: f64` in `(0, 5000]`, `command_id: string` | `accepted: bool`; drive expires after `valid_for_ms` simulated time |
| `manipulator_observe` | none | `joint_positions_rad: [f64; 6]`, `joint_velocities_rad_s: [f64; 6]`, `end_position_m: [f64; 3]`, `end_orientation_xyzw: [f64; 4]` |
| `manipulator_move` | `joint_positions_rad: [f64; 6]`, `command_id: string` | `accepted: bool` |
| `stop` | `command_id: string` | `accepted: bool`; holds base and arm |

`timestamp_ns` is simulated time in nanoseconds and `sequence` is the engine
step count. Values are finite and movement bounds are enforced by the engine.
The v2 socket is owner-only (`0600`) and removed on normal shutdown. IsOS verifies the package and passes the executable and scene to EOS. EOS starts the simulator as its direct child and connects its hardware adapters as socket clients. The scoped R06 replay proved physical stop before termination and reap for both scenes; R05 cleanup alone did not prove that.

<a id="verification"></a>
### Verification

On 2026-10-30, `cmake --build build -j4` and all ten CTest cases passed on
Ubuntu with MuJoCo 3.3.1. `tests/v2.py` exercised real JPEG capture, base
motion, six-joint command, safe stop, and socket cleanup. With
`MUJOCO_GUI=1` and `DISPLAY=:0`, `xwininfo` reported a visible 640×480
window. A v2 base command moved observed base x from -1.20 m to -0.951 m;
XWD captures of that window had different pixel hashes. The unavailable GUI
test confirmed startup failure removes every socket. The commands and full
output are in `logs/test/2026-10-30-v2-live/{build,ctest,bundle,gui}.log`;
XWD captures are in that same directory. Reproduce the visual check with
`python3 tests/gui.py build/eos-mujoco-sim assets/scene.xml
logs/test/2026-10-30-v2-live` on a desktop with X11 access.

The earlier six-node preset and port metadata passed `python3 tests/nodes.py` (four tests) on 2026-10-30. `python3 tools/bundle.py --build-dir build --output logs/test/20261030-general-interfaces/bundle-r3` staged that release candidate, and `ctest --test-dir build --output-on-failure` passed all ten simulator tests. Complete local output is in `logs/test/20261030-general-interfaces/`. The then-current eight-node preset was checked with the same Python command; its baseline simulator suite passed ten tests on 2026-10-31 in `logs/test/20261031-generic-device-preset/`.

An isolated IsOS home linked the previous `bundle-r3`, previewed `sim-hardware` with a scene and socket, and validated the resulting graph through EOS `aether-profile`. That preview added six nodes, kept package pins only on the four former MuJoCo types, and reported three IsOS-owned processes. Reproduction details are in `logs/test/20261030-general-interfaces/graph-preview.log`. That earlier replay is historical evidence; the current two-node `0.2.1` camera set needs a new cross-owner replay.

<a id="package-version-011-check-2026-10-31"></a>
### Package version 0.1.1 check (2026-10-31)

`python3 tests/nodes.py`, `python3 tests/release.py`, and `ctest --test-dir build --output-on-failure` passed (10 simulator tests). `python3 tools/bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` staged a bundle whose release and descriptor report package `0.1.1`. Descriptor schema and socket protocol remain `2.0.0`. Output is in ignored `logs/test/20261031-version-alignment/`.

<a id="isos-and-eos-deployment"></a>
### IsOS and EOS deployment

For the current IsOS/EOS path, build and link a local `island/mujoco-sim@0.1.2` bundle as described in the [backend guide](start.md). The published v1.0.1 package uses the retired graph shape; its [release guide](#package-release-record) remains for historical installations. MuJoCo 3.3.1 is an operator-provided dependency; set `MUJOCO_ROOT` to the real installation before building the bundle and running the graph.

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

Stage and select EOS and IsosUI builds with `isos build eos`, `isos version select eos <selector>`, `isos build isosui`, and `isos version select isosui <selector>`. A selector identifies one exact receipt; when multiple EOS builds share a commit, use its source fingerprint. `isos init` exits without starting services. Run `isos serve` in a terminal, preview the installed `sim-hardware` node set with `isos pkg preview-set` or the IsOS API, choose the scene and owner-only socket, then Validate and Apply the draft with the revision-checked IsOS interface. The IsosUI catalog editor is part of the later U01 workbench gate. The set declares an EOS-owned simulator process and three generic hardware adapters; this candidate has no Dispatcher command binding. IsOS preserves an authored graph until the operator applies the new revision.

**P02 package catalog and IsOS selection.** The bundle builder now emits the `0.1.0` catalog descriptor and four-node `0.2.1` set with stable `scene`, `camera_device`, `base_device` and `manipulator_device` parameters. Build and inspect the bundle with `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <empty-directory>`; `backend-v2.json` contains two scene IDs, their labels, profiles and SHA-256 values, plus the three device descriptions and scene support lists. After P01 verifies the exact `island/mujoco-sim@0.1.2` receipt, the IsOS P02/P03 slices expose available IDs, Validate and Apply the selected scene and devices against the current saved revision, and retain unavailable saved IDs for correction. A scene edit creates a new saved revision; Restart is required to replace the EOS-owned child. See the [P02 package contract](#p02-descriptor-extension) and [negative fixtures](../tests/fixtures/scene_catalog/negative-cases.json).

Run `isos run` in another terminal to start the applied deployment. IsOS preflights the exact package, assets, scene, MuJoCo library, EOS executables, sockets, and ports before starting graph children. EOS starts the simulator as its direct child. The scoped R06 replay proved physical stop ordering for pick-place and navigation; broader failure qualification remains open. `isos deployment stop` stops the deployment only; `isos stop` shuts down the manager, API, UI, deployment, and independent IsOS services. EGIA uses EOS's normal agent interface and never connects to the private benchmark socket. The service manager for model-like processes is separate from this hardware graph.

**R05 managed readiness, scoped qualified:** after Apply, EOS launches the verified child in strict mode and probes `health` for every graph-declared camera, base and arm device. It requires `version:"2.0.0"`, the echoed request ID, `ok:true`, `accepted:true` and `features` containing `strict-socket-v1`. Treat a socket file or process startup line as progress, not readiness. A missing feature, wrong device, failed camera render or exited child leaves the backend unavailable; inspect the current run's first failure event. The pinned cross-owner replay passed this path for pick-place and navigation, including read-only capture and observations. At that R05 baseline, the EOS catalog exposed only `safety.estop` for MuJoCo and withheld `base.velocity` and `arm.movej`; the R06 replay below subsequently exercised governed movement and stop. The R05 replay itself released no managed movement. See the [qualification](#r05-cross-owner-qualification).

To verify the simulator owner slice directly, start `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"` in a private directory and send a framed `health` request with `node:"base-0"`. The response must echo the ID and include `ok:true`, `accepted:true` and `strict-socket-v1`. Managed launch rejects `--socket` and `--benchmark-socket`; direct launch without the flag continues to support them. `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` replays the owner checks, including full retention capacity.

For a P02 catalog failure, inspect the unavailable scene/device reason and the first package or Apply failure event before changing the draft. A changed linked asset requires explicit relink under the P01 receipt rule. A missing `MUJOCO_ROOT` library blocks launch readiness; a scene/profile mismatch blocks Apply. The graph and running child retain their prior revisions on these failures.

Stop through `isos deployment stop` after inspecting the result and current run logs. R05 adds strict identity and retransmission protection; the merged R06 companion lane and scoped replay proved separate base/arm acknowledgment before simulator termination and reap for both scenes. An `accepted:true` reply alone is never evidence of confirmed safe stop; inspect EOS's selected terminal receipt and IsOS's final outcome.

**R06 scoped first-use behavior:** the reviewed `strict-stop-v1` owner implementation merged in [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21), and a real pick-place/navigation IsOS → EOS → MuJoCo replay exercised governed movement and stop. With exact verified owner builds, use the same Validate/Apply/Run path. The managed child derives an owner-only companion socket at the main socket path plus `.stop`; no graph field is added. Check that `health` for each actuator reports both `strict-socket-v1` and `strict-stop-v1` and that EOS probes the companion stop socket before its catalog offers `base.velocity` or `arm.movej`. EOS sends the matching 32-character `generation_id` from both health paths and `stop_epoch:"0"` with the first bounded managed movement and sends the current proved epoch with later movements; a stale **new** command fails `stop_fenced`, while an identical old command ID returns its stored R05 result. Submit the movement through EOS, then use EOS/IsOS stop while a movement or capture is active. EOS sends governed stops with that generation ID to the companion socket. A delayed request from an old child fails `stale_generation`. Its strict `stop` response must echo its request ID and contain `base_stop:"stopped"`, `arm_stop:"stopped"`, the matching `generation_id`, a nonempty decimal-string `stop_epoch`, `ok:true`, and `accepted:true`; EOS must validate that proof before terminating and reaping its direct child, then publish the selected terminal receipt only after cleanup. The values are defined in the [socket contract](core/adapter.md#r06-managed-stop-contract): status strings are unitless proof states, while `stop_epoch` is a child-local ordering counter used as a movement precondition. A missing/unknown status, timeout, child crash or `stop_outcome_unknown` means safe stop is unconfirmed; inspect the first correlated failure event and the EOS journal, then verify bounded child and both socket paths are cleaned up. Do not infer physical stop from process exit or `accepted` alone. The scoped replay confirmed both stop parts, matching generation and epoch `1`, and no surviving child/group/socket; lost stop socket and child crash remained unknown. See the [R06 evidence](#r06-owner-merge-and-scoped-cross-owner-replay). Forced timeout/KILL, GUI unavailability, stale or wrong pipe, and crash recovery still require broader R06 qualification before full M3 control is claimed.

The v2 package permits `MUJOCO_GUI=1` in the simulator node's `settings.env`. It opens a live X11 view from the same simulator engine used by the v2 socket. The standalone `--gui` launcher below opens a separate static MuJoCo viewer instead. See [backend.md](start.md) for the node and socket contracts.

<a id="package-release-record"></a>
### Package release record

[中文](../docs_cn/changelog_cn.md#软件包发布记录)

<a id="011-release--2026-11-04"></a>
### `0.1.1` release — 2026-11-04

**Status:** `v0.1.1` is published from the exact binary build source `04b65882cd11b0aff8ce56473164691dbd662196`. Fresh public downloads match the selected manifest and archive hashes below. A focused clean IsOS home verified and installed the public package, selected the scene and devices, applied the graph, launched EOS to ready, and confirmed Stop and child reap. The later five-owner released-asset replay passed its stated Q04/M5 gate, with the scope and limits recorded below. Rebuilding from a later documentation commit produces a different candidate and requires new verification.

**Operator-visible changes.** IsOS can verify and install `island/mujoco-sim@0.1.1`, list its two scenes and available camera, base and manipulator devices, preview the `sim-hardware` node set, and Validate/Apply the selected graph. EOS launches the verified simulator as its direct child, reads real camera frames, admits movement through Dispatcher and confirms physical Stop before child termination and reap. The selected clean-home run also exercised a child fault, governed restart, package and edge rejection, and explicit graph migration. The [Q03 qualification record](#final-selected-source-and-merged-head-archive-evidence-2026-11-04) and [EOS Q04 replay record](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md) describe the scope and raw evidence.

**Compatibility and migration.** This is an IsOS schema v4 backend package with a graph `0.2.1` set and registered `@v0.2` types. Previously verified releases containing `eos.process.mujoco@v1.0` remain readable through their legacy reader; the current `0.1.2` candidate does not contribute it. Migration is explicit and revision checked. The published `v1.0.1` package uses the retired graph shape and is a separate release. The current `0.1.2` candidate requires an operator-provided MuJoCo 3.3.1 library. The published `v0.1.1` asset used MuJoCo 3.16.0 and recorded Ubuntu 24.04, `glibc>=2.39`, and x86_64. The [package contract](#native-012-asset-requirements) owns the native dependency rules.

**Install or upgrade after publication.** Set `MUJOCO_ROOT` to the installed MuJoCo 3.16.0 tree, verify the published manifest and archive as below, then use the [backend guide](start.md) to install or link the exact `0.1.1` package, select a scene and devices, Validate/Apply, and start EOS. A saved legacy graph is read without changing its bytes until the operator requests migration.

**Known limits.** This qualification used a local simulated hosted Origin and the native Ubuntu 24.04 asset. It does not establish a public HTTPS deployment, another architecture or distribution, a physical robot cutover, or a high-rate actuator channel. MuJoCo remains an external runtime dependency. The package does not expose benchmark truth to EOS or EGIA.

<a id="exact-published-bytes-and-candidate-checks"></a>
#### Exact published bytes and candidate checks

The frozen Q04 final-5 candidate was built from source commit `04b65882cd11b0aff8ce56473164691dbd662196`. Its selected **input** `release.json` SHA-256 is `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`; the archive is 8,797,162 bytes with SHA-256 `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`. The IsOS-installed manifest is a separate byte stream and is not the publication input. Current remote `master` contains later documentation only; `v0.1.1` peels to the exact build source, as required by IsOS package provenance. The newly created tag was initially placed on the documentation descendant and corrected immediately after publication; the manifest and archive bytes did not change. Any non-documentation change requires a new build, manifest, digest and clean-home replay.

With the candidate copied from the sealed Q04 `live/package-input/` directory into an operator-owned directory under `/home`, run and retain the output of:

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

The last command compares the reviewed build source with the current documentation descendant; the published tag itself resolves to the build source. Review `readelf` and the manifest's full sorted `required_libraries` list against the target host, and keep the selected EOS [full offline verifier command](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md) and its `Q01_FULL_VERIFIED` output with the release record. CMake/CTest (26/26) and the 3,630-file archive review are recorded there. The selected Q04 asset must be uploaded unchanged; a fresh build with a later stamped `source_commit` is a new candidate even if its tests pass.

The documentation review reran `git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror`, `cmake -S . -B logs/test/20261104-q04-release-notes/build -DMUJOCO_ROOT=<MuJoCo 3.16.0 root>`, `cmake --build logs/test/20261104-q04-release-notes/build -j4`, and `ctest --test-dir logs/test/20261104-q04-release-notes/build --output-on-failure` on the reviewed master base: formatting passed and CTest passed 26/26. The R05/R06 fixture matrices passed 31/48 cases, five node-contribution tests passed, local document links passed, and the copied selected manifest/archive/ELF checks above passed. Complete local output is ignored by Git under `logs/test/20261104-q04-release-notes/`; this rerun checks the current source, while the frozen Q04 archive remains the exact release candidate.

<a id="postpublication-checks"></a>
#### Postpublication checks

The first public download check passed: `sha256sum` returned the selected `c421039…` manifest and `bb2862…` archive digests, the archive had 56 safe members, and remote `v0.1.1^{}` resolved to `04b65882cd11b0aff8ce56473164691dbd662196`. An independent clean-home smoke used those downloaded bytes with IsOS `c45011f`, public EOS candidate `a4b66d3`, and MuJoCo 3.16.0; package verification/install, `pick-place` preview, Validate/Apply, managed readiness and confirmed Stop/reap passed. The complete local output is under `/home/ashex/q04t/mujoco-public-smoke/`. That was the initial published-byte smoke. The later [five-owner released-asset replay](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md#seventh-attempt-published-owner-assets-2026-11-04-approved) used the published MuJoCo archive in a clean IsOS home and passed its released-asset main, Restart, migration, and Stop profile. It complements the separately sealed merged-head six-case replay. The release gate is complete for that stated scope; the published-asset replay did not render a UI Vision frame or exercise public HTTPS Origin.

The published `v0.1.1` release contains the exact manifest as `release.json` and archive as `mujoco-sim-v0.1.1-linux-x86_64.tar.gz`. Download both into a fresh directory under `/home` and compare their SHA-256 and archive size with the values above; inspect the public tag target, manifest `source_commit`, license, archive layout, ELF dependencies and release URLs. The focused install/readiness/Stop smoke above and the later Q04/M5 released-asset replay have passed for their documented scopes. The sealed EOS run `logs/test/20261104-public-five-assets-7/` records the published asset bytes, provenance, live observations, Restart, migration, Stop, independent review, and checksum manifest. Use a new run ID and fresh verification for any new candidate or deployment environment.

```sh
download=/home/ashex/release-candidates/mujoco-0.1.1-public
mkdir -p "$download"
gh release download v0.1.1 --repo Island-Team/isos-mujoco-sim --dir "$download" --pattern release.json --pattern mujoco-sim-v0.1.1-linux-x86_64.tar.gz
sha256sum "$download/release.json" "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
stat -c '%s %n' "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
git ls-remote --tags origin refs/tags/v0.1.1
```

<a id="aether-v2-node-candidate-details"></a>
### Aether v2 node candidate details

`tools/bundle.py` stages the local `island/mujoco-sim@0.1.2` backend, a schema v4 `release.json`, and a checksummed archive. Its `node_contributions` declares one package-owned simulator process type, the `mujoco-v2` adapter family, and the `sim-hardware` node set. The set uses generic EOS camera, base, manipulator, gate, and primitive binding types. Each hardware node selects and pins the MuJoCo adapter in its settings; the package does not own those generic types. IsOS verifies the release and lists the nodes after install or link; graph preview and apply remain explicit operator actions. The backend descriptor still owns executable, scene, device, and MuJoCo library metadata. See the [backend guide](start.md) for build and validation steps.

For the native `0.1.2` candidate, run the CMake/CTest gates first, then invoke `tools/bundle.py --build-dir <build> --mujoco-root "$MUJOCO_ROOT" --output <empty directory>`. The builder stages the CMake-installed executable and inspects it before archiving. Review `assets[0].libc`, `tested_ubuntu`, `required_libraries`, archive digest, and an extracted archive's `readelf -d bin/eos-mujoco-sim` output. The Ubuntu 24.04 host currently records `glibc>=2.39` and the exact MuJoCo 3.3.1 SONAME. The archived executable relies on IsOS's managed `LD_LIBRARY_PATH` for the external MuJoCo library. Do not publish a candidate until a clean IsOS-managed relocation and stop replay passes.

<a id="earlier-published-release"></a>
### Earlier published release

Version 1.0.1 is published as a GitHub Release and in the Island package-center catalog for `island/mujoco-sim`. The older v0.1.0 entry remains in the legacy catalog schema; v1.0.1 uses an IsOS schema v4 manifest.

`tools/release.py` assembles a local candidate for the curated
Island package center. It runs the existing CTest suite, stages the simulator
binary, scene assets, license files, and EOS configuration templates, then
measures the exact archive size and SHA-256 digest. It does not upload or
publish a release.

Build on each target machine separately. Supply the minimum glibc version
established for that binary and only Ubuntu versions actually tested there:

```sh
python3.12 tools/release.py \
  --version 1.0.1 \
  --build-dir build \
  --eos-root ../Island-eos \
  --output /home/ashex/release-candidates/island-mujoco-legacy \
  --glibc-min 2.35 \
  --tested-ubuntu 24.04
```

The archive contains `bin/eos-mujoco-sim` as a launcher. It requires an
operator-provided MuJoCo 3.16.0 installation and `MUJOCO_ROOT` pointing at its
root directory. The archive includes neither the MuJoCo library nor EOS. The
candidate manifest lists all SONAMEs reported by `ldd`; `isos packages doctor`
checks them before installation. Review the full list and the actual target
machine before approval.

The builder writes `island-release.<arch>.draft.json` using IsOS release schema v4. Its `assets` entry records the tested Linux architecture and minimum glibc, while `source_commit`, SHA-256, and byte size identify the exact source and archive. Build each target natively, review both drafts and assets, and combine only qualified target entries into the final `island-release.json` uploaded with the GitHub `v1.0.1` release. Do not claim an architecture or Ubuntu version that was not tested.

The activation bundle contains `module.toml`, `eos.toml`, and `binding.toml` from the current EOS layout. IsOS installs the backend but stages activation until `isos config apply`; it never edits an operator's active deployment on download. The generated EOS module launches the packaged `eos-mujoco-sim` with sockets under the deployment run directory. MuJoCo 3.16.0 remains an operator-provided dependency. Set `MUJOCO_ROOT` in the IsOS-managed EOS node's `launch.env` so EOS passes the MuJoCo installation root to the child simulator process.

After uploading, verify the release source, asset bytes, licenses, digest, requirements, and EOS behavior. A member's submission needs an independent reviewer before publication; a developer can publish a complete manifest directly. A changed binary needs a new version.

To inspect archive layout without claiming qualification, pass `--skip-tests`. Do not submit that candidate for approval.

<a id="current-012-candidate-verification-2026-11-11"></a>
### Current `0.1.2` candidate verification (2026-11-11)

From this source checkout, `python3 tests/nodes.py` and `ctest --test-dir build -R '^(scene-catalog|bundle-catalog|strict-socket|strict-stop-lane|strict-stop-lane-navigation)$' --output-on-failure` pass. Build with `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <empty-directory>`, then run `isos pkg verify <bundle>/release.json <archive>` and `ISOS_HOME=<isolated-home> isos pkg link island/mujoco-sim 0.1.2 <bundle> --manifest <bundle>/release.json`; both pass against the current IsOS source. `aether-profile catalog --node-types <linked-node-types.json>` accepts the contributed process and reports `mujoco-v2` as not compiled. The current IsOS preview calls an EOS `validate --file` command that this EOS profile does not expose, so graph Apply and managed readiness are not qualified by these checks. Full CTest passed 25/27 tests; the two scene-view checks require `bin/compile` and `bin/simulate`, which the local MuJoCo installation lacks. Complete local outputs are under ignored `data/test/20261111-general-hal/`.

<a id="package-qualification-records"></a>
### Package qualification records

Selector checks passed on 2026-11-15: `python3 tests/nodes.py` (14 tests), `python3 -m json.tool config/package-config.json`, and `git diff --check`. The node test checks options against the scene catalog, the verified task, and sample defaults. Full command output is under ignored `data/test/20261115-package-selectors/`.

The native camera dimension change was checked with `cmake --build build -j4`, `ctest --test-dir build --output-on-failure -j4` (35/35), `python3 tests/nodes.py` (13/13), and `git diff --check`. Complete output is retained in ignored `data/test/20261115-native-camera-source-dimensions/`. The selected native preset now declares 1280 × 720 and the strict service test confirms its JPEG metadata and bytes; rejection cases cover missing, fractional, and zero dimensions.

On 2026-11-13, the 2048-pixel candidate passed 18 Python tests, all 33 CTest cases, a native plugin 2048 × 2048 RGB8 exchange, the 0.2.4 candidate build, and static `isos pkg verify`. Changed bilingual pages passed the link audit. Complete output is under ignored `data/test/20261113-robocasa-2048/`. Managed `pkg check` and release publication remain separate gates.

The `0.2.5` source candidate passed 24 RoboCasa Python boundary tests, 11 node-contribution tests, and all 34 CTest cases on 2026-11-15. The packaged launcher rejected missing and nonexecutable interpreters and an unprepared Python environment before creating its socket. IsOS `pkg check --source <checkout> --version 0.2.5 --output <empty evidence directory> --graph <RoboCasa graph> --graph <native graph> --package-config <local package.toml>` reported `qualified:true`, with static verification, native ABI, owner validation, and managed replay passed for both presets. The exact inputs and complete logs are under ignored `data/test/20261115-general-hardware/`; its `pkg-check/check.json` identifies the checked source commit and asset digest. This is candidate qualification, not release publication.

<a id="historical-process-node-declaration-020"></a>
### Historical process node declaration (0.2.0)

The historical `isos.package@v1` schema `0.2.0` `release.json` adds `node_contributions.processes[]` for `eos.process.mujoco.simulator@v0.2`. IsOS verifies the declaration against archived bytes and the contributed process type. EOS implements the named lifecycle adapter. Previously verified releases containing the historical `@v1.0` type remain readable through their existing reader path; this manifest does not contribute that type. Graphs store the exact package pin and stable scene ID, never resolved paths.

| Field | JSON type / unit | Purpose | Validation and default |
| --- | --- | --- | --- |
| `processes[].node_type` | string / — | Process type to launch | Required `eos.process.mujoco.simulator@v0.2`; must name a contributed process type; no default. |
| `processes[].entrypoint` | relative path / — | Verified child executable | Required `bin/eos-mujoco-sim`; executable within the archive, without traversal or symlink escape; no default. |
| `processes[].lifecycle_adapter` | string / — | EOS readiness and stop adapter | Required `mujoco-v2`; EOS must register it; no default. |
| `processes[].args` | string array / — | Verified child argument template | `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}`; EOS binds the private socket and verified scene path at Run. |
| `processes[].resources[]` | array / — | Selector bindings | Required one scene binding; no default. |
| `resources[].setting` | string / — | Process setting holding the resource ID | Required `scene`; must match the node setting; no default. |
| `resources[].kind` | string / — | Catalog resource class | Required `scene`; selected value is a stable scene ID; no default. |
| `resources[].descriptor` | relative path / — | Verified catalog metadata | Required `package-resources.json`; regular archived file without traversal or symlink escape; no default. |
| `processes[].host_inputs[]` | array / — | Host inputs for launch | Required one `MUJOCO_ROOT` directory declaration; no default. |
| `host_inputs[].name` | string / — | Environment variable name | Required `MUJOCO_ROOT`; value is not stored in graph; no default. |
| `host_inputs[].kind` | string / — | Host value type | Required `directory`; IsOS resolves an existing directory; no default. |
| `host_inputs[].required` | boolean / — | Whether launch needs the input | Required `true`; missing input blocks launch. |

The package build entrypoint is `build.sh --output <empty-absolute-directory>`. It requires `MUJOCO_ROOT`, incrementally builds the executable and adapter targets in the ignored `.local/package-build/` CMake directory, and writes `release.json` and the manifest-named archive, such as `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`, into the output directory. A build lock serializes use of that directory. Every invocation reruns CMake configuration and package staging; changed source files, build options, or the selected MuJoCo root trigger the relevant CMake work. Development builds and CTest still build and verify the test targets. The manifest digest and size cover those exact archive bytes. Archive entries are path sorted with zero owner and timestamps, and gzip mtime is zero; repeated archives of fixed payload bytes have the same digest. `python3 tests/archive.py` checks this boundary. Installation does not activate a graph or restart a run.

`package-resources.json` has `contract:"isos.package-resources@v1"`, string `schema_version:"0.1.0"`, and `resources[]`. A scene resource requires `kind:"scene"`, a unique stable string `id`, nonblank `label` and `description`, a contained relative `path` to MJCF, and its lowercase SHA-256 `sha256`. A device resource requires `kind:"device"`, unique stable string `id`, nonblank `label` and `description`, `metadata.device_kind` (`camera`, `base`, or `manipulator`), and nonempty unique `metadata.scene_ids[]` referencing declared scene IDs. All fields are required and have no default. The generic IsOS selector reads this file; `backend-v2.json` remains the MuJoCo-specific EOS adapter contract and legacy descriptor.

**Owner and status.** This repository owns the MuJoCo-specific `backend-v2.json` descriptor and `node_contributions` in its current release manifest. The P02 sections below document the historical 0.1.2 candidate; the current source uses the 0.2.0 contract above. IsOS owns the general release-manifest schema, verified receipt and package admission, graph revision, and `/node-options` response. `tools/bundle.py` emits the P02 catalog and `@v0.2` process contribution; IsOS semantic admission and the generic P03 option API are implemented in their owner repository; the pinned R05 replay verifies their use with this package. `backend-v2.json`, schema `2.0.0`, protocol name `mujoco-v2`, and socket wire `2.0.0` remain compatibility identities when the authored graph format is `0.2.1`.

<a id="historical-012-descriptor-fields"></a>
### Historical 0.1.2 descriptor fields

| Field | Type / unit | Purpose / owner | Default, validation and compatibility |
| --- | --- | --- | --- |
| `schema_version` | string | Descriptor parser identity / this package | Required `2.0.0`; IsOS rejects unknown major versions, retaining this identity. |
| `package.id`, `package.version` | strings | Exact package pin / this package | Required `island/mujoco-sim`, `0.1.2`; must match verified receipt. |
| `entrypoint` | relative path | Simulator binary / this package | Required `bin/eos-mujoco-sim`; IsOS checks regular executable stays inside verified bundle. |
| `protocol` | string | EOS adapter factory identity / this package and EOS | Required `mujoco-v2`; EOS must have matching compiled factory. |
| `scenes[] .id` | unique string | Stable scene selector value / this package | Current `pick-place`, `navigation`; no path is stored in graph. |
| `scenes[] .path` | relative path | Scene MJCF and assets / this package | Must resolve within verified bundle to readable supported scene; no traversal or symlink escape. |
| `devices.camera`, `.base`, `.manipulator` | strings | Simulator device IDs / this package | Current `cam-0`, `base-0`, `arm-0`; exact IDs used by adapter settings. |
| `runtime.mujoco_version` | string | External MuJoCo ABI requirement / this package | `3.3.1`; IsOS checks installed library and executable compatibility. |
| `runtime.environment_variable` | string | Installation root input / this package | `MUJOCO_ROOT`; never copied into graph as a secret or unverified executable path. |
| `runtime.library` | relative path | Required shared library beneath root / this package | `lib/libmujoco.so.3.3.1`; IsOS verifies before launch. |

The historical descriptor has no human scene/device descriptions, scene profile or per-scene digest. Its device map is package-wide. IsOS's existing resolver checks containment and referenced file bytes; its P02 companion adds descriptor-level profile and digest checks. The simulator engine itself checks the profile when loading a scene.

<a id="p02-descriptor-extension"></a>
### P02 descriptor extension

The following fields are additive within descriptor schema `2.0.0`. `scenes[].id` and `devices.<kind>` remain the stable values stored in graph settings; paths, XML markers and hashes are package metadata only. `catalog_version:"0.1.0"` is the sole target discriminator. When it is present, every scene must supply `label`, `description`, `profile` and `sha256`, and `device_catalog` must be complete. When absent, none of those target fields may appear anywhere; that exact old shape is legacy-only. Any partial mix fails as `mujoco_catalog_incomplete`; an unknown catalog version fails as `mujoco_catalog_unsupported`, both before option publication. An already verified historical descriptor without metadata remains readable for its legacy graph behavior, but IsOS does not synthesize new-graph options from it. This decision is made from the descriptor's shape and exact discriminator, never from a filename or a guessed package version.

| Field | JSON type / unit | Purpose and owner | Default, validation and compatibility |
| --- | --- | --- | --- |
| `catalog_version` | string / — | Select P02 metadata rules; MuJoCo package | Absent only for complete legacy shape; present value must be exactly `0.1.0` with all target fields. Partial or unknown versions fail closed. |
| `scenes[].id` | nonblank slug / — | Stable scene selector; MuJoCo package | Required unique within the exact release; current IDs are `pick-place` and `navigation`; never a path. |
| `scenes[].label` | nonblank string / — | Operator display; MuJoCo package | Required for a P02 candidate; legacy catalog display may fall back to `id` without changing bytes. |
| `scenes[].description` | nonblank string / — | Scene purpose and visible task; MuJoCo package | Required for a P02 candidate; no graph field or runtime authority. |
| `scenes[].profile` | string enum / — | Expected engine scene type; MuJoCo package | Required, exactly `eos_benchmark_pick_place_v1` or `eos_benchmark_navigation_v1`; must equal the sole supported MJCF custom numeric marker after safe XML parsing and a real engine load test. |
| `scenes[].path` | safe relative path / — | Scene MJCF; MuJoCo package | Existing required field; regular file inside P01-verified payload, no symlink or traversal; never returned as selector value. |
| `scenes[].sha256` | lowercase 64-hex string / SHA-256 | Bind exact MJCF bytes to scene identity; MuJoCo package | Required for a P02 candidate; compare with the selected file at discovery, Validate, Apply, Run and Restart. P01's payload-tree digest separately covers referenced assets. |
| `devices.<kind>` | nonblank slug / — | Existing simulator device ID by `camera`, `base`, `manipulator`; MuJoCo package | Exactly these three kinds and one distinct ID each for this simulator; preserve legacy string-map shape. |
| `device_catalog[]` | array of objects / — | Human and scene availability metadata; MuJoCo package | Required for a P02 candidate; exactly one entry per `devices` kind and ID, no extras or duplicate IDs. |
| `device_catalog[].kind`, `.id` | strings / — | Device class and stable selector ID; MuJoCo package | Required exact match to `devices[kind]`; current IDs are `cam-0`, `base-0`, `arm-0`. |
| `device_catalog[].label`, `.description` | nonblank strings / — | Operator display and capability; MuJoCo package | Required; no device capability is inferred from a label. |
| `device_catalog[].scene_ids` | nonempty array of scene IDs / — | Scenes in which this device is usable; MuJoCo package | Required unique IDs from `scenes[]`; both current scenes support all three devices. IsOS rejects selection absent from the chosen scene. |

`runtime.mujoco_version`, `runtime.environment_variable` and `runtime.library` keep their existing meanings. IsOS checks the declared `3.3.1` library under `MUJOCO_ROOT` before Apply and Run and reports an unavailable reason when it is absent or incompatible; the package does not bundle the library. A file with the expected name alone is not a claim of ABI compatibility: the launch/readiness boundary must establish the actual loaded version before reporting ready. P01 verifies the exact release receipt, all payload bytes and path containment first. P02 checks semantic scene/profile and device-map consistency against that verified handle. Changing a binary, scene XML, referenced asset or contributed sidecar under a fixed `0.1.2` pin invalidates the P01 receipt; publish a new package version for intentional changes.

The P02 descriptor is frozen in [`target-descriptor.json`](../tests/fixtures/scene_catalog/target-descriptor.json); [`legacy-descriptor.json`](../tests/fixtures/scene_catalog/legacy-descriptor.json) freezes the exact old shape. The bundle builder computes both scene SHA-256 values from copied XML and checks the profile markers, declared model elements, and referenced assets before packaging. Relative MJCF asset references may traverse up from the scene directory only while remaining within the verified bundle; missing, escaping or linked assets fail. Real engine load and replay remain in CTest.

<a id="p02-contribution-and-graph-boundary"></a>
### P02 contribution and graph boundary

The package contributes one new process type, `eos.process.mujoco.simulator@v0.2`, at `eos/process/mujoco`, while previously verified releases with `eos.process.mujoco@v1.0` remain readable through their legacy path. The new type declares `implementation:{"kind":"managed_process","interface":"mujoco-v2","version":"1","lifecycle_adapter":"mujoco-v2"}` and has a nonblank `description`; its `scene` setting has a nonblank description and `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`. `socket` (owner-only Unix socket path), optional `env` (string table) and `start_timeout_ms` (positive integer milliseconds) have described types and validation. Process status and health are runtime-owned and are not graph ports. The process instance pins `node.package:{"id":"island/mujoco-sim","version":"0.2.0"}`; it never stores a resolved executable or scene path in settings. This sidecar adds no actuator or safety adapter route.

The current `sim-hardware` node set targets graph `0.2.1` and contains the package-owned process plus one generic EOS JPEG camera (12 MiB observation JSON cap) `device@v0.2`. The camera instance pins the MuJoCo adapter and references the process. Base and manipulator remain in the resource catalog, but no managed base or manipulator instance is contributed until EOS proves actuator Stop. The package does not contribute or override generic EOS types. Verification and link do not prove graph Apply or runtime readiness. Historical saved graphs retain their existing reader path.

**Target graph admission.** The P02 set declares stable `scene`, `camera_device`, `base_device`, `manipulator_device` and owner-only `socket` parameters. The default scene is `pick-place`; the three device defaults are `cam-0`, `base-0`, `arm-0`. Once the IsOS and EOS graph admission path is available, Preview and Apply must require the selected IDs to be present in the exact verified descriptor, match hardware kind and selected scene, and pass graph-wide admission. An admitted graph stores IDs and the exact package pin. IsOS owns composition and revision compare-and-swap; a scene change must create a new saved revision and reach the child only after Restart. A running simulator must not change scenes in place. Current verification and link pass, while preview is blocked by the IsOS/EOS validation command mismatch and `mujoco-v2` is not compiled in the current EOS owner.

P03 owns the generic `GET`/`POST /node-options` grouping by `(node_path,setting)`, selected-value echo and unavailable-option presentation. This package supplies selector declarations and verified catalog metadata; it does not define an HTTP envelope. R05 owns strict socket feature negotiation, request `node`/operation validation and command deduplication. A P02 catalog entry alone is not socket enforcement evidence; the R05 strict health and device-operation tests provide that proof for managed launch.

<a id="p02-diagnostics-and-isos-admission-target"></a>
### P02 diagnostics and IsOS admission target

IsOS retains the P01 diagnostic shape `{code,path,message,id,version,stage}` and its HTTP 422 admission result. P02 adds the stable `code` values below. `stage` is `descriptor` for direct package metadata checks and `admission` for a selected graph setting or external library check. A direct install/link/verify operation has `path:""` as P01 requires; the frozen fixture's `mutation.path` identifies the descriptor field being tested. During Validate, Apply, Run or Restart, `path` is the exact graph JSON Pointer in the table, with instance IDs taken from the candidate graph. The examples use the `sim-hardware` preset's `simulator` and `arm` IDs; a base device fault points to the corresponding `drive` adapter setting. A malformed catalog is rejected during package verification before a graph setting can be selected; its graph-time path is the process `package` pin. Messages are bounded corrective text, never a raw XML parse error, local path or environment value. An unrelated installed package cannot block a graph that does not pin it.

| Failure | Stable code | Graph-time `path` | Stage |
| --- | --- | --- | --- |
| Target discriminator absent with any target field, or present with any missing field | `mujoco_catalog_incomplete` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `descriptor` |
| Unsupported `catalog_version` value | `mujoco_catalog_unsupported` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `descriptor` |
| Duplicate/blank scene ID, blank description, unsupported profile literal or invalid scene declaration after P01 containment | `mujoco_scene_invalid` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `descriptor` |
| Declared profile differs from the sole supported marker or required model elements | `mujoco_scene_profile_mismatch` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| Declared scene SHA-256 differs from verified XML bytes | `mujoco_scene_digest_mismatch` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| Selected scene ID not in the verified catalog | `mujoco_scene_unavailable` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/settings/scene` | `admission` |
| Duplicate/blank device ID, mismatched map/catalog kind or ID, invalid scene-support list | `mujoco_device_invalid` | `/cores/eos/layers/hardware/groups/manipulator/nodes/arm/adapter/settings/device_id` | `descriptor` |
| Selected device ID absent, wrong kind or unsupported in selected scene | `mujoco_device_unavailable` | `/cores/eos/layers/hardware/groups/manipulator/nodes/arm/adapter/settings/device_id` | `admission` |
| Required MuJoCo library absent or version/ABI incompatible | `mujoco_library_unavailable` | `/cores/eos/layers/process/groups/mujoco/nodes/simulator/package` | `admission` |

For a descriptor-only check, the `path` is empty even when the table shows the corresponding graph-time field. P01's `package_changed` at `payload` and `package_unsafe_path` at the containing stage take precedence over every P02 code. In particular, a linked scene modified after verification yields `package_changed`; a symlinked scene path yields `package_unsafe_path`. A package candidate with intact P01 payload bytes but a wrong declared scene digest yields `mujoco_scene_digest_mismatch` in P02 semantic checking before receipt publication. P03 presents an unavailable option using these bounded causes, but the HTTP option envelope remains IsOS-owned. The complete mutation and expected `{code,path,stage}` tuples are frozen in [`negative-cases.json`](../tests/fixtures/scene_catalog/negative-cases.json).

Example target descriptor excerpt (the full fixture has both scenes and all three devices):

```json
{
  "schema_version": "2.0.0",
  "catalog_version": "0.1.0",
  "package": {
    "id": "island/mujoco-sim",
    "version": "0.1.2"
  },
  "scenes": [
    {
      "id": "pick-place",
      "label": "Pick and place",
      "description": "Reach, grasp and place an object",
      "profile": "eos_benchmark_pick_place_v1",
      "path": "assets/scene.xml",
      "sha256": "6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"
    }
  ],
  "devices": {
    "camera": "cam-0",
    "base": "base-0",
    "manipulator": "arm-0"
  }
}
```

For a selected `navigation` scene whose XML declares `eos_benchmark_pick_place_v1`, IsOS reports scene/profile mismatch at the process `settings.scene` path and leaves saved and active revisions unchanged. If `arm-0` is missing from `navigation`'s declared device support, the manipulator option is unavailable with a bounded reason and Apply fails at its adapter setting. If `MUJOCO_ROOT` lacks the required library, the package remains installed but the selected scene cannot become ready. The MuJoCo builder classifies direct descriptor failures with these P02 codes; the IsOS companion slice maps graph-time failures to the exact paths above.

The general `release.json` fields (`id`, `version`, digest, architecture, source, license and assets) follow IsOS's package contract. This package contributes the new process type, the `mujoco-v2` adapter family and `sim-hardware` node set. The package owns only the simulator process type. Camera, base, and manipulator types remain generic EOS types. A node instance's `description` describes that configured instance; the registered process `NodeType.description` describes the reusable type. Old verified sidecars without type descriptions retain their compatibility fallback.

<a id="native-012-asset-requirements"></a>
#### Native `0.1.2` asset requirements

The candidate archive contains the CMake-installed `bin/eos-mujoco-sim`, with no absolute `RPATH` or `RUNPATH` from the build tree. The `release.json` asset records `libc` as `glibc>=major.minor` measured on the native build host, `tested_ubuntu` as that host's Ubuntu release, and `required_libraries` as the sorted resolved SONAME closure of the installed executable. On the Ubuntu 24.04 qualification host the conservative libc claim is `glibc>=2.39`. The directly needed and resolved MuJoCo SONAME must be exactly `libmujoco.so.3.3.1` and resolve beneath the selected `MUJOCO_ROOT/lib`; an absent or mismatched SONAME or any unresolved library blocks archive creation. The archive does not include the external MuJoCo library. IsOS resolves `MUJOCO_ROOT` and passes its library directory in `LD_LIBRARY_PATH` to the EOS-managed simulator child; a graph setting or package pin never embeds the build host's path. `required_libraries` and `tested_ubuntu` describe the tested native target, not a promise that an untested host is compatible.

<a id="historical-contribution-compatibility"></a>
### Historical contribution compatibility

Historical verified sidecars contributed only `eos.process.mujoco@v1.0`, had no process-type description or selector, and composed a `1.0.0` graph with fixed device IDs. Old sidecars may receive a catalog-only description fallback from their readers, without changed verified bytes. The current builder emits one `eos.process.mujoco.simulator@v0.2` process type and a two-node `0.2.1` camera-only set; IsOS accepts and verifies the new descriptor before publishing this preset as a graph option. Package assets may use the same P03 option mechanism later; this release defines no `egia.tensor` execution.

<a id="historical-v020-binary-adapter"></a>
### Historical v0.2.0 binary adapter

The release schema `0.2.0` declares `adapters:[{"family":"mujoco-v2","library":"lib/libmujoco-eos-node.so","sha256":"<64 lowercase hex>"}]` and an identical `node_contributions.libraries` path/digest. This library implements the versioned `isos_node_v1` C ABI; it is not a second simulator process. EOS passes the admitted graph instance to `create`, owns callback lifetime and the simulator child, and calls `stop` before unloading. A successful plugin Stop means observation callbacks are quiescent; EOS separately proves actuator stop through the strict companion socket before child termination. The first `sim-hardware` set contains only the simulator process and JPEG camera. Base and manipulator remain cataloged resources but are unavailable for managed execution until EOS proves actuator Stop.

<a id="local-verification"></a>
### Local verification

On 2026-11-08, `./launch.sh --robocasa --seed 42 --steps 20` completed twice with the same task instruction, 20 steps, and `success: false`. This confirms the upstream task loads and its success rule is queried; it does not establish an agent policy score. The C++ MuJoCo 3.3.1 build passed 27/27 CTest cases.

<a id="local-verification-2026-11-16"></a>
### Local verification, 2026-11-16

The native custom-scene GUI replay passed and exited automatically. IsOS `pkg check` passed for native and RoboCasa full graphs at candidate version `0.2.6` with 256 × 192 camera settings; `tests/package_logs.py` found matching service output and EOS run IDs. The three-kitchen GUI record and headless replay completed for `1:1`, `2:2`, and `3:3`, with three actions and matching summaries per kitchen. The bounded actions did not complete the `CloseFridge` task; this replay verifies launch, action delivery, deterministic replay, GUI exit, and cleanup. Complete local output is under ignored `data/test/20261116-full-interfaces/`, including `robocasa-three-final/summary.json`.

<a id="local-verification-2026-11-18"></a>
### Local verification, 2026-11-18

The 0.2.7 source candidate with the package-owned RoboCasa setup helper passed 15 node tests, the archive digest check, and all 35 CTest cases. An IsOS topic build with package setup descriptor support passed `pkg check` for both native and RoboCasa full graphs, including managed Apply, readiness, interfaces, logs, and Stop. The check report records its exact source commit; the IsOS topic commit was `182403ab0`. An isolated CLI install showed the RoboCasa prompt, preserved configuration when declined, and saved populated paths when accepted using an already prepared local runtime. The fresh network download path was not replayed here. Full package and CLI output is under ignored `data/test/20261118-release-027-audit/`, especially `pkg-check-027-setup-3/`, `setup-decline.log`, and `setup-accept.log`. This is candidate evidence; IsOS review and publication precede a 0.2.7 package release.

<a id="scene-runtime-and-integration"></a>
## Scene runtime and integration

**Status:** The scene engine, framed socket, package-owned P02 scene/device catalog, and IsOS P02/P03 admission and options are implemented. R05 strict launch and health integration passed scoped IsOS → EOS → MuJoCo qualification on pinned heads. The R06 MuJoCo stop lane is merged and a scoped real IsOS → EOS → MuJoCo stop replay passed. Broader R06 failure qualification and full M3 control qualification remain open. Product release `0.1.1` does not make socket protocol `2.0.0` a product release.

The owner contracts are [package descriptor and contributions](package.md), [MuJoCo-owned socket](core/adapter.md), and [benchmark RPC](core/benchmark.md). This design describes the algorithms rather than redefining their payloads.

<a id="target-activation-algorithm"></a>
### Target activation algorithm

1. IsOS obtains the exact P01-verified package handle and checks the P02 scene profile, XML digest, device map, per-scene device support and external MuJoCo library. It passes only stable IDs and availability reasons to the later P03 option resolver. Package installation does not edit the graph.
2. The operator previews `sim-hardware`, chooses stable scene/device IDs, checks the draft and applies one revision. IsOS resolves verified paths in generated config; the graph keeps IDs and the exact package pin. A legacy `1.0.0` graph and `@v1.0` types remain readable; new authored graphs use `0.1.0` and newly registered types `@v0.1` after all readers support them.
3. EOS reads that revision without editing it, selects the compiled internal `mujoco-v2` adapter factory, and starts the verified simulator as its direct child with the R05 managed strict launch flag. The child cannot advertise `strict-socket-v1` until strict checks and historical gRPC actuator-listener suppression are active. EOS requires the strict health feature for every declared device before publishing readiness. Failed health or a mismatched device keeps the node unavailable and is logged with `run_id`, optional `node_path` and `correlation_id`.
4. The dispatcher admits each actuator command before the adapter sends it. EOS verifies graph node, device kind, scene and package pin; the simulator validates the exact device/operation pair and finite scene bounds, then deduplicates `(node,command_id)` to protect identical bounded transport retransmission. EOS never replays an uncertain released command automatically. The merged R06 companion lane supplies the physical fence and separate base/arm proof; EOS and IsOS still own admission closure, receipt classification, and process cleanup.
5. On shutdown EOS closes command admission, requests stop for every admitted actuator with a bounded deadline, records any missing acknowledgment, then terminates and reaps its child. IsOS reports deployment stopped only after EOS exits or a bounded forced-stop path is recorded. The simulator removes owner-only sockets on normal exit.

<a id="p02-catalog-construction-and-compatibility"></a>
### P02 catalog construction and compatibility

The bundle builder retains the authored stable scene IDs, derives their digests from packaged XML bytes, and cross-checks the device catalog against the engine-supported camera, base and arm model elements. A deterministic fixture pins the expected profile markers, all three device IDs and the package-owned process type. A build or candidate bundle fails when a declared marker differs from the sole marker in the XML, when a model lacks an element required by a declared device, or when a scene or device ID duplicates another. Real MuJoCo engine load and replay tests establish that these XML files remain usable; XML catalog checking alone does not establish model compatibility.

IsOS first uses P01 receipt verification and path containment, then parses the exact verified descriptor. The exact `catalog_version:"0.1.0"` discriminator requires complete scene and device metadata; its absence requires the complete legacy shape. A partial mix fails before any option is published. IsOS compares the selected scene ID with its declared profile and XML hash, checks the chosen device ID against the kind and scene, and checks the external library before graph publication or spawn. It reports unavailable choices for a repairable draft and rejects an unavailable selected value at Apply with the contract's stable `{code,path,stage}` diagnostic. It repeats verification on Run and Restart; a changed linked payload requires explicit relink and cannot quietly update the running graph. A scene edit uses IsOS revision compare-and-swap and reaches EOS only after a new saved revision is restarted.

The new `sim-hardware` preset contains seven nodes in the EOS core and relies on the dispatch-control node already in the IsOS starter. Its hardware nodes are generic EOS `@v0.1` registrations with an exact package-pinned `mujoco-v2` adapter. Only the process type is contributed by MuJoCo. Previously verified legacy sidecars remain readable for old graph behavior; neither a legacy `@v1.0` type nor an unregistered IsOS Vision type is placed in the new preset. P03 owns generic `(node_path,setting)` option grouping and UI echo. In managed strict mode, R05 checks the exact device and operation; direct legacy mode retains its historical ignored `node` behavior. See the [P02 package contract](#p02-descriptor-extension) and [frozen fixtures](../tests/fixtures/scene_catalog/README.md).

The design review fixture check parses the four JSON fixtures, verifies the target/legacy discriminator shapes and frozen diagnostic tuples, hashes both repository scene XML files, checks each declared profile marker and device/scene relation, and validates relative Markdown links. Full output is in `logs/test/20261101-p02-design/fixture-doc-check.log`. The implementation replay uses `python3 tests/catalogtest.py`, `python3 tests/nodes.py`, `python3 tests/release.py`, `cmake -S . -B build-p02 -DMUJOCO_ROOT=<absolute MuJoCo 3.16.0 root>`, `cmake --build build-p02 -j4`, `ctest --test-dir build-p02 --output-on-failure`, and `python3 tools/bundle.py --build-dir build-p02 --output logs/test/20261101-p02-scene-catalog/bundle`. On Linux x86_64 with MuJoCo 3.16.0, 12/12 CTest cases passed, including real scene engine load, replay and archive construction; the staged bundle contains two hashed scenes, three described devices, both process identities, and a seven-node preset. Full output is in `logs/test/20261101-p02-scene-catalog/`. A historical probe against the then-current IsOS P01 binary rejected the new additive descriptor because its strict decoder still accepts only legacy fields (`isos-p01-link.log`); the later IsOS P02 slice resolved this earlier dependency, as the R05 clean-home replay below confirms.

<a id="target-command-and-log-algorithms"></a>
### Target command and log algorithms

**R05 simulator implementation.** The [socket contract](core/adapter.md) owns the exact flag, health fields, bounds, errors and retention. IsOS generated config selects a verified package and scene for an EOS-managed launch. EOS derives `--managed-strict-socket` from that managed launch, not from a graph-writable setting. In strict mode the simulator rejects both historical gRPC `SimulatorService` and benchmark socket arguments. `SimulatorService.Execute` would otherwise be a second actuator route outside Dispatcher, while benchmark Reset/Step could change the same engine state. A trusted evaluator uses a separate direct launch. Direct launches without the flag preserve the existing legacy framed, gRPC and benchmark behavior under wire `2.0.0`.

Strict readiness is an end-to-end check, not a successful connect. EOS probes health on each graph-declared scene device and checks protocol version, echoed request ID, positive `ok` and `accepted`, and `strict-socket-v1` in the response feature list. The simulator binds its strict framed listener only after it can enforce exact device/operation matching, finite typed movement limits, and bounded IDs. EOS refuses and reaps a child that omits or contradicts the feature. EOS `BackendChild::wait_ready` and adapter health now require the exact feature before readiness; the pinned real-child replay covers both scenes.

For a valid motion or `stop`, the server reserves `(node,command_id)` before calling the engine and stores a canonical typed-operation fingerprint and result for the whole child generation. An identical transport retransmission gets the prior result with the new transport request ID; a conflict gets `command_id_conflict`. Concurrent duplicates cannot release twice. Fixed movement and reserved stop capacities reject new commands rather than evicting a key; no TTL expiry may permit same-child replay. This bounded in-process retention does not replace the EOS durable Dispatcher journal: after a disconnect, timeout or restart, an uncertain released command remains unknown, and EOS reconciles from fresh observations or requires a new explicit admission. The managed server enforces `node` and `command_id` and serially accepts connections; R05 does not claim stop preemption. The merged R06 child provides the dedicated bounded stop lane and dual acknowledgments; the EOS/IsOS receipt and child cleanup determine whether a particular stop can be called confirmed.

Emit a sanitized JSONL event once for startup identity (package, scene ID, protocol and `run_id`), then on readiness changes, command admission/result, socket failures and shutdown. Do not log image bytes, arbitrary environment values or all high-rate observations. A first-use reader starts at the current run's first ready/failure event, then filters by canonical `node_path` and `correlation_id`. The shared event shape, rotation and cursor reading are defined by IsOS; this package supplies source `mujoco` and its own event codes.

**R05 design evidence:** [31 frozen cases](../tests/fixtures/strict_socket/cases.json) cover direct-launch compatibility, strict launch isolation, health proof, device/operation matching, typed bounds, duplicate/conflict/capacity, malformed frames and EOS no-replay. On 2026-11-02, `python3 tests/fixtures/strict_socket/check.py`, `python3 tests/catalogtest.py`, `python3 tests/nodes.py`, `python3 tests/release.py` and `git diff --check` passed; complete output and commands are in ignored `logs/test/20261102-r05-strict-design/design-check.log`. These record the design gate; runtime verification and dependent EOS strict-client qualification are recorded separately below.

**R05 simulator implementation evidence:** On Linux x86_64 with GCC 13.3 and MuJoCo 3.16.0, run `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`, `cmake --build build -j4`, and `ctest --test-dir build --output-on-failure`. All 16 CTest cases passed in the initial implementation gate; the final independent-review gate passed 18/18, including real strict socket launch/negative requests, 65,536 movement keys, 4,096 reserved stop keys, uncertain-result retention and legacy v2/gRPC/benchmark compatibility. `python3 tests/fixtures/strict_socket/check.py`, catalog/contribution/release checks, Python compilation and `git diff --check` passed. Complete output is in ignored `logs/test/20261102-r05-strict-impl/gates.log` and `logs/test/20261102-r05-strict-review-fixes/gates.log`. The C++ device table is generated from the package-owned P02 catalog and intersected with the loaded engine profile; the engine checks loaded joint ranges. EOS strict-client and no-replay evidence is recorded in the cross-owner qualification below. R06 preemptive stop was still open at this R05 gate; the merged R06 evidence appears below.

**R05 implementation review fixes:** Duplicate motion/stop responses retain their original `timestamp_ns`, `sequence`, admission and error; only the transport `id` changes. A live two-client replay test compares both responses and proves that a late duplicate does not restart the physical base lease. Strict camera health renders a frame before advertising its feature; a test-only EGL preload forces failure and verifies `device_unavailable`. The final gate commands and results are in ignored `logs/test/20261102-r05-strict-review-fixes/gates.log`.

<a id="r05-cross-owner-qualification"></a>
### R05 cross-owner qualification

The sealed EOS evidence at `logs/test/20261102-r05-cross-owner-qualifier/qualification.md` and independent `reviewer-verdict.md` is pinned to EOS `9701a4d449249a3cd90bd5bd8d2ba98809d59435`, MuJoCo `41e17107b7c7abe43cd29cc388b7dd157979d476`, and IsOS `1db1aa52df959f06e7c494797edd09a2b5289bcf`. Its 85 sealed files passed `sha256sum -c evidence.sha256`; `commands.txt` and complete logs in that directory reproduce the checks. The reviewer approved scoped R05 owner-row completion after normal PR checks and status documentation.

Fresh IsOS homes linked the exact package, selected pick-place and navigation, Validated and Applied, then ran EOS, which launched the verified simulator as its direct child. Each scene passed strict camera/base/arm health, read-only capture and observations, ready-event ordering, and child/socket/grant cleanup. The pick-place replay covered two process generations and rejected the old grant. Negative tests rejected wrong scene, wrong device, and tampered linked assets without changing saved or active state. MuJoCo strict CTest passed 7/7 focused cases, EOS wire 8/8, process 16/16, real child both scenes, and durable uncertain-command no-replay checks. The live EOS catalog exposed only `safety.estop` because the MuJoCo adapter has no `has_terminal_stop_fence`; `base.velocity` and `arm.movej` were withheld before Submit. The replay released no managed movement. R06 must prove the physical stop fence, dedicated stop lane, separate base/arm acknowledgments and safe termination order before full M3 first-use control can be claimed.

<a id="r06-stop-lane-design-target"></a>
### R06 stop-lane design target

The [owner socket contract](core/adapter.md#r06-managed-stop-contract) fixes the additive fields, stable errors, 1000 ms stop deadline, 250 ms per-connection ingress deadline, and `strict-stop-v1` feature. The [48-case design matrix](../tests/fixtures/strict_stop_lane/cases.json) pins failure, concurrency and lifecycle cases. The three-worker ingress change passed independent design and implementation review and merged in PR #21. Scoped cross-owner safe-stop replay passed; broader failure qualification remains open.

The managed main listener uses at most 32 normal work slots and 8 ingress slots. It derives a separate owner-only `.stop` socket with its own listener, three stop ingress workers, 250 ms accept-relative partial-frame expiry and one reserved stop execution slot. The companion listener parses only `health` and `stop`; EOS probes its health and sends all governed stops there. Eight blocked main ingress connections cannot occupy the companion slots. With two earlier partial stop frames and no other queued peer, the third worker can classify a connected valid stop within its own 250 ms ingress deadline, preserving the 500 ms classification bound; a fourth frame behind three stalled workers may expire in the queue and yields unknown stop. No detached thread or unbounded per-client allocation may retain engine state. The stop lane records a new engine stop epoch at reservation, invalidates both motion leases and pending old command tokens, and performs base and arm holds under a short engine command-state lock. Each managed child also generates a fresh 128-bit `generation_id` on startup; both health paths return it, and EOS echoes it on every managed movement and companion stop. An old child's delayed request fails `stale_generation` even when its epoch number matches the new child's initial `"0"`. Every managed movement also carries the current `stop_epoch` precondition, starting at `"0"`; the engine checks it in the same lock before writing targets. The movement ledger is checked **before** comparing a new key's epoch: an identical old-key replay returns its stored result after a stop, while a changed epoch under that key conflicts. A move that committed before the fence may finish its response later, but the stop overwrites its targets before acknowledging. A queued pre-fence move fails `command_interrupted`; a delayed **new-key** old frame first parsed after the fence fails `stop_fenced`. This is the required ordering proof behind EOS `has_terminal_stop_fence`, not the socket reply's old `accepted` bit.

Rendering must leave the command-state lock after a bounded immutable state snapshot and use a separate bounded render context. Stop cancels queued capture and fences publication from a capture already rendering. The server closes an active JPEG stream at stop reservation and uses a separate publication gate: a positive stop waits until any old stream has left that gate, while a stream still blocked at the 1000 ms deadline makes the stop unknown. A fixed stop executor may continue physical hold work after that deadline; the response stays `stop_outcome_unknown` and new movement remains inhibited for the child generation. Companion health reads cached identity and feature state without taking the engine mutex. EGL can remain uninterruptible; in that failure case the bounded stop path still reaches the engine, while EOS eventually kills and reaps the child. A successful stop reports independent `base_stop` and `arm_stop` values plus `stop_epoch`, with a post-commit timestamp and sequence. Partial proof returns `stop_outcome_unknown`; timeout or a lost reply is unknown to EOS even if the child physically stopped. An identical stop retransmission returns the stored fields and never reissues it. Direct-launch `2.0.0` remains unchanged.

**Cross-owner responsibilities:** EOS must derive and probe the companion `.stop` path, compare its health generation with the main listener, choose an outer monotonic deadline longer than its 500 ms accept/classification bound plus 1000 ms server budget, and bound connect/write/read and SIGTERM/SIGKILL/reap phases; the reviewed EOS design allocates three seconds for the physical companion request. It must send the current `generation_id` and `stop_epoch` with every movement, the generation with every companion stop, validate both stop statuses and the returned generation/new epoch, close Dispatcher admission before emergency stop, prevent a delayed release from reaching the adapter after stop, and record `OutcomeUnknown` when either proof is missing. A later authorized controlled stop may allow a newly admitted command with the proved new epoch; emergency shutdown must remain closed. EOS advertises movement only when the feature and terminal fence are available; broader R06 qualification remains open. IsOS must preflight the derived companion path length with the package/socket selection, owns reverse dependent EGIA/EOS process-group stop, and must not report completed safe stop when EOS reports unknown. The simulator cannot prove EOS ordering or IsOS process lifecycle by itself.

**R06 design-only evidence, 2026-11-02:** `python3 tests/fixtures/strict_stop_lane/check.py` validated 47 unique target cases and EN/CN contract markers. The R05 fixture checker, scene catalog (8 tests), node contributions (5 tests), release check (1 test), Python compilation and `git diff --check` passed. Complete commands and output are in ignored `logs/test/20261102-r06-stop-design/design-check.log`. No C++ implementation or runtime stop claim is in this design commit; independent design review and EOS adapter agreement are next.

**R06 implementation candidate evidence, 2026-11-02:** On Linux x86_64 with GCC 13.3 and MuJoCo 3.16.0, run `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`, `cmake --build build -j4`, and `ctest --test-dir build --output-on-failure`. The initial 21 CTest cases passed, including the R05 compatibility cases, real pick-place/navigation stop sockets, eight blocked main ingress frames, two blocked companion ingress frames, generation restart rejection, old-key replay after stop, engine-level delayed write and active-arm interruption, and a graphics call held after capture snapshot while stop completed and the old frame was discarded. Independent review found three P1 races; the follow-up added deterministic blocked-engine, companion-health and JPEG-publication tests, with the full 23-case result recorded in `logs/test/20261102-r06-strict-stop-review-fixes/`. A further review found that the 250 ms ingress timer began after dequeue. The accept-time correction carries an absolute deadline in each queue entry, checks expiry after the final read, and adds a three-worker companion ingress pool so two earlier partial frames cannot consume a valid stop's entire accept-relative budget. The new test holds all three workers with partial frames, verifies the fourth partial frame was accepted, pauses the child past its original deadline, checks immediate closure after resume, and checks valid stop classification behind two partial frames. The 24-case full suite, R06/R05 fixtures, Python compile and diff checks are recorded in ignored `logs/test/20261102-r06-strict-stop-accept-deadline/`; the queued accept-deadline regression passed ten repetitions and independent design and implementation re-reviews approved exact head `212f757`. Complete initial output and exact commands are in ignored `logs/test/20261102-r06-strict-stop-implementation/`. The owner tests alone do not prove EOS safe-stop behavior; the scoped cross-owner replay below verifies confirmed and unknown outcomes, while broader R06 qualification remains open.

<a id="r06-owner-merge-and-scoped-cross-owner-replay"></a>
### R06 owner merge and scoped cross-owner replay

[PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) squash-merged reviewed head `212f7572205eee3dd271d876bf9779eecb76d1f1` into `master` at `c171208f0ef605fd4d5275d75567928713c50e96`. The owner gate passed 24/24 CTest cases, ten repetitions of the accept-deadline regression, and the frozen R06 48-case and R05 31-case fixture checks. Complete owner output is under ignored `logs/test/20261102-r06-strict-stop-accept-deadline/`.

In fresh P01-linked IsOS homes, a real pick-place and navigation replay admitted EGIA-grant gRPC base and arm movements. EOS Stop emitted one schema-1 receipt with both parts confirmed, matching generation and epoch `1`, before MuJoCo termination and reap. IsOS retained `stopped` after polling; an independent process scan found no surviving child, group or socket. Lost stop socket and MuJoCo SIGKILL were classified unknown, without false confirmation. The complete raw commands, receipts, events, journals and checksum manifest are in ignored `/home/ashex/projects/isos/logs/test/20261102-r06-full-cross-owner/` and the scope is recorded in [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21). Forced timeout/KILL, GUI unavailability, stale or wrong pipe, and crash recovery remain broader R06 qualification work. This merge does not tag or publish `0.1.1`.

**Documentation status correction, 2026-11-02:** On the merged `c171208` owner tree, `python3 tests/fixtures/strict_stop_lane/check.py`, `python3 tests/fixtures/strict_socket/check.py`, `python3 tests/catalogtest.py`, `python3 tests/nodes.py`, `python3 tests/release.py`, `cmake -S . -B build -DMUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0`, `cmake --build build -j4`, `ctest --test-dir build --output-on-failure`, a changed-Markdown relative-link check, and `git diff --check` passed. CTest passed 24/24; the changed documents had 119 existing relative link targets. Complete output is in ignored `logs/test/20261102-r06-doc-status/`.

[中文](../docs_cn/architecture_cn.md)

One simulator process loads one scene profile at startup. Its engine owns MuJoCo model and data, deterministic seeded reset, fixed-step physics, robot command targets, telemetry, camera rendering, and scene-specific scores. The EOS-facing service and the benchmark service share that engine, but publish different information. The simulator socket returns device health, command outcomes, telemetry, and camera JPEGs. The benchmark socket lets a trusted evaluator reset or step the world and inspect ground truth and scores.

Direct launch uses `--scene`; an IsOS/EOS v2 deployment selects the scene in its applied shared graph and EOS passes that path to its simulator child. The selected MJCF declares exactly one supported custom numeric marker, `eos_benchmark_pick_place_v1` or `eos_benchmark_navigation_v1`; an unknown or multiple benchmark markers are rejected. The engine then checks required named elements, including `navigation_goal` for the navigation profile. A different XML file is not automatically an admitted benchmark; each profile needs explicit reset and scoring logic, documented capabilities, and tests. Changing a scene requires a process restart.

The simulator still exposes the legacy `eos.simulator.v1.SimulatorService` gRPC socket for older direct integrations. The current IsOS/EOS v2 runtime connects generic camera, base, and manipulator adapters to the separate owner-only framed socket selected by `--v2-socket`; its contract is in [backend.md](start.md). EOS owns the simulator child and exposes graph-declared observation and primitive ports to agents. The benchmark socket remains separate from both robot-facing interfaces. This package does not link into EOS core.

EGIA attaches to an already-running EOS gateway, discovers its healthy devices and versioned primitives, and executes through EOS. It does not receive benchmark seed, goal truth, privileged state, or score. EGIA fleet aliases identify EOS endpoints; the simulation scene remains EOS's configuration choice. Agent evaluation compares an EGIA or other agent's EOS-visible behavior with a separate evaluator's private result.

The published v1.0.1 package and its generated EOS profile belong to the legacy route. For v2, IsOS links or installs an exact `island/mujoco-sim@0.1.1` bundle, verifies its executable, scene, assets, and external MuJoCo library, and applies a shared graph revision through the `sim-hardware` node set. EOS reads that graph and starts the verified simulator as its direct child. A source build may still run directly with absolute scene and socket paths.

For the native `0.1.1` release, CMake keeps `MUJOCO_ROOT/lib` in the build-tree RUNPATH so local tests can run. Packaging uses `cmake --install` into a temporary stage and inspects that installed executable before copying it into the archive. An absolute installed RUNPATH, wrong MuJoCo SONAME, unresolved dependency, or resolution outside the selected MuJoCo root fails packaging. The measured Ubuntu and glibc versions and resolved SONAME closure go into the asset record. IsOS supplies `LD_LIBRARY_PATH` for the selected external library at managed launch; this is the relocation boundary. The bundle integration test extracts the final archive to a different path and runs the strict socket path with that environment.

**Native release evidence, 2026-11-03:** On Ubuntu 24.04 x86_64 with glibc 2.39 and MuJoCo 3.16.0 under `/home`, `cmake -S . -B build-native -DMUJOCO_ROOT=<root>`, `cmake --build build-native -j4`, `TMPDIR=<home temp> ctest --test-dir build-native --output-on-failure -j2`, `python3 tests/catalogtest.py`, `python3 tests/nodes.py`, `python3 tests/release.py`, and `git diff --check` passed. CTest was 26/26, including negative native requirements and an archive extraction plus relocated strict-socket launch with an environment matching IsOS's backend resolver. `tools/bundle.py --build-dir build-native --mujoco-root <root> --output logs/test/20261103-native-release-metadata/bundle` produced an asset with `glibc>=2.39`, `tested_ubuntu:["24.04"]`, the resolved SONAME closure, and archive SHA-256 `eebf8f1e8267b8a766ae4c25dc657516a0b645bdf5867cef974d5535a67a383b`. The installed ELF has no RUNPATH/RPATH. `isos pkg verify <manifest> <archive>` accepted the exact archive on this host. Complete output is under ignored `logs/test/20261103-native-release-metadata/`. A separate clean IsOS/EOS managed replay is still required before publication.

<a id="timing-and-failures"></a>
### Timing and failures

MuJoCo advances in fixed 2 ms physics steps. A reset sets a deterministic seeded initial state and pauses real-time stepping. The evaluator can advance a bounded number of steps, inspect state, score, and resume live stepping. Repeatability requires the same scene version, seed, command sequence, and stepping schedule; asynchronous real-time observation is not a deterministic replay contract.

Startup fails for a missing or invalid scene, missing required scene elements, or an unusable socket. Unavailable or unsupported devices and commands fail through the EOS-facing service. The benchmark service reports reset or step errors in `StateResponse.ok` and `error`. Ground-truth fields that are irrelevant to a scene should not be used as an agent input or inferred as a goal.

**Related:** [Usage](start.md) · [Simulator RPC](core/native.md) · [Benchmark RPC](core/benchmark.md)

<a id="legacy-caller-audit"></a>

<a id="legacy-caller-audit-2026-11-04"></a>
### Legacy caller audit (2026-11-04)

[中文](../docs_cn/changelog_cn.md#旧实现调用者核查2026-11-04)

The managed IsOS path uses the strict framed v2 socket. The following older paths still have callers, so they are retained.

| Candidate | Build, runtime, or test caller | Decision |
|---|---|---|
| `src/isos/service.cpp`, `src/isos/service.h`, `proto/simulator.proto` | `src/isos/main.cpp` calls `Serve`; direct `launch.sh` passes `--socket` and `--benchmark-socket`; `tests/smoke.sh`, `tests/eval.py`, and `smoke-rpc` exercise the gRPC paths. The simulator proto is mirrored in EOS. | Retain direct-run compatibility and the published proto. Managed strict mode forbids both listeners. |
| `proto/benchmark.proto`, `benchmark-eval` | The trusted direct-run evaluator uses Reset, Step, and score RPCs; `tests/eval.py` exercises it. | Retain, private to the evaluator. |
| `benchmark-reset` | `tests/q03bench.py` uses this private tool for deterministic seeded resets in the Q03 socket benchmark; the Q03 qualification commands name the target. | Retain until the benchmark harness has a replacement. |
| `--v2-socket` direct mode | `tests/v2.py` and the Q03 harness exercise it; direct clients may coexist with the historical listeners. | Retain. The README and English usage example now show all three distinct sockets. |

No candidate above is unused implementation. The IsOS-managed child still starts with `--managed-strict-socket` and only the owner-only v2 and companion stop sockets.

<a id="current-baseline"></a>
### Current baseline

- Commands: `eos-mujoco-sim --help` lists direct `--socket`, `--benchmark-socket`, optional `--v2-socket`, and `--managed-strict-socket`; `launch.sh`/`kill.sh` own a standalone process; `benchmark-eval` is evaluator-only.
- Installation: `CMakeLists.txt` installs only `eos-mujoco-sim` to `bin`. `tools/bundle.py` produces the separate IsOS package; tests and benchmark tools are not installed by CMake.
- Interfaces: the direct historical gRPC simulator and benchmark sockets remain private; the managed path exposes only the framed v2 socket and derived `.stop` companion. The exact request and response contract is `docs/core/adapter.md`.
- Graph versions: `tools/nodes.py` emits seven `@v0.1` registered types; `tools/catalog.py` emits catalog `0.1.0`. IsOS owns authored graph versioning and persistence; the simulator does not edit the applied graph.

<a id="remaining-qualification"></a>
### Remaining qualification

The `v0.1.1` package is published, and the selected Q03/Q04 replays below passed. Broader R06 failure qualification remains open for forced timeout or kill, GUI unavailability, stale or wrong pipe, and crash recovery. Full logging and first-failure discovery through IsOS still require end-to-end verification. Record exact package and owner pins, run IDs, commands, and outcomes for each new qualification run.

<a id="q03-simulator-qualification-design"></a>
### Q03 simulator qualification design

[中文](../docs_cn/architecture_cn.md)

**Status:** owner source checks, selected-source Q03 final-17 replay, and merged-head Q04 final-5 replay passed. Independent Q04 archive review found no P1/P2 findings. The `v0.1.1` tag is published, and the later five-owner released-asset replay passed its stated Q04/M5 gate; see the [package release record](#package-release-record) and [EOS Q04 qualification](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md). The simulator owns scene loading, deterministic reset, physics, rendering, its private socket, and benchmark scoring. EOS owns the robot-facing route. Never expose benchmark ground truth through EOS, EGIA, or UI.

**Q03 owner baseline (2026-11-03):** the direct socket harness is implemented in `tests/q03bench.py`, with private `benchmark-reset` and negative unit tests. The measured run is local evidence, not the cross-owner installed replay or release approval. Complete initial output remains in ignored `logs/test/20261103-q03-mujoco/`; the final renderer-probe bundle is in `logs/test/20261103-q03-mujoco-review-final/`, and the collision-free raw samples and six child logs are in `logs/test/20261103-q03-mujoco-review-final-2/`.

<a id="fixed-inputs-and-owner-checks"></a>
### Fixed inputs and owner checks

Build from the fetched `master` commit with MuJoCo 3.16.0 and record the compiler, CMake, CTest, library, source and scene hashes. Run tracked C++ sources through `clang-format --dry-run --Werror`; run CMake configure/build and full CTest, then the focused strict socket/capacity/Stop, scene, engine and benchmark tests. Run the node-contribution fixture and construct a fresh `island/mujoco-sim@0.1.1` bundle in an empty output directory. Save its manifest/archive SHA-256 and verify it through IsOS in a clean home. Keep complete command, output and exit records under ignored `logs/test/<run-id>/`, including failed attempts.

The installed owner replay must select both catalog scenes, prove exact package and scene admission, observe a read-only frame, send one admitted base or arm command through EOS, inject simulator death, and observe the current-run failure and governed Stop/reap. Preserve selected graph revision, run IDs, package receipt, child identity and the cross-owner verifier result. Independent standalone CTest is necessary but does not substitute for this installed replay.

<a id="initial-socket-baseline"></a>
### Initial socket baseline

Use a private, owner-only v2 Unix socket and no GUI. For each of `assets/scene.xml` and `assets/scenes/navigation/scene.xml`, launch three fresh simulator processes. Use a direct non-managed benchmark process (never an EOS-owned managed child) with private absolute, distinct `--socket`, `--benchmark-socket`, `--v2-socket`, and `--scene` paths. For example, `build-q03/eos-mujoco-sim --socket /absolute/private/legacy.sock --benchmark-socket /absolute/private/benchmark.sock --v2-socket /absolute/private/v2.sock --scene /absolute/scene.xml --manual-step`. Require a successful private `Reset(seed=42)` and record its response before each process warm-up; keep the engine paused, with no asynchronous stepping, for all measured requests. Use the package EGL-only `SimEngine::RenderCamera` path and 640×480 `cam-0` capture. The socket does not export a resolved renderer identity; enable the opt-in EGL context probe on the child, record its runtime EGL vendor and GL renderer from the child log, and assert the observed JPEG format, byte length and image dimensions on every repetition. After 20 warm-up calls, issue 200 serial `base_observe` requests and 20 serial `camera_capture` requests. Record every monotonic elapsed time, response status and byte count, and the measured wall duration for each operation group. Report successful requests/s or frames/s, midpoint median and nearest-rank p99 in milliseconds for each process and pooled samples; report all failures and timeouts separately. This measures the simulator socket, not IsOS HTTP, EOS Dispatcher or browser latency. No performance target is inferred from the initial measurements.

The harness must fail clearly on unavailable socket, malformed response, timeout, wrong scene and unexpected child exit; focused tests must cover those paths. An independent agent reviews this design before implementation and reviews the harness, evidence and PR before merge into MuJoCo `master`. The Q03 cross-owner summary records final exact pins; Q04 owns publication and tags.

<a id="reproducible-owner-evidence"></a>
### Reproducible owner evidence

From the repository root, set `MUJOCO_ROOT=/home/ashex/mujoco-3.16.0-linux-x86_64/mujoco-3.16.0` and run:

```sh
git ls-files -z '*.cc' '*.cpp' '*.h' '*.hpp' | xargs -0 -r clang-format --dry-run --Werror
cmake -S . -B build-q03 -DMUJOCO_ROOT="$MUJOCO_ROOT"
cmake --build build-q03 -j4
ctest --test-dir build-q03 --output-on-failure
ctest --test-dir build-q03 -R 'strict-socket|strict-capacity|strict-stop|v2-socket|benchmark-eval|engine-test|scene-catalog|bundle-catalog|q03-socket' --output-on-failure
python3 tests/fixtures/strict_socket/check.py
python3 tests/fixtures/strict_stop_lane/check.py
python3 tests/nodes.py
python3 tools/bundle.py --build-dir build-q03 --output logs/test/20261103-q03-mujoco-review-final/bundle
python3 tests/q03bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/pick-place.json
python3 tests/q03bench.py --sim build-q03/eos-mujoco-sim --reset build-q03/benchmark-reset --scene assets/scenes/navigation/scene.xml --warmup 20 --observe 200 --capture 20 --repetitions 3 --json logs/test/20261103-q03-mujoco-review-final-2/navigation.json
```

The post-format full CTest passed 25/25 and the focused set passed 16/16. The static R05 and R06 fixture matrices passed 31 and 48 cases; the node contribution checker passed. The first formatting check failed in three pre-existing files (`tests/smoke.cpp`, `src/isos/service.cpp`, `src/mujoco/gui.cpp`, 86 diagnostics); a separate formatting-only commit corrected them and the final tracked C++ check passed. The final package builder produced `mujoco-sim-v0.1.1-linux-x86_64.tar.gz` with SHA-256 `05a9346db26f43510c1986ff7431038ae29197ac85300a2f1efd1211f3458fe6`. At this initial owner baseline, the installed IsOS→EOS replay was still open for the cross-owner gate.

On this x86_64 Linux host, C++ is GCC 13.3.0, MuJoCo is the installed 3.16.0 tree, and the benchmark uses the package EGL path without a GUI. `environment.json` records the kernel, tool versions, source pin, binaries, scenes, library and archive hashes. The runtime probe resolved EGL vendor `NVIDIA` and GL renderer `NVIDIA GeForce RTX 2080 Ti/PCIe/SSE2` for all six processes. With seed 42, paused scenes, 20 warm-up observations, three fresh processes per scene and 200 observations plus 20 captures per process, the final raw run recorded:

| Scene | Operation | Success/failure | Throughput | Median | p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| Pick-place | `base_observe` | 600/0 | 17,549/s | 0.054 ms | 0.089 ms |
| Pick-place | `camera_capture` | 60/0 | 716 frames/s | 1.261 ms | 2.961 ms |
| Navigation | `base_observe` | 600/0 | 18,033/s | 0.053 ms | 0.074 ms |
| Navigation | `camera_capture` | 60/0 | 731 frames/s | 1.262 ms | 2.453 ms |

Throughput uses successful calls divided by summed measured group wall time. Median is the midpoint of sorted successful samples; p99 is nearest rank. Earlier raw attempts in the same log directory differ, likely from local load; no performance target or cross-host claim follows from this baseline. Each repetition records its own values, successful `Reset(seed=42)`, observed JPEG probe dimensions and all sample statuses, bytes and timeout flags. Failed requests record zero accepted payload bytes; summaries count timeouts separately. The opt-in child log records the runtime EGL vendor and GL renderer after context creation; the socket response supplies the observed JPEG dimensions. Log filenames use the benchmark output stem, keeping the two `scene.xml` workloads separate. The prior run overwrote child logs because both scenes shared that basename; its raw samples remain preserved but its child logs are superseded by this run. These numbers cover only the private simulator socket.

<a id="selected-installed-archive-evidence-2026-11-03"></a>
#### Selected installed archive evidence, 2026-11-03

The selected 0.1.1 bundle records MuJoCo source commit `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`; this exact source identity must remain in `release.json`. The selected release file SHA-256 is `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`, and the archive asset SHA-256 is `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`. EOS Q03 selection SHA-256 is `116aef2846750a96275645e4dec3021ad716ce6fb80b05c087a2ce377a74b990`; frozen review main and case build receipts have SHA-256 `977293e097779f636cb70bde9f3d5657bc9351b0b9f67534ca7beb41a97ef915` and `20b2dc444d4f90ca1e4cf4b8a2404893c53cd20de19a090ce02debf0c539ab5d`.

In the sealed clean-home replay, IsOS verified and installed that archive, selected the `pick-place` scene and available camera/base/manipulator devices, and EOS launched the verified MuJoCo executable as its direct child. A real 640×480 camera frame reached EOS, EGIA Vision and browser observations. R06/A03 selected-pin fault trials passed child death, stop/reap and restart checks without replaying uncertain movement; final deployment Stop was confirmed with no managed survivors. The six selected case groups and `Q01_FULL_VERIFIED` are preserved under ignored EOS `logs/test/20261103-q03-selected-final-15/`. The private socket benchmark above remains a separate fixed-workload measurement. This installed replay covers a local simulated hosted Origin. At this final-15 gate, Q04 merged-head review and tag publication had not yet run. Changing the package source HEAD requires rebuilding and reverifying the 0.1.1 bundle.

<a id="final-selected-source-and-merged-head-archive-evidence-2026-11-04"></a>
#### Final selected-source and merged-head archive evidence, 2026-11-04

The later sealed Q03 `20261103-q03-selected-final-17` archive retained the selected package source `3bf8a50aa2100b3eb1758ea4795bdcdddb65391e`, release file SHA-256 `591cd2ec454b659bbe97645811a6c928081045636e82e52b5b2f2dda3247b445`, and archive SHA-256 `53f9fa5d9af4b92b74635fd22447a9f08450b89a19725b6d26b6bd5850a5be96`. Its frozen selection SHA-256 is `35dd4e5aa4c209bf84935002a4eded756f3eb5a1c147b2fb12bd5d894e46b78a`; the verifier on exact selected EOS source `219f031bae9dbfc9d9f53f62c910b9e235bb2138` returned `Q01_FULL_VERIFIED` for all six groups. The independent EOS audit is in `logs/test/20261104-q03-final17-independent-audit/`: selected-source verification passed, while a later checkout rejected its changed harness digest. The final-15 record above remains historical.

For Q04 `20261103-q04-merged-home-final-5`, the release was rebuilt from merged MuJoCo `master` `04b65882cd11b0aff8ce56473164691dbd662196`. Its `release.json` SHA-256 is `c421039753c24ffc74658d6b1dfe5c9de6a1ed77b64df8fbaee77063da837096`, and the installed archive SHA-256 is `bb2862b01c3ccab8b68570e766a0ad26c8c5783b3c87cf99225eb0edb7a260f4`; the frozen external selection SHA-256 is `7f5cefa5b6521d42d28b88c916679f2b668ba93fd61bbcbbfed4bb8fcc722b87`. IsOS verified and installed that exact bundle in a clean home; EOS launched the simulator as a direct child, produced a real camera frame and governed base result, then confirmed physical Stop before child termination and reap. The selected R06/A03 fault and restart case passed without replaying uncertain motion. The full selected verifier returned `Q01_FULL_VERIFIED`, and independent archive review checked 3,630 sealed files with no P1/P2 findings. Raw receipts, events, child proof and commands are in ignored EOS `logs/test/20261103-q04-merged-home-final-5/`. This is a local simulated hosted-Origin replay, not a published `v0.1.1` package or public HTTPS deployment; release closure and tagging were still open at this gate.

<a id="mujoco-simulator-process-node"></a>
## MuJoCo simulator process node

**Historical process type.** The v0.2.0 source candidate contributes `eos.process.mujoco.simulator@v0.2` at `core=eos`, `layer=process`, `group=mujoco`. Its implementation kind is `managed_process`. That `sim-hardware` preset contains the process and one JPEG camera; base and manipulator remain cataloged but unavailable for managed execution until actuator Stop proof. Historical 0.1.x packages retain their existing reader path. Registered `NodeType.description`: “Starts one verified MuJoCo scene as an EOS-owned simulator child and supplies only the graph-declared simulated devices.” The instance description records this deployment’s purpose.

<a id="first-use-behavior"></a>
### First-use behavior

1. IsOS verifies the exact package receipt, executable, scene assets, device map and external MuJoCo library. It presents stable scene/device options with descriptions and unavailable reasons; the operator selects IDs rather than paths.
2. IsOS validates the `sim-hardware` preview and applies a revision. EOS reads the graph without mutation, resolves its verified `mujoco-v2` library and starts the verified simulator as its direct child.
3. The node becomes ready only after socket health and declared device checks. The JPEG camera adapter is a separate EOS node instance; this process node cannot bypass their dispatcher admission.
4. On failure, retain the unavailable node and reason in status. Open logs at this run's first ready/failure event, then filter by node path and correlation ID.
5. On shutdown, EOS closes admission and requests the R06 physical stop before terminating and reaping the child. It records an unacknowledged stop as an unknown outcome; the scoped R06 replay confirmed separate base and arm acknowledgments.

<a id="algorithm-and-compatibility"></a>
### Algorithm and compatibility

Package selection is exact receipt → digest/path verification → descriptor validation → option resolution → graph validation → child spawn → socket health → adapter activation. A scene change requires a new graph revision and child restart. The socket `2.0.0`, descriptor `2.0.0`, release schema `0.2.0` and `mujoco-v2` adapter name are independent compatibility identities. Unknown future graph or type versions fail with a version diagnostic; old saved graphs are not rewritten until explicit revision-checked migration. See [integration design](architecture.md) for command deduplication and stop ordering.

<a id="historical-eos-mujoco-process-node"></a>
## Historical EOS MuJoCo process node

`eos.process.mujoco.simulator@v0.2` belongs to the historical `0.2.0` `sim-hardware` set. It starts one verified MuJoCo scene as an EOS-owned child and provides the private service used by that set's JPEG camera. It is a process lifecycle node, not an agent control or observation port. Current full hardware presets contain device nodes and let IsOS start their selected runtime service implicitly; they do not include this process node.

<a id="placement-and-settings"></a>
### Placement and settings

The node is `core:eos`, `layer:process`, `group:mujoco`, `kind:software`, with `process` lifecycle and capability. The set includes this node and `native/front` camera. The process type itself has no input or output ports.

| Setting | Type / unit | What the operator selects | Validation and default |
| --- | --- | --- | --- |
| `scene` | string / stable ID | `pick-place` or `navigation` from the verified package catalog | Required; no resolved path in the graph; default in the set is `pick-place`. |
| `socket` | string / private Unix path | EOS-owner endpoint for the child | Required; no type default. |
| `env` | string table / — | Child environment references | Optional; empty when absent. |
| `start_timeout_ms` | positive integer / ms | Time allowed for child readiness | Optional in the type; EOS policy applies if absent. |

IsOS verifies the exact package receipt, scene XML digest, selected scene ID, and host MuJoCo library. EOS resolves `bin/eos-mujoco-sim` and the scene path from that verified package, then launches `--managed-strict-socket --v2-socket ${socket} --scene ${resource.scene.path}` with its `mujoco-v2` lifecycle adapter. The operator does not write an executable path or benchmark socket into the node.

<a id="readiness-and-stop"></a>
### Readiness and Stop

The child must open its owner-only socket and pass strict health for the graph-declared devices before EOS publishes readiness. A missing scene, wrong library, unhealthy camera render, incompatible protocol, or child exit leaves the node unavailable with a reason; socket existence alone is insufficient. EOS closes command admission before Stop, asks the companion stop lane for whole-robot proof, records an unknown outcome if proof is missing, and reaps the child. A scene change requires a new graph revision and child restart. The simulator cannot expose benchmark reset or score through this managed node. See the [runtime control contract](core/adapter.md) for frames, errors, and deadlines.

## Local build and configuration checks

Package mode reuses the ignored `.local/package-build/` CMake tree. The 2026-11-18 cache replay under ignored `data/test/20261118-package-build-cache/` ran `./build.sh --output <empty-directory> --version 0.2.6` twice: 20.25 seconds for the first build and 4.13 seconds for the second. Both archives had the same SHA-256. `python3 tests/archive.py` passed, and an invalid `MUJOCO_ROOT` was rejected.
`ctest --test-dir .local/package-build --output-on-failure -j4` passed all 35 tests. Package mode now builds only the executable and adapter targets; use the development build and CTest when test targets must be rebuilt.

Run `python3 tests/config_modes.py` to check both configuration boundaries: package selector edits leave `./launch.sh --show-config` unchanged, while development settings and `.env` leave the package build's selected MuJoCo root unchanged. The 2026-11-16 check passed with `python3 tests/build_env.py`; complete output is under ignored `data/test/20261116-config-mode-isolation/checks.log`.

<a id="design-verification"></a>

### Design verification

From the MuJoCo repository root, `git diff --check` and a relative-link audit of the four changed Markdown files passed, with zero broken links. A full audit of all 58 Markdown files using the sibling IsOS `scripts/check_doc_links.py` found five pre-existing broken anchors outside this change. Logs and the audit command are saved under ignored `data/test/20261115-interaction-node-roles/`.

## Camera dimension qualification

On 2026-11-13, the `0.2.3` source candidate passed isolated `isos pkg check` with the EOS command acknowledgment fix from IsOS PR #504. That qualification ran `isos pkg check --source <this checkout> --version 0.2.3 --output <empty evidence directory> --graph <RoboCasa full-preset graph pinned to 0.2.3> --graph <native full-preset graph pinned to 0.2.3> --package-config <local package.toml>` with `ISOS_AETHER_BIN_DIR` pointing to the corrected EOS binaries and the normal local EI and MuJoCo host paths set. The 256 × 192 and 512 × 512 configurations each passed static verification, native ABI, owner admission, managed observation/control/logs, and confirmed Stop for both presets. All three RoboCasa camera frames reported the requested dimensions. The exact commands, inputs, `check.json`, owner exchanges, and complete build logs are retained under ignored `data/test/2026-11-13-camera-size/`; the candidate archive SHA-256 is `58e3d9fa8d45345d5fe9a0da5f804d016bc6fbddbcb08fcceeece32d92c0bf6f`. Publication and graph repinning remain separate operator actions.


## R06 implementation review record

R06 design and negative fixture coverage is [frozen here](../tests/fixtures/strict_stop_lane/README.md). The reviewed MuJoCo owner head `212f757` passed 24/24 CTest cases and ten repetitions of the queued accept-deadline regression, plus the 48-case R06 and 31-case R05 fixture checks, before [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21) merged at `c171208`. The scoped IsOS → EOS → MuJoCo replay confirmed dual-part stops and cleanup for pick-place and navigation, and classified lost stop socket and child crash as unknown. [Evidence and reproducible commands](#r06-stop-lane-design-target) record the exact scope. Forced timeout/KILL, GUI unavailability, stale or wrong pipe, and crash recovery remain broader R06 qualification work; this package merge does not publish a `0.1.1` release tag.


## Package qualification evidence — 20 November 2026

On 2026-11-20, `./build.sh --output <empty-directory>` built the schema 0.2.2 candidate; all 35 CTest cases passed using `cmake --build .local/package-build --parallel 4` and `ctest --test-dir .local/package-build --output-on-failure -j4`. The focused checks above passed, and `python3 tests/eos_contracts.py --eos-profile <isos-p>/target/debug/aether-profile --plugin .local/package-build/libmujoco-eos-node.so --output <evidence>/eos-contracts` passed 21 EOS graph admission cases and nine payload schema checks. These EOS checks use the owner-local graph projection. Complete logs are under ignored `data/test/20261120-package-contract/`. They do not establish graph 0.3.1 package-release qualification.

On 2026-11-20, the clean source candidate at `2af08df93d3fdbc96421700cbe0217da2f964284` passed `isos pkg check --source <checkout> --version 0.2.8 --output <empty evidence directory> --graph <native full-preset graph> --graph <RoboCasa full-preset graph> --package-config <local package.toml>` with the graph 0.3.1 replay fixes in IsOS PR #551. Both complete presets passed static verification, native ABI, owner validation, managed observations and commands, rejection and duplicate checks, logs, child failure, socket cleanup, and confirmed Stop. The graphs explicitly bind each actuator command input to an API-only Dispatcher part. Set `MUJOCO_ROOT`, `ISOS_AETHER_BIN_DIR`, `ISOS_EI_BIN_DIR`, `ISOS_EI_FACTORY_DEFAULTS_DIR`, and `EI_PYTHON` to prepared local dependencies. Full inputs and logs are retained under ignored `data/test/20261120-package-merge/check-031-v4/`; `check.json` records `qualified:true` and archive SHA-256 `eb94665a6ca516e74ae0394342e0b286d6eaaa93665096b4913a1ed9b56d68dc`. This qualifies the local source candidate; release publication and immutable catalog assets remain separate.
