# Proven Artifacts

## Session Scope

This reference captures the Dify Chatflow build that succeeded on `2026-04-22` in:

- Workspace: `<PLAYWRIGHT_DIFY_ROOT>`
- App URL: `<DIFY_APP_WORKFLOW_URL>`
- App name: `IoT Protocol Parser`

## Proven Findings

- `Context7` was available in the new session and resolved Dify docs through `/langgenius/dify-docs`.
- Visible foreground browser actions worked after escalation for Edge launch.
- Dify app menu exposed both `Export DSL` and `Import DSL`.
- A one-shot DSL import succeeded and rewrote the app draft to a 7-node, 6-edge chain.
- Direct workflow draft replay through raw API writes was not treated as reliable.

## Important Local Files

- Session handoff: `<PLAYWRIGHT_DIFY_ROOT>/SESSION-HANDOFF-2026-04-22-ASCII.md`
- Final imported DSL: `<OUTPUT_DIR>/iot-protocol-parser-final.yml`
- Draft after successful import: `<OUTPUT_DIR>/post-import-draft.json`
- Post-import page readback: `<OUTPUT_DIR>/post-import-body.txt`
- Supported upload extensions: `<OUTPUT_DIR>/support-type.json`
- Dataset listing: `<OUTPUT_DIR>/datasets-list.json`
- Browser storage with current token shape: `<OUTPUT_DIR>/browser-storage.json`

## Proven Browser Tactics

- The app dropdown was reachable as the fourth top-level button in this instance during the successful session.
- After opening that menu, `Export DSL` and `Import DSL` were visible as stable buttons.
- Text matching in the Chinese UI was brittle because of encoding artifacts; button enumeration and menu inspection were safer than hardcoded labels.

## Proven API Tactics

- The console token lived in `localStorage.console_token`.
- Draft read endpoint:
  - `GET /console/api/apps/{appId}/workflows/draft`
- File support endpoint:
  - `GET /console/api/files/support-type`
- Dataset list endpoint:
  - `GET /console/api/datasets?page=1&limit=100`

## Successful Draft Shape

Imported node chain:

`Start -> Document Extractor -> Parameter Extractor -> Knowledge Retrieval -> Parser Generator -> Parser Self Check -> Answer`

Confirmed draft properties after import:

- `features.file_upload.enabled = true`
- `features.file_upload.allowed_file_types = ["document"]`
- `Document Extractor.variable_selector = ["sys", "files"]`
- `Answer.answer = "{{#1776862000002.text#}}"`

## Remaining Gap From The Successful Import

The `Knowledge Retrieval` node came back with:

- `dataset_ids = []`

So the known follow-up is:

1. Rebind the target dataset in the Dify UI.
2. Read back the draft JSON.
3. Confirm `dataset_ids` is no longer empty.

## Candidate Dataset Observed In This Session

The IoT knowledge base that looked relevant in the live dataset listing was:

- Dataset id: `<DATASET_ID>`

Do not assume it remains correct without checking the live dataset list again.
