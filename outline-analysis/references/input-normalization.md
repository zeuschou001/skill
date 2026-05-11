# Input Normalization Reference

Use this before requirement analysis when source materials are not already clean text.

## Required Preflight

Before running extraction, check the tool and environment requirements:

- Python 3.10 or newer is available.
- `skills/outline-analysis/scripts/extract_outline_materials.py` exists in the installed skill.
- The source file or directory exists and is readable.
- The output directory, or its nearest existing parent directory, is writable.
- The requested material types are within the extractor's capability boundary: Markdown/text, CSV, DOCX, basic PDF text, XLSX/XLSM XML content, HTML, and Axure HTML exports are parsed; screenshots/images, legacy `.xls`, `.rp`, PPT/PPTX, scanned PDFs, macros, charts, and image-only content require OCR, conversion, or manual notes.

Use the bundled preflight command first:

```bash
python3 skills/outline-analysis/scripts/extract_outline_materials.py --check --source <material-path> --out <output-dir>
```

If the preflight returns `ok: false`, stop normalization, report the failed checks, and ask for the missing tool, readable source, writable output location, OCR text, converted XLSX/CSV, exported HTML, screenshots, or manual description needed to proceed.

When the input is a directory or bundle and preflight passes, create a material index first, then normalize each readable file. The generic extractor may be used as a helper:

```bash
python3 skills/outline-analysis/scripts/extract_outline_materials.py --source <material-path> --out <output-dir>
```

## Generic Record

- Material ID:
- File name or material name:
- Material type:
- Conversion method:
- Coverage:
- Source location:
- Summary:
- Structured entries:
- Unreadable content:
- Impact on analysis:

## Material Index

| Field | Purpose |
|---|---|
| Material ID | Stable ID such as `M01`, `M02`, or a user-provided ID |
| File path | Original local path or relative path inside the bundle |
| Material type | Markdown, text, PDF, DOCX, XLSX, HTML, Axure HTML export, screenshot, archive, unsupported binary |
| Conversion method | Parser, OCR/manual read, spreadsheet row extraction, HTML visible text extraction, prototype page extraction |
| Coverage | Pages, sheets, rows, HTML pages, screenshots, readable characters, or parsed controls |
| Missing content | Images without OCR, formulas not evaluated, hidden prototype states, unreadable binary content |
| Confidence | High, medium, low, or blocked |
| Output location | Normalized Markdown, text, JSON, page index, or manual note file |

## Markdown Or Text

- Preserve headings, tables, numbered clauses, code blocks, and links.
- Normalize duplicate blank lines and record file path plus heading as source location.
- For long documents, create a heading index and extract requirement-bearing sections before summarizing.

## DOCX

- Extract paragraphs, headings, tables, headers, footers, comments if readable, and embedded relationship targets when available.
- Preserve table rows as Markdown tables or row lists and record table number or paragraph order.
- Record unsupported content such as tracked changes, embedded images, charts, SmartArt, macros, or scanned pages.
- If the DOCX is mostly screenshots or embedded PDFs, request OCR text or screenshots and mark confidence accordingly.

## PDF

- Extract title, table of contents, section headings, clause numbers, definitions, tables, captions, appendices, and page numbers.
- Preserve page number or section number for every extracted conclusion.
- Mark partial extraction explicitly.
- If text cannot be extracted, ask for OCR text, selectable text, screenshots, or a human summary.

## Spreadsheet Or Excel

- Process each worksheet separately.
- Preserve sheet name, header, row number, column name, merged-cell meaning, notes, and formula meaning.
- Convert requirement rows into source location, original text, system capability, priority, existing capability, gap, workload, and notes.
- For large sheets, first summarize workbook structure and then extract high-priority rows.
- For XLSX/XLSM, extract workbook metadata, sheet names, non-empty row counts, headers, merged-cell notes when possible, formulas as formula text, and requirement-bearing rows.
- For legacy `.xls`, request CSV/XLSX conversion unless a local parser is available; do not silently ignore it.

## Prototype

- Extract page list, page purpose, entry points, controls, fields, buttons, states, dialogs, validation rules, navigation, main flows, and error prompts.
- Use page name plus area or control name as the source location.
- If the source prototype cannot be parsed, ask for exported HTML, screenshots, page inventory, or a human page description.
- Do not infer invisible interactions from a screenshot.

## HTML Or Exported Prototype

- Extract visible text, headings, menu nodes, filters, form fields, table headers, buttons, tabs, dialogs, state labels, prompts, and navigation links.
- For Axure HTML exports, read root `*.html`, `data/document.js`, `plugins/sitemap/sitemap.js`, and `files/<page>/data.js` where present.
- Build a page inventory and a page-to-requirement mapping before writing final requirements.
- Mark text embedded only in images as missing unless OCR or manual screenshot review is performed.
- Use `references/html-prototype-analysis.md` for the full workflow.

## Image Or Screenshot

- Extract visible text, layout, form fields, buttons, states, error prompts, and obvious flow relationships.
- Use screenshot ID, visible title, or region as source location.
- Do not treat decorative visuals or unseen interactions as confirmed requirements.

## Archive Or Material Bundle

- First list files, file types, readability, priority, and processing status.
- Mark duplicate or conflicting versions.
- Put unopened files into material gaps and explain the impact.
