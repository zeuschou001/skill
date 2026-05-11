---
name: dify-chatflow-dsl-builder
description: Use when building or repairing local Dify Chatflow apps on this machine, especially when node wiring, RAG bindings, or multi-turn routing must be changed and the live draft JSON is the only reliable source of truth.
---

# Dify Chatflow DSL Builder

## Overview

This is the local-use entry skill for the Dify instance already exercised on this machine.

Treat the live workflow draft as the source of truth after every meaningful change. UI state, DSL import success messages, and visually correct node graphs are not enough.

Local baseline for this installed copy:

- Workspace: `<PLAYWRIGHT_DIFY_ROOT>`
- App URL: `<DIFY_APP_WORKFLOW_URL>`
- References: `./references`
- Example assets: `./assets/examples`

## Core Workflow

1. Confirm Context7 MCP is available in the current session. If it is missing on the host machine, proactively ask the user whether to install or enable Context7 MCP before continuing.
2. Confirm Playwright MCP is available before any browser or visible UI work. If it is missing on the host machine, proactively ask the user whether to install or enable Playwright MCP before continuing.
3. Use Context7 against official Dify docs before editing the app.
4. Read the current draft, config, and dataset metadata before changing anything.
5. Discuss the proposed design plan with the user and wait for explicit user review approval before executing changes. Do not perform UI edits, DSL import, draft patch/write, or other workflow-changing actions until the design is approved.
6. Choose the least fragile edit path:
   - Visible UI only for small prompt or selector edits.
   - `GET draft -> patch JSON -> POST draft -> GET verify` for structural rewiring and route repair.
   - `Export DSL -> edit -> Import DSL` only as a bootstrap path, not as the final authority.
7. Re-read the draft JSON after every important change.
8. Stop and verify graph shape, variable bindings, retrieval bindings, and final answer binding.

## Official Node Model

Check these with Context7 before editing:

- `Chatflow` / `advanced-chat` is required for multi-turn collection.
- `Document Extractor` converts uploaded files to text and should read `["sys", "files"]`.
- `Parameter Extractor` is for structured fact extraction from free text.
- `Knowledge Retrieval` is the retrieval leg that feeds supporting context into LLM nodes.
- `If/Else` controls route branching and must be validated by actual case wiring.
- `Variable Assigner` items are schema-validated and every item needs an `operation`.
- `Answer` is the terminal output node and must reference a reachable upstream text variable.

## Required Checks

- Confirm the app is `Chatflow` / `advanced-chat`, not a single-turn workflow.
- Confirm `features.file_upload.enabled` if uploaded documents are part of the design.
- Confirm the `Document Extractor` input selector points to `["sys", "files"]`.
- Confirm the graph has the expected node count, edge count, and node types after every structural change.
- Confirm retrieval nodes still have the intended `dataset_ids` after import.
- Confirm every referenced variable comes from a node that is actually reachable on that branch.
- Confirm `Variable Assigner.items` is either valid or empty; never leave a half-filled placeholder item.
- Confirm the final `Answer` node returns the intended upstream text variable.

## Preferred Decision Rule

- If the change is mostly prompts, descriptions, or one selector: stay in the visible UI and verify the draft.
- If the change adds or rewires several nodes: prefer draft patch and readback verification.
- If DSL import appears to succeed but the graph comes back simplified, partially rewired, or missing bindings: trust the readback, not the import result toast.

## Safe Operating Rules

- If the user requires visible actions, keep browser operations in the foreground.
- Do not perform delete operations unless the user explicitly asks.
- Do not trust OCR-like Chinese text matching blindly; inspect stable selectors or menu/button indexes first.
- Do not assume imported dataset bindings survive DSL import; verify `dataset_ids` afterward.
- Do not assume `conversation_variables` can be durably written in this instance.
- Do not let one downstream LLM reference mutually exclusive upstream branches.
- Do not stop at "the page looks right". Always verify through draft JSON readback.

## Proven Pattern

This session converged on a working phase-1 pattern for protocol assistants:

`Start -> Document Extractor -> Parameter Extractor -> Readiness / Intent Judge -> If/Else`

Then split by case:

- `follow_up -> Answer - Follow-up`
- `analysis -> Knowledge Retrieval -> Analyst -> Answer`
- `generate -> Knowledge Retrieval -> Code Generator -> Code Self Check -> Answer`

Routing rules that prevented everything from falling into follow-up:

- `follow_up`: `intent = generate_code` and `generation_ready = false`
- `analysis`: `intent = analyze_protocol`
- `generate`: `intent = generate_code` and `generation_ready = true`

## Local References

Read the proven local session notes at [proven-artifacts.md](./references/proven-artifacts.md).

Read the repaired phase-1 playbook at [phase1-proven-playbook.md](./references/phase1-proven-playbook.md).

Use the optional IoT protocol parser DSL example at [iot-protocol-parser-final.yml](./assets/examples/iot-protocol-parser-final.yml) only when the target app is similar, then verify every binding through draft readback. This example is not required for the skill to operate.

The skill root is flat: `SKILL.md` is the only skill entry point, with references and reusable examples bundled under root-level folders.

## Common Failure Modes

- `Context7` not loaded in the new session: ask whether to install or enable Context7 MCP before researching node behavior.
- `Playwright MCP` not available when browser work is needed: ask whether to install or enable Playwright MCP before attempting visible UI automation.
- Browser automation cannot find a menu item by visible text: inspect current button indexes and menu state before clicking again.
- Draft API reads succeed but writes fail with `400`: compare payload shape with the latest working draft before changing strategy.
- DSL import succeeds but a retrieval node comes back with `dataset_ids: []`: rebind that node and verify again.
- A route looks valid in the canvas but runtime says a variable is missing: the downstream node is referencing the wrong branch output.
- `VariableAssignerNodeData ... items.0.operation Field required`: remove the placeholder item or supply a full valid assign rule.
- Analysis requests go to follow-up anyway: the `follow_up` case is too broad and is missing the `intent = generate_code` guard.
- Feature toggles look enabled in UI but draft still disagrees: trust the draft JSON, not the screenshot.
