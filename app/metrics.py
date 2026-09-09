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

import config
import indexer

APP_DIR = Path(__file__).resolve().parent


def _plataforma():
    """Import tardio do utilitário da plataforma — só o dashboard precisa dele.
    Se ele não compilar (aconteceu em 2026-09-04, merge com marcadores de
    conflito) ou a plataforma não declarar nenhum, o erro fica restrito a
    /api/metricas em vez de derrubar o servidor inteiro no import."""
    util = config.atual().caminho("utilitario")
    if util is None:
        raise RuntimeError("esta plataforma não declara um utilitário (chave 'utilitario')")
    if not util.exists():
        raise FileNotFoundError(f"utilitário declarado mas ausente: {util}")
    pasta = str(util.parent)
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    return __import__(util.stem)


def _tipo_re():
    tipos = config.atual().tipos
    if not tipos:
        return None
    return re.compile(r"-(" + "|".join(re.escape(x) for x in tipos) + r")\b")


EXTS_CODIGO = {".py", ".js", ".html", ".css"}


def _metricas_log():
    plataforma = _plataforma()
    etapa_re = config.atual().etapa_re
    tipo_re = _tipo_re()
    texto = plataforma.ler_log_texto()
    linhas = plataforma.parse_tabelas_do_log(texto)
    por_etapa = Counter()
    por_tipo = Counter()
    sem_destino_por_etapa = Counter()
    por_dia = Counter()
    for l in linhas:
        campo = l["etapa_tipo"]
        m_etapa = etapa_re.search(campo)
        etapa = m_etapa.group(1) if m_etapa else "outro"
        m_tipo = tipo_re.search(campo) if tipo_re else None
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
    root = config.atual().raiz
    total_arquivos = 0
    total_md = 0
    linhas_codigo = 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
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
    """Conta o marcador `parte_do_nucleo:` do caso aplicado. Só faz sentido
    onda plataforma de origem declara `metricas_pastas` — numa plataforma genérica esse
    campo não existe, e a métrica sai do dashboard em vez de contar zero como
    se fosse informação."""
    cfg = config.atual()
    pastas = cfg.get("metricas_pastas")
    if not pastas:
        return {}
    nucleo = []
    for rel in pastas:
        area = cfg.raiz / str(rel).replace("\\", "/")
        if area.exists():
            nucleo.extend(area.rglob("*.md"))
    for nome in indexer.pastas_de_projeto():
        cm = cfg.projetos_dir / nome / "CLAUDE.md"
        if cm.exists():
            nucleo.append(cm)
    marcados = [
        p for p in nucleo
        if re.search(r"^parte_do_nucleo:\s*true", p.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    ]
    return {"marcados_parte_do_nucleo": len(marcados)}


def compute_metrics():
    """Custa uma varredura completa da plataforma — o server.py calcula no
    reindex e guarda em STATE, não chama isto a cada GET /api/metricas."""
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
