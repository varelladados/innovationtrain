"""Indexer — varre C:\\Plataforma, classifica cada arquivo pertinente e produz um
índice JSON. Ver CLAUDE.md para a convenção de nomes/tipos (fonte de verdade).
"""
import json
import os
import re
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
ROOT = PROJECT_DIR.parent  # C:\Plataforma
CACHE_DIR = PROJECT_DIR / "cache"
INDEX_PATH = CACHE_DIR / "index.json"

TEXT_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".py"}
MAX_TEXT_READ_BYTES = 500_000

EXCLUDE_PREFIXES = (
    ".git",
    "node_modules",
    "__pycache__",
    ".claude",  # config/skills do próprio Claude Code, não é conteúdo do usuário
    ".Biblioteca/Takeout_Google",
    "outro-app-local/build",
    "outro-app-local/dist",
    "pasta-de-rascunho/subpasta",
    "PRJ-Estacao",
)

STUB_MAX_BYTES = 220
STUB_MAX_LINES = 4

PROCESSED_FRONTMATTER_RE = re.compile(r"^registro-id:\s*(\S+)", re.MULTILINE)
PROCESSED_FILENAME_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}-SB[CIZ](-[A-Z]{3})?-\d+-")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def sanity_check():
    if not (ROOT / "_indice.md").exists():
        raise RuntimeError(
            f"_indice.md não encontrado em {ROOT} — raiz resolvida parece errada, "
            "abortando indexação em vez de varrer a árvore errada."
        )


EXCLUDE_DIR_NAMES = {".git", "node_modules", "__pycache__", ".claude"}  # .claude em qualquer nível (CLAUDE.md, portfolio.SKIP_DIRS)


def is_excluded(rel_posix: str) -> bool:
    for pref in EXCLUDE_PREFIXES:
        if rel_posix == pref or rel_posix.startswith(pref + "/"):
            return True
    parts = rel_posix.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    return False


def classify(rel_posix: str, name: str, suffix: str) -> str:
    if rel_posix == "_indice.md":
        return "orquestra"
    if rel_posix == "_metodo/trilha.md":
        return "trilha"
    if name in ("_indice.md", "o-captura.md", "o-ideias.md", "_indice-projetos.md",
                "o-plataformatools.md", "o-framework-metodo.md", "o-biblioteca.md",
                "o-metaclaude.md") or name.startswith("o-"):
        return "orquestra"
    if name == "CLAUDE.md":
        return "orquestra"
    if name.startswith("backlog-") or rel_posix.endswith("/docs/BACKLOG.md") or name == "BACKLOG.md":
        return "backlog"
    if name.startswith("readme-"):
        return "readme"
    if name.startswith("changelog-"):
        return "changelog"
    if rel_posix == "1-capturas/LOG/_log.md":
        return "log"
    if name == "SKILL.md":
        return "skill"
    if name == "glossario.md":
        return "glossary"
    if name == "doutrina.md":
        return "doctrine"
    if name == "chaves.md":
        return "linkmap"
    if name == "_leia-me.md":
        return "readme"
    if suffix == ".py":
        return "script"
    if suffix in (".html", ".htm"):
        return "dashboard-html"
    if suffix == ".md":
        return "other-markdown"
    return "other-pertinent"


def read_text(path: Path, limit=None):
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    if limit and len(data) > limit:
        return data[:limit]
    return data


def split_frontmatter(content: str):
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    raw = m.group(1)
    body = content[m.end():]
    fm = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, body


def extract_title(name: str, body: str) -> str:
    m = HEADING_RE.search(body)
    if m:
        return m.group(1).strip()
    stem = name
    if stem.startswith("o-"):
        stem = stem[2:]
    if stem.startswith("backlog-") or stem.startswith("readme-") or stem.startswith("changelog-"):
        stem = stem.split("-", 1)[1]
    return Path(stem).stem


def is_processed(name: str, frontmatter: dict):
    if "registro-id" in frontmatter:
        return True, frontmatter["registro-id"]
    m = PROCESSED_FILENAME_RE.match(name)
    if m:
        return True, name
    return False, None


