from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import zlib
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


SUPPORTED_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".csv",
    ".pdf",
    ".docx",
    ".xlsx",
    ".xlsm",
    ".html",
    ".htm",
}

INDEX_ONLY_SUFFIXES = {
    ".xls",
    ".rp",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
}

AXURE_RUNTIME_HTML = {
    "index.html",
    "start.html",
    "start_with_pages.html",
    "start_c_1.html",
    "expand.html",
    "reload.html",
    "other.html",
}

MIN_PYTHON = (3, 10)


@dataclass
class ExtractionResult:
    material_id: str
    source: Path
    material_type: str
    output: Path | None
    meta: dict[str, object]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0
        self._hidden_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        style = attrs_dict.get("style", "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            self._hidden_depth += 1
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        if tag in {"p", "div", "br", "tr", "li", "section", "article", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if self._hidden_depth and tag in {"div", "span", "p", "td", "tr"}:
            self._hidden_depth -= 1
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._skip_depth or self._hidden_depth:
            return
        if data.strip():
            self.text_parts.append(data)


def decode_pdf_stream(body: bytes) -> bytes:
    if b"stream" not in body:
        return b""
    stream = body.split(b"stream", 1)[1].split(b"endstream", 1)[0]
    stream = stream.strip(b"\r\n")
    if b"/FlateDecode" in body:
        try:
            return zlib.decompress(stream)
        except zlib.error:
            return b""
    return stream


def read_pdf_objects(path: Path) -> dict[int, bytes]:
    data = path.read_bytes()
    objects: dict[int, bytes] = {}
    for match in re.finditer(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", data, re.S):
        objects[int(match.group(1))] = match.group(3)
    return objects


def parse_unicode_hex(value: str) -> str:
    raw = bytes.fromhex(value)
    if not raw:
        return ""
    if len(raw) % 2 == 0:
        try:
            return raw.decode("utf-16-be")
        except UnicodeDecodeError:
            pass
    return raw.decode("latin1", "ignore")


def parse_cmap(stream: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    mode = ""
    for raw_line in stream.splitlines():
        line = raw_line.strip()
        if line.endswith("beginbfchar"):
            mode = "char"
            continue
        if line == "endbfchar":
            mode = ""
            continue
        if line.endswith("beginbfrange"):
            mode = "range"
            continue
        if line == "endbfrange":
            mode = ""
            continue
        if mode == "char":
            match = re.fullmatch(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", line)
            if match:
                mapping[match.group(1).upper()] = parse_unicode_hex(match.group(2))
        elif mode == "range":
            array_match = re.fullmatch(
                r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>\s+\[(.*?)\]", line
            )
            if array_match:
                code = int(array_match.group(1), 16)
                width = len(array_match.group(1))
                for dst in re.findall(r"<([0-9A-Fa-f]+)>", array_match.group(3)):
                    mapping[f"{code:0{width}X}"] = parse_unicode_hex(dst)
                    code += 1
                continue
            range_match = re.fullmatch(
                r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", line
            )
            if range_match:
                start_i = int(range_match.group(1), 16)
                end_i = int(range_match.group(2), 16)
                dst_i = int(range_match.group(3), 16)
                width = len(range_match.group(1))
                for offset, code in enumerate(range(start_i, end_i + 1)):
                    mapping[f"{code:0{width}X}"] = chr(dst_i + offset)
    return mapping


def parse_literal_string(text: str, pos: int) -> tuple[str, int]:
    assert text[pos] == "("
    pos += 1
    depth = 1
    result: list[str] = []
    while pos < len(text) and depth:
        ch = text[pos]
        if ch == "\\":
            if pos + 1 < len(text):
                nxt = text[pos + 1]
                escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}
                result.append(escapes.get(nxt, nxt))
                pos += 2
                continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                pos += 1
                break
        result.append(ch)
        pos += 1
    return "".join(result), pos


def decode_text_token(token: str, font_map: dict[str, str]) -> str:
    if token.startswith("<") and token.endswith(">"):
        hex_value = re.sub(r"\s+", "", token[1:-1]).upper()
        if len(hex_value) % 4 == 0:
            chars = [font_map.get(hex_value[i : i + 4], "") for i in range(0, len(hex_value), 4)]
            decoded = "".join(chars)
            if decoded:
                return decoded
        return bytes.fromhex(hex_value).decode("latin1", "ignore")
    if font_map:
        raw = token.encode("latin1", "ignore")
        decoded_parts: list[str] = []
        for step in (2, 1):
            parts = []
            for idx in range(0, len(raw), step):
                key = raw[idx : idx + step].hex().upper()
                parts.append(font_map.get(key, ""))
            candidate = "".join(parts)
            if candidate and len(candidate) >= max(1, len(raw) // max(step, 1) // 2):
                decoded_parts.append(candidate)
        if decoded_parts:
            return max(decoded_parts, key=len)
    return token


def extract_pdf_text(path: Path) -> tuple[str, dict[str, object]]:
    objects = read_pdf_objects(path)
    decoded_streams = {obj_id: decode_pdf_stream(body) for obj_id, body in objects.items()}
    to_unicode: dict[int, dict[str, str]] = {}
    for obj_id, body in objects.items():
        if b"/ToUnicode" in body:
            match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
            if match:
                cmap_obj = int(match.group(1))
                cmap_text = decoded_streams.get(cmap_obj, b"").decode("latin1", "ignore")
                to_unicode[obj_id] = parse_cmap(cmap_text)

    pages: list[tuple[int, str]] = []
    page_objs = [
        (obj_id, body)
        for obj_id, body in objects.items()
        if re.search(rb"/Type\s*/Page\b", body) and not re.search(rb"/Type\s*/Pages\b", body)
    ]
    for page_no, (_obj_id, body) in enumerate(page_objs, start=1):
        fonts: dict[str, dict[str, str]] = {}
        font_section = re.search(rb"/Font\s*<<(.*?)>>", body, re.S)
        if font_section:
            for name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", font_section.group(1)):
                fonts[name.decode("latin1")] = to_unicode.get(int(ref), {})

        contents: list[int] = []
        array_match = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
        if array_match:
            contents = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", array_match.group(1))]
        else:
            single_match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", body)
            if single_match:
                contents = [int(single_match.group(1))]

        page_text_parts: list[str] = []
        for content_id in contents:
            content = decoded_streams.get(content_id, b"").decode("latin1", "ignore")
            current_font: dict[str, str] = {}
            idx = 0
            while idx < len(content):
                font_match = re.match(r"/(\w+)\s+[-.\d]+\s+Tf", content[idx:])
                if font_match:
                    current_font = fonts.get(font_match.group(1), {})
                    idx += font_match.end()
                    continue
                ch = content[idx]
                if ch == "<":
                    end = content.find(">", idx)
                    if end != -1:
                        token = content[idx : end + 1]
                        after = content[end + 1 : end + 8]
                        if re.search(r"\bTj\b", after):
                            page_text_parts.append(decode_text_token(token, current_font))
                        idx = end + 1
                        continue
                if ch == "(":
                    token, idx = parse_literal_string(content, idx)
                    after = content[idx : idx + 8]
                    if re.search(r"\bTj\b", after):
                        page_text_parts.append(decode_text_token(token, current_font))
                    continue
                if ch == "[":
                    end = content.find("]", idx)
                    if end != -1 and re.search(r"\bTJ\b", content[end + 1 : end + 8]):
                        array = content[idx : end + 1]
                        for token in re.findall(r"<[0-9A-Fa-f\s]+>|\((?:\\.|[^\\)])*\)", array):
                            if token.startswith("("):
                                value, _ = parse_literal_string(token, 0)
                                page_text_parts.append(decode_text_token(value, current_font))
                            else:
                                page_text_parts.append(decode_text_token(token, current_font))
                        idx = end + 1
                        continue
                if content.startswith("ET", idx) or content.startswith(" T*", idx):
                    page_text_parts.append("\n")
                idx += 1
        page_text = "".join(page_text_parts)
        page_text = re.sub(r"[ \t]+", " ", page_text)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text).strip()
        pages.append((page_no, page_text))

    combined = "\n\n".join(f"## Page {page_no}\n{text}" for page_no, text in pages)
    meta = {
        "pages": len(pages),
        "characters": sum(len(text) for _page_no, text in pages),
        "fonts_with_cmap": len(to_unicode),
        "empty_pages": [page_no for page_no, text in pages if not text],
    }
    return combined, meta


def cell_name_to_col(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref or "")
    if not letters:
        return 0
    value = 0
    for ch in letters.group(0):
        value = value * 26 + ord(ch) - ord("A") + 1
    return value


def parse_xlsx(path: Path) -> tuple[str, dict[str, object]]:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("main:si", ns):
                text = "".join(t.text or "" for t in si.findall(".//main:t", ns))
                shared.append(text)

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkgrel:Relationship", ns)
        }
        sheet_sections: list[str] = []
        sheet_stats = []
        for sheet in workbook.findall("main:sheets/main:sheet", ns):
            sheet_name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{ns['rel']}}}id"]
            target = rel_targets[rel_id]
            sheet_path = "xl/" + target.lstrip("/")
            root = ET.fromstring(zf.read(sheet_path))
            rows_out: list[list[str]] = []
            for row in root.findall("main:sheetData/main:row", ns):
                values: list[str] = []
                last_col = 0
                for cell in row.findall("main:c", ns):
                    col = cell_name_to_col(cell.attrib.get("r", ""))
                    while last_col + 1 < col:
                        values.append("")
                        last_col += 1
                    cell_type = cell.attrib.get("t")
                    value = ""
                    if cell_type == "inlineStr":
                        value = "".join(t.text or "" for t in cell.findall(".//main:t", ns))
                    else:
                        v = cell.find("main:v", ns)
                        if v is not None and v.text is not None:
                            value = v.text
                            if cell_type == "s" and value.isdigit():
                                idx = int(value)
                                value = shared[idx] if 0 <= idx < len(shared) else value
                    values.append(value)
                    last_col = col
                while values and not str(values[-1]).strip():
                    values.pop()
                if any(str(v).strip() for v in values):
                    rows_out.append(values)

            width = max((len(row) for row in rows_out), default=0)
            non_empty = sum(1 for row in rows_out for value in row if str(value).strip())
            sheet_stats.append(
                {
                    "name": sheet_name,
                    "rows": len(rows_out),
                    "columns": width,
                    "non_empty_cells": non_empty,
                }
            )
            lines = [f"## Sheet: {sheet_name}", f"- Rows: {len(rows_out)}", f"- Columns: {width}"]
            for row_no, values in enumerate(rows_out, start=1):
                cells = [str(v).replace("\n", " ").strip() for v in values]
                if not any(cells):
                    continue
                rendered = " | ".join(cells)
                if len(rendered) > 1200:
                    rendered = rendered[:1200] + "..."
                lines.append(f"- R{row_no}: {rendered}")
            sheet_sections.append("\n".join(lines))

    return "\n\n".join(sheet_sections), {"sheets": sheet_stats, "shared_strings": len(shared)}


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


def collapse_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</p\s*>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return collapse_text(fragment)


def unique_preserve_order(values: Iterable[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = collapse_text(str(raw))
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if limit is not None and len(result) >= limit:
            break
    return result


def md_escape(value: object) -> str:
    text = str(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def safe_stem(value: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value, flags=re.UNICODE)
    value = value.strip("-._")
    return value[:80] or "material"


def read_text(path: Path) -> str:
    return decode_bytes(path.read_bytes())


def extract_axure_widgets(source: str) -> list[dict[str, object]]:
    widgets: list[dict[str, object]] = []
    pattern = re.compile(
        r"<!--\s*(?P<comment>.*?)\s*-->\s*"
        r"<div\s+id=\"(?P<id>u\d+)\"\s+class=\"(?P<class>[^\"]*)\"(?P<attrs>[^>]*)>"
        r"(?P<body>.*?)(?=<!--\s*.*?\s*-->\s*<div\s+id=\"u\d+\"|\Z)",
        re.S,
    )
    for match in pattern.finditer(source):
        widget_id = match.group("id")
        text_match = re.search(
            rf"<div\s+id=\"{re.escape(widget_id)}_text\"[^>]*(?P<attrs>[^>]*)>"
            r"(?P<body>.*?)</div>",
            match.group("body"),
            re.S,
        )
        text = ""
        visible = True
        if text_match:
            text = strip_tags(text_match.group("body"))
            attrs = text_match.group("attrs").replace(" ", "").lower()
            visible = "display:none" not in attrs and "visibility:hidden" not in attrs
        classes = match.group("class")
        comment = collapse_text(match.group("comment"))
        widgets.append(
            {
                "id": widget_id,
                "comment": comment,
                "classes": classes,
                "text": text,
                "visible": visible,
                "kind": classify_widget(classes, comment, text),
            }
        )
    return widgets


def classify_widget(classes: str, comment: str, text: str) -> str:
    raw = f"{classes} {comment}".lower()
    if "text_field" in raw or "文本框" in raw:
        return "field"
    if "text_area" in raw:
        return "textarea"
    if "droplist" in raw or "combo" in raw or "下拉" in raw:
        return "select"
    if "checkbox" in raw or "复选" in raw:
        return "checkbox"
    if "radio" in raw or "单选" in raw:
        return "radio"
    if "primary_button" in raw or "link_button" in raw or "button" in raw or "按钮" in raw:
        return "button"
    if "table_cell" in raw or "单元格" in raw:
        return "table_cell"
    if text:
        return "label"
    return "container"


def extract_html(path: Path) -> tuple[str, dict[str, object]]:
    source = read_text(path)
    parser = VisibleTextParser()
    parser.feed(source)
    title = collapse_text("".join(parser.title_parts)) or path.stem
    visible_text = unique_preserve_order(collapse_text("".join(parser.text_parts)).splitlines())
    widgets = extract_axure_widgets(source)
    visible_widgets = [w for w in widgets if w["visible"] and w["text"]]
    hidden_widgets = [w for w in widgets if not w["visible"] and w["text"]]
    action_widgets = [
        w
        for w in widgets
        if w["kind"] in {"field", "textarea", "select", "checkbox", "radio", "button", "table_cell"}
        and w["text"]
    ]
    lines = [
        f"# HTML Extraction: {title}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source | `{path}` |",
        f"| Visible text count | {len(visible_text)} |",
        f"| Axure widget count | {len(widgets)} |",
        f"| Action/field candidate count | {len(action_widgets)} |",
        "",
        "## Visible Text",
        "",
    ]
    lines.extend(f"- {text}" for text in visible_text[:300])
    if action_widgets:
        lines.extend(["", "## Field And Action Candidates", ""])
        lines.append("| Widget ID | Kind | Label/Text | Source |")
        lines.append("|---|---|---|---|")
        for widget in action_widgets[:200]:
            lines.append(
                "| {id} | {kind} | {text} | {source} |".format(
                    id=md_escape(widget["id"]),
                    kind=md_escape(widget["kind"]),
                    text=md_escape(widget["text"]),
                    source=md_escape(path.name),
                )
            )
    if hidden_widgets:
        lines.extend(["", "## Hidden Text Or States", ""])
        lines.extend(f"- {md_escape(w['text'])}" for w in hidden_widgets[:100])
    meta = {
        "title": title,
        "visible_text_count": len(visible_text),
        "widget_count": len(widgets),
        "action_widget_count": len(action_widgets),
        "hidden_text_count": len(hidden_widgets),
        "links": unique_preserve_order(parser.links, limit=100),
        "visible_text_sample": visible_text[:30],
        "action_widget_sample": [
            {"id": w["id"], "kind": w["kind"], "text": w["text"]} for w in action_widgets[:30]
        ],
    }
    return "\n".join(lines).rstrip() + "\n", meta


def js_string_literals(source: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r'"((?:\\.|[^"\\]){1,300})"', source):
        value = match.group(1).replace(r"\"", '"').replace(r"\n", "\n")
        value = html.unescape(value)
        value = re.sub(r"[^<\n]*font-family:[^>]*>", "", value)
        value = re.sub(r'^["\']?>+', "", value)
        if "<" in value and ">" in value:
            value = strip_tags(value)
        value = collapse_text(value)
        if re.search(r"[\u4e00-\u9fffA-Za-z]", value):
            values.append(value)
    return unique_preserve_order(values, limit=500)


def extract_interaction_hints(path: Path) -> list[str]:
    if not path.exists():
        return []
    source = read_text(path)
    candidates = js_string_literals(source)
    keywords = (
        "Click",
        "Mouse",
        "Focus",
        "LostFocus",
        "显示",
        "隐藏",
        "设置",
        "打开",
        "链接",
        "跳转",
        "选中",
        "校验",
        "提示",
        ".html",
    )
    return [item for item in candidates if any(keyword in item for keyword in keywords)][:80]


def is_axure_export(path: Path) -> bool:
    return path.is_dir() and (path / "data" / "document.js").exists() and any(path.glob("*.html"))


def find_axure_exports(root: Path) -> list[Path]:
    if root.is_file():
        return []
    exports: list[Path] = []
    for directory in [root, *[p for p in root.rglob("*") if p.is_dir()]]:
        if is_axure_export(directory) and not any(directory != existing and is_under(directory, existing) for existing in exports):
            exports.append(directory)
    return exports


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def prototype_pages(root: Path) -> list[Path]:
    pages = []
    for path in sorted(root.glob("*.html"), key=lambda item: item.name):
        if path.name.lower() in AXURE_RUNTIME_HTML:
            continue
        pages.append(path)
    return pages


def read_axure_document_hints(root: Path) -> tuple[str, list[str]]:
    document_js = root / "data" / "document.js"
    if not document_js.exists():
        return root.name, []
    document_source = read_text(document_js)
    document_urls = unique_preserve_order(re.findall(r'"([^"]+\.html)"', document_source), limit=300)
    quoted = unique_preserve_order(re.findall(r'"([\u4e00-\u9fff][^"]{1,40})"', document_source), limit=20)
    project_hint = quoted[0] if quoted else root.name
    return project_hint, document_urls


def extract_axure_prototype(root: Path) -> tuple[str, dict[str, object]]:
    project_hint, document_urls = read_axure_document_hints(root)
    unordered_pages = prototype_pages(root)
    pages_by_name = {page.name: page for page in unordered_pages}
    ordered_pages = [pages_by_name[url] for url in document_urls if url in pages_by_name]
    ordered_names = {page.name for page in ordered_pages}
    pages = ordered_pages + [page for page in unordered_pages if page.name not in ordered_names]
    page_rows: list[dict[str, object]] = []
    details: list[str] = []
    for index, page in enumerate(pages, start=1):
        _text, meta = extract_html(page)
        data_js = root / "files" / page.stem / "data.js"
        interactions = extract_interaction_hints(data_js)
        row = {
            "index": index,
            "page": meta["title"],
            "html": page.relative_to(root).as_posix(),
            "data_js": data_js.relative_to(root).as_posix() if data_js.exists() else "",
            "visible_text_count": meta["visible_text_count"],
            "action_widget_count": meta["action_widget_count"],
            "interaction_hint_count": len(interactions),
            "key_labels": meta["visible_text_sample"][:12],
            "action_widgets": meta["action_widget_sample"][:12],
            "interaction_hints": interactions[:12],
        }
        page_rows.append(row)
        details.extend(
            [
                "",
                f"### {index}. {row['page']}",
                "",
                f"- Source: `{row['html']}`",
                f"- Page data: `{row['data_js'] or 'not found'}`",
                f"- Visible text count: {row['visible_text_count']}",
                f"- Field/action candidate count: {row['action_widget_count']}",
                "",
                "Key visible text:",
                "",
            ]
        )
        details.extend(f"- {label}" for label in row["key_labels"])
        if row["action_widgets"]:
            details.extend(["", "Field/action candidates:", ""])
            details.extend(
                f"- {item['kind']}: {item['text']}" for item in row["action_widgets"] if item["text"]
            )
        if interactions:
            details.extend(["", "Interaction hints:", ""])
            details.extend(f"- {hint}" for hint in interactions[:12])

    lines = [
        f"# HTML Prototype Extraction: {project_hint}",
        "",
        "## Conversion Record",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source path | `{root}` |",
        "| Export type | Axure/HTML prototype export |",
        "| Conversion method | Root HTML visible text, Axure widget block scan, page `data.js` interaction string scan, `data/document.js` URL scan |",
        f"| Page count | {len(page_rows)} |",
        f"| Document URL hints | {len(document_urls)} |",
        "| Missing content | Text embedded only in images, canvas rendering, unreadable minified runtime state, and interactions not expressed as strings |",
        "| Confidence | Medium-high for page inventory and visible labels; medium for hidden interactions |",
        "",
        "## Page Inventory",
        "",
        "| # | Page | HTML | Page Data | Visible Text | Field/Action Candidates | Interaction Hints | Key Labels |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in page_rows:
        labels = "；".join(str(label) for label in row["key_labels"][:6])
        lines.append(
            "| {index} | {page} | `{html}` | `{data_js}` | {visible} | {actions} | {hints} | {labels} |".format(
                index=row["index"],
                page=md_escape(row["page"]),
                html=md_escape(row["html"]),
                data_js=md_escape(row["data_js"] or "not found"),
                visible=row["visible_text_count"],
                actions=row["action_widget_count"],
                hints=row["interaction_hint_count"],
                labels=md_escape(labels),
            )
        )
    lines.extend(
        [
            "",
            "## Page To Requirement Translation Input",
            "",
            "| Page | Prototype Evidence | Candidate Requirement Use | Source Location | Confidence |",
            "|---|---|---|---|---|",
        ]
    )
    for row in page_rows:
        labels = "；".join(str(label) for label in row["key_labels"][:8])
        lines.append(
            "| {page} | {labels} | Use as functional capability, query/output fields, operation permissions, flow or data-object evidence after business-rule confirmation | {source} | Medium |".format(
                page=md_escape(row["page"]),
                labels=md_escape(labels),
                source=md_escape(row["html"]),
            )
        )
    lines.extend(["", "## Page Details", *details])
    meta = {
        "project_hint": project_hint,
        "page_count": len(page_rows),
        "document_url_hints": document_urls,
        "pages": page_rows,
    }
    return "\n".join(lines).rstrip() + "\n", meta


def extract_docx(path: Path) -> tuple[str, dict[str, object]]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    sections: list[str] = [f"# DOCX Extraction: {path.stem}", "", f"- Source: `{path}`", ""]
    paragraph_count = 0
    table_count = 0
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "word/document.xml" not in names:
            raise ValueError("DOCX does not contain word/document.xml")
        root = ET.fromstring(zf.read("word/document.xml"))
        body = root.find("w:body", ns)
        if body is not None:
            for child in list(body):
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "p":
                    text = "".join(node.text or "" for node in child.findall(".//w:t", ns))
                    text = collapse_text(text)
                    if text:
                        paragraph_count += 1
                        sections.append(text)
                elif tag == "tbl":
                    table_count += 1
                    sections.extend(["", f"## Table {table_count}", ""])
                    for row in child.findall(".//w:tr", ns):
                        cells = []
                        for cell in row.findall("w:tc", ns):
                            cell_text = collapse_text(" ".join(node.text or "" for node in cell.findall(".//w:t", ns)))
                            cells.append(cell_text)
                        if cells:
                            sections.append("- " + " | ".join(cells))

        header_footer_count = 0
        for name in sorted(names):
            if re.match(r"word/(header|footer)\d+\.xml", name):
                header_footer_count += 1
                part = ET.fromstring(zf.read(name))
                text = collapse_text(" ".join(node.text or "" for node in part.findall(".//w:t", ns)))
                if text:
                    sections.extend(["", f"## {name}", "", text])

    meta = {
        "paragraphs": paragraph_count,
        "tables": table_count,
        "header_footer_parts": header_footer_count,
    }
    return "\n".join(sections).rstrip() + "\n", meta


def extract_plain_text(path: Path) -> tuple[str, dict[str, object]]:
    text = read_text(path)
    lines = [line.rstrip() for line in text.splitlines()]
    non_empty = [line for line in lines if line.strip()]
    if path.suffix.lower() in {".md", ".markdown"}:
        rendered = text
    else:
        rendered = f"# Text Extraction: {path.stem}\n\n- Source: `{path}`\n\n" + "\n".join(lines)
    return rendered.rstrip() + "\n", {"lines": len(lines), "non_empty_lines": len(non_empty), "characters": len(text)}


def extract_file(path: Path) -> tuple[str, str, dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt", ".csv"}:
        text, meta = extract_plain_text(path)
        return "Markdown/Text", text, meta
    if suffix in {".html", ".htm"}:
        text, meta = extract_html(path)
        return "HTML", text, meta
    if suffix == ".docx":
        text, meta = extract_docx(path)
        return "DOCX", text, meta
    if suffix == ".pdf":
        text, meta = extract_pdf_text(path)
        return "PDF", text, meta
    if suffix in {".xlsx", ".xlsm"}:
        text, meta = parse_xlsx(path)
        return "Excel", text, meta
    raise ValueError(f"Unsupported file type: {suffix}")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def output_path(out_dir: Path, material_id: str, source: Path, suffix: str = ".md") -> Path:
    return out_dir / f"{material_id}-{safe_stem(source.stem)}{suffix}"


def collect_files(source: Path, axure_roots: list[Path]) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() in SUPPORTED_SUFFIXES | INDEX_ONLY_SUFFIXES else []
    files: list[Path] = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        if any(is_under(path, root) for root in axure_roots):
            continue
        if path.suffix.lower() in SUPPORTED_SUFFIXES | INDEX_ONLY_SUFFIXES:
            files.append(path)
    return sorted(files)


def nearest_existing_parent(path: Path) -> Path | None:
    candidate = path.expanduser()
    if candidate.exists() and candidate.is_file():
        return candidate.parent
    if candidate.exists() and candidate.is_dir():
        return candidate
    candidate = candidate.parent
    while not candidate.exists():
        if candidate.parent == candidate:
            return None
        candidate = candidate.parent
    return candidate if candidate.is_dir() else candidate.parent


def readable_path(path: Path) -> bool:
    return path.exists() and os.access(path, os.R_OK)


def writable_output_parent(path: Path) -> tuple[bool, str | None]:
    parent = nearest_existing_parent(path)
    if parent is None:
        return False, None
    return os.access(parent, os.W_OK | os.X_OK), str(parent)


def preflight_check(source: Path | None, out_dir: Path | None) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info < MIN_PYTHON:
        errors.append(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required, current version is {python_version}.")

    script_path = Path(__file__).resolve()
    if not script_path.exists():
        errors.append(f"Bundled extractor script is missing: {script_path}")

    source_status: dict[str, object] = {"provided": source is not None}
    if source is None:
        warnings.append("No --source path provided; only runtime capability was checked.")
    else:
        checked_source = source.expanduser()
        source_status.update(
            {
                "path": str(checked_source),
                "exists": checked_source.exists(),
                "readable": readable_path(checked_source),
                "kind": "directory" if checked_source.is_dir() else "file" if checked_source.is_file() else "missing",
            }
        )
        if not checked_source.exists():
            errors.append(f"Source path does not exist: {checked_source}")
        elif not readable_path(checked_source):
            errors.append(f"Source path is not readable: {checked_source}")

    output_status: dict[str, object] = {"provided": out_dir is not None}
    if out_dir is None:
        warnings.append("No --out path provided; output writability was not checked.")
    else:
        checked_out = out_dir.expanduser()
        writable, parent = writable_output_parent(checked_out)
        output_status.update({"path": str(checked_out), "nearest_existing_parent": parent, "writable": writable})
        if not writable:
            errors.append(f"Output path is not writable or has no writable existing parent: {checked_out}")

    capabilities = {
        "parsed": sorted(SUPPORTED_SUFFIXES),
        "indexed_only": sorted(INDEX_ONLY_SUFFIXES),
        "not_included": [
            "OCR for scanned PDFs or screenshots",
            "legacy .xls binary parsing",
            "PowerPoint slide text extraction",
            "Axure .rp binary parsing",
            "macro, chart, SmartArt, and image text extraction",
        ],
        "external_python_packages": "none required",
    }

    return {
        "ok": not errors,
        "python": {"version": python_version, "minimum": f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}", "ok": sys.version_info >= MIN_PYTHON},
        "script": str(script_path),
        "source": source_status,
        "output": output_status,
        "capabilities": capabilities,
        "warnings": warnings,
        "errors": errors,
    }


def normalize_materials(
    source: Path, out_dir: Path, material_prefix: str, start_index: int = 1
) -> list[ExtractionResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[ExtractionResult] = []
    counter = start_index

    axure_roots = find_axure_exports(source) if source.is_dir() else []
    for root in axure_roots:
        material_id = f"{material_prefix}{counter:02d}"
        counter += 1
        text, meta = extract_axure_prototype(root)
        out_path = output_path(out_dir, material_id, root)
        write(out_path, text)
        write(out_path.with_suffix(".json"), json.dumps(meta, ensure_ascii=False, indent=2))
        results.append(ExtractionResult(material_id, root, "Axure HTML Prototype", out_path, meta))

    for path in collect_files(source, axure_roots):
        material_id = f"{material_prefix}{counter:02d}"
        counter += 1
        out_path = output_path(out_dir, material_id, path)
        try:
            material_type, text, meta = extract_file(path)
            write(out_path, text)
        except Exception as exc:  # Keep one bad material from blocking the index.
            material_type = "Unsupported or failed"
            meta = {"error": str(exc), "suffix": path.suffix.lower()}
            out_path = None
        results.append(ExtractionResult(material_id, path, material_type, out_path, meta))

    return results


def write_index(results: list[ExtractionResult], out_dir: Path) -> None:
    index = [
        {
            "id": result.material_id,
            "source": str(result.source),
            "type": result.material_type,
            "output": str(result.output) if result.output else None,
            "meta": result.meta,
        }
        for result in results
    ]
    write(out_dir / "material-index.json", json.dumps(index, ensure_ascii=False, indent=2))

    lines = [
        "# Material Extraction Index",
        "",
        "| Material ID | Type | Source | Output | Coverage / Status |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        coverage = result.meta.get("page_count") or result.meta.get("pages") or result.meta.get("sheets")
        if isinstance(coverage, list):
            coverage_text = f"{len(coverage)} items"
        elif coverage:
            coverage_text = str(coverage)
        else:
            coverage_text = str(result.meta.get("error") or result.meta.get("characters") or "extracted")
        lines.append(
            "| {id} | {typ} | `{source}` | `{output}` | {coverage} |".format(
                id=result.material_id,
                typ=md_escape(result.material_type),
                source=md_escape(result.source),
                output=md_escape(result.output or ""),
                coverage=md_escape(coverage_text),
            )
        )
    write(out_dir / "material-index.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize mixed outline-analysis materials, including DOCX, PDF, Markdown, Excel, HTML, and Axure HTML exports."
    )
    parser.add_argument("--check", "--preflight", action="store_true", help="Run environment and path preflight checks only.")
    parser.add_argument("--source", type=Path, help="Source file or directory to normalize.")
    parser.add_argument("--out", type=Path, help="Output directory for normalized Markdown/JSON.")
    parser.add_argument("--material-prefix", default="M", help="Material ID prefix, default: M.")
    parser.add_argument("--start-index", default=1, type=int, help="First numeric material index, default: 1.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        report = preflight_check(args.source, args.out)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 2
    if args.source is None:
        raise SystemExit("--source is required unless --check is used")
    if args.out is None:
        raise SystemExit("--out is required unless --check is used")
    source = args.source.expanduser()
    if not source.exists():
        raise FileNotFoundError(source)
    results = normalize_materials(source, args.out, args.material_prefix, args.start_index)
    write_index(results, args.out)
    print(json.dumps({"materials": len(results), "out": str(args.out)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
