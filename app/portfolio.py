"""Portfólio — inventário de tudo que "roda" em cada Projeto (GET /api/portfolio).

"Executável" no sentido amplo: link publicado na internet, repositório, .bat
que abre o app, .exe empacotado, servidor Python, protótipo HTML standalone,
design system, apresentação. Cada item ganha um `kind` (o que é) e um `estagio`
(estável / protótipo / rascunho) — o hub filtra por isso.

Fontes, em ordem de autoridade:
1. `portfolio.json` na raiz do projeto (curadoria manual, opcional):
   {"estavel": "https://…", "destaque": ["app.html"], "ocultar": ["x.html"],
    "estavel_local": ["app-local-campo-v1.1.html"], "tags": ["b2b"], "nota": "…"}
2. `4-projetos/_indice-projetos.md` (status e resumo canônicos)
3. `CLAUDE.md` do projeto (id, tipo) + URLs citadas em CLAUDE.md/readme-*/backlog-*
4. git do projeto (remote, último commit, nº de commits)
5. varredura da pasta (heurística por extensão/nome — ver classificar_arquivo)
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

import config
import indexer

SKIP_DIRS = {".git", "node_modules", "__pycache__", "cache", "backups", "build", ".claude", ".venv", "venv", "_setup"}
LAUNCHER_EXT = {".bat", ".cmd", ".ps1"}
BIN_EXT = {".exe"}
SERVER_NAMES = {"server.py", "main.py", "app.py"}
DOC_HINTS = ("manual", "apresentacao", "documentacao", "portfolio", "roteiro", "arquitetura",
             "proposta", "plano", "tutorial", "relatorio", "estudo", "analise")
DESIGN_HINTS = ("design-system", "identidade", "wireframe", "icone", "mockup")
DRAFT_HINTS = ("copia", "old", "backup", ".bak", "antigo", "-v0", "_v0", "teste")
NOAR_HOSTS = ("github.io", "vercel.app", "netlify.app", "onrender.com", "fly.dev", "railway.app",
              "pages.dev", "herokuapp.com", "claude.ai/code/artifact", "streamlit.app", "hf.space")
URL_RE = re.compile(r"https?://[^\s)>\"'`\]\\]+")
PROJETOS_ROW_RE = re.compile(
    r"^\|\s*\[([^\]]+)\]\(\.\./([^/]+)/CLAUDE\.md\)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*(.*?)\s*\|\s*$",
    re.MULTILINE)
MAX_EXECS_POR_PROJETO = 80


def _alt(valores):
    return "|".join(re.escape(v) for v in valores)


def _re_tipo():
    """Casa a sigla de tipo de projeto declarada pela plataforma."""
    tipos = config.atual().tipos
    return re.compile(r"\b(" + _alt(tipos) + r")\b") if tipos else None


def _re_id_tipo():
    """Casa o tipo dentro de um identificador (…-SBZ-DIG-…)."""
    cfg = config.atual()
    if not cfg.tipos:
        return None
    return re.compile(r"-(?:" + _alt(cfg.siglas) + r")-(" + _alt(cfg.tipos) + r")-")


def _pasta_pattern():
    """Trecho de regex que reconhece uma pasta de projeto dentro de um caminho.

    Com prefixo declarado (legado) é o próprio prefixo; sem ele, qualquer
    segmento serve — o resultado é filtrado depois contra as pastas reais.
    """
    bruto = (config.atual().get("projetos") or {}).get("prefixo_re")
    if not bruto:
        return r"[^/`]+"
    return bruto.lstrip("^") + r"[^/`]+" 


def _ler(p: Path, limit=200_000):
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _git(pasta: Path):
    info = {"url": None, "ultimo_commit": None, "commits": 0}
    if not (pasta / ".git").exists():
        return info
    def run(*args):
        try:
            r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, timeout=8)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""
    url = run("remote", "get-url", "origin")
    if url:
        url = re.sub(r"\.git$", "", url)
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url.split(":", 1)[1]
        info["url"] = url
    info["ultimo_commit"] = run("log", "-1", "--format=%ad", "--date=short") or None
    n = run("rev-list", "--count", "HEAD")
    info["commits"] = int(n) if n.isdigit() else 0
    return info


def _tabela_projetos():
    indice = config.atual().caminho("indice_projetos")
    txt = _ler(indice) if indice else ""
    out = {}
    for m in PROJETOS_ROW_RE.finditer(txt):
        _, pasta, git, claude, status, resumo = m.groups()
        resumo = re.sub(r"^\(linhagem[^)]*\)\s*", "", resumo.strip())  # nota de linhagem não é resumo
        out[pasta] = {"status": status.strip().strip("*"), "resumo": resumo, "ordem": len(out)}
    return out


_LOG_CACHE = {}


def _ids_do_log():
    """pasta -> (id, tipo) a partir das linhas de projeto do registro
    (fallback pra CLAUDE.md sem frontmatter)."""
    if _LOG_CACHE:
        return _LOG_CACHE
    cfg = config.atual()
    registro = cfg.arquivo("registro")
    if not registro:
        return _LOG_CACHE
    txt = _ler(registro, 2_000_000)
    sigla_projeto = cfg.siglas[-1] if cfg.siglas else ""
    padrao = (r"^\|\s*(\S+-(?:" + _alt(cfg.siglas) + r")(?:-([A-Z]{3}))?-\d+-\S+)\s*"
              r"\|[^|]*\|[^|]*\|\s*`[^`]*?/(" + _pasta_pattern() + r")/?`")
    for m in re.finditer(padrao, txt, re.MULTILINE):
        id_, tipo, pasta = m.groups()
        # a última linha do estágio de projeto vence (regularizações vêm depois)
        if f"-{sigla_projeto}-" in id_ or pasta not in _LOG_CACHE:
            _LOG_CACHE[pasta] = (id_, tipo)
    return _LOG_CACHE


def _frontmatter_claude(pasta: Path):
    txt = _ler(pasta / "CLAUDE.md", 6000)
    fm = {}
    for chave in ("id", "tipo", "status", "origem_nota", "origem_captura"):
        m = re.search(rf"^{chave}:\s*(.+)$", txt, re.MULTILINE)
        if m:
            fm[chave] = m.group(1).strip()
    sigla = None
    re_tipo, re_id_tipo = _re_tipo(), _re_id_tipo()
    if "tipo" in fm and re_tipo:
        m = re_tipo.search(fm["tipo"])
        sigla = m.group(1) if m else None
    if not sigla and "id" in fm and re_id_tipo:
        m = re_id_tipo.search(fm["id"])
        sigla = m.group(1) if m else None
    if not sigla or "id" not in fm:
        log_id, log_tipo = _ids_do_log().get(pasta.name, (None, None))
        if not sigla and log_tipo:
            sigla = log_tipo
        if "id" not in fm and log_id:
            fm["id"] = log_id
    fm["tipo_sigla"] = sigla or "—"
    return fm


def _urls_documentadas(pasta: Path):
    textos = [_ler(pasta / "CLAUDE.md")]
    for p in pasta.glob("readme-*.md"):
        textos.append(_ler(p))
    for p in pasta.glob("backlog-*.md"):
        textos.append(_ler(p))
    vistos, links = set(), []
    for txt in textos:
        for u in URL_RE.findall(txt):
            u = u.rstrip(".,;:*)")
            if u in vistos:
                continue
            if "localhost" in u or "127.0.0.1" in u:
                continue
            kind = None
            if any(h in u for h in NOAR_HOSTS):
                kind = "no-ar"
            elif re.match(r"https://github\.com/[^/]+/[^/]+/?$", u):
                kind = "repo"
            if not kind:
                continue
            vistos.add(u)
            links.append({"url": u, "kind": kind, "label": "no ar" if kind == "no-ar" else "repositório", "origem": "doc"})
    return links


def classificar_arquivo(rel: str, name: str, curadoria: dict):
    """Devolve (kind, estagio) ou None se o arquivo não é 'executável' no sentido amplo."""
    low = name.lower()
    ext = Path(low).suffix
    partes = rel.lower().split("/")
    em_dist = any(p in ("dist", "out") for p in partes[:-1])
    if ext in LAUNCHER_EXT:
        kind = "launcher"
    elif ext in BIN_EXT:
        kind = "binario"
    elif low in SERVER_NAMES and ext == ".py":
        kind = "servidor"
    elif ext in (".html", ".htm"):
        if any(h in low for h in DESIGN_HINTS):
            kind = "design"
        elif any(h in low for h in DOC_HINTS):
            kind = "doc"
        elif em_dist:
            kind = "build"
        else:
            kind = "prototipo"
    else:
        return None
    if name in curadoria.get("estavel_local", []) or rel in curadoria.get("estavel_local", []):
        estagio = "estavel"
    elif any(h in low for h in DRAFT_HINTS) or any(h in rel.lower() for h in ("/versoes/", "-teste/")):
        estagio = "rascunho"
    elif kind in ("doc", "design"):
        estagio = None
    elif kind == "binario":
        estagio = "estavel"
    else:
        estagio = "prototipo"
    return kind, estagio


def _varrer(pasta: Path, curadoria: dict):
    ocultar = set(curadoria.get("ocultar", []))
    destaque = set(curadoria.get("destaque", []))
    execs = []
    for dirpath, dirnames, filenames in os.walk(pasta):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            full = Path(dirpath) / fname
            rel = full.relative_to(pasta).as_posix()
            if rel in ocultar or fname in ocultar:
                continue
            c = classificar_arquivo(rel, fname, curadoria)
            if not c:
                continue
            kind, estagio = c
            try:
                st = full.stat()
            except OSError:
                continue
            grupo = rel.split("/")[0] if "/" in rel else "raiz"
            execs.append({
                "path": f"{pasta.name}/{rel}",
                "rel": rel,
                "nome": fname,
                "kind": kind,
                "estagio": estagio,
                "grupo": grupo,
                "destaque": (rel in destaque or fname in destaque),
                "size_bytes": st.st_size,
                "mtime": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
            })
    ordem_kind = {"launcher": 0, "binario": 1, "servidor": 2, "prototipo": 3, "build": 4, "doc": 5, "design": 6}
    ordem_est = {"estavel": 0, "prototipo": 1, None: 2, "rascunho": 3}
    execs.sort(key=lambda e: (not e["destaque"], ordem_kind[e["kind"]], ordem_est[e["estagio"]], e["grupo"] != "raiz", e["rel"].lower()))
    return execs[:MAX_EXECS_POR_PROJETO]


def build_portfolio():
    _LOG_CACHE.clear()  # o registro muda entre reindexações; cache vale só dentro de uma build
    cfg = config.atual()
    tabela = _tabela_projetos()
    base = cfg.projetos_dir
    tem_prefixo = cfg.projetos_prefixo_re is not None
    projetos = []
    for nome_pasta in sorted(indexer.pastas_de_projeto(), key=str.lower):
        item = base / nome_pasta
        curadoria = {}
        pj = item / "portfolio.json"
        if pj.exists():
            try:
                curadoria = json.loads(_ler(pj))
            except Exception:
                curadoria = {"_erro": "portfolio.json inválido"}
        fm = _frontmatter_claude(item)
        git = _git(item)
        links = _urls_documentadas(item)
        if curadoria.get("estavel"):
            links = [l for l in links if l["url"] != curadoria["estavel"]]
            links.insert(0, {"url": curadoria["estavel"], "kind": "no-ar", "label": "estável", "origem": "curadoria"})
        if git["url"] and not any(l["url"].rstrip("/") == git["url"].rstrip("/") for l in links):
            links.append({"url": git["url"], "kind": "repo", "label": "repositório", "origem": "git"})
        execs = _varrer(item, curadoria)
        meta = tabela.get(item.name, {})
        # nome exibido: a pasta não carrega acento (evita escape de caminho em git),
        # então `portfolio.json` pode declarar o nome de verdade — ex.: "Estação"
        nome = curadoria.get("nome") or (
            item.name.split("-", 1)[1].replace("_", " ")
            if tem_prefixo and "-" in item.name else item.name.replace("_", " "))
        prefixo = item.name.split("-", 1)[0] if tem_prefixo else None
        contagens = {
            "no_ar": sum(1 for l in links if l["kind"] == "no-ar"),
            "roda_local": sum(1 for e in execs if e["kind"] in ("launcher", "binario", "servidor")),
            "prototipos": sum(1 for e in execs if e["kind"] in ("prototipo", "build")),
            "docs": sum(1 for e in execs if e["kind"] in ("doc", "design")),
            "rascunhos": sum(1 for e in execs if e["estagio"] == "rascunho"),
        }
        projetos.append({
            "pasta": item.name,
            "nome": nome,
            "prefixo": prefixo,
            "tipo": fm.get("tipo_sigla") or "—",
            "id": fm.get("id"),
            "status": meta.get("status") or fm.get("status", "").split("—")[0].strip() or "sem status",
            "resumo": meta.get("resumo") or "",
            "listada": item.name in tabela,
            "ordem": meta.get("ordem", 999),
            "git": git,
            "links": links,
            "execs": execs,
            "contagens": contagens,
            "tags": curadoria.get("tags", []),
            "nota": curadoria.get("nota"),
            "repo_publico": bool(curadoria.get("repo_publico")),
            "tem_claude": (item / "CLAUDE.md").exists(),
        })
    totais = {
        "projetos": len(projetos),
        "no_ar": sum(p["contagens"]["no_ar"] for p in projetos),
        "roda_local": sum(p["contagens"]["roda_local"] for p in projetos),
        "prototipos": sum(p["contagens"]["prototipos"] for p in projetos),
        "docs": sum(p["contagens"]["docs"] for p in projetos),
        "com_repo": sum(1 for p in projetos if p["git"]["url"]),
    }
    return {"gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "projetos": projetos, "totais": totais}


def encontrar_exec(portfolio: dict, path: str):
    for p in portfolio.get("projetos", []):
        for e in p["execs"]:
            if e["path"] == path:
                return p, e
    return None, None


if __name__ == "__main__":
    import sys

    config.iniciar(sys.argv[1:])
    pf = build_portfolio()
    print(json.dumps(pf["totais"], ensure_ascii=False))
    for p in pf["projetos"]:
        c = p["contagens"]
        print(f"{p['pasta']:<34} {p['tipo']:<4} {p['status']:<12} no-ar={c['no_ar']} local={c['roda_local']} prot={c['prototipos']} docs={c['docs']} rasc={c['rascunhos']} git={p['git']['ultimo_commit']}")
