"""Frente 2 do console operacional — GET /api/workflow: os estágios da
plataforma ativa e as pendências, juntos numa view só, em vez de espalhados (pendentes.md, LOG,
trem avulso gerado sob pedido). Leitura pura sobre o índice já calculado pelo
indexer (STATE["entries"]) — nenhum write, nenhuma varredura de disco extra.

Escopo v1 (decisão pendente do usuário, ver plano-console-operacional-2026-09-06.md
frente 2): só leitura. Decidir uma pendência continua sendo uma sessão do Claude
Code — esta view mostra, não decide.
"""
import re
from pathlib import Path

import config
import pendencias


def _etapa_re():
    return re.compile(r"-(" + "|".join(re.escape(s) for s in config.atual().siglas) + r")-")


def _etapa_de(path):
    nome = path.rsplit("/", 1)[-1]
    m = _etapa_re().search(nome)
    return m.group(1) if m else None


def _estagio_de(etapa):
    """1..N — é o que a escala de maturidade da interface colore."""
    cfg = config.atual()
    for e in cfg.estagios:
        if e["sigla"] == etapa:
            return e["n"]
    return None


def colunas_do_quadro():
    """As colunas do kanban, e como um item cai numa delas.

    Onde a plataforma declara um ciclo de vida dentro do estágio (uma
    legado, com .entrada/.pendente/.historico), as colunas são ele. Onde não
    declara — a taxonomia nova — as colunas são os próprios estágios, que é o
    quadro que faz sentido quando o item muda de pasta ao avançar.
    """
    cfg = config.atual()
    ciclo = [str(s).lstrip("._") for s in (cfg.get("ciclo_vida") or [])]
    if ciclo:
        return ciclo, "ciclo"
    return [e["pasta"] for e in cfg.estagios], "estagio"


def build_workflow(entries):
    stages, modo = colunas_do_quadro()
    colunas = {stage: [] for stage in stages}
    for e in entries:
        if modo == "ciclo":
            stage = e.get("lifecycle_stage")
        else:
            stage = e["path"].split("/", 1)[0] if "/" in e["path"] else None
        if stage not in colunas:
            continue
        # O `_` do começo do nome significa "isto é maquinário, não conteúdo
        # seu" (metodo/taxonomia.md, parada 5). O trem só mostra conteúdo: sem
        # isto, um `_leia-me.md` dentro de `_historico/` vira carta e a coluna
        # mente na contagem.
        if Path(e["path"]).name.startswith("_"):
            continue
        etapa = _etapa_de(e["path"])
        colunas[stage].append({
            "path": e["path"],
            "title": e["title"],
            "etapa": etapa,
            "estagio": _estagio_de(etapa),
            "mtime": e["mtime"],
            "is_stub": e["is_stub"],
        })
    for stage in stages:
        colunas[stage].sort(key=lambda x: x["mtime"], reverse=True)

    return {
        "colunas": colunas,
        "totais": {stage: len(colunas[stage]) for stage in stages},
        "rotulos": _rotulos(stages, modo),
        "pendencias": pendencias.listar_pendencias_ativas(),
    }


ROTULO_CICLO = {
    "entrada": "Entrada (ninguém viu ainda)",
    "pendente": "Pendente (sem destino)",
    "historico": "Histórico (já seguiu)",
}


def _rotulos(stages, modo):
    if modo == "ciclo":
        return {s: ROTULO_CICLO.get(s, s) for s in stages}
    cfg = config.atual()
    return {e["pasta"]: e.get("plural") or e["nome"] for e in cfg.estagios}
