# IsOS managed MuJoCo backend


## v0.2.x external adapter candidate (current source)

The current source builds `island/mujoco-sim@0.2.0` by default. `./build.sh --output <absolute-empty-directory> --version 0.2.x` selects an unpublished patch candidate; each published fix receives a new patch version. The release uses `isos.package@v1` schema `0.2.0` and contributes the `mujoco-v2` adapter family through `lib/libmujoco-eos-node.so`. The manifest records its SHA-256 in both `adapters` and `node_contributions.libraries`; the exact archive pins the same bytes. The output directory preserves the manifest asset basename, such as `mujoco-sim-v0.2.0-linux-x86_64.tar.gz`. `bin/eos-mujoco-sim` remains the verified supervised child. The library exports `isos_node_v1` with create/start/input/health/stop/destroy, consumes the admitted node's `adapter.settings`, probes `strict-socket-v1`, and translates camera, base, and manipulator observations into generic `@v0.2` payloads. It accepts only `{"op":"observe"}` input; it rejects direct movement. The current `sim-hardware` set contains only the simulator process and JPEG camera, with `jpeg` capability. Base and manipulator remain in the resource catalog but outside managed graphs until actuator Stop proof is complete. EOS must own Dispatcher admission and physical stop proof before a command set may be published.

For `isos pkg check --source`, export `MUJOCO_ROOT` to the local 3.3.1 installation; the explicit environment value takes precedence over `config.toml` and `.env`. `python3 tests/build_env.py` verifies this build input boundary without downloading anything. The manifest bounds IsOS compatibility to `[0.2.3,0.3.0)` and requires IsOS `package-process-v1` plus EOS `native-plugin-v1`; the release check still records the exact qualified IsOS build. The `.so` is a Linux C++/protobuf binary and requires the IsOS host's ABI table plus matching runtime libraries. Building the file alone does not establish compatibility: IsOS checks the manifest and digest, EOS checks the ABI and callbacks, and managed qualification checks the simulator child, data schemas, readiness, and Stop. Other platforms and in-process Python remain future work; Python may use a supervised process interface. `python3 tests/plugin.py <built-lib>` exercises strict health, observation, movement rejection, and Stop against a stub. The older `0.1.2` notes below are historical candidate evidence, not instructions for this source release.

## Historical 0.1.2 candidate notes

The `0.1.2` bundle below is a local development candidate using MuJoCo 3.3.1. It is not a published release; historical `0.1.1` evidence later on this page remains tied to MuJoCo 3.16.0.

