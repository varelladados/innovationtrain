"""View por projeto (Projeto): junta o que já existe em quatro fontes e deixa o
humano anotar no backlog do projeto sem abrir sessão do Claude Code.

Fontes (nenhuma inventada aqui, todas já existiam):
- `portfolio.build_portfolio()` — status, resumo canônico, git, links, execs;
- `_metodo/portfolio/perfis/<pasta>.json` — maturidade 0-5 × 6 dimensões,
  lacunas, ligações, documentos-chave (rodada de portfólio de 2026-09-05);
- índice do app — os `backlog-*.md` daquele projeto;
- `CLAUDE.md` do projeto.

Escrita: só `POST /api/projeto/anotar`, que acrescenta UMA linha de checkbox no
backlog do projeto. É de propósito o formato que a automação já lê (`plataforma.py`
varre `- [ ]` em todo `backlog*.md`; o snapshot do avanço vê o arquivo mudado),
então a anotação feita aqui reaparece pra IA na próxima rodada sem nenhum
formato novo. Sem `**[ESSENCIAL]**`: anotação não é bloqueio de entrega.
"""
import hashlib
import json
import re
import shutil
import threading
import time
from datetime import date
from pathlib import Path

import portfolio as portfolio_mod

import config
import indexer

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
BACKUPS_DIR = PROJECT_DIR / "cache" / "backups"



def _pasta_valida(pasta):
    """Allow-list de verdade: a pasta tem que ser uma das pastas de projeto que
    o indexer enxerga na plataforma ativa. Substitui o regex de prefixo, que
    deixou de existir na taxonomia nova — e é mais forte, porque valida contra
    o disco em vez de contra um formato de nome."""
    if not pasta or "/" in pasta or "\\" in pasta or pasta in (".", ".."):
        return False
    return pasta in indexer.pastas_de_projeto()
CHECKBOX_LINHA_RE = re.compile(r"^\s*-\s*\[[ xX]\]")
LINKS_HEADING_RE = re.compile(r"^##\s+Links\s*$", re.IGNORECASE)

MIN_TEXTO, MAX_TEXTO = 3, 500

_LOCK = threading.Lock()


class ProjetoError(Exception):
    pass


class ConflitoError(ProjetoError):
    """O arquivo mudou desde a leitura (vira HTTP 409)."""


def sha1(texto: str) -> str:
    """Hash do conteúdo com fim de linha normalizado.

    A normalização não é detalhe: o `text_cache` do indexer lê com `read_text()`
    (universal newlines, CRLF vira LF) e a escrita aqui lê com `newline=""` pra
    poder preservar o CRLF original. Sem normalizar, todo backlog em CRLF daria
    conflito 409 eterno — foi o que aconteceu no primeiro teste ao vivo.
    """
    return hashlib.sha1(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _perfil(pasta):
    perfis = config.atual().caminho("perfis")
    if perfis is None:
        return None
    caminho = perfis / f"{pasta}.json"
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"_erro": f"perfil ilegível: {e}"}


def _backlogs_do(entries, pasta):
    return [
        {"path": e["path"], "title": e["title"], "size_bytes": e["size_bytes"]}
        for e in entries
        if e["type"] == "backlog" and e["path"].startswith(pasta + "/")
    ]


