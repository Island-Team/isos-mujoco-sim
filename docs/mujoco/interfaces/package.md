# MuJoCo package descriptor and contributions

[中文](../../../docs_cn/mujoco/interfaces/package_cn.md) · [Socket](socket.md) · [Package release](../package-release.md)

**Owner and status.** This repository owns the MuJoCo-specific `backend-v2.json` descriptor and `node_contributions` in its schema v4 `release.json`. IsOS owns the general release-manifest schema, [verified receipt and package admission](https://github.com/Island-Team/isos/blob/master/docs/isos/interfaces/package-verification.md), graph revision, and `/node-options` response. Existing bundle generation is implemented in `tools/build-backend-bundle.py`; the P02 catalog extension and `@v0.1` contribution below are **target design — not implemented**. `backend-v2.json`, schema `2.0.0`, protocol name `mujoco-v2`, and socket wire `2.0.0` remain compatibility identities when the authored graph format is `0.1.0`.

## Current descriptor fields

| Field | Type / unit | Purpose / owner | Default, validation and compatibility |
| --- | --- | --- | --- |
| `schema_version` | string | Descriptor parser identity / this package | Required `2.0.0`; IsOS rejects unknown major versions, retaining this identity. |
| `package.id`, `package.version` | strings | Exact package pin / this package | Required `island/mujoco-sim`, `0.1.1`; must match verified receipt. |
| `entrypoint` | relative path | Simulator binary / this package | Required `bin/eos-mujoco-sim`; IsOS checks regular executable stays inside verified bundle. |
| `protocol` | string | EOS adapter factory identity / this package and EOS | Required `mujoco-v2`; EOS must have matching compiled factory. |
| `scenes[] .id` | unique string | Stable scene selector value / this package | Current `pick-place`, `navigation`; no path is stored in graph. |
| `scenes[] .path` | relative path | Scene MJCF and assets / this package | Must resolve within verified bundle to readable supported scene; no traversal or symlink escape. |
| `devices.camera`, `.base`, `.manipulator` | strings | Simulator device IDs / this package | Current `cam-0`, `base-0`, `arm-0`; exact IDs used by adapter settings. |
| `runtime.mujoco_version` | string | External MuJoCo ABI requirement / this package | `3.16.0`; IsOS checks installed library and executable compatibility. |
| `runtime.environment_variable` | string | Installation root input / this package | `MUJOCO_ROOT`; never copied into graph as a secret or unverified executable path. |
| `runtime.library` | relative path | Required shared library beneath root / this package | `lib/libmujoco.so.3.16.0`; IsOS verifies before launch. |

The current descriptor has no human scene/device descriptions, scene profile or per-scene digest. Its device map is package-wide. IsOS's present resolver checks containment and referenced file bytes but does not establish that an XML file has the declared benchmark profile. The simulator engine itself checks that profile when loading a scene.

## P02 descriptor extension — target design, not implemented

The following fields are additive within descriptor schema `2.0.0`. `scenes[].id` and `devices.<kind>` remain the stable values stored in graph settings; paths, XML markers and hashes are package metadata only. The new package candidate requires all metadata below, while an already verified historical descriptor without it remains readable for its legacy graph behavior. IsOS does not synthesize new-graph options from an old descriptor.

| Field | JSON type / unit | Purpose and owner | Default, validation and compatibility |
| --- | --- | --- | --- |
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

`runtime.mujoco_version`, `runtime.environment_variable` and `runtime.library` keep their existing meanings. IsOS checks the declared `3.16.0` library under `MUJOCO_ROOT` before Apply and Run and reports an unavailable reason when it is absent or incompatible; the package does not bundle the library. A file with the expected name alone is not a claim of ABI compatibility: the launch/readiness boundary must establish the actual loaded version before reporting ready. P01 verifies the exact release receipt, all payload bytes and path containment first. P02 checks semantic scene/profile and device-map consistency against that verified handle. Changing a binary, scene XML, referenced asset or contributed sidecar under a fixed `0.1.1` pin invalidates the P01 receipt; publish a new package version for intentional changes.

The P02 target descriptor is frozen in [`tests/fixtures/scene_catalog/target-descriptor.json`](../../../tests/fixtures/scene_catalog/target-descriptor.json). Its two SHA-256 values name the repository's current scene XML bytes. The fixture is a design target, not a presently emitted bundle.

## P02 contribution and graph boundary — target design, not implemented

The package contributes one new process type, `eos.process.mujoco@v0.1`, at `eos/process/mujoco`, and retains the exact `eos.process.mujoco@v1.0` historical identity for verified legacy readers. The new type has a nonblank `description`; its `scene` setting has a nonblank description and `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`. `socket` (owner-only Unix socket path), optional `env` (string table) and `start_timeout_ms` (positive integer milliseconds) have described types and validation. Its `status` and `health` outputs carry complete descriptions, `in_process` transport and `state` data class. The process instance pins `node.package:{"id":"island/mujoco-sim","version":"0.1.1"}`; it never stores a resolved executable or scene path in settings. This sidecar adds no actuator or safety adapter route.

The `sim-hardware` new-graph node set is a draft template for `0.1.0`, not executable authority. It includes the package-owned new process type, generic EOS camera/base/manipulator `@v0.1` types, generic EOS base/arm primitive bindings `@v0.1`, and an EOS camera gate `@v0.1`. The IsOS starter already supplies `eos.dispatcher.control@v0.1`; the set must not duplicate it. Each generic hardware instance uses `node.adapter.package` for the exact MuJoCo pin, references the process node, and stores the selected `device_id` and matching `simulator_node` in adapter settings. The package does not contribute, rename or override a generic EOS type. The old `isos.ui.vision@v1.0` is omitted from this `0.1.0` set until its owner registers a compatible type; a package must not invent an IsOS UI identity. Previously verified legacy sidecars and saved `1.0.0` graphs remain readable under their established behavior; neither a new preset nor a legacy read silently rewrites them.

The P02 set declares stable `scene`, `camera_device`, `base_device`, `manipulator_device` and owner-only `socket` parameters. The default scene is `pick-place`; the three device defaults are `cam-0`, `base-0`, `arm-0`. Preview and Apply require the selected IDs to be present in the exact verified descriptor, match hardware kind and selected scene, and pass graph-wide admission. The graph stores IDs and the exact package pin. IsOS owns composition and revision compare-and-swap, so changing the scene produces a new saved revision; it reaches the child only after Restart. No scene change mutates a running simulator in place.

P03 owns the generic `GET`/`POST /node-options` grouping by `(node_path,setting)`, selected-value echo and unavailable-option presentation. This package supplies selector declarations and verified catalog metadata; it does not define an HTTP envelope. R05 owns strict socket feature negotiation, request `node`/operation validation and command deduplication. A P02 catalog entry is not evidence that the current socket enforces device IDs.

Example target descriptor excerpt (the full fixture has both scenes and all three devices):

```json
{"schema_version":"2.0.0","package":{"id":"island/mujoco-sim","version":"0.1.1"},"scenes":[{"id":"pick-place","label":"Pick and place","description":"Reach, grasp and place an object","profile":"eos_benchmark_pick_place_v1","path":"assets/scene.xml","sha256":"6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"}],"devices":{"camera":"cam-0","base":"base-0","manipulator":"arm-0"}}
```

For a selected `navigation` scene whose XML declares `eos_benchmark_pick_place_v1`, IsOS reports scene/profile mismatch at the process `settings.scene` path and leaves saved and active revisions unchanged. If `arm-0` is missing from `navigation`'s declared device support, the manipulator option is unavailable with a bounded reason and Apply fails at its adapter setting. If `MUJOCO_ROOT` lacks the required library, the package remains installed but the selected scene cannot become ready. The current implementation's generic errors precede these P02-specific diagnostics.

The general `release.json` fields (`id`, `version`, digest, architecture, source, license and assets) follow IsOS's package contract. This package contributes one process node type, the `mujoco-v2` adapter family and `sim-hardware` node set. The package owns only the simulator process type. Camera, base, manipulator, gate, primitive binding and Vision types remain generic types owned by EOS or IsOS. A node instance's `description` describes that configured instance; the target registered process `NodeType.description` describes the reusable type. The current sidecar has no type description, so IsOS supplies the defined compatibility fallback until a new sidecar is published.

## Current contribution compatibility

The present sidecar contributes only `eos.process.mujoco@v1.0`, has no process-type description or selector and composes a `1.0.0` graph with fixed device IDs. Old sidecars may receive a catalog-only description fallback from their readers, without changed verified bytes. A new `@v0.1` contribution is emitted only after matching EOS and IsOS readers accept it and P01 verification seals it. Package assets may use the same P03 option mechanism later; this release defines no `egia.tensor` execution.
