# Validation Checklist

Use this before final output.

- Source materials are listed with credibility, conversion method, coverage, and missing content.
- Preflight checks for Python version, bundled extractor availability, readable source paths, writable output paths, and unsupported material types were run before extraction.
- Markdown, text, DOCX, PDF, Excel/XLSX, HTML, prototype, screenshot, and archive inputs are either normalized or explicitly marked unsupported with impact.
- Axure HTML exports include a page inventory, visible text/control extraction, page data coverage, and missing hidden/image-only content.
- Every key requirement has a requirement ID, source evidence, source location, priority, data source, and acceptance point.
- Prototype-derived requirements map from page/control evidence to requirement IDs and do not rely on page names alone.
- Scope-in, scope-out, external responsibilities, and dependencies are explicit.
- Policies or standards are classified as mandatory, recommended, reference, or assumption.
- Existing, reusable, configurable, modified, new, and out-of-scope capabilities are distinguished.
- Major modules map to requirement IDs.
- Major flows include main path, exception path, state change, and verification path.
- Core data objects include source, destination, quality checks, and audit requirements.
- Interfaces and integrations include direction, method, payload summary, idempotency, error handling, and responsibility boundary.
- Risks include unresolved material gaps and assumptions.
- Tables are used for material indexes, page inventories, requirement lists, module mappings, risk lists, and requirement-to-design mappings when the output is a formal deliverable.
- No design item depends only on unreadable or unconverted material.
