"""Métricas do dashboard — GET /api/metricas.

Lê o registro da plataforma ativa e reaproveita `indexer.is_excluded` para a
varredura de arquivos, em vez de duplicar regex. Até o Trecho 6 isto dependia do
utilitário da plataforma, o que fazia o Dashboard sumir em
qualquer outra plataforma; a regra de reconhecer uma linha de registro é a mesma
de lá, agora com o identificador vindo do config. Mesmo formato de saída do
protótipo em `.design/mockups/gerar_metricas_dashboard.py`, contra o qual os
números foram validados à mão.
"""
import datetime
import os
import re
from collections import Counter
from pathlib import Path

import config
import indexer

APP_DIR = Path(__file__).resolve().parent


TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def _linhas_do_registro():
    """As linhas de tabela do registro da plataforma ativa.

    Antes isto era importado do utilitário da plataforma — o que fazia o
    Dashboard depender de um script que só existe
    naquela plataforma. A regra é a mesma de lá (seis colunas, a primeira
    contendo um identificador), agora com o identificador vindo do config.
    """
    cfg = config.atual()
    registro = cfg.arquivo("registro")
    if registro is None:
        raise RuntimeError("esta plataforma não declara um arquivo de registro")
    if not registro.exists():
        raise FileNotFoundError(f"registro não encontrado: {registro}")
    ident = cfg.identificador_re
    linhas = []
    for line in registro.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        cols = [c.strip() for c in m.group(1).split("|")]
        if len(cols) != 6:
            continue
        if cols[0] in ("ID", "---") or set(cols[0]) <= {"-"}:
            continue
        if not ident.search(cols[0]):
            continue
        linhas.append({"id": cols[0], "data": cols[1], "etapa_tipo": cols[2],
                       "local": cols[3], "resumo": cols[4], "link": cols[5]})
    return linhas


def _tipo_re():
    """Casa o tipo do item na coluna Etapa/Tipo — **ancorado no início**.

    A versão herdada procurava o tipo em qualquer lugar da coluna, e por isso
    contava o tipo do DESTINO em toda linha que já tinha avançado: uma entrada
    crua (que não tem tipo nenhum) aparecia como `DIG` só porque a seta dela
    apontava para um item já promovido. Numa plataforma real isso inflou a contagem em 8
    linhas. A coluna começa com a sigla do estágio, e o tipo, quando existe, vem
    logo depois — é só isso que conta.
    """
    cfg = config.atual()
    if not cfg.tipos:
        return None
    siglas = "|".join(re.escape(s) for s in cfg.siglas)
    tipos = "|".join(re.escape(x) for x in cfg.tipos)
    return re.compile(r"^(?:" + siglas + r")-(" + tipos + r")\b")


EXTS_CODIGO = {".py", ".js", ".html", ".css"}


def _metricas_log():
    etapa_re = config.atual().etapa_re
    tipo_re = _tipo_re()
    linhas = _linhas_do_registro()
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


def _metricas_nucleo():
    """Conta o marcador de núcleo que a plataforma declarar em `frontmatter`.

    Só faz sentido onda plataforma de origem declara **as duas coisas** — o campo e as
    `metricas_pastas` onde procurá-lo. Sem isso a métrica sai do dashboard, em
    vez de contar zero como se fosse informação.
    """
    cfg = config.atual()
    campo = cfg.fm("nucleo")
    pastas = cfg.get("metricas_pastas")
    if not campo or not pastas:
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
    padrao = re.compile(rf"^{re.escape(campo)}:\s*true", re.MULTILINE)
    marcados = [
        p for p in nucleo
        if padrao.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    return {"marcados_nucleo": len(marcados), "campo_nucleo": campo}


def compute_metrics():
    """Custa uma varredura completa da plataforma — o server.py calcula no
    reindex e guarda em STATE, não chama isto a cada GET /api/metricas."""
    try:
        log, nucleo, erro = _metricas_log(), _metricas_nucleo(), None
    except Exception as e:  # utilitário quebrado/ausente: só o dashboard degrada
        log, nucleo, erro = {}, {}, f"métricas indisponíveis: {type(e).__name__}: {e}"
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
