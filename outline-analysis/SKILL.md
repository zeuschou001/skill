---
name: outline-analysis
description: Two-stage requirement analysis and high-level design workflow for turning raw business materials into reviewable concept design. Use when Codex is asked to analyze PRDs, meeting notes, policy standards, industry guides, spreadsheets, PDFs, prototypes, screenshots, benchmark tables, existing-system notes, or other source materials; when the user asks for requirement analysis, outline analysis, high-level design, 概要设计, 需求分析, 材料可读化, or one-shot design output.
---

# Outline Analysis

## Overview

Use this skill to produce structured design input and high-level design from incomplete or material-heavy business requirements. Always preserve traceability from source material to requirement to design.

This skill can also normalize common material files into reviewable design input. Supported inputs include Markdown or text notes, PDF, DOCX, XLSX/XLSM spreadsheets, HTML pages, Axure HTML prototype exports, screenshots, benchmark tables, archives, and mixed material directories.

## Workflow

1. Parse intent and scope.
   Identify whether the user wants material normalization only, requirement analysis only, high-level design only, or the full two-stage flow.
2. Run the required preflight check.
   Before reading or converting files, verify the local runtime and tools are usable for the requested materials: Python 3.10+, the bundled extractor script is present, source paths are readable, output paths are writable, and unsupported formats are known. Read `references/input-normalization.md` for the exact command and expected checks.
3. Normalize source materials.
   If inputs include PDFs, DOCX files, spreadsheets, Markdown, HTML prototypes, screenshots, images, archives, or other non-text files, first convert them into readable text, structured summaries, page/control indexes, or source indexes. Read `references/input-normalization.md` when needed. For exported HTML prototypes, especially Axure HTML exports, also read `references/html-prototype-analysis.md`.
4. Run requirement analysis.
   Extract facts before conclusions. Translate prototype pages, visible controls, fields, table headers, actions, states, and navigation evidence into candidate requirements with source locations. Produce the 8-section requirement-analysis output. Read `references/requirement-analysis-template.md` when the user needs a formal deliverable.
5. Check design readiness.
   Continue to high-level design only when business goals, roles, scope, key rules, data sources, external dependencies, risks, and unresolved questions are clear enough. If not, list the blocking gaps.
6. Run high-level design.
   Produce the 10-section high-level-design output. Map prototype-derived requirements to modules, page groups, flows, data objects, interfaces, permissions, and acceptance points. Read `references/high-level-design-template.md` when the user needs a formal deliverable.
7. Validate the result.
   Check that every major design item maps back to a requirement ID, source location, data object, interface or integration point, and acceptance point.

## Rules

- Keep the skill domain-neutral. Extract domain terms from the user's materials, but do not hard-code one industry's assumptions.
- Do not infer requirements from filenames, partial screenshots, unreadable PDFs, or unparsed prototypes.
- Distinguish facts, constraints, recommendations, assumptions, conflicts, and missing information.
- For policies, standards, and evaluation materials, distinguish mandatory constraints, recommended capabilities, reference guidance, and project assumptions.
- For benchmark tables and existing systems, distinguish reuse, configuration, modification, new build, and out-of-scope capabilities.
- For non-text materials, record conversion method, source location, coverage, missing content, and confidence.
- Do not run material extraction until the preflight check has passed. If a required tool, readable source, or writable output path is missing, report the blocker and the affected material types first.
- For HTML prototype exports, treat visible page evidence as confirmed only when it is present in HTML, page data, sitemap data, screenshots, or explicit notes. Do not invent hidden interactions from filenames alone.
- Prefer boring, reviewable outputs over broad summaries. Use headings and tables for material indexes, page inventories, requirement lists, module mappings, risks, and open questions. The output must support architecture review, test design, and later detailed design.

## Output Selection

- If the user asks for `需求分析`, `需求理解`, or `设计输入`, output only the requirement-analysis stage.
- If the user asks for `概要设计`, `模块设计`, `接口设计`, or `数据设计` and no structured requirements exist, run requirement analysis first, then high-level design.
- If the user provides a prior requirement-analysis result, use it as the primary source and do not re-analyze unrelated raw materials unless needed to resolve gaps.

## References

- `references/input-normalization.md`: how to convert Markdown, text, DOCX, PDFs, spreadsheets, HTML, prototypes, screenshots, images, and archives into analyzable input.
- `references/html-prototype-analysis.md`: how to extract exported HTML or Axure HTML prototypes and translate pages/controls into requirements and high-level design.
- `references/requirement-analysis-template.md`: formal 8-section requirement-analysis output.
- `references/high-level-design-template.md`: formal 10-section high-level-design output.
- `references/validation-checklist.md`: final quality gate before reporting completion.
