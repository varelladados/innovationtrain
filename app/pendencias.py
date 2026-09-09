"""Pendências-formulário: parse tolerante + escrita da resposta.

Por que parser próprio em vez de reusar `gerar_trem_pendencias.py`: aquele script
busca literalmente o heading `## Resposta (marque uma opção)` e descarta o card
quando não acha opções — o que esconde da UI as pendências multi-pergunta
(`## Pergunta 1 — …`, `### 1. …`) e as variantes de heading que existem de fato
na pasta. Aqui nenhuma pendência some: o que não parseia vira card cru.

O QUE ESTE MÓDULO PODE ESCREVER (contrato da skill, SKILL.md linhas 50-55):
marcar/desmarcar `- [ ]`/`- [x]` numa linha de bloco de resposta, e preencher a
linha "Outra resposta:". Nada mais. Quem *resolve* a pendência é a skill, na
rodada seguinte — ela renomeia pra `pendencia-resolvida-*`, escreve o bloco
`## Resolvida em <data>`, incrementa `**Adiada:**` quando o marcado foi "Deixar
para depois", e regenera pendentes.md/chaves.md. O app nunca faz nada disso:
"Nunca fecha uma pendência por inferência — só o campo ## Resposta explícito fecha."
"""
import re
import shutil
import threading
import time
from pathlib import Path

import config

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
BACKUPS_DIR = PROJECT_DIR / "cache" / "backups"


def _execucao_dir():
    """Pasta das pendências da plataforma ativa, ou None se ela não declara uma."""
    return config.atual().caminho("pendencias")

NOME_RE = re.compile(r"^pendencia-ativa-(\d{4}-\d{2}-\d{2})-(.+)\.md$")
REF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9._-]*$", re.IGNORECASE)

TITULO_RE = re.compile(r"^#\s*Pendência:\s*(.+)$", re.MULTILINE)
CAMPO_RE = r"^\*\*{campo}:\*\*\s*(.*)$"
CHECKBOX_RE = re.compile(r"^(\s*-\s*\[)([ xX])(\]\s*)(.*)$")

# Headings que abrem um bloco de opções: "## Resposta…", "## Pergunta 2 — …",
# "### 1. …" (sub-pergunta de um "## Perguntas").
ABRE_BLOCO_RE = re.compile(
    r"^(?:##\s*Resposta\b.*|##\s*Pergunta\s*\d+\b.*|###\s*\d+[.)]\s*.*)$"
)
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
PERGUNTA_SIMPLES_RE = re.compile(r"^##\s*Pergunta\s*$")

VAZIO_OUTRA_RE = re.compile(r"^[\s_]*$")
MAX_TEXTO_OUTRA = 600

_LOCK = threading.Lock()


class PendenciaError(Exception):
    pass


class ConflitoError(PendenciaError):
    """A linha no disco mudou desde a leitura (vira HTTP 409)."""

    def __init__(self, atual):
        super().__init__("conflito: a linha mudou desde a última leitura")
        self.atual = atual


# ---------------------------------------------------------------- parse


def _rel(caminho: Path):
    """Caminho relativo à raiz da plataforma; devolve o absoluto se estiver fora
    dela (acontece só em teste, com fixture em pasta temporária)."""
    try:
        return str(caminho.relative_to(config.atual().raiz)).replace("\\", "/")
    except ValueError:
        return str(caminho).replace("\\", "/")


def _campo(texto, campo, default=None):
    m = re.search(CAMPO_RE.format(campo=re.escape(campo)), texto, re.MULTILINE)
    if not m:
        return default
    valor = m.group(1).strip()
    return valor or default


def _secao(linhas, nome):
    """Corpo de uma seção `## <nome>` até o próximo heading."""
    alvo = re.compile(rf"^##\s*{nome}\s*$", re.IGNORECASE)
    for i, ln in enumerate(linhas):
        if alvo.match(ln.strip()):
            corpo = []
            for prox in linhas[i + 1:]:
                if HEADING_RE.match(prox):
                    break
                corpo.append(prox)
            return "\n".join(corpo).strip()
    return ""


def _classificar_opcao(label):
    baixo = label.lower()
    if baixo.startswith("outra resposta"):
        return "outra"
    if "deixar para depois" in baixo:
        return "adiar"
    return "opcao"


def _quebrar_label(texto):
    """`A — razão` vira ('A', 'razão'); sem travessão, tudo é label."""
    if " — " in texto:
        label, _, reason = texto.partition(" — ")
        return label.strip(), reason.strip()
    return texto.strip(), ""


def _texto_da_outra(label_completo):
    """Devolve o que foi escrito depois de 'Outra resposta:' ('' se ainda vazio)."""
    _, _, depois = label_completo.partition(":")
    return "" if VAZIO_OUTRA_RE.match(depois) else depois.strip()