**Current implementation:** This page records the existing bundle and integration path. [Package descriptor and contributions](../interfaces/package.md) and [simulator socket](../interfaces/socket.md) are the owner-specific field contracts; [architecture](../architecture.md) explains integration and [remaining qualification](../architecture.md#remaining-qualification) records the open checks. The `v2` in a protocol or generated descriptor filename is retained for compatibility; this topic page has no version suffix.

[中文](../../../docs_cn/mujoco/usage/isos-pkg_cn.md)

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

The release's `node_contributions` declares the `sim-hardware` set, `mujoco-v2` adapter family, and package-owned `eos.process.mujoco.simulator@v0.2` process type. The `0.2.1` set adds that process plus general EOS camera, base, and manipulator `device@v0.2` instances. Each hardware node pins `island/mujoco-sim@0.1.2` in `node.adapter.package` and selects its stable device ID. This first set is observation-only: it declares no Dispatcher command binding or camera gate. IsOS verifies the release, then validates a composed graph at preview and Apply; EOS readiness and Stop require a separately tested owner runtime. See the [package contribution contract](../interfaces/package.md#p02-contribution-and-graph-boundary).

The backend node's `settings.env` can contain `MUJOCO_GUI=1` or
`MUJOCO_GUI=true`. This opens an X11 window titled `IsOS MuJoCo — live
simulation` while EOS owns the simulator child. It renders camera frames from the
same `SimEngine` instance controlled by the v2 socket and benchmark socket.
The default is headless. A desktop with an accessible `DISPLAY` is required;
an unavailable display makes the simulator fail at startup. The independent
`tools/view.sh` viewer remains a static scene preview.

**R05 scoped qualification:** an EOS-managed strict child accepts only the framed v2 socket and rejects the historical gRPC robot and benchmark sockets. A separate direct launch retains those sockets for legacy clients and trusted evaluation. The pinned IsOS → EOS → MuJoCo replay proved strict health for the declared camera, base and arm in both scenes, read-only capture and observations, and child/socket cleanup. The R06 owner stop fence merged, and scoped cross-owner movement and stop replay passed; broader R06 failure qualification remains open. See the [owning socket contract](../interfaces/socket.md) and [R05 evidence](../architecture.md#r05-cross-owner-qualification).

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

## Verification

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

## Package version 0.1.1 check (2026-10-31)

`python3 tests/nodes.py`, `python3 tests/release.py`, and `ctest --test-dir build --output-on-failure` passed (10 simulator tests). `python3 tools/bundle.py --build-dir build --output logs/test/20261031-version-alignment/bundle` staged a bundle whose release and descriptor report package `0.1.1`. Descriptor schema and socket protocol remain `2.0.0`. Output is in ignored `logs/test/20261031-version-alignment/`.

## IsOS and EOS deployment

For the current IsOS/EOS path, build and link a local `island/mujoco-sim@0.1.2` bundle as described in the [backend guide](isos-pkg.md). The published v1.0.1 package uses the retired graph shape; its [release guide](isos-pkg.md#package-release-record) remains for historical installations. MuJoCo 3.3.1 is an operator-provided dependency; set `MUJOCO_ROOT` to the real installation before building the bundle and running the graph.

```sh
source .env
python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output /absolute/path/to/mujoco-v2-bundle
isos init --mode dev
isos pkg link island/mujoco-sim 0.1.2 /absolute/path/to/mujoco-v2-bundle --manifest /absolute/path/to/mujoco-v2-bundle/release.json
isos pkg node-sets
```

Stage and select EOS and IsosUI builds with `isos build eos`, `isos version select eos <selector>`, `isos build isosui`, and `isos version select isosui <selector>`. A selector identifies one exact receipt; when multiple EOS builds share a commit, use its source fingerprint. `isos init` exits without starting services. Run `isos serve` in a terminal, preview the installed `sim-hardware` node set with `isos pkg preview-set` or the IsOS API, choose the scene and owner-only socket, then Validate and Apply the draft with the revision-checked IsOS interface. The IsosUI catalog editor is part of the later U01 workbench gate. The set declares an EOS-owned simulator process and three generic hardware adapters; this candidate has no Dispatcher command binding. IsOS preserves an authored graph until the operator applies the new revision.

**P02 package catalog and IsOS selection.** The bundle builder now emits the `0.1.0` catalog descriptor and four-node `0.2.1` set with stable `scene`, `camera_device`, `base_device` and `manipulator_device` parameters. Build and inspect the bundle with `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <empty-directory>`; `backend-v2.json` contains two scene IDs, their labels, profiles and SHA-256 values, plus the three device descriptions and scene support lists. After P01 verifies the exact `island/mujoco-sim@0.1.2` receipt, the IsOS P02/P03 slices expose available IDs, Validate and Apply the selected scene and devices against the current saved revision, and retain unavailable saved IDs for correction. A scene edit creates a new saved revision; Restart is required to replace the EOS-owned child. See the [P02 package contract](../interfaces/package.md#p02-descriptor-extension) and [negative fixtures](../../../tests/fixtures/scene_catalog/negative-cases.json).

Run `isos run` in another terminal to start the applied deployment. IsOS preflights the exact package, assets, scene, MuJoCo library, EOS executables, sockets, and ports before starting graph children. EOS starts the simulator as its direct child. The scoped R06 replay proved physical stop ordering for pick-place and navigation; broader failure qualification remains open. `isos deployment stop` stops the deployment only; `isos stop` shuts down the manager, API, UI, deployment, and independent IsOS services. EGIA uses EOS's normal agent interface and never connects to the private benchmark socket. The service manager for model-like processes is separate from this hardware graph.

**R05 managed readiness, scoped qualified:** after Apply, EOS launches the verified child in strict mode and probes `health` for every graph-declared camera, base and arm device. It requires `version:"2.0.0"`, the echoed request ID, `ok:true`, `accepted:true` and `features` containing `strict-socket-v1`. Treat a socket file or process startup line as progress, not readiness. A missing feature, wrong device, failed camera render or exited child leaves the backend unavailable; inspect the current run's first failure event. The pinned cross-owner replay passed this path for pick-place and navigation, including read-only capture and observations. At that R05 baseline, the EOS catalog exposed only `safety.estop` for MuJoCo and withheld `base.velocity` and `arm.movej`; the R06 replay below subsequently exercised governed movement and stop. The R05 replay itself released no managed movement. See the [qualification](../architecture.md#r05-cross-owner-qualification).

To verify the simulator owner slice directly, start `build/eos-mujoco-sim --managed-strict-socket --v2-socket /absolute/private/run/strict.sock --scene "$PWD/assets/scene.xml"` in a private directory and send a framed `health` request with `node:"base-0"`. The response must echo the ID and include `ok:true`, `accepted:true` and `strict-socket-v1`. Managed launch rejects `--socket` and `--benchmark-socket`; direct launch without the flag continues to support them. `ctest --test-dir build -R 'strict-socket|strict-capacity|v2-socket' --output-on-failure` replays the owner checks, including full retention capacity.

For a P02 catalog failure, inspect the unavailable scene/device reason and the first package or Apply failure event before changing the draft. A changed linked asset requires explicit relink under the P01 receipt rule. A missing `MUJOCO_ROOT` library blocks launch readiness; a scene/profile mismatch blocks Apply. The graph and running child retain their prior revisions on these failures.

Stop through `isos deployment stop` after inspecting the result and current run logs. R05 adds strict identity and retransmission protection; the merged R06 companion lane and scoped replay proved separate base/arm acknowledgment before simulator termination and reap for both scenes. An `accepted:true` reply alone is never evidence of confirmed safe stop; inspect EOS's selected terminal receipt and IsOS's final outcome.

**R06 scoped first-use behavior:** the reviewed `strict-stop-v1` owner implementation merged in [PR #21](https://github.com/Island-Team/isos-mujoco-sim/pull/21), and a real pick-place/navigation IsOS → EOS → MuJoCo replay exercised governed movement and stop. With exact verified owner builds, use the same Validate/Apply/Run path. The managed child derives an owner-only companion socket at the main socket path plus `.stop`; no graph field is added. Check that `health` for each actuator reports both `strict-socket-v1` and `strict-stop-v1` and that EOS probes the companion stop socket before its catalog offers `base.velocity` or `arm.movej`. EOS sends the matching 32-character `generation_id` from both health paths and `stop_epoch:"0"` with the first bounded managed movement and sends the current proved epoch with later movements; a stale **new** command fails `stop_fenced`, while an identical old command ID returns its stored R05 result. Submit the movement through EOS, then use EOS/IsOS stop while a movement or capture is active. EOS sends governed stops with that generation ID to the companion socket. A delayed request from an old child fails `stale_generation`. Its strict `stop` response must echo its request ID and contain `base_stop:"stopped"`, `arm_stop:"stopped"`, the matching `generation_id`, a nonempty decimal-string `stop_epoch`, `ok:true`, and `accepted:true`; EOS must validate that proof before terminating and reaping its direct child, then publish the selected terminal receipt only after cleanup. The values are defined in the [socket contract](../interfaces/socket.md#r06-managed-stop-contract): status strings are unitless proof states, while `stop_epoch` is a child-local ordering counter used as a movement precondition. A missing/unknown status, timeout, child crash or `stop_outcome_unknown` means safe stop is unconfirmed; inspect the first correlated failure event and the EOS journal, then verify bounded child and both socket paths are cleaned up. Do not infer physical stop from process exit or `accepted` alone. The scoped replay confirmed both stop parts, matching generation and epoch `1`, and no surviving child/group/socket; lost stop socket and child crash remained unknown. See the [R06 evidence](../architecture.md#r06-owner-merge-and-scoped-cross-owner-replay). Forced timeout/KILL, GUI unavailability, stale or wrong pipe, and crash recovery still require broader R06 qualification before full M3 control is claimed.

The v2 package permits `MUJOCO_GUI=1` in the simulator node's `settings.env`. It opens a live X11 view from the same simulator engine used by the v2 socket. The standalone `--gui` launcher below opens a separate static MuJoCo viewer instead. See [backend.md](isos-pkg.md) for the node and socket contracts.

## Package release record

[中文](../../../docs_cn/mujoco/usage/isos-pkg_cn.md#软件包发布记录)

## `0.1.1` release — 2026-11-04

**Status:** `v0.1.1` is published from the exact binary build source `04b65882cd11b0aff8ce56473164691dbd662196`. Fresh public downloads match the selected manifest and archive hashes below. A focused clean IsOS home verified and installed the public package, selected the scene and devices, applied the graph, launched EOS to ready, and confirmed Stop and child reap. The later five-owner released-asset replay passed its stated Q04/M5 gate, with the scope and limits recorded below. Rebuilding from a later documentation commit produces a different candidate and requires new verification.

**Operator-visible changes.** IsOS can verify and install `island/mujoco-sim@0.1.1`, list its two scenes and available camera, base and manipulator devices, preview the `sim-hardware` node set, and Validate/Apply the selected graph. EOS launches the verified simulator as its direct child, reads real camera frames, admits movement through Dispatcher and confirms physical Stop before child termination and reap. The selected clean-home run also exercised a child fault, governed restart, package and edge rejection, and explicit graph migration. The [Q03 qualification record](../architecture.md#final-selected-source-and-merged-head-archive-evidence-2026-11-04) and [EOS Q04 replay record](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md) describe the scope and raw evidence.

**Compatibility and migration.** This is an IsOS schema v4 backend package with a graph `0.2.1` set and registered `@v0.2` types. Previously verified releases containing `eos.process.mujoco@v1.0` remain readable through their legacy reader; the current `0.1.2` candidate does not contribute it. Migration is explicit and revision checked. The published `v1.0.1` package uses the retired graph shape and is a separate release. The current `0.1.2` candidate requires an operator-provided MuJoCo 3.3.1 library. The published `v0.1.1` asset used MuJoCo 3.16.0 and recorded Ubuntu 24.04, `glibc>=2.39`, and x86_64. The [package contract](../interfaces/package.md#native-011-asset-requirements) owns the native dependency rules.

**Install or upgrade after publication.** Set `MUJOCO_ROOT` to the installed MuJoCo 3.16.0 tree, verify the published manifest and archive as below, then use the [backend guide](isos-pkg.md) to install or link the exact `0.1.1` package, select a scene and devices, Validate/Apply, and start EOS. A saved legacy graph is read without changing its bytes until the operator requests migration.

**Known limits.** This qualification used a local simulated hosted Origin and the native Ubuntu 24.04 asset. It does not establish a public HTTPS deployment, another architecture or distribution, a physical robot cutover, or a high-rate actuator channel. MuJoCo remains an external runtime dependency. The package does not expose benchmark truth to EOS or EGIA.

### Exact published bytes and candidate checks

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

### Postpublication checks

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

## Aether v2 node candidate details

`tools/bundle.py` stages the local `island/mujoco-sim@0.1.2` backend, a schema v4 `release.json`, and a checksummed archive. Its `node_contributions` declares one package-owned simulator process type, the `mujoco-v2` adapter family, and the `sim-hardware` node set. The set uses generic EOS camera, base, manipulator, gate, and primitive binding types. Each hardware node selects and pins the MuJoCo adapter in its settings; the package does not own those generic types. IsOS verifies the release and lists the nodes after install or link; graph preview and apply remain explicit operator actions. The backend descriptor still owns executable, scene, device, and MuJoCo library metadata. See the [backend guide](isos-pkg.md) for build and validation steps.

For the native `0.1.2` candidate, run the CMake/CTest gates first, then invoke `tools/bundle.py --build-dir <build> --mujoco-root "$MUJOCO_ROOT" --output <empty directory>`. The builder stages the CMake-installed executable and inspects it before archiving. Review `assets[0].libc`, `tested_ubuntu`, `required_libraries`, archive digest, and an extracted archive's `readelf -d bin/eos-mujoco-sim` output. The Ubuntu 24.04 host currently records `glibc>=2.39` and the exact MuJoCo 3.3.1 SONAME. The archived executable relies on IsOS's managed `LD_LIBRARY_PATH` for the external MuJoCo library. Do not publish a candidate until a clean IsOS-managed relocation and stop replay passes.

## Earlier published release

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

## Current `0.1.2` candidate verification (2026-11-11)

From this source checkout, `python3 tests/nodes.py` and `ctest --test-dir build -R '^(scene-catalog|bundle-catalog|strict-socket|strict-stop-lane|strict-stop-lane-navigation)$' --output-on-failure` pass. Build with `python3 tools/bundle.py --build-dir build --mujoco-root "$MUJOCO_ROOT" --output <empty-directory>`, then run `isos pkg verify <bundle>/release.json <archive>` and `ISOS_HOME=<isolated-home> isos pkg link island/mujoco-sim 0.1.2 <bundle> --manifest <bundle>/release.json`; both pass against the current IsOS source. `aether-profile catalog --node-types <linked-node-types.json>` accepts the contributed process and reports `mujoco-v2` as not compiled. The current IsOS preview calls an EOS `validate --file` command that this EOS profile does not expose, so graph Apply and managed readiness are not qualified by these checks. Full CTest passed 25/27 tests; the two scene-view checks require `bin/compile` and `bin/simulate`, which the local MuJoCo installation lacks. Complete local outputs are under ignored `data/test/20261111-general-hal/`.
