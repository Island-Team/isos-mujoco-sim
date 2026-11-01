# MuJoCo package descriptor and contributions

[中文](../../../docs_cn/mujoco/interfaces/package_cn.md) · [Socket](socket.md) · [Package release](../package-release.md)

**Owner and status.** This repository owns the MuJoCo-specific `backend-v2.json` descriptor and `node_contributions` in its schema v4 `release.json`. IsOS owns the general release-manifest schema, [verified receipt and package admission](https://github.com/Island-Team/isos/blob/master/docs/isos/interfaces/package-verification.md), graph revision, and `/node-options` response. `tools/build-backend-bundle.py` emits the P02 catalog and `@v0.1` contribution; IsOS semantic admission and the generic P03 option API are separate implementation slices. `backend-v2.json`, schema `2.0.0`, protocol name `mujoco-v2`, and socket wire `2.0.0` remain compatibility identities when the authored graph format is `0.1.0`.

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

The historical descriptor has no human scene/device descriptions, scene profile or per-scene digest. Its device map is package-wide. IsOS's existing resolver checks containment and referenced file bytes; its P02 companion adds descriptor-level profile and digest checks. The simulator engine itself checks the profile when loading a scene.

## P02 descriptor extension

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

`runtime.mujoco_version`, `runtime.environment_variable` and `runtime.library` keep their existing meanings. IsOS checks the declared `3.16.0` library under `MUJOCO_ROOT` before Apply and Run and reports an unavailable reason when it is absent or incompatible; the package does not bundle the library. A file with the expected name alone is not a claim of ABI compatibility: the launch/readiness boundary must establish the actual loaded version before reporting ready. P01 verifies the exact release receipt, all payload bytes and path containment first. P02 checks semantic scene/profile and device-map consistency against that verified handle. Changing a binary, scene XML, referenced asset or contributed sidecar under a fixed `0.1.1` pin invalidates the P01 receipt; publish a new package version for intentional changes.

The P02 descriptor is frozen in [`target-descriptor.json`](../../../tests/fixtures/scene_catalog/target-descriptor.json); [`legacy-descriptor.json`](../../../tests/fixtures/scene_catalog/legacy-descriptor.json) freezes the exact old shape. The bundle builder computes both scene SHA-256 values from copied XML and checks the profile markers, declared model elements, and referenced assets before packaging. Relative MJCF asset references may traverse up from the scene directory only while remaining within the verified bundle; missing, escaping or linked assets fail. Real engine load and replay remain in CTest.

## P02 contribution and graph boundary

The package contributes one new process type, `eos.process.mujoco@v0.1`, at `eos/process/mujoco`, and retains the exact `eos.process.mujoco@v1.0` historical identity for verified legacy readers. The new type has a nonblank `description`; its `scene` setting has a nonblank description and `selector:{"provider":"package","resource":"scene","package_from":"node.package"}`. `socket` (owner-only Unix socket path), optional `env` (string table) and `start_timeout_ms` (positive integer milliseconds) have described types and validation. Its `status` and `health` outputs carry complete descriptions, `in_process` transport and `state` data class. The process instance pins `node.package:{"id":"island/mujoco-sim","version":"0.1.1"}`; it never stores a resolved executable or scene path in settings. This sidecar adds no actuator or safety adapter route.

The `sim-hardware` new-graph node set is a draft template for `0.1.0`, not executable authority. It includes the package-owned new process type, generic EOS camera/base/manipulator `@v0.1` types, generic EOS base/arm primitive bindings `@v0.1`, and an EOS camera gate `@v0.1`. The IsOS starter already supplies `eos.dispatcher.control@v0.1`; the set must not duplicate it. Each generic hardware instance uses `node.adapter.package` for the exact MuJoCo pin, references the process node, and stores the selected `device_id` and matching `simulator_node` in adapter settings. The package does not contribute, rename or override a generic EOS type. The old `isos.ui.vision@v1.0` is omitted from this `0.1.0` set until its owner registers a compatible type; a package must not invent an IsOS UI identity. Previously verified legacy sidecars and saved `1.0.0` graphs remain readable under their established behavior; neither a new preset nor a legacy read silently rewrites them.

The P02 set declares stable `scene`, `camera_device`, `base_device`, `manipulator_device` and owner-only `socket` parameters. The default scene is `pick-place`; the three device defaults are `cam-0`, `base-0`, `arm-0`. Preview and Apply require the selected IDs to be present in the exact verified descriptor, match hardware kind and selected scene, and pass graph-wide admission. The graph stores IDs and the exact package pin. IsOS owns composition and revision compare-and-swap, so changing the scene produces a new saved revision; it reaches the child only after Restart. No scene change mutates a running simulator in place.

P03 owns the generic `GET`/`POST /node-options` grouping by `(node_path,setting)`, selected-value echo and unavailable-option presentation. This package supplies selector declarations and verified catalog metadata; it does not define an HTTP envelope. R05 owns strict socket feature negotiation, request `node`/operation validation and command deduplication. A P02 catalog entry is not evidence that the current socket enforces device IDs.

## P02 diagnostics and IsOS admission target

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

For a descriptor-only check, the `path` is empty even when the table shows the corresponding graph-time field. P01's `package_changed` at `payload` and `package_unsafe_path` at the containing stage take precedence over every P02 code. In particular, a linked scene modified after verification yields `package_changed`; a symlinked scene path yields `package_unsafe_path`. A package candidate with intact P01 payload bytes but a wrong declared scene digest yields `mujoco_scene_digest_mismatch` in P02 semantic checking before receipt publication. P03 presents an unavailable option using these bounded causes, but the HTTP option envelope remains IsOS-owned. The complete mutation and expected `{code,path,stage}` tuples are frozen in [`negative-cases.json`](../../../tests/fixtures/scene_catalog/negative-cases.json).

Example target descriptor excerpt (the full fixture has both scenes and all three devices):

```json
{"schema_version":"2.0.0","catalog_version":"0.1.0","package":{"id":"island/mujoco-sim","version":"0.1.1"},"scenes":[{"id":"pick-place","label":"Pick and place","description":"Reach, grasp and place an object","profile":"eos_benchmark_pick_place_v1","path":"assets/scene.xml","sha256":"6c677b07597ddf3d18cf7b30dddd407a09d1c53086d61c919592d16723d32aea"}],"devices":{"camera":"cam-0","base":"base-0","manipulator":"arm-0"}}
```

For a selected `navigation` scene whose XML declares `eos_benchmark_pick_place_v1`, IsOS reports scene/profile mismatch at the process `settings.scene` path and leaves saved and active revisions unchanged. If `arm-0` is missing from `navigation`'s declared device support, the manipulator option is unavailable with a bounded reason and Apply fails at its adapter setting. If `MUJOCO_ROOT` lacks the required library, the package remains installed but the selected scene cannot become ready. The MuJoCo builder classifies direct descriptor failures with these P02 codes; the IsOS companion slice maps graph-time failures to the exact paths above.

The general `release.json` fields (`id`, `version`, digest, architecture, source, license and assets) follow IsOS's package contract. This package contributes the new process type and its retained historical identity, the `mujoco-v2` adapter family and `sim-hardware` node set. The package owns only the simulator process type. Camera, base, manipulator, gate and primitive binding types remain generic EOS types. A node instance's `description` describes that configured instance; the registered process `NodeType.description` describes the reusable type. Old verified sidecars without type descriptions retain their compatibility fallback.

## Historical contribution compatibility

Historical verified sidecars contributed only `eos.process.mujoco@v1.0`, had no process-type description or selector, and composed a `1.0.0` graph with fixed device IDs. Old sidecars may receive a catalog-only description fallback from their readers, without changed verified bytes. The current builder emits both process identities and the `@v0.1` seven-node preset; IsOS must accept and verify the new descriptor before it can publish this preset as a graph option. Package assets may use the same P03 option mechanism later; this release defines no `egia.tensor` execution.