def detalhe(pasta, entries, text_cache, portfolio=None):
    """Tudo que a view de projeto precisa, numa chamada só."""
    if not _pasta_valida(pasta):
        raise ProjetoError("pasta não é um projeto desta plataforma")

    pf = portfolio or portfolio_mod.build_portfolio()
    projeto = next((p for p in pf.get("projetos", []) if p["pasta"] == pasta), None)
    if projeto is None:
        raise ProjetoError("projeto não encontrado no portfólio")

    perfil = _perfil(pasta)
    backlogs = _backlogs_do(entries, pasta)
    for b in backlogs:
        conteudo = text_cache.get(b["path"], "")
        b["raw"] = conteudo
        b["sha1"] = sha1(conteudo)
        b["abertos"] = len([
            ln for ln in conteudo.splitlines()
            if ln.strip().startswith("- [ ]")
        ])

    claude_path = f"{pasta}/CLAUDE.md"
    return {
        "pasta": pasta,
        "projeto": projeto,
        "perfil": perfil,
        "maturidade": (perfil or {}).get("maturidade"),
        "lacunas": (perfil or {}).get("lacunas", []),
        "ligacoes": (perfil or {}).get("ligacoes", []),
        "documentos_chave": (perfil or {}).get("documentos_chave", []),
        "backlogs": backlogs,
        "claude_path": claude_path if claude_path in text_cache else None,
        "claude_raw": text_cache.get(claude_path, ""),
    }


def _posicao_de_insercao(linhas):
    """Antes do `## Links` de rodapé, se houver; senão depois da última linha de
    checkbox; senão no fim. Mantém o rodapé de links sempre por último, que é a
    convenção de todo backlog da plataforma de origem."""
    for i, ln in enumerate(linhas):
        if LINKS_HEADING_RE.match(ln.strip()):
            fim = i
            while fim > 0 and not linhas[fim - 1].strip():
                fim -= 1
            return fim
    ultimo_check = None
    for i, ln in enumerate(linhas):
        if CHECKBOX_LINHA_RE.match(ln):
            ultimo_check = i
    if ultimo_check is not None:
        return ultimo_check + 1
    fim = len(linhas)
    while fim > 0 and not linhas[fim - 1].strip():
        fim -= 1
    return fim


def anotar(pasta, backlog_path, texto, expected_sha1, entries, text_cache):
    """Acrescenta `- [ ] <texto> _(via console, AAAA-MM-DD)_` no backlog do projeto."""
    if not _pasta_valida(pasta):
        raise ProjetoError("pasta não é um projeto desta plataforma")

    permitidos = {b["path"] for b in _backlogs_do(entries, pasta)}
    if backlog_path not in permitidos:
        raise ProjetoError("este arquivo não é um backlog deste projeto")

    limpo = (texto or "").strip()
    if len(limpo) < MIN_TEXTO:
        raise ProjetoError(f"texto precisa ter pelo menos {MIN_TEXTO} caracteres")
    if len(limpo) > MAX_TEXTO:
        raise ProjetoError(f"texto acima de {MAX_TEXTO} caracteres")
    if "\n" in limpo or "\r" in limpo:
        raise ProjetoError("texto precisa caber numa linha só")
    if limpo.startswith("- [") or limpo.startswith("#"):
        raise ProjetoError("escreva só o texto — o marcador de checkbox é acrescentado aqui")

    caminho = config.atual().raiz / backlog_path
    if not caminho.is_file():
        raise ProjetoError("backlog não existe no disco")

    with _LOCK:
        with caminho.open(encoding="utf-8", newline="") as f:
            conteudo = f.read()
        if expected_sha1 and sha1(conteudo) != expected_sha1:
            raise ConflitoError("conflito: o backlog mudou desde a última leitura")

        eol = "\r\n" if "\r\n" in conteudo else "\n"
        linhas = conteudo.split(eol)
        nova = f"- [ ] {limpo} _(via console, {date.today().isoformat()})_"
        pos = _posicao_de_insercao(linhas)
        linhas.insert(pos, nova)
        novo_conteudo = eol.join(linhas)

        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUPS_DIR / f"{backlog_path.replace('/', '_')}-{int(time.time())}.bak"
        shutil.copy2(caminho, backup)

        with caminho.open("w", encoding="utf-8", newline="") as f:
            f.write(novo_conteudo)

    return {
        "ok": True,
        "linha": nova,
        "line_number": pos,
        "sha1": sha1(novo_conteudo),
        "conteudo": novo_conteudo,
    }