def _parse_blocos(linhas):
    """Agrupa as linhas de checkbox por bloco (pergunta). Toda linha de checkbox
    pertence ao último heading de bloco visto; checkbox órfão cai num bloco
    implícito, pra nunca sumir da tela."""
    blocos = []
    atual = None
    titulo_pendente = None  # texto de um "## Pergunta" simples, usado pelo "## Resposta"

    for idx, linha in enumerate(linhas):
        crua = linha.rstrip("\r\n")

        if PERGUNTA_SIMPLES_RE.match(crua.strip()):
            corpo = []
            for prox in linhas[idx + 1:]:
                if HEADING_RE.match(prox):
                    break
                if prox.strip().startswith("**Atualização"):
                    break  # histórico logado dentro da pergunta, não é a pergunta
                corpo.append(prox)
            titulo_pendente = " ".join(" ".join(corpo).split())
            continue

        if ABRE_BLOCO_RE.match(crua.strip()):
            heading = HEADING_RE.match(crua.strip()).group(1).strip()
            if re.match(r"^Resposta\b", heading, re.IGNORECASE):
                texto = titulo_pendente or ""
                titulo = "Resposta"
            else:
                texto = heading
                titulo = heading
            atual = {"titulo": titulo, "texto": texto, "opcoes": []}
            blocos.append(atual)
            continue

        if HEADING_RE.match(crua.strip()):
            atual = None  # heading qualquer fecha o bloco corrente
            continue

        m = CHECKBOX_RE.match(crua)
        if not m:
            continue
        if atual is None:
            atual = {"titulo": "Resposta", "texto": titulo_pendente or "", "opcoes": []}
            blocos.append(atual)
        conteudo = m.group(4).strip()
        label, reason = _quebrar_label(conteudo)
        kind = _classificar_opcao(conteudo)
        atual["opcoes"].append({
            "line_number": idx,
            "text": crua,
            "label": label,
            "reason": reason,
            "marcado": m.group(2).lower() == "x",
            "kind": kind,
            "texto_livre": _texto_da_outra(conteudo) if kind == "outra" else "",
        })

    return [b for b in blocos if b["opcoes"]]


def _estado(blocos):
    for bloco in blocos:
        for op in bloco["opcoes"]:
            if op["kind"] == "opcao" and op["marcado"]:
                return "respondida"
            if op["kind"] == "outra" and (op["marcado"] or op["texto_livre"]):
                return "respondida"
    for bloco in blocos:
        for op in bloco["opcoes"]:
            if op["kind"] == "adiar" and op["marcado"]:
                return "adiada-marcada"
    return "aberta"


def parse_pendencia(caminho: Path):
    nome_m = NOME_RE.match(caminho.name)
    if not nome_m:
        return None
    data, slug = nome_m.group(1), nome_m.group(2)

    try:
        with caminho.open(encoding="utf-8", errors="replace", newline="") as f:
            texto = f.read()
    except OSError as e:
        return {
            "ref": f"{data}-{slug}", "slug": slug, "data": data,
            "title": slug, "estado": "nao-parseavel", "parse_ok": False,
            "erro": str(e), "perguntas": [], "adiada": 0,
            "categoria": "Sustentação", "icon": "ti-settings",
        }

    linhas = texto.splitlines()
    titulo_m = TITULO_RE.search(texto)
    categoria_raw = _campo(texto, "Categoria", "") or ""
    categoria = "Incremento" if "incremento" in categoria_raw.lower() else "Sustentação"
    adiada_raw = _campo(texto, "Adiada", "0") or "0"
    adiada_m = re.search(r"\d+", adiada_raw)

    essencial_raw = (
        _campo(texto, "Essencial pra rodar")
        or _campo(texto, "Essencial pra concluir o processo")
        or ""
    )

    blocos = _parse_blocos(linhas)

    card = {
        "ref": f"{data}-{slug}",
        "slug": slug,
        "data": data,
        "arquivo": caminho.name,
        "path": _rel(caminho),
        "title": titulo_m.group(1).strip() if titulo_m else slug,
        "fonte": _campo(texto, "Fonte", ""),
        "item_relacionado": _campo(texto, "Item relacionado", ""),
        "adiada": int(adiada_m.group(0)) if adiada_m else 0,
        "categoria": categoria,
        "icon": "ti-bulb" if categoria == "Incremento" else "ti-settings",
        "essencial": essencial_raw.lower().startswith("sim"),
        "essencial_texto": essencial_raw,
        "revisar_quando": _campo(texto, "Revisar quando", ""),
        "contexto": _secao(linhas, "Contexto"),
        "perguntas": blocos,
        "parse_ok": bool(blocos),
        "estado": _estado(blocos) if blocos else "nao-parseavel",
    }
    if not blocos:
        card["raw"] = texto[:1500]
    return card


