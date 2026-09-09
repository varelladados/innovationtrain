"""Frente 1 do console operacional — captura de nota crua (SBC) pela UI, sem
abrir sessão do Claude Code. Mesma mecânica da skill encaminhando-trecho-para-
captura (novo-id -> arquivo em .pendente/ -> linha no LOG), só que disparada
por POST /api/nota/nova em vez de chat. Nunca classifica, nunca decide destino
— ver PRJ-Estacao/plano-console-operacional-2026-09-06.md, frente 1.

plataforma.py é chamado via subprocess, nunca importado direto: `novo-id` faz
sys.exit() em erro, o que mataria o servidor inteiro se fosse import (mesmo
motivo documentado em metrics.py para o import tardio).
"""
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
ROOT = PROJECT_DIR.parent  # C:\Plataforma
PLATAFORMA_PY = ROOT / "_ferramentas" / "scripts" / "plataforma.py"
PENDENTE_DIR = ROOT / "1-capturas" / ".pendente"
LOG_PATH = ROOT / "1-capturas" / "LOG" / "_log.md"
CACHE_DIR = PROJECT_DIR / "cache"
BACKUPS_DIR = CACHE_DIR / "backups"

SECAO_MARCADOR = "captura via console (Estação)"

TEMPLATE = """---
id: {id}
data: {data_iso}
origem: nota criada pela UI do console (Estação) — captura crua, sem classificação
tags: []
status: vaga
links: []
parte_do_nucleo: false
registro-id: {id}
---

## Conteúdo bruto

{texto}
"""

# Serializa toda a operação (novo-id lê o LOG pra achar o maior SEQ do dia; duas
# chamadas concorrentes sem isso podem gerar o mesmo SEQ — bug real já documentado
# na skill encaminhando-trecho).
_LOCK = threading.Lock()


class NotaError(Exception):
    pass


def _slug_words(texto, max_words=5):
    norm = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    palavras = re.findall(r"[a-zA-Z0-9]+", norm.lower())[:max_words]
    return " ".join(palavras) or "nota"


def _gerar_id(texto):
    slug = _slug_words(texto)
    try:
        proc = subprocess.run(
            [sys.executable, str(PLATAFORMA_PY), "novo-id", "--etapa", "SBC", "--slug", slug],
            capture_output=True, text=True, timeout=10, cwd=str(ROOT),
        )
    except Exception as e:
        raise NotaError(f"falha ao chamar plataforma.py: {e}")
    if proc.returncode != 0:
        raise NotaError(f"plataforma.py novo-id falhou: {(proc.stderr or proc.stdout).strip()}")
    novo_id = proc.stdout.strip().splitlines()[0].strip() if proc.stdout.strip() else ""
    if not novo_id:
        raise NotaError("plataforma.py novo-id não devolveu um ID")
    return novo_id


def _escrever_arquivo_sbc(id_, texto):
    PENDENTE_DIR.mkdir(parents=True, exist_ok=True)
    caminho = PENDENTE_DIR / f"{id_}.md"
    if caminho.exists():
        raise NotaError(f"arquivo já existe: {caminho.name} (colisão de ID)")
    conteudo = TEMPLATE.format(id=id_, data_iso=date.today().isoformat(), texto=texto.strip())
    tmp = caminho.with_suffix(".md.tmp")
    tmp.write_text(conteudo, encoding="utf-8", newline="\n")
    tmp.replace(caminho)  # gravação atômica — mesmo padrão do dois apps locais anteriores
    return caminho


def _resumo_curto(texto, limite=180):
    plano = " ".join(texto.split())
    if len(plano) <= limite:
        return plano
    corte = plano.rfind(" ", 0, limite)
    return plano[: corte if corte > 0 else limite].rstrip() + "…"


def _find_section_span(texto, heading):
    idx = texto.index(heading)
    m = re.search(r"\r?\n#{1,6}\s", texto[idx + len(heading):])
    fim = idx + len(heading) + (m.start() if m else len(texto) - idx - len(heading))
    return idx, fim