LIFECYCLE_STAGES = {".entrada", ".pendente", ".historico"}


def lifecycle_stage(rel_posix: str):
    """Estágio de triagem física dentro de 1-capturas (convenção 2026-08-31),
    ortogonal à etapa Captura/Ideia/Projeto — ver o-captura.md."""
    parts = rel_posix.split("/")
    for p in parts[:-1]:
        if p in LIFECYCLE_STAGES:
            return p.lstrip(".")
    return None


def is_stub(size_bytes: int, body: str) -> bool:
    if size_bytes > STUB_MAX_BYTES:
        return False
    nonblank = [ln for ln in body.splitlines() if ln.strip()]
    return len(nonblank) <= STUB_MAX_LINES


def build_index():
    sanity_check()
    entries = []
    text_cache = {}

    # first pass: collect top-level project-prefixed folders (PJx-/PRx-),
    # regardless of whether they have a CLAUDE.md yet — a project folder
    # with NO CLAUDE.md at all (e.g. um-projeto) is exactly the kind
    # of orphan this flag exists to catch, not just ones missing from the list.
    PROJECT_PREFIX_RE = re.compile(r"^(PJ|PR)[A-Z]-")
    project_like_folders = set()
    for item in ROOT.iterdir():
        if item.is_dir() and PROJECT_PREFIX_RE.match(item.name):
            project_like_folders.add(item.name)

    projetos_listed = set()
    projetos_path = ROOT / "4-projetos" / "_indice-projetos.md"
    if projetos_path.exists():
        content = read_text(projetos_path) or ""
        for m in re.finditer(r"\[([A-Za-z0-9_.\-À-ÿ]+)\]\(\.\./([A-Za-z0-9_.\-À-ÿ]+)/CLAUDE\.md\)", content):
            projetos_listed.add(m.group(2))

    orphan_folders = project_like_folders - projetos_listed

    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        pruned = []
        for d in dirnames:
            candidate = f"{rel_dir}/{d}" if rel_dir else d
            if is_excluded(candidate):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        for fname in filenames:
            rel_path = f"{rel_dir}/{fname}" if rel_dir else fname
            if is_excluded(rel_path):
                continue
            suffix = Path(fname).suffix.lower()
            if suffix not in TEXT_EXTENSIONS:
                continue
            full = Path(dirpath) / fname
            try:
                stat = full.stat()
            except OSError:
                continue

            content = read_text(full, limit=MAX_TEXT_READ_BYTES)
            if content is None:
                continue

            frontmatter, body = split_frontmatter(content)
            file_type = classify(rel_path, fname, suffix)
            # heading '# ...' só faz sentido em markdown; num .py a primeira linha de
            # comentário na coluna 0 virava título ('-*- coding: utf-8 -*-', '----')
            title = extract_title(fname, body if suffix == ".md" else "")
            processed, processed_id = is_processed(fname, frontmatter)
            stub = is_stub(stat.st_size, body if suffix == ".md" else content)
            snippet = " ".join(body.split())[:220] if suffix == ".md" else " ".join(content.split())[:220]

            parent_folder = rel_dir
            top_folder = rel_path.split("/", 1)[0] if "/" in rel_path else ""
            orphaned = top_folder in orphan_folders
            stage = lifecycle_stage(rel_path)

            entry = {
                "path": rel_path,
                "type": file_type,
                "title": title,
                "size_bytes": stat.st_size,
                "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)),
                "parent_folder": parent_folder,
                "processed": processed,
                "processed_id": processed_id,
                "is_stub": stub,
                "snippet": snippet,
                "orphaned": orphaned,
                "lifecycle_stage": stage,
                "frontmatter": frontmatter,
            }
            entries.append(entry)
            text_cache[rel_path] = content

    entries.sort(key=lambda e: e["path"].lower())
    return entries, text_cache


def save_index(entries):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count": len(entries),
        "entries": entries,
    }
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


if __name__ == "__main__":
    entries, _ = build_index()
    payload = save_index(entries)
    print(f"Indexed {payload['count']} files -> {INDEX_PATH}")
    from collections import Counter
    counts = Counter(e["type"] for e in entries)
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
