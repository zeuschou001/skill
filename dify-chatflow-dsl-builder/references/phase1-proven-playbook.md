# Phase 1 Proven Playbook

## Scope

This playbook captures the parts of the Dify Chatflow build that were actually validated on this machine during the `2026-04-22` to `2026-04-23` repair cycle.

Use it when continuing or rebuilding a protocol-oriented Chatflow with:

- knowledge base / RAG
- uploaded protocol documents
- multi-turn follow-up for missing parameters
- separate analysis and code-generation routes

## What Proved Reliable

- `GET /console/api/apps/{appId}/workflows/draft` is the truth source.
- `POST /console/api/apps/{appId}/workflows/draft` can persist repairs when the payload shape matches the live draft.
- Direct DSL import is useful for coarse bootstrap, but not reliable for preserving every structural edit.
- `conversation_variables` did not persist durably in this instance and should not be the foundation of the design.
- Dataset bindings can disappear after import and must be read back from the draft.

## What Broke

- `Variable Assigner.items` contained an incomplete placeholder object, which caused:
  - `VariableAssignerNodeData ... items.0.operation Field required`
- A downstream node referenced `#1776862000001.text#` from the wrong branch, which caused:
  - `Variable #1776862000001.text# not found`
- The first `If/Else` routing made `follow_up` too broad, so analysis and generation requests were both hijacked into follow-up.
- One retrieval branch existed in the graph but was not actually connected from all intended cases.

## Repair Rules

- If `Variable Assigner` is not actively needed, keep `items = []`.
- Never let `Answer` or a review node consume outputs from mutually exclusive branches.
- Give follow-up its own terminal answer node when the other branches continue into retrieval and generation.
- Re-read the full draft after every route repair; canvas correctness is not enough.

## Recommended Phase 1 Graph

Use this logical shape:

`Start -> Document Extractor -> Parameter Extractor -> Readiness Judge -> If/Else`

Then:

- `follow_up -> Answer - Follow-up`
- `analysis -> Knowledge Retrieval - Official -> Analyst -> Answer`
- `generate -> Knowledge Retrieval - Official -> Code Generator -> Code Self Check -> Answer`

## Required Node Bindings

- `features.file_upload.enabled = true`
- `features.file_upload.allowed_file_types = ["document"]`
- `Document Extractor.variable_selector = ["sys", "files"]`
- `Knowledge Retrieval.query_variable_selector = [StartNodeId, "sys.query"]`
- `Answer.answer` must point to the text output of the terminal node on that branch

## Proven Route Conditions

These conditions fixed the "everything goes to follow-up" failure:

- `follow_up`
  - contains `"intent": "generate_code"`
  - contains `"generation_ready": "false"`
- `analysis`
  - contains `"intent": "analyze_protocol"`
- `generate`
  - contains `"intent": "generate_code"`
  - contains `"generation_ready": "true"`

The key point is that `follow_up` must not trigger only on `generation_ready = false`. It must also require `intent = generate_code`.

## Prompt Design Guidance

- `Parameter Extractor` should normalize:
  - `intent`
  - `target_language`
  - protocol facts such as transport, frame format, endianness, checksum, examples
  - `missing_info`
- `Readiness Judge` should decide whether the request is analysis or generation, and whether generation can proceed with the facts already available.
- Do not make `protocol_name` or a perfect `frame_format` hard blockers if the generation task can still proceed from sample frames plus explicit constraints.

## Verification Checklist

- Draft can be read successfully before and after each change.
- Graph edges match the intended branches.
- `dataset_ids` is not empty after retrieval is rebound.
- No node references an upstream output that is unreachable on its branch.
- A follow-up-only case returns a follow-up question instead of code.
- An analysis-only case reaches retrieval and the analysis LLM.
- A generate-ready case reaches retrieval, generation, self-check, and terminal answer.

## Local Files

- Current repaired draft:
  - `<OUTPUT_DIR>/phase1-route-conditions-fixed-draft.json`
- Route-condition repair result:
  - `<OUTPUT_DIR>/fix-route-conditions.json`
- Branch-routing repair result:
  - `<OUTPUT_DIR>/fix-branch-routing-phase1.json`
- Acceptance notes:
  - `<OUTPUT_DIR>/phase1-waived-final-acceptance-notes.md`
- Repair scripts:
  - `<PLAYWRIGHT_DIFY_ROOT>/dify-fix-branch-routing-phase1.js`
  - `<PLAYWRIGHT_DIFY_ROOT>/dify-fix-route-conditions.js`
  - `<PLAYWRIGHT_DIFY_ROOT>/dify-relax-generation-gate.js`
