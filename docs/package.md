# Package declaration and qualification

[中文](../docs_cn/package_cn.md) · [Docs](README.md)

This package contributes EOS hardware nodes and two IsOS-supervised services. This page owns package-specific manifest, resource, and configuration rules. [Node groups](node/README.md) own graph-visible ports; [adapter control](core/adapter.md) owns the private socket. General release-manifest admission remains owned by IsOS. Historical process declarations are retained in [changelog](changelog.md).

<a id="mujoco-package-descriptor-and-contributions"></a>
## MuJoCo package descriptor and contributions

This page owns the current hardware package declaration. Historical process declarations are in [changelog](changelog.md). Runtime control fields for the RoboCasa and native presets are in the [control contract](core/adapter.md).

The optional `ubuntu22` CMake build profile uses a separate `.local/package-build-ubuntu22` directory and requires an Ubuntu 22.04/glibc 2.35 host and Python 3.11 or newer. Both development and package builds use this directory, and cross-compilation is rejected. `MUJOCO_BUILD_PROFILE=ubuntu22` selects it through the existing package build entrypoint. Only this profile checks the installed simulator and adapter ELF glibc versions against 2.35. Unset the variable to retain the existing native build and package checks. The profile does not grant release qualification.

<a id="full-robot-hardware-package"></a>
### Full robot hardware package

The default source build is the unpublished `0.2.8` candidate. Its actuator inputs use the current standard payload schemas and `{owner:"isos",id:<data_type>,version:"1.0"}` port contracts. EOS forwards these validated payloads unchanged through the selected parts Dispatcher; the package plugin translates them to native or RoboCasa private wire fields. Noncamera observations use `observation`; camera output remains `frame`, and torso exposes measured `joint_channels@v0.1` through `observation`. Versions through `0.2.7` retain their legacy declarations and adapter translation. The standard native arm omits an unenforced speed claim. Each package preset remains hardware-only; compose a parts Dispatcher with one selected command input for each actuator.

The `0.2.8` source candidate contributes seven EOS hardware type definitions and **Native robot** and **RoboCasa robot** device presets. Each instance pins the exact package both as its type owner and as its adapter owner. The types live in the EOS hardware layer under camera, base, manipulator, gripper, and torso groups; other packages may choose different layers and groups. A preset contains no process node. IsOS starts only the package service referenced by selected nodes, owns its child and logs, and passes a private service endpoint to EOS. EOS loads the verified `libmujoco-eos-node.so` through `isos_node_v2` and admits actuator commands through its Dispatcher.

The exact node type declarations are indexed under [EOS hardware node interfaces](node/README.md). The following fields follow the current generic IsOS package release and service declarations; IsOS validates the archived bytes and resolves host configuration at Apply and Run.

| Declaration | Type / unit | Purpose and required value | Absence, validation, and compatibility |
| --- | --- | --- | --- |
| `node_contributions.node_types[]` | object array / — | Seven EOS hardware types across camera, base, manipulator, gripper, torso | Required for these presets; exact type IDs and port types are in the node interface pages. Unknown types fail admission. |
| `node_contributions.runtime_services[].id` | string / — | `native` or `robocasa` service identity | Required, unique; no default. |
| `runtime_services[].entrypoint` | package path / — | `bin/eos-mujoco-sim` or `bin/robocasa-worker` | Required verified executable inside the archive; no path escape or default. |
| `runtime_services[].args` | string array / — | Owner launch template using `${socket}` and verified scene resource where applicable | Required; references must resolve from declared service inputs. |
| `runtime_services[].config_service_type` | string / — | Selects `native` or `robocasa` configuration | Required and matched to a configured service instance. |
| `runtime_services[].node_types` | string array / — | Types eligible for this service | Required, nonempty, and contributed by the exact release. |
| `runtime_services[].resources` | object array / — | Native scene selector bound to `package-resources.json` | Required for native; absent for RoboCasa. |
| `runtime_services[].environment` | object array / — | Verified host and service values for the child | Required variables are declared by the exact service; missing configured values block Run. |
| `runtime_services[].requirements` | path and kind array / — | Selected service's local prerequisites | Native requires the MuJoCo library file. RoboCasa requires the configured Python interpreter file and assets directory; IsOS checks only the selected service. |
| `runtime_services[].required_node_settings` | type-to-field map / — | Requires width and height on selected native and RoboCasa camera nodes | IsOS checks presence and declared integer bounds at Apply. |
| `node_sets[].nodes[].profile.adapter.settings` | object / — | `service_instance` and `device_id` bind each preset device | Both required strings, no defaults; IsOS verifies service/type/device relation. |

