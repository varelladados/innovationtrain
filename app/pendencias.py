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


#: Os nomes que uma pasta de pendência tem quando a estação não declara a chave.
PASTAS_CONVENCIONAIS = ("_pendencias", "pendencias")


def _rotulo_da_ativa(cfg):
    """O nome da estação ativa como o `central.json` a chama.

    O `estacao.json` de uma estação pode chamá-la de outra coisa que o registro
    do hub: usar o nome do registro faz a ativa aparecer na lista com o mesmo
    rótulo das outras, em vez de dois nomes para a mesma coisa.
    """
    try:
        raiz = cfg.raiz.resolve()
    except OSError:
        return cfg.nome
    for reg in config.estacoes():
        caminho = reg.get("caminho")
        if not caminho or not reg.get("nome"):
            continue
        try:
            if Path(caminho).resolve() == raiz:
                return reg["nome"]
        except OSError:
            continue
    return cfg.nome


def _pastas_da_estacao(cfg, rotulo):
    """As pastas de pendência de uma estação: a que ela declara, e a de cada
    projeto dentro dela. Devolve [(rótulo da origem, Path)].

    Os dois níveis existem porque a estação só declara o primeiro: pendência de
    projeto mora no `_pendencias/` do próprio projeto (`T_*.md`, "as de cada
    projeto, no `_pendencias/` … do projeto"). Ler só o declarado é o que
    mantinha 23 das 28 pendências ativas invisíveis no app.
    """
    saida = []
    declarada = cfg.caminho("pendencias")
    if declarada and declarada.is_dir():
        saida.append((rotulo, declarada))
    elif not declarada:
        # Estação que não declara a chave (as do Embarque não declaram) ainda
        # pode ter a pasta pelo nome de sempre. Convenção como plano B da
        # configuração: sem isto a pendência existe no disco e some da tela.
        for nome in PASTAS_CONVENCIONAIS:
            p = cfg.raiz / nome
            if p.is_dir():
                saida.append((rotulo, p))
                break
    if not cfg.tem_projetos:
        return saida
    base = cfg.projetos_dir
    if not base.is_dir():
        return saida
    excluir = set(cfg.excluir)
    for proj in sorted(base.iterdir()):
        if not proj.is_dir() or proj.name.startswith("_") or proj.name in excluir:
            continue
        for nome in PASTAS_CONVENCIONAIS:
            p = proj / nome
            if p.is_dir():
                saida.append((f"{rotulo} › {proj.name}", p))
    return saida


def _pastas(escopo="estacao"):
    """Onde mora pendência-formulário, com o rótulo da origem de cada pasta.

    `escopo="estacao"` é só a estação ativa — é o que o snapshot estático e o
    briefing usam, e é o que preserva a fronteira da estação na publicação.
    `escopo="todas"` soma as outras estações do `central.json` e a pasta da
    própria Central: o console local mostra o que está em aberto no ecossistema
    inteiro, que é o que ninguém enxerga olhando uma estação de cada vez.

    Estação registrada cujo caminho não existe (volume não montado, pasta
    movida) é pulada em silêncio: a aba continua mostrando o resto.
    """
    vistos = set()
    saida = []

    def somar(pares):
        for rotulo, pasta in pares:
            try:
                chave = pasta.resolve()
            except OSError:
                continue
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append((rotulo, pasta))

    ativa = config.atual()
    somar(_pastas_da_estacao(ativa, _rotulo_da_ativa(ativa)))
    if escopo != "todas":
        return saida

    for reg in config.estacoes():
        caminho = reg.get("caminho")
        if not caminho or not Path(caminho).is_dir():
            continue
        try:
            cfg = config.carregar(caminho, reg.get("taxonomia"))
        except RuntimeError:
            continue  # estacao.json ilegível não derruba a lista inteira
        somar(_pastas_da_estacao(cfg, reg.get("nome") or cfg.nome))

    hub = config.hub_dir() / "pendencias"
    if hub.is_dir():
        somar([(config.hub_dir().name, hub)])
    return saida

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
    """Caminho relativo à raiz da estação; devolve o absoluto se estiver fora
    dela (pendência de outra estação, ou fixture em pasta temporária)."""
    try:
        return str(caminho.relative_to(config.atual().raiz)).replace("\\", "/")
    except ValueError:
        return str(caminho).replace("\\", "/")


