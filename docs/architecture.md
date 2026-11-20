# Package architecture

[中文](../docs_cn/architecture_cn.md) · [Docs](README.md)

The package provides a native C++ MuJoCo service and an isolated Python RoboCasa service, selected through verified IsOS package declarations. The services supply robot observations and admitted actuation to EOS. EGIA and other agents act through EOS; they never receive evaluator ground truth.

## Ownership and data flow

| Component | Responsibility |
| --- | --- |
| IsOS | Verify exact package bytes, bind configuration and selected resources at Apply, launch selected services, capture output, and supervise service children. |
| EOS | Load the verified adapter, check device health, publish admitted observations, admit movement through Dispatcher, and classify Stop proof. |
| Native service | Load one selected MJCF, enforce device and generation checks, step physics, render JPEG, and enforce the native stop fence. |
| RoboCasa service | Own one Gym environment, serialize bounded hardware commands, return RGB8 camera data and measured robot state, and provide run-bound Stop results. |
| Trusted evaluator | Control private benchmark episodes and read scores through a separate direct-launch boundary. |

A graph node selects an exact package, adapter, service instance, and device. IsOS validates that selection and resolves private endpoints; EOS consumes the applied configuration without editing the graph. Commands pass Dispatcher admission, adapter validation, and service validation before physics changes. Replies establish command outcome; node observations follow their own publication path.

Native `cam-0` renders JPEG from the selected native scene. RoboCasa returns RGB8 over its private socket; the current adapter encodes it as JPEG for `frame`. Camera delivery sequence belongs to each adapter instance and does not prove that cached scene pixels changed. See the [camera group](node/eos/hardware/camera.md).

## Lifecycle and failure

Selection and configuration → Validate → Apply → Run → device health → admitted control → Stop is the managed lifecycle. Apply does not launch services. Missing dependencies, invalid devices, rendering failure, or service exit prevents successful readiness or observation. EOS closes admission and requests Stop proof before IsOS terminates its service children. A timeout, crash, or partial proof remains unknown, even if the process later exits. Rebuilding a candidate or changing configuration requires fresh Apply and Run.

The native strict service uses generation identity, retained command results, and a companion stop lane. The RoboCasa worker serializes Gym steps and latches its run-bound stop result. Their exact differences, bounds, and errors belong to [adapter control](core/adapter.md). Neither transport access nor graph connectivity grants movement authority.

## Source and compatibility

`src/mujoco/` owns the native engine, `src/isos/` its service, `src/plugin/` the adapter, and `robocasa_core/` plus `tools/robocasa_worker.py` the RoboCasa boundary. The [core index](core/README.md) maps their focused implementation and contract pages. Historical EOS-owned process nodes and qualification records are in [changelog](changelog.md); they do not describe current IsOS-owned services.

Source, package release, graph format, node type, native ABI, socket protocol, and protobuf namespaces are independent identities. An exact old package pin retains its declarations; upgrading a package requires checking its ports and selected configuration rather than changing unrelated version strings.

<a id="simulator-mapping-for-interaction-roles"></a>
## Simulator mapping for interaction roles

**Target design — not implemented.** IsOS proposes per-interaction caller/responder and publisher/subscriber roles for typed graph routes. This page maps that design to the current MuJoCo package without changing its socket, package, node IDs, or benchmark boundary. The [IsOS interaction design](https://github.com/Island-Team/isos-p/blob/docs/interaction-node-roles/docs/isos/design/interaction-nodes.md) owns the graph-level proposal; MuJoCo continues to own only its [private simulator protocol](core/adapter.md).

<a id="current-boundary"></a>
### Current boundary

The simulator answers bounded private device requests. EOS is the only robot-side caller through its selected adapter. A camera capture or device observation is a request and reply even though the reply contains a frame or state. EOS validates and converts that reply, then may publish a typed observation on an admitted graph output. MuJoCo itself does not have a graph publisher or subscriber port. Movement reaches the simulator only after EOS Dispatcher admission; private benchmark scoring remains evaluator-only.

| Exchange | Graph-facing interpretation | Owner and constraint |
| --- | --- | --- |
| EOS health or observation request → MuJoCo reply | EOS adapter is caller; simulator is responder. EOS may subsequently publish the checked observation. | MuJoCo owns request framing and device checks; EOS owns graph routing and freshness. |
| EOS admitted movement request → MuJoCo reply | EOS adapter is caller; simulator is responder. The reply is one command result, not an observation publication. | EOS Dispatcher owns authorization, durable command identity, and outcome handling; MuJoCo enforces its own strict device and generation checks. |
| EOS governed Stop → MuJoCo Stop proof | Owner lifecycle operation, outside ordinary graph publication. | EOS verifies the separate actuator proofs before IsOS terminates and reaps the selected package-service child. |
| Evaluator benchmark request → benchmark reply | No graph role. | Trusted evaluator only; result and scoring truth cannot enter EOS or EI inference routes. |

<a id="package-implication"></a>
### Package implication

A future package contribution may advertise a camera observation source or a device request service only after IsOS and EOS define and implement the matching versioned interaction declarations and route adapter. The package must not infer a graph role from `camera_capture`, `base_observe`, HTTP GET/POST, or socket direction. Its logical node type remains a simulator-backed device; one registered interaction could be caller-facing while another is publisher-facing. Endpoint addresses and child generations are resolved for a selected run, never authored into graph bytes.

The first cross-repository check should capture a frame through the existing strict socket, validate it at EOS, deliver it to a declared subscriber, then stop the run while capture is pending. Reject an unavailable service, stale run or revision, wrong device, invalid frame, blocked consumer, and missing route before claiming support. The separate movement check must prove that no new caller role bypasses EOS Dispatcher, and that an uncertain reply is not retried with a new command ID.

Implementation work is tracked in the [interaction route acceptance TODO](development.md#interaction-route-todo).