Each selected service writes a bounded ready line to stdout after its private listeners are available and a stopped line during normal cleanup. IsOS captures stdout and stderr into its deployment JSONL as `package_service_output` records with the exact package ID and version, service instance, stream, generation, and run ID. EOS writes its own owner records with that run ID. The [full interface replay](development.md) checks this correlation; the IsOS log reader and retention rules remain owned by IsOS.

Each camera hardware node has integer `settings.camera_width` and `settings.camera_height` in the 64–2048 pixel range. Both presets supply 1280 × 720. Both services require these fields on selected camera nodes. IsOS passes selected settings through `${selected_nodes.settings_json}`: `ISOS_NATIVE_CAMERA_SIZES` for native `cam-0` and `ISOS_ROBOCASA_CAMERA_SIZES` for RoboCasa. The native simulator renders and JPEG-encodes at the selected dimensions; direct simulator runs without these settings retain the scene dimensions. The worker validates the selected camera IDs and sizes before creating Gym. The raw hardware adapter renders each selected agent/free camera at its own configured dimensions. A graph edit takes effect after Apply and the next Run. Package configuration contains shared host paths, scene, task, and seed. Earlier exact package releases retain their original camera configuration behavior.

The `0.2.8` candidate encodes RoboCasa RGB8 observations to JPEG in the native adapter before emitting `image_frame@v0.2`. Its RoboCasa camera profiles advertise `jpeg`; the worker socket still carries bounded RGB8. This candidate requires the IsOS package setup descriptor change to be reviewed and published, then exact package qualification and publication, before a graph pinned to `0.2.8` can be deployed from a release.

For 0.2.8, the package descriptor also declares a verified RoboCasa setup helper. In an interactive IsOS CLI, `isos pkg configure island/mujoco-sim@0.2.8 --service robocasa` asks before downloading a pinned RoboCasa source, Python 3.11 environment, and first-task assets when either configured RoboCasa host path is absent. It writes the resulting paths into the config draft for operator review. Declining leaves manual path configuration available. The Web form continues to require manual paths. The setup data stays in IsOS deployment-local storage outside the verified package.

`config/package-config.json` declares bilingual labels and descriptions for the generic IsOS package form. Its `services.native.scene` enum offers the verified `pick-place` and `navigation` scene IDs, with `pick-place` as the default. Its `services.robocasa.task` enum currently offers only `CloseFridge`, the task verified by local smoke replay, and selects it by default; the wider pinned upstream task registry is not yet qualified for this package selector. IsOS validates selected values against the descriptor options. `config/package.toml` provides `[package]`, `[host]`, `[services.native]`, and `[services.robocasa]`. A selected native service needs a local MuJoCo 3.3.1 root. A selected RoboCasa service needs local assets and an explicitly selected Python interpreter. These large host resources are not downloaded with the release. Their paths are local deployment configuration, not graph node settings. Every hardware adapter setting selects a `service_instance`; IsOS resolves that instance at Apply and Run.

Build the candidate with `./build.sh --output ABSOLUTE_EMPTY_DIRECTORY --version 0.2.8` or a later unused version. Published tags through v0.2.7 remain unchanged. A candidate is publishable only after the IsOS `pkg check` replay succeeds for both presets, including rejection, crash, logs, and Stop cases.

The RoboCasa launcher receives `host.python_interpreter` as `ISOS_PACKAGE_PYTHON` and executes the packaged worker with `-B`. The package contains Python source, not a frozen Python binary or the RoboCasa environment. IsOS checks the selected interpreter and assets paths as service requirements at Apply and Run; the launcher additionally requires an executable interpreter. Missing Python modules or an incompatible prepared environment fail worker startup before health reports ready. A native-only selection has no Python requirement.

## Verified scene and device resources

`package-resources.json` uses `contract:"isos.package-resources@v1"`, string `schema_version:"0.1.0"`, and a required `resources` array. Resource IDs are stable selectors, not executable paths or graph identities. The package builder emits this catalog from the checked native scene/device descriptor; IsOS verifies the archived file and selected resources before Run.

| Resource field | Type / unit | Meaning, default, and validation |
| --- | --- | --- |
| `kind` | string / — | Required `scene` or `device`; no default. |
| `id` | string / — | Required unique stable resource ID; no default. |
| `label`, `description` | string / — | Required nonblank display text; no default or execution authority. |
| Scene `path` | string / package-relative path | Required contained regular MJCF file; reject traversal or symlink escape. |
| Scene `sha256` | string / — | Required lowercase SHA-256 of exact scene bytes; a mismatch rejects selection. |
| Device `metadata.device_kind` | string / — | Required `camera`, `base`, `manipulator`, or `gripper`; no default. |
| Device `metadata.scene_ids` | string array / — | Required nonempty unique references to declared scenes; the selected scene must support the device. |