def _dentro_da_ativa(caminho: Path):
    """O arquivo está sob a raiz da estação ativa?

    É o que decide se a UI pode oferecer "abrir arquivo": `/files/` serve só de
    dentro da raiz ativa, de propósito. Para a pendência de outra estação a tela
    mostra o caminho em vez de um link que daria 404.
    """
    try:
        caminho.resolve().relative_to(config.atual().raiz.resolve())
        return True
    except (ValueError, OSError):
        return False


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
        "local": _dentro_da_ativa(caminho),
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


def listar_pendencias_ativas(escopo="estacao"):
    """Contrato consumido por workflow.py: {cards, erro}. Nunca levanta.

    Cada card leva a `origem` — o rótulo da pasta de onde veio —, porque com
    mais de uma origem na mesma lista "de quem é esta decisão?" deixa de ser
    dedutível do título.
    """
    try:
        pastas = _pastas(escopo)
        if not pastas:
            declarada = config.atual().caminho("pendencias")
            if declarada is None:
                return {"cards": [], "erro": "esta estação não declara uma pasta de pendências"}
            return {"cards": [], "erro": f"pasta não encontrada: {declarada}"}
        cards = []
        for rotulo, pasta in pastas:
            for arquivo in sorted(pasta.glob("pendencia-ativa-*.md")):
                card = parse_pendencia(arquivo)
                if not card:
                    continue
                card["origem"] = rotulo
                cards.append(card)
        cards.sort(key=lambda c: (-c["adiada"], c["origem"], c["ref"]))
        return {"cards": cards, "erro": None}
    except Exception as e:  # nunca derruba a aba Workflow inteira
        return {"cards": [], "erro": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- escrita


def _caminho_de(ref, origem=None):
    """O arquivo de uma pendência ativa, procurado em todas as pastas conhecidas.

    `origem` é o rótulo que o card carrega; com ele a busca fica presa àquela
    pasta. Sem ele, duas estações com o mesmo `<data>-<slug>` tornam o `ref`
    ambíguo — e aí o pedido é recusado, em vez de escrever no arquivo errado.
    """
    if not ref or not REF_RE.match(ref):
        raise PendenciaError("ref inválido")
    pastas = _pastas("todas")
    if not pastas:
        raise PendenciaError("esta estação não declara uma pasta de pendências")
    achados = []
    for rotulo, pasta in pastas:
        if origem and rotulo != origem:
            continue
        caminho = pasta / f"pendencia-ativa-{ref}.md"
        try:
            caminho.resolve().relative_to(pasta.resolve())
        except (ValueError, OSError):
            continue  # ref que tenta sair da pasta
        if caminho.is_file():
            achados.append(caminho)
    if not achados:
        raise PendenciaError("pendência ativa não encontrada")
    if len(achados) > 1:
        raise PendenciaError("ref ambíguo entre origens: recarregue a lista")
    return achados[0]


def _opcao_por_linha(card, line_number):
    for bloco in card["perguntas"]:
        for op in bloco["opcoes"]:
            if op["line_number"] == line_number:
                return op
    return None


def responder(ref, line_number, expected_text, acao, texto="", origem=None):
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
        caminho = _caminho_de(ref, origem)
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
        # o card volta pra lista no lugar do antigo: sem a origem ele perderia
        # de onde veio e o próximo clique nele ficaria ambíguo
        atualizado["origem"] = origem or _origem_de(caminho)
        return {
            "ok": True,
            "new_line": nova,
            "estado": atualizado["estado"],
            "card": atualizado,
        }


def _origem_de(caminho: Path):
    """O rótulo da pasta em que este arquivo está, ou '' se não for uma conhecida."""
    try:
        pai = caminho.resolve().parent
    except OSError:
        return ""
    for rotulo, pasta in _pastas("todas"):
        try:
            if pasta.resolve() == pai:
                return rotulo
        except OSError:
            continue
    return ""