def _append_row_to_section(texto, heading, linha, eol):
    idx, fim = _find_section_span(texto, heading)
    secao = texto[idx:fim]
    linhas = secao.split(eol)
    ultimo_row = None
    for i, l in enumerate(linhas):
        if l.strip().startswith("|") and l.strip().endswith("|"):
            ultimo_row = i
    if ultimo_row is None:
        raise NotaError(f"seção '{heading.strip()}' existe mas não tem tabela reconhecível")
    linhas.insert(ultimo_row + 1, linha)
    nova_secao = eol.join(linhas)
    return texto[:idx] + nova_secao + texto[fim:]


def _append_log(id_, texto):
    """Acrescenta uma linha na tabela de hoje da seção 'captura via console' do LOG
    central — cria a seção se ainda não existir hoje. NUNCA edita linha existente
    (doutrina: LOG é append-only). Lê/escreve sem tradução de fim de linha e preserva
    o padrão (LF/CRLF) já usado no arquivo — mesmo cuidado documentado em
    server.py::_handle_backlog_toggle, pra nunca reescrever o arquivo inteiro só por
    causa da quebra de linha. Faz backup antes de gravar."""
    if not LOG_PATH.exists():
        raise NotaError(f"LOG central não encontrado: {LOG_PATH}")

    with LOG_PATH.open(encoding="utf-8", newline="") as f:
        original = f.read()
    eol = "\r\n" if "\r\n" in original else "\n"

    hoje = date.today().isoformat()
    heading = f"## Entradas {hoje} — {SECAO_MARCADOR}"
    header_tabela = "| ID | Data | Etapa/Tipo | Local | Resumo | Link |"
    separador = "|---|---|---|---|---|---|"
    resumo = _resumo_curto(texto)
    link = f"[arquivo](<../.pendente/{id_}.md>)"
    linha = f"| {id_} | {hoje} | SBC | `../.pendente/` | {resumo} | {link} |"

    if heading in original:
        novo_texto = _append_row_to_section(original, heading, linha, eol)
    else:
        nova_secao = eol.join([heading, "", header_tabela, separador, linha])
        marcador = eol + "## Pendente"
        pos = original.rfind(marcador)
        if pos == -1:
            novo_texto = original.rstrip(eol) + eol * 2 + nova_secao + eol
        else:
            antes = original[:pos].rstrip(eol)
            depois = original[pos:].lstrip(eol)
            novo_texto = antes + eol * 2 + nova_secao + eol * 2 + depois

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backup_name = f"1-capturas_LOG__log.md-{int(time.time())}.bak"
    shutil.copy2(LOG_PATH, BACKUPS_DIR / backup_name)
    with LOG_PATH.open("w", encoding="utf-8", newline="") as f:
        f.write(novo_texto)


def _sincronizar_pendentes():
    try:
        subprocess.run(
            [sys.executable, str(PLATAFORMA_PY), "gerar-pendentes"],
            capture_output=True, text=True, timeout=15, cwd=str(ROOT),
        )
    except Exception:
        pass  # nunca derruba a criação da nota por isso — pendentes.md só fica atrasado


def criar_captura_crua(texto):
    """Cria uma Captura crua (SBC) a partir de texto solto: gera ID, grava o
    arquivo em .pendente/, registra no LOG central e ressincroniza pendentes.md.
    Levanta NotaError em qualquer falha (nunca deixa meio-registrado sem avisar)."""
    texto = (texto or "").strip()
    if not texto:
        raise NotaError("texto vazio")

    with _LOCK:
        id_ = _gerar_id(texto)
        caminho = _escrever_arquivo_sbc(id_, texto)
        try:
            _append_log(id_, texto)
        except Exception:
            caminho.unlink(missing_ok=True)
            raise
        _sincronizar_pendentes()

    return {"id": id_, "path": str(caminho.relative_to(ROOT)).replace("\\", "/")}
