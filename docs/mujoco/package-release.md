# Island package release

[中文](../../docs_cn/mujoco/package-release_cn.md)

## Aether v2 node candidate

`tools/build-backend-bundle.py` stages the local `island/mujoco-sim@0.1.1` backend, a schema v4 `release.json`, and a checksummed archive. Its `node_contributions` declares one package-owned simulator process type, the `mujoco-v2` adapter family, and the `sim-hardware` node set. The set uses generic EOS camera, base, manipulator, gate, and primitive binding types plus an IsOS Vision panel. Each hardware node selects and pins the MuJoCo adapter in its settings; the package does not own those generic types. IsOS verifies the release and lists the nodes after install or link; graph preview and apply remain explicit operator actions. The backend descriptor still owns executable, scene, device, and MuJoCo library metadata. See the [backend guide](backend.md) for build and validation steps.

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
  --output /tmp/island-mujoco-release \
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
