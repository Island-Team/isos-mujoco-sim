# Island package release

[中文](../../docs_cn/mujoco/package-release_cn.md)

## `0.1.1` release — 2026-11-04

**Status:** `v0.1.1` is published from the exact binary build source `04b65882cd11b0aff8ce56473164691dbd662196`. Fresh public downloads match the selected manifest and archive hashes below. A focused clean IsOS home verified and installed the public package, selected the scene and devices, applied the graph, launched EOS to ready, and confirmed Stop and child reap. Full public camera, control, fault and restart replay remains a separate release-closure check. Rebuilding from a later documentation commit produces a different candidate and requires new verification.

**Operator-visible changes.** IsOS can verify and install `island/mujoco-sim@0.1.1`, list its two scenes and available camera, base and manipulator devices, preview the `sim-hardware` node set, and Validate/Apply the selected graph. EOS launches the verified simulator as its direct child, reads real camera frames, admits movement through Dispatcher and confirms physical Stop before child termination and reap. The selected clean-home run also exercised a child fault, governed restart, package and edge rejection, and explicit graph migration. The [Q03 qualification record](q03-qualification.md#final-selected-source-and-merged-head-archive-evidence-2026-11-04) and [EOS Q04 replay record](https://github.com/Island-Team/Island-eos/blob/master/docs/island/q04-merged-qualification.md) describe the scope and raw evidence.

**Compatibility and migration.** This is an IsOS schema v4 backend package for graph `0.1.0` and registered `@v0.1` types. The old `eos.process.mujoco@v1.0` contribution remains for verified legacy reads; migration is explicit and revision checked. The published `v1.0.1` package uses the retired graph shape and is a separate release. The package requires an operator-provided MuJoCo 3.16.0 library; the selected asset records Ubuntu 24.04, `glibc>=2.39`, and x86_64. The [package contract](interfaces/package.md#native-011-asset-requirements) owns the native dependency rules.

**Install or upgrade after publication.** Set `MUJOCO_ROOT` to the installed MuJoCo 3.16.0 tree, verify the published manifest and archive as below, then use the [backend guide](backend.md) to install or link the exact `0.1.1` package, select a scene and devices, Validate/Apply, and start EOS. A saved legacy graph is read without changing its bytes until the operator requests migration.

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

The first public download check passed: `sha256sum` returned the selected `c421039…` manifest and `bb2862…` archive digests, the archive had 56 safe members, and remote `v0.1.1^{}` resolved to `04b65882cd11b0aff8ce56473164691dbd662196`. An independent clean-home smoke used those downloaded bytes with IsOS `c45011f`, public EOS candidate `a4b66d3`, and MuJoCo 3.16.0; package verification/install, `pick-place` preview, Validate/Apply, managed readiness and confirmed Stop/reap passed. The complete local output is under `/home/ashex/q04t/mujoco-public-smoke/`. The remaining camera/control/fault/restart replay is tracked separately and must pass before claiming complete postpublication qualification.

The published `v0.1.1` release contains the exact manifest as `release.json` and archive as `mujoco-sim-v0.1.1-linux-x86_64.tar.gz`. Download both into a fresh directory under `/home` and compare their SHA-256 and archive size with the values above; inspect the public tag target, manifest `source_commit`, license, archive layout, ELF dependencies and release URLs. The focused install/readiness/Stop smoke above has passed. Complete the remaining clean IsOS home replay with both scenes, camera and governed movement, injected fault/restart, confirmed Stop and child reap. Record the downloaded bytes and complete replay output under `logs/test/<run-id>/`. Do not mark postpublication qualification complete if any digest or replay differs.

```sh
download=/home/ashex/release-candidates/mujoco-0.1.1-public
mkdir -p "$download"
gh release download v0.1.1 --repo Island-Team/isos-mujoco-sim --dir "$download" --pattern release.json --pattern mujoco-sim-v0.1.1-linux-x86_64.tar.gz
sha256sum "$download/release.json" "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
stat -c '%s %n' "$download/mujoco-sim-v0.1.1-linux-x86_64.tar.gz"
git ls-remote --tags origin refs/tags/v0.1.1
```

## Aether v2 node candidate details

`tools/build-backend-bundle.py` stages the local `island/mujoco-sim@0.1.1` backend, a schema v4 `release.json`, and a checksummed archive. Its `node_contributions` declares one package-owned simulator process type, the `mujoco-v2` adapter family, and the `sim-hardware` node set. The set uses generic EOS camera, base, manipulator, gate, and primitive binding types. Each hardware node selects and pins the MuJoCo adapter in its settings; the package does not own those generic types. IsOS verifies the release and lists the nodes after install or link; graph preview and apply remain explicit operator actions. The backend descriptor still owns executable, scene, device, and MuJoCo library metadata. See the [backend guide](backend.md) for build and validation steps.

For the native `0.1.1` candidate, run the CMake/CTest gates first, then invoke `tools/build-backend-bundle.py --build-dir <build> --mujoco-root "$MUJOCO_ROOT" --output <empty directory>`. The builder stages the CMake-installed executable and inspects it before archiving. Review `assets[0].libc`, `tested_ubuntu`, `required_libraries`, archive digest, and an extracted archive's `readelf -d bin/eos-mujoco-sim` output. The Ubuntu 24.04 host currently records `glibc>=2.39` and the exact MuJoCo 3.16.0 SONAME. The archived executable relies on IsOS's managed `LD_LIBRARY_PATH` for the external MuJoCo library. Do not publish a candidate until a clean IsOS-managed relocation and stop replay passes.

## Earlier published release

Version 1.0.1 is published as a GitHub Release and in the Island package-center catalog for `island/mujoco-sim`. The older v0.1.0 entry remains in the legacy catalog schema; v1.0.1 uses an IsOS schema v4 manifest.

`tools/build-package-release.py` assembles a local candidate for the curated
Island package center. It runs the existing CTest suite, stages the simulator
binary, scene assets, license files, and EOS configuration templates, then
measures the exact archive size and SHA-256 digest. It does not upload or
publish a release.

Build on each target machine separately. Supply the minimum glibc version
established for that binary and only Ubuntu versions actually tested there:

```sh
python3.12 tools/build-package-release.py \
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