The native descriptor `backend-v2.json` separately pins `catalog_version:"0.1.0"`, supported scene profiles, and the private device mapping. `tools/catalog.py` rejects partial metadata, unknown profiles, duplicate IDs, unavailable model elements, or mismatched digests. The resource catalog does not describe RoboCasa Gym environments. Exact old package bytes retain their original descriptor shape; schema and package release versions are independent.


## Current wrapper admission (schema 0.2.2)

The unpublished 0.2.8 candidate uses manifest schema `0.2.2`. It remains hardware-only: seven EOS hardware types, two device presets, and two IsOS-supervised services. Graph `0.3.1`, port payloads, and `isos_node_v2` are independent and unchanged. The package declares no node extensions because it has no node string settings requiring text editors or Unicode constraints; it does not require `node-extensions-v1`. Scene, robot model, task, and seed remain shared service configuration.

Current camera width and height settings are required integers from 64 to 2048 px; presets explicitly supply 1280 × 720. The type declares 1280 × 720 defaults; saved node profiles retain explicit values for service handoff. JPEG quality and capture cadence are also declared user-adjustable node settings. RoboCasa task and seed are required package configuration fields. The seed is an unsigned 32-bit integer (0–4294967295), with 42 in both the form and TOML template; the worker also rejects an out-of-range seed before creating Gym. Form defaults do not replace missing TOML values.

`./build.sh --output ABSOLUTE_EMPTY_DIRECTORY` selects the current source candidate version; `--version 0.2.x` may select a canonical later unpublished candidate. Versions below the source candidate are rejected by both build entry points because current configuration and interfaces cannot reconstruct those historical releases. A local release tag does not block an explicitly selected source build, including rebuilding a registered source pin after a clean HEAD change. Such builds remain local source candidates; IsOS qualification and publication checks enforce unused catalog versions, immutable published tags, and release assets.

Run `python3 tests/nodes.py`, `python3 tests/build_env.py`, `python3 tests/config_modes.py`, `python3 tests/robocasaworker.py`, and `python3 tests/bundle.py BUILD/eos-mujoco-sim MUJOCO_ROOT` for declaration, invocation, configuration isolation, worker failure/Stop, and current archive relocation checks. The archive check validates configuration and resource hashes, setup helpers and executable service entrypoints, then exercises native capture/rejection/Stop and a missing RoboCasa interpreter. Full qualification still requires clean-source `isos pkg check` with both service graphs and deployment-local package configuration.

The 0.2.8 candidate discovers supported RoboCasa body parts through the raw composite controller. Use the [body preparation tool](core/robocasa.md) to generate exact hardware, Dispatcher and model control declarations; adapter readiness pins the runtime manifest digest. Fixed presets remain compatibility examples. Torso now includes real joint-local measured channels; mixed prismatic/hinge units are preserved.

## Local candidate qualification, 22 November 2026

The unpublished 0.2.8 candidate built from source `d0d6cda4b4cdc50849498f8f54f73231e3c36428` passed current IsOS package qualification for both full native and discovered PandaOmron service graphs. Archive SHA-256 is `b125e54a8db1867ebd67148199f777bbf65675d21b9081c2838610ce5097f3d2`; qualification SHA-256 is `2ff22a77f0adbac94af9ad54cfdc0244988ee9ca7e5fdbefa6b6c4eb85ab9808`. The check covered exact Apply/readiness, all typed observations and controls, identity rejection/deduplication, child failure, confirmed Stop, socket cleanup and mandatory service/EOS log identities. Complete local evidence is retained under ignored `data/test/20261122-body/qualification-clock-stable/`; `tests/package_logs.py` passed against that output.

This candidate includes explicit observation capture clocks, truthful cached simulation-time measurements for paused worlds, and the24-step bounded initial Stop settling window with the unchanged two-consecutive-sample proof tolerance. The independent idle-worker test confirmed Stop without first issuing movement commands. Fixed-base `Panda` remains unverified for this pinned kitchen because its reset requires the mobile-base yaw joint. Optional unsupported controller families remain explicitly unavailable; local qualification does not publish a tag/release or prove autonomous task success. See [verification commands](development.md#robot-body-candidate-verification-22-november-2026).

Current 0.2.8 camera nodes declare 1280 × 720 defaults, adjustable JPEG quality/capture cadence, and an independent free spectator camera. See the [camera node](node/eos/hardware/camera.md).
