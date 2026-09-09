"""Frente 2 do console operacional — GET /api/workflow: o pipeline SBC->SBI->SBZ e as
pendências ativas, juntos numa view só, em vez de espalhados (pendentes.md, LOG,
trem avulso gerado sob pedido). Leitura pura sobre o índice já calculado pelo
indexer (STATE["entries"]) — nenhum write, nenhuma varredura de disco extra.

Escopo v1 (decisão pendente do usuário, ver plano-console-operacional-2026-09-06.md
frente 2): só leitura. Decidir uma pendência continua sendo uma sessão do Claude
Code — esta view mostra, não decide.
"""
import re

import pendencias

ETAPA_RE = re.compile(r"-SB([CIZ])-")
ETAPA_MAP = {"C": "SBC", "I": "SBI", "Z": "SBZ"}
STAGES = ("entrada", "pendente", "historico")


def _etapa_de(path):
    nome = path.rsplit("/", 1)[-1]
    m = ETAPA_RE.search(nome)
    return ETAPA_MAP.get(m.group(1)) if m else None


def build_workflow(entries):
    colunas = {stage: [] for stage in STAGES}
    for e in entries:
        stage = e.get("lifecycle_stage")
        if stage not in STAGES:
            continue
        colunas[stage].append({
            "path": e["path"],
            "title": e["title"],
            "etapa": _etapa_de(e["path"]),
            "mtime": e["mtime"],
            "is_stub": e["is_stub"],
        })
    for stage in STAGES:
        colunas[stage].sort(key=lambda x: x["mtime"], reverse=True)

    return {
        "colunas": colunas,
        "totais": {stage: len(colunas[stage]) for stage in STAGES},
        "pendencias": pendencias.listar_pendencias_ativas(),
    }
