"""A trilha de exemplo: um slideshow de estados reais da plataforma.

**Não há motor de promoção aqui, e é de propósito.** "Avançar" na trilha não
calcula nada: ele restaura o próximo instantâneo, que é uma pasta com a
plataforma inteira já no estado seguinte. O mesmo comando que devolve o exemplo
ao início (`plataforma.py reiniciar`) serve os dois casos — muda só de onde ele
copia.

Isso mantém a fronteira que importa: numa plataforma de verdade a passagem entre
estágios é decisão e escrita, feita por uma sessão de IA com o roteiro do
briefing. O que a trilha mostra é **como fica**, não como se automatiza.

O passo atual não é guardado em lugar nenhum: ele é **deduzido** comparando o
`_registro.md` da plataforma com o de cada instantâneo. Sem estado, sem arquivo
de controle para dessincronizar — e se alguém editar o exemplo à mão, a trilha
responde honestamente "fora dos passos" em vez de mentir um número.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

import config


class TrilhaError(Exception):
    pass


def _sha(caminho):
    try:
        return hashlib.sha1(caminho.read_bytes()).hexdigest()
    except OSError:
        return None


def passos(cfg=None):
    """Os estados da trilha, do inicial ao último. Vazio fora de exemplo.

    O passo 0 é o `estado_inicial` — o mesmo que o botão reiniciar usa. Os
    demais vêm da chave `tutorial.passos` do `plataforma.json`.
    """
    cfg = cfg or config.atual()
    inicial = cfg.get("estado_inicial")
    if not inicial:
        return []
    out = [{"n": 0, "rotulo": "Como ela vem", "pasta": str(inicial)}]
    for i, p in enumerate((cfg.get("tutorial") or {}).get("passos") or [], start=1):
        out.append({"n": i, "rotulo": p.get("rotulo") or f"Passo {i}",
                    "pasta": p.get("pasta")})
    return out


def estado(cfg=None):
    """Onde a plataforma está na trilha, deduzido do registro.

    `passo` é `None` quando o conteúdo não bate com instantâneo nenhum — o que
    acontece assim que alguém mexe na plataforma à mão. Não é erro: é a resposta
    honesta, e a interface a usa para oferecer "voltar ao início" em vez de
    "próximo passo".
    """
    cfg = cfg or config.atual()
    lista = passos(cfg)
    if not lista:
        return {"tem": False, "passo": None, "total": 0, "passos": []}

    registro = cfg.arquivo("registro")
    atual_sha = _sha(registro) if registro else None
    rel_registro = cfg.arquivo_rel("registro") or "_registro.md"

    passo = None
    for p in lista:
        pasta = (cfg.raiz / str(p["pasta"]).replace("\\", "/")).resolve()
        if atual_sha and _sha(pasta / rel_registro) == atual_sha:
            passo = p["n"]
            break
    return {"tem": True, "passo": passo, "total": len(lista) - 1,
            "passos": [{"n": p["n"], "rotulo": p["rotulo"]} for p in lista]}


def restaurar(n, cfg=None):
    """Deixa a plataforma no estado do passo `n`. Quem apaga e copia é o utilitário."""
    cfg = cfg or config.atual()
    lista = passos(cfg)
    if not lista:
        raise TrilhaError("esta plataforma não é um exemplo: ela não tem trilha")
    alvo = next((p for p in lista if p["n"] == n), None)
    if alvo is None:
        raise TrilhaError(f"a trilha tem os passos 0 a {len(lista) - 1}")

    util = cfg.caminho("utilitario") or (config.hub_dir() / "metodo" / "plataforma.py")
    if not Path(util).is_file():
        raise TrilhaError(f"utilitário não encontrado: {util}")
    try:
        proc = subprocess.run(
            [sys.executable, str(util), "reiniciar", "--raiz", str(cfg.raiz),
             "--de", str(alvo["pasta"]), "--confirmar"],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace")
    except Exception as e:
        raise TrilhaError(f"falha ao chamar o utilitário: {e}")
    if proc.returncode != 0:
        raise TrilhaError((proc.stdout or proc.stderr or "").strip() or "o utilitário recusou")
    return {"passo": n, "rotulo": alvo["rotulo"], "saida": (proc.stdout or "").strip()}
