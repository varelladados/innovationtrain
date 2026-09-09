"""Métricas do dashboard Método — GET /api/metricas.

Reaproveita a lógica de contagem já existente em _ferramentas/scripts/plataforma.py
(ler_log_texto, parse_tabelas_do_log) e em indexer.py (is_excluded), em vez
de duplicar regex/varredura. Mesmo formato de saída do protótipo standalone
em .design/mockups/gerar_metricas_dashboard.py — ver esse arquivo pra
contexto de como os números foram validados manualmente contra o LOG.
"""
import datetime
import os
import re
import sys
from collections import Counter
from pathlib import Path

import indexer

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent.parent
_PLATAFORMA_SCRIPTS = ROOT / "_ferramentas" / "scripts"


def _plataforma():
    """Import tardio de _ferramentas/scripts/plataforma.py — só o dashboard precisa dele. Se o
    plataforma.py não compilar (aconteceu em 2026-09-04, merge com marcadores de conflito),
    o erro fica restrito a /api/metricas em vez de derrubar o servidor inteiro no import."""
    if str(_PLATAFORMA_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_PLATAFORMA_SCRIPTS))
    import plataforma  # noqa: E402
    return plataforma

ETAPA_RE = re.compile(r"\b(SBC|SBI|SBZ)\b")
TIPO_RE = re.compile(r"-(DIG|DAD|CON|ADE)\b")
EXTS_CODIGO = {".py", ".js", ".html", ".css"}


def _metricas_log():
    plataforma = _plataforma()
    texto = plataforma.ler_log_texto()
    linhas = plataforma.parse_tabelas_do_log(texto)
    por_etapa = Counter()
    por_tipo = Counter()
    sem_destino_por_etapa = Counter()
    por_dia = Counter()
    for l in linhas:
        campo = l["etapa_tipo"]
        m_etapa = ETAPA_RE.search(campo)
        etapa = m_etapa.group(1) if m_etapa else "outro"
        m_tipo = TIPO_RE.search(campo)
        tipo = m_tipo.group(1) if m_tipo else None
        por_etapa[etapa] += 1
        if tipo:
            por_tipo[tipo] += 1
        if "→" not in campo:
            sem_destino_por_etapa[etapa] += 1
        por_dia[l["data"]] += 1
    return {
        "por_etapa": dict(por_etapa),
        "por_tipo": dict(por_tipo),
        "sem_destino_por_etapa": dict(sem_destino_por_etapa),
        "por_dia": dict(sorted(por_dia.items())),
        "total_linhas_log": len(linhas),
    }


def _metricas_arquivos():
    total_arquivos = 0
    total_md = 0
    linhas_codigo = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = [
            d for d in dirnames
            if not indexer.is_excluded(f"{rel_dir}/{d}" if rel_dir else d)
        ]
        for fname in filenames:
            rel = f"{rel_dir}/{fname}" if rel_dir else fname
            if indexer.is_excluded(rel):
                continue
            total_arquivos += 1
            suf = Path(fname).suffix.lower()
            if suf == ".md":
                total_md += 1
            if suf in EXTS_CODIGO:
                try:
                    with (Path(dirpath) / fname).open(encoding="utf-8", errors="replace") as f:
                        linhas_codigo += sum(1 for _ in f)
                except OSError:
                    pass
    return {"total_arquivos": total_arquivos, "total_md": total_md, "linhas_codigo": linhas_codigo}


def _metricas_parte_do_nucleo():
    areas = [
        ROOT / "1-capturas" / ".pendente", ROOT / "1-capturas" / ".historico",
        ROOT / "1-capturas" / ".entrada", ROOT / "3-ideias", ROOT / "_metodo",
    ]
    nucleo = []
    for area in areas:
        if area.exists():
            nucleo.extend(area.rglob("*.md"))
    prefixos = _plataforma().PROJETO_PREFIXOS
    for pasta in ROOT.iterdir():
        if pasta.is_dir() and pasta.name.startswith(prefixos):
            cm = pasta / "CLAUDE.md"
            if cm.exists():
                nucleo.append(cm)
    marcados = [
        p for p in nucleo
        if re.search(r"^parte_do_nucleo:\s*true", p.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    ]
    return {"marcados_parte_do_nucleo": len(marcados)}


def compute_metrics():
    """Custa uma varredura completa de C:\\Plataforma — o server.py calcula no reindex e guarda
    em STATE, não chama isto a cada GET /api/metricas."""
    try:
        log, nucleo, erro = _metricas_log(), _metricas_parte_do_nucleo(), None
    except Exception as e:  # plataforma.py quebrado/ausente: só o dashboard degrada
        log, nucleo, erro = {}, {}, f"plataforma.py indisponível: {type(e).__name__}: {e}"
    return {
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "erro": erro,
        "log": log,
        "arquivos": _metricas_arquivos(),
        "nucleo": nucleo,
        "esforco": {
            "hora_homem": None,
            "hora_maquina": None,
            "nota": "TODO — metodologia decidida, falta implementar (ver pendencia-resolvida-2026-08-31-dashboard-acompanhamento.md e backlog-estacao.md)",
        },
    }