def listar_pendencias_ativas():
    """Contrato consumido por workflow.py: {cards, erro}. Nunca levanta."""
    try:
        execucao = _execucao_dir()
        if execucao is None:
            return {"cards": [], "erro": "esta plataforma não declara uma pasta de pendências"}
        if not execucao.exists():
            return {"cards": [], "erro": f"pasta não encontrada: {execucao}"}
        cards = [parse_pendencia(p) for p in sorted(execucao.glob("pendencia-ativa-*.md"))]
        cards = [c for c in cards if c]
        cards.sort(key=lambda c: (-c["adiada"], c["ref"]))
        return {"cards": cards, "erro": None}
    except Exception as e:  # nunca derruba a aba Workflow inteira
        return {"cards": [], "erro": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- escrita


def _caminho_de(ref):
    if not ref or not REF_RE.match(ref):
        raise PendenciaError("ref inválido")
    execucao = _execucao_dir()
    if execucao is None:
        raise PendenciaError("esta plataforma não declara uma pasta de pendências")
    caminho = execucao / f"pendencia-ativa-{ref}.md"
    try:
        caminho.resolve().relative_to(execucao.resolve())
    except ValueError:
        raise PendenciaError("ref fora da pasta de execução")
    if not caminho.is_file():
        raise PendenciaError("pendência ativa não encontrada")
    return caminho


def _opcao_por_linha(card, line_number):
    for bloco in card["perguntas"]:
        for op in bloco["opcoes"]:
            if op["line_number"] == line_number:
                return op
    return None


def responder(ref, line_number, expected_text, acao, texto=""):
    """Marca/desmarca uma opção ou preenche 'Outra resposta'. Só isso.

    Concorrência otimista: a linha no disco tem que bater com `expected_text`
    (o que o navegador leu), senão 409 — a rodada agendada do avanço pode ter
    mexido no arquivo no meio do caminho.
    """
    if acao == "adiar":
        acao = "marcar"  # marcar a linha de "Deixar para depois" é a mesma escrita
    if acao not in ("marcar", "desmarcar", "outra"):
        raise PendenciaError(f"ação desconhecida: {acao}")
    if not isinstance(line_number, int):
        raise PendenciaError("line_number precisa ser inteiro")

    with _LOCK:
        caminho = _caminho_de(ref)
        card = parse_pendencia(caminho)
        if card is None or not card["parse_ok"]:
            raise PendenciaError("pendência sem bloco de resposta reconhecível")

        opcao = _opcao_por_linha(card, line_number)
        if opcao is None:
            raise PendenciaError("linha não é uma opção de bloco de resposta")

        with caminho.open(encoding="utf-8", newline="") as f:
            conteudo = f.read()
        eol = "\r\n" if "\r\n" in conteudo else "\n"
        linhas = conteudo.split(eol)
        if not (0 <= line_number < len(linhas)):
            raise PendenciaError("line_number fora do arquivo")

        atual = linhas[line_number]
        if atual.rstrip("\r\n") != (expected_text or "").rstrip("\r\n"):
            raise ConflitoError(atual)

        m = CHECKBOX_RE.match(atual)
        if not m:
            raise PendenciaError("linha não contém checkbox")
        prefixo, _, meio, conteudo_linha = m.groups()

        if acao == "marcar":
            nova = f"{prefixo}x{meio}{conteudo_linha}"
        elif acao == "desmarcar":
            nova = f"{prefixo} {meio}{conteudo_linha}"
        else:  # outra
            if opcao["kind"] != "outra":
                raise PendenciaError("a linha escolhida não é 'Outra resposta'")
            limpo = (texto or "").strip()
            if not limpo:
                raise PendenciaError("texto vazio")
            if len(limpo) > MAX_TEXTO_OUTRA:
                raise PendenciaError(f"texto acima de {MAX_TEXTO_OUTRA} caracteres")
            if "\n" in limpo or "\r" in limpo:
                raise PendenciaError("texto precisa caber numa linha só")
            rotulo, _, _ = conteudo_linha.partition(":")
            nova = f"{prefixo}x{meio}{rotulo}: {limpo}"

        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUPS_DIR / f"{caminho.name}-{int(time.time())}.bak"
        shutil.copy2(caminho, backup)

        linhas[line_number] = nova
        with caminho.open("w", encoding="utf-8", newline="") as f:
            f.write(eol.join(linhas))

        atualizado = parse_pendencia(caminho)
        return {
            "ok": True,
            "new_line": nova,
            "estado": atualizado["estado"],
            "card": atualizado,
        }
