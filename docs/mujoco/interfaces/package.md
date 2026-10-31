# MuJoCo package descriptor and contributions

[中文](../../../docs_cn/mujoco/interfaces/package_cn.md) · [Socket](socket.md) · [Package release](../package-release.md)

**Owner and status.** This repository owns the MuJoCo-specific `backend-v2.json` descriptor and `node_contributions` in its schema v4 `release.json`. IsOS owns the general release-manifest schema, registry verification, node graph and `/node-options` API. Existing bundle generation is implemented in `tools/build-backend-bundle.py`; the selector and `@v0.1` contributions below are target design. `backend-v2.json`, schema `2.0.0`, protocol name `mujoco-v2`, and socket wire `2.0.0` remain compatibility identities even when authored graph format becomes `0.1.0`.

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

The general `release.json` fields (`id`, `version`, digest, architecture, source, license and assets) follow IsOS's package contract. This package contributes one process node type, the `mujoco-v2` adapter family and `sim-hardware` node set. The package owns only the simulator process type. Camera, base, manipulator, gate, primitive binding and Vision types remain generic types owned by EOS or IsOS. A node instance's `description` describes that configured instance; the target registered process `NodeType.description` describes the reusable type. The current sidecar has no type description, so IsOS supplies the defined compatibility fallback until a new sidecar is published.

## Selector contract projection

The target sidecar marks `scene` with a package-scene selector and hardware `device_id` with a package-device selector. IsOS resolves options from the exact installed package receipt and current graph pin, not from an arbitrary user path. For each option it returns stable ID, label, description, availability and reason; a missing or unavailable saved ID remains visible in the UI but blocks Apply. Selection of `pick-place` yields `assets/scene.xml`, `navigation` yields `assets/scenes/navigation/scene.xml` only after verification. A device selector is constrained by registered hardware kind and the descriptor's device map. Package assets can use the same option mechanism later; this release does not define EGIA tensor execution.

New contributions use `@v0.1` node IDs after matching EOS and IsOS readers accept them. Existing `@v1.0` IDs remain readable for their established behavior; IsOS does not silently rewrite an applied graph. A schema-v4 receipt and its content digest remain immutable. A changed binary or scene requires a new package version.

## Failure example

If `scene="navigation"` is selected but its asset fails verification, IsOS returns an unavailable scene option with a reason and the graph cannot Apply. EOS never starts a child with an unverified path. If the package is installed but the required MuJoCo library is absent, installation may remain recorded while run readiness is false; the UI displays the library issue and the exact package pin.
