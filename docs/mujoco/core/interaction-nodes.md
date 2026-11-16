# Simulator mapping for interaction roles

[中文](../../../docs_cn/mujoco/core/interaction-nodes_cn.md) · [Design index](README.md) · [Runtime control](../interfaces/control.md)

**Target design — not implemented.** IsOS proposes per-interaction caller/responder and publisher/subscriber roles for typed graph routes. This page maps that design to the current MuJoCo package without changing its socket, package, node IDs, or benchmark boundary. The [IsOS interaction design](https://github.com/Island-Team/isos-p/blob/docs/interaction-node-roles/docs/isos/design/interaction-nodes.md) owns the graph-level proposal; MuJoCo continues to own only its [private simulator protocol](../interfaces/control.md).

## Current boundary

The simulator answers bounded private device requests. EOS is the only robot-side caller through its selected adapter. A camera capture or device observation is a request and reply even though the reply contains a frame or state. EOS validates and converts that reply, then may publish a typed observation on an admitted graph output. MuJoCo itself does not have a graph publisher or subscriber port. Movement reaches the simulator only after EOS Dispatcher admission; private benchmark scoring remains evaluator-only.

| Exchange | Graph-facing interpretation | Owner and constraint |
| --- | --- | --- |
| EOS health or observation request → MuJoCo reply | EOS adapter is caller; simulator is responder. EOS may subsequently publish the checked observation. | MuJoCo owns request framing and device checks; EOS owns graph routing and freshness. |
| EOS admitted movement request → MuJoCo reply | EOS adapter is caller; simulator is responder. The reply is one command result, not an observation publication. | EOS Dispatcher owns authorization, durable command identity, and outcome handling; MuJoCo enforces its own strict device and generation checks. |
| EOS governed Stop → MuJoCo Stop proof | Owner lifecycle operation, outside ordinary graph publication. | EOS verifies the separate actuator proofs and reaps its directly supervised simulator child; IsOS separately supervises any package-service child it owns. |
| Evaluator benchmark request → benchmark reply | No graph role. | Trusted evaluator only; result and scoring truth cannot enter EOS or EI inference routes. |

## Package implication

A future package contribution may advertise a camera observation source or a device request service only after IsOS and EOS define and implement the matching versioned interaction declarations and route adapter. The package must not infer a graph role from `camera_capture`, `base_observe`, HTTP GET/POST, or socket direction. Its logical node type remains a simulator-backed device; one registered interaction could be caller-facing while another is publisher-facing. Endpoint addresses and child generations are resolved for a selected run, never authored into graph bytes.

The first cross-repository check should capture a frame through the existing strict socket, validate it at EOS, deliver it to a declared subscriber, then stop the run while capture is pending. Reject an unavailable service, stale run or revision, wrong device, invalid frame, blocked consumer, and missing route before claiming support. The separate movement check must prove that no new caller role bypasses EOS Dispatcher, and that an uncertain reply is not retried with a new command ID.

## Design verification

From the MuJoCo repository root, `git diff --check` and a relative-link audit of the four changed Markdown files passed, with zero broken links. A full audit of all 58 Markdown files using the sibling IsOS `scripts/check_doc_links.py` found five pre-existing broken anchors outside this change. Logs and the audit command are saved under ignored `data/test/20261115-interaction-node-roles/`.
