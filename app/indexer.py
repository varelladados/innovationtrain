"""Indexer — varre a raiz da plataforma ativa, classifica cada arquivo
pertinente e produz um índice JSON.

Até o Trecho 3 a raiz era `PROJECT_DIR.parent` e os nomes da plataforma estavam
escritos aqui como constante. Agora tudo que é nome de plataforma sai de
`config.atual()` — e é lido **na hora da chamada**, para que trocar de
plataforma não exija reiniciar o servidor. Ver `metodo/taxonomia.md`.
"""
import json
import os
import re
import time
from pathlib import Path

import config

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
CACHE_DIR = PROJECT_DIR / "cache"
INDEX_PATH = CACHE_DIR / "index.json"

TEXT_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".py"}
MAX_TEXT_READ_BYTES = 500_000

STUB_MAX_BYTES = 220
STUB_MAX_LINES = 4

HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def raiz() -> Path:
    return config.atual().raiz


def sanity_check():
    cfg = config.atual()
    if not cfg.ok():
        raise RuntimeError(
            f"{cfg.marcador} não encontrado em {cfg.raiz} — a raiz resolvida não "
            "parece ser uma plataforma, abortando indexação em vez de varrer a "
            "árvore errada."
        )


#: Sempre excluídos, em qualquer nível e em qualquer plataforma — não são
#: conteúdo de ninguém.
EXCLUDE_DIR_NAMES = {".git", "node_modules", "__pycache__", ".claude"}


def is_excluded(rel_posix: str) -> bool:
    for pref in config.atual().excluir:
        if rel_posix == pref or rel_posix.startswith(pref + "/"):
            return True
    parts = rel_posix.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    return False


def classify(rel_posix: str, name: str, suffix: str) -> str:
    cfg = config.atual()

    indice = cfg.arquivo_rel("indice")
    if indice and (rel_posix == indice or name == Path(indice).name):
        return "orquestra"

    trilha = cfg.get("trilha")
    if trilha and rel_posix == str(trilha).replace("\\", "/"):
        return "trilha"

    prefixo = cfg.get("indice_prefixo")
    if prefixo and name.startswith(prefixo):
        return "orquestra"

    if name == "CLAUDE.md":
        return "orquestra"
    if name.startswith("backlog-") or rel_posix.endswith("/docs/BACKLOG.md") or name == "BACKLOG.md":
        return "backlog"
    if name.startswith("readme-"):
        return "readme"
    if name.startswith("changelog-"):
        return "changelog"

    registro = cfg.arquivo_rel("registro")
    if registro and rel_posix == registro:
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
    prefixo = config.atual().get("indice_prefixo")
    if prefixo and stem.startswith(prefixo):
        stem = stem[len(prefixo):]
    if stem.startswith("backlog-") or stem.startswith("readme-") or stem.startswith("changelog-"):
        stem = stem.split("-", 1)[1]
    return Path(stem).stem


def is_processed(name: str, frontmatter: dict):
    chave = config.atual().fm("processado")
    if chave in frontmatter:
        return True, frontmatter[chave]
    if config.atual().id_re.match(name):
        return True, name
    return False, None


def lifecycle_stage(rel_posix: str):
    """Estágio de triagem física dentro de um estágio da taxonomia — ortogonal
    à etapa. Uma plataforma pode declarar quantas quiser em `ciclo_vida`; na
    taxonomia padrão é só o `_historico/` de cada estágio."""
    cfg = config.atual()
    nomes = set(cfg.get("ciclo_vida") or [cfg.historico])
    for p in rel_posix.split("/")[:-1]:
        if p in nomes:
            return p.lstrip("._")
    return None


def is_stub(size_bytes: int, body: str) -> bool:
    if size_bytes > STUB_MAX_BYTES:
        return False
    nonblank = [ln for ln in body.splitlines() if ln.strip()]
    return len(nonblank) <= STUB_MAX_LINES


def pastas_de_projeto():
    """Nomes das pastas que são projeto, na pasta de projetos da plataforma.

    Com prefixo declarado (legado), só as que casam — inclusive as que ainda
    não têm `CLAUDE.md`, que é justamente o órfão que o índice existe para
    pegar. Sem prefixo (taxonomia nova), toda pasta dentro da pasta de
    projetos é um projeto, menos o `_historico/`.
    """
    cfg = config.atual()
    base = cfg.projetos_dir
    prefixo_re = cfg.projetos_prefixo_re
    achadas = set()
    try:
        itens = list(base.iterdir())
    except OSError:
        return achadas
    for item in itens:
        if not item.is_dir():
            continue
        if item.name in EXCLUDE_DIR_NAMES or item.name == cfg.historico:
            continue
        if prefixo_re is None or prefixo_re.match(item.name):
            achadas.add(item.name)
    return achadas


def build_index():
    sanity_check()
    cfg = config.atual()
    root = cfg.raiz
    entries = []
    text_cache = {}

    project_like_folders = pastas_de_projeto()

    # Órfão = pasta de projeto que o índice canônico não lista. Sem índice
    # canônico declarado não existe "estar fora dele" — ninguém é órfão.
    listados = set()
    indice_projetos = cfg.caminho("indice_projetos")
    if indice_projetos and indice_projetos.exists():
        content = read_text(indice_projetos) or ""
        for m in re.finditer(r"\[([A-Za-z0-9_.\-À-ÿ]+)\]\(\.\./([A-Za-z0-9_.\-À-ÿ]+)/CLAUDE\.md\)", content):
            listados.add(m.group(2))
        orphan_folders = project_like_folders - listados
    else:
        orphan_folders = set()

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
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
    import sys

    config.iniciar(sys.argv[1:])
    entries, _ = build_index()
    payload = save_index(entries)
    print(f"Indexed {payload['count']} files -> {INDEX_PATH}")
    from collections import Counter
    counts = Counter(e["type"] for e in entries)
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
