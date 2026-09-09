"""Frente 3 do console operacional — GET /api/avanco: resumo da última rodada da
skill rotina-de-avanco, lido de historico.md (prosa livre, não estruturado — só
extrai o último heading e o primeiro parágrafo, nunca inventa o que não está
escrito lá). Disparar uma rodada nova continua exigindo uma sessão do Claude
Code (a skill decide por julgamento, não é mecânica) — este módulo só mostra
o que já aconteceu, ver plano-console-operacional-2026-09-06.md, frente 3.
"""
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent.parent
HISTORICO_PATH = ROOT / "_ferramentas" / "skills" / "rotina-de-avanco" / "execucao" / "historico.md"

# Só headings de rodada de verdade — o arquivo termina com um "## Links" de
# rodapé (mesma convenção de qualquer orquestra deste corpus), que não é uma
# rodada e não pode ser confundido com uma.
HEADING_RE = re.compile(r"^##\s+((?:Rodada|Intervenção manual)\b.+)$", re.MULTILINE)
LIMITE_RESUMO = 400


def ultima_rodada():
    if not HISTORICO_PATH.exists():
        return {"erro": "historico.md não encontrado", "titulo": None, "resumo": None, "path": None}
    try:
        texto = HISTORICO_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"erro": str(e), "titulo": None, "resumo": None, "path": None}

    matches = list(HEADING_RE.finditer(texto))
    if not matches:
        return {"erro": "nenhuma rodada encontrada em historico.md", "titulo": None, "resumo": None, "path": None}

    ultimo = matches[-1]
    titulo = ultimo.group(1).strip()
    corpo = texto[ultimo.end():].strip()
    paragrafo = corpo.split("\n\n")[0].strip() if corpo else ""
    resumo = " ".join(paragrafo.split())
    if len(resumo) > LIMITE_RESUMO:
        corte = resumo.rfind(". ", 0, LIMITE_RESUMO)
        resumo = (resumo[: corte + 1] if corte > 0 else resumo[:LIMITE_RESUMO]).rstrip() + "…"

    return {
        "erro": None,
        "titulo": titulo,
        "resumo": resumo,
        "path": str(HISTORICO_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
