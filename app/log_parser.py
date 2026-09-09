"""Parser dedicado das tabelas markdown do registro central da plataforma.
Extrai linhas estruturadas {id, data, etapa, local, resumo, link, arrow_target}
em vez de deixar o LOG renderizar como markdown genérico.
"""
import re

ROW_RE = re.compile(r"^\|(.+)\|\s*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
ARROW_RE = re.compile(r"→\s*[`\[]?([^\s`\]]+)")


def _split_cells(line: str):
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def _first_link(cell: str):
    m = LINK_RE.search(cell)
    if m:
        return m.group(2)
    return None


def parse_log_tables(content: str):
    lines = content.splitlines()
    rows = []
    current_section = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            current_section = line[3:].strip()
        if line.startswith("| ID ") or line.startswith("|ID"):
            header_cells = [c.lower() for c in _split_cells(line)]
            if i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|\s*$", lines[i + 1]):
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = _split_cells(lines[j])
                    if len(cells) == len(header_cells):
                        row = dict(zip(header_cells, cells))
                        etapa = row.get("etapa/tipo", "")
                        arrow_m = ARROW_RE.search(etapa)
                        arrow_target = arrow_m.group(1).strip("`[]") if arrow_m else None
                        link_cell = row.get("link", "")
                        link_m = LINK_RE.search(link_cell)
                        rows.append({
                            "section": current_section,
                            "id": row.get("id", ""),
                            "data": row.get("data", ""),
                            "etapa": etapa,
                            "arrow_target": arrow_target,
                            "local": row.get("local", ""),
                            "resumo": row.get("resumo", ""),
                            "link_text": link_m.group(1) if link_m else link_cell,
                            "link_href": link_m.group(2) if link_m else None,
                        })
                    j += 1
                i = j
                continue
        i += 1
    return rows
