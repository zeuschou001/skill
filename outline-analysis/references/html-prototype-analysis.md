# HTML Prototype Analysis Reference

Use this reference when source materials include exported HTML prototypes, Axure HTML exports, static UI mockups, or a directory that contains HTML pages plus generated `files/`, `images/`, `data/`, `plugins/`, or `resources/` folders.

## Detection

Treat a directory as an HTML prototype export when one or more of these signals exist:

| Signal | Meaning | Action |
|---|---|---|
| Root `*.html` pages | Each file is likely a page or entry shell | Extract title, visible text, page-level source location |
| `files/<page>/data.js` | Axure page data | Extract interaction strings, widget labels, image references, page-specific evidence |
| `data/document.js` | Axure document metadata | Extract project name, sitemap hints, global styles and page URLs when readable |
| `plugins/sitemap/sitemap.js` | Axure player sitemap plugin | Use only as navigation support; page data is usually in `data/document.js` and root HTML |
| `images/<page>/` | Rendered image assets | Record as visual evidence; do not infer text unless visible in HTML or OCR/screenshot review |
| `resources/`, `plugins/` | Viewer runtime | Exclude from business requirement extraction unless it contains sitemap or document metadata |

## Extraction Output

Create one prototype material record and one page inventory. Use table output rather than long prose.

| Output | Required Columns |
|---|---|
| Prototype material record | Material ID, prototype name, source path, export type, conversion method, page count, extracted coverage, missing content, confidence |
| Page inventory | Page ID or order, page name, HTML source, page data source, parent/group if known, visible text count, key labels, field/button candidates, interaction hints |
| Page-to-requirement mapping | Page/group, visible evidence, candidate requirement, source location, confidence, unresolved questions |
| Prototype-to-design mapping | Requirement ID, page/group, target module, flow, data object, permission point, acceptance focus |

## Axure HTML Extraction

For Axure HTML exports, process in this order:

1. Read root HTML pages and ignore runtime shells such as `index.html`, `start.html`, `start_with_pages.html`, `resources/*.html`, and reload helper pages unless they contain business UI.
2. Extract `<title>`, visible text blocks, table-like labels, form labels, buttons, tabs, filters, menu names, error prompts, empty states, and dialog labels.
3. For each page, read `files/<page>/data.js` when present and extract readable interaction strings such as click events, show/hide actions, navigation targets, dynamic panel states, selected states, and validation prompts.
4. Read `data/document.js` to confirm project name, page URLs, page names, groups, global variables, and sitemap hints when they are readable.
5. Preserve source locations as `MaterialID:<page>.html`, `MaterialID:files/<page>/data.js`, or `MaterialID:data/document.js`.
6. Mark coverage as partial when text is only embedded in images, canvas, minified JavaScript, or unreadable runtime assets.

## Requirement Translation Rules

Convert prototype evidence into requirements conservatively:

| Prototype Evidence | Requirement Signal | Requirement Analysis Treatment |
|---|---|---|
| Page title or menu node | Functional capability or sub-capability | Create or enrich a functional requirement; record source page |
| Filter fields, search boxes, date ranges | Query and filtering behavior | Capture input fields, default values if visible, and validation gaps |
| Table headers, list columns | Data attributes and output fields | Add output/data requirements; flag unclear data source |
| Buttons and action links | User operation | Capture trigger, expected result, permission need, and pending confirmation |
| Tabs, steps, dynamic panels | State or sub-flow | Capture flow stages and state transitions only when visible or described |
| Error prompts, empty states, disabled states | Validation or exception branch | Add acceptance and exception requirements |
| Repeated page patterns | Reusable module or component | Group requirements but keep page-specific source evidence |

Do not treat a page name alone as proof of all underlying business rules. When a page implies a domain calculation, approval rule, report format, or integration, mark the rule as pending unless the material states it explicitly.

## High-Level Design Translation

When prototype-derived requirements enter high-level design:

| Design Area | How Prototype Evidence Should Be Used |
|---|---|
| Module划分 | Group pages by business capability, not by visual menu only; keep reuse/configuration/new-build labels |
| Core流程 | Use visible page sequence, buttons, states, and dialogs as flow evidence; mark hidden jumps pending |
| 数据设计 | Derive candidate entities and attributes from table headers, forms, filters, and detail panels |
| 接口设计 | Use import/export/sync/API/page data cues as integration candidates; require external system confirmation |
| 权限设计 | Map page groups and operation buttons to role/action permissions |
| 非功能设计 | Use dashboard, query, export, upload, batch operation, and audit pages to identify performance, traceability, and data-quality needs |
| 验收设计 | Convert page evidence into visible acceptance checks: page loads, filters work, fields validate, table columns export, operations leave audit trail |

## Review Notes

- Prefer concise tables over stacked paragraphs.
- Keep page-level source evidence even when multiple pages are merged into one requirement.
- Separate confirmed visible evidence from inferred business intent.
- If an `.rp` file is unreadable but an HTML export is available, treat the `.rp` as a low-confidence binary source and the HTML export as the analyzable prototype source.
