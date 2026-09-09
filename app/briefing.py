"""Briefing pra IA — o pedaço "sub-harness" do console.

A IA não mora dentro deste app: o app é o espaço de trabalho do humano, e as
sessões do Claude Code / Codex são o processador. O que faltava era a ponte —
sair daqui com o texto certo pra colar lá, já com os caminhos reais e os
guardrails do método, em vez de reescrever o pedido toda vez.

Três briefings, todos derivados do estado real do disco:
- `pendencias`  — as que o humano já respondeu no app e esperam encaminhamento;
- `classificar` — uma Captura crua específica, contra o checklist do fluxo v2;
- `avancar`     — um projeto, com os itens [ESSENCIAL] abertos do backlog.

Os guardrails são **hardcoded** de propósito. Parsear `doutrina.md` pra montar o
texto deixaria o gerador quebrar em silêncio a cada edição de prosa; aqui eles
são estáveis e testáveis, e o briefing cita o caminho da doutrina pra IA ler a
íntegra quando precisar.
"""
import re
from pathlib import Path

import pendencias as pendencias_mod

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent.parent

DOUTRINA = "_metodo/doutrina.md"
CHECKLIST = "_metodo/templates/checklist-classificacao.md"
FLUXO = "_metodo/fluxo.v2.md"

GUARDRAILS = f"""## Guardrails (regras permanentes da plataforma de origem — íntegra em `{DOUTRINA}`)

- **Apagar é sempre lógico, nunca físico.** Rebaixar/consolidar acontece em índice e `.md`; pasta de Projeto/Ideia não some.
- **O LOG central (`1-capturas/LOG/_log.md`) é append-only.** Nunca edite nem apague linha existente; continuação usa o mesmo ID com sufixo `-N`.
- **Nunca pule etapa:** SBC → SBI → SBZ em ordem, cada uma com ID próprio e linha própria no LOG, mesmo que as três aconteçam na mesma sessão.
- **IDs só via `python _ferramentas/scripts/plataforma.py novo-id`** — nunca monte o ID à mão, e grave a linha do LOG antes de pedir o próximo (senão dois itens nascem com o mesmo SEQ).
- **Nunca fecha pendência por inferência** — só o campo `## Resposta` explícito fecha; "Deixar para depois" incrementa `**Adiada:**` e mantém ativa.
- **Nunca commite automaticamente**, e nunca dê push sem autorização explícita e separada.
- **Artefato de sessão vive no repositório**: plano, relatório ou análise substancial é copiado pra raiz do projeto com a convenção local (`plano-<assunto>-<AAAA-MM-DD>.md`) e commitado na mesma sessão.
- `.Biblioteca` fica de fora de tudo isso — nunca entra em stage automático."""


def _rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except (ValueError, TypeError):
        return str(p).replace("\\", "/")


def _cabecalho(titulo):
    return f"# {titulo}\n\nContexto: você está numa sessão do Claude Code com `cwd` em `C:\\Plataforma`."


def briefing_pendencias():
    """As pendências que o humano respondeu no console e ainda não foram encaminhadas."""
    dados = pendencias_mod.listar_pendencias_ativas()
    respondidas = [c for c in dados["cards"] if c["estado"] == "respondida"]
    adiadas = [c for c in dados["cards"] if c["estado"] == "adiada-marcada"]

    linhas = [_cabecalho("Encaminhar pendências respondidas no console"), ""]
    if not respondidas:
        linhas += ["Nenhuma pendência respondida aguardando encaminhamento agora.", ""]
    else:
        linhas += [
            f"O usuário respondeu **{len(respondidas)}** pendência(s) pela interface do "
            "Estação (marcou a opção no próprio arquivo). Processe cada uma com a "
            "skill `rotina-de-avanco` (passo 3 — pendências respondidas): aplique a decisão, "
            "renomeie o arquivo pra `pendencia-resolvida-*`, escreva o bloco "
            "`## Resolvida em <data>` explicando o que foi feito, e regenere "
            "`pendentes.md`/`chaves.md`.", "",
        ]
        for c in respondidas:
            marcadas = []
            for bloco in c["perguntas"]:
                for op in bloco["opcoes"]:
                    if not (op["marcado"] or (op["kind"] == "outra" and op["texto_livre"])):
                        continue
                    if op["kind"] == "outra" and op["texto_livre"]:
                        marcadas.append(op["texto_livre"])
                    else:
                        # label sozinho costuma ser só "A"/"B" — a razão é o que
                        # diz de fato o que foi escolhido
                        marcadas.append(
                            f"{op['label']} — {op['reason']}" if op["reason"] else op["label"])
            linhas.append(f"- `{c['path']}`")
            linhas.append(f"  - **{c['title']}**")
            if c["fonte"]:
                linhas.append(f"  - Fonte (chave de junção, não altere): `{c['fonte']}`")
            for m in marcadas:
                linhas.append(f"  - Resposta marcada: _{m}_")
        linhas.append("")
    if adiadas:
        linhas += [
            f"Além dessas, {len(adiadas)} está(ão) com \"Deixar para depois\" marcado — "
            "incremente `**Adiada:**`, volte o checkbox pra `[ ]` e mantenha ativa:", "",
        ]
        linhas += [f"- `{c['path']}` — {c['title']}" for c in adiadas]
        linhas.append("")
    linhas.append(GUARDRAILS)
    return {"texto": "\n".join(linhas), "itens": [c["path"] for c in respondidas]}


def briefing_classificar(path, text_cache=None):
    """Classificar uma Captura crua específica pelo checklist do fluxo v2."""
    if not path:
        raise ValueError("informe o caminho da Captura")
    rel = _rel(path)
    if "1-capturas" not in rel:
        raise ValueError("o caminho não está em 1-capturas")

    trecho = ""
    if text_cache:
        bruto = text_cache.get(rel, "")
        corpo = re.sub(r"^---\r?\n.*?\r?\n---\r?\n?", "", bruto, flags=re.DOTALL)
        trecho = " ".join(corpo.split())[:400]

    linhas = [
        _cabecalho("Classificar uma Captura crua"), "",
        f"Item: `{rel}`",
    ]
    if trecho:
        linhas += ["", f"> {trecho}…"]
    linhas += [
        "",
        f"O Passo 0 já está feito (o item tem ID e linha no LOG). Aplique o Passo 1 de "
        f"`{CHECKLIST}` — os 4 critérios (forma definida · serve de input sem reprocessar · "
        "é decisão/v1/resumo com próximos passos · deixou de ser ambíguo). **2 ou mais "
        "\"sim\" promovem a Ideia**; menos que isso, o item fica em `.pendente/`, e dúvida "
        f"genuína vai pro saco Refinar. O fluxo inteiro está em `{FLUXO}`.",
        "",
        "Se promover: gere o ID novo com `plataforma.py novo-id --etapa SBI --tipo <DIG|DAD|CON|ADE>`, "
        "crie `3-ideias/<ID>/<ID>.md` com `origem_captura:`, acrescente a **linha nova** "
        "no LOG e o marcador `→<ID-SBI>` na linha da SBC, e mova o arquivo pra `.historico/`.",
        "",
        GUARDRAILS,
    ]
    return {"texto": "\n".join(linhas), "itens": [rel]}


def briefing_avancar(pasta, entries, text_cache):
    """Avançar um projeto: o que está aberto e marcado como essencial."""
    from projetos import PASTA_RE  # import tardio: evita ciclo no boot
    if not pasta or not PASTA_RE.match(pasta):
        raise ValueError("pasta não é uma Projeto válida")

    backlogs = [e for e in entries if e["type"] == "backlog" and e["path"].startswith(pasta + "/")]
    essenciais, abertos_total = [], 0
    for b in backlogs:
        for linha in text_cache.get(b["path"], "").splitlines():
            if not linha.strip().startswith("- [ ]"):
                continue
            abertos_total += 1
            if "**[ESSENCIAL]**" in linha:
                texto = linha.strip()[5:].replace("**[ESSENCIAL]**", "").strip()
                essenciais.append((b["path"], " ".join(texto.split())[:180]))

    linhas = [
        _cabecalho(f"Avançar o projeto {pasta}"), "",
        f"Leia primeiro `{pasta}/CLAUDE.md` (a orquestra do projeto) e os backlogs:",
        "",
    ]
    linhas += [f"- `{b['path']}`" for b in backlogs] or ["- (nenhum backlog indexado)"]
    linhas += ["", f"Itens abertos: **{abertos_total}**, dos quais **{len(essenciais)}** marcados `[ESSENCIAL]`."]
    if essenciais:
        linhas += ["", "Essenciais (pré-requisito pra entregar):", ""]
        linhas += [f"- {texto}  \n  _em `{caminho}`_" for caminho, texto in essenciais]
    linhas += [
        "",
        "Avance o que der sozinho (código, doc, pesquisa) e transforme em "
        "pendência-formulário só o que depender de decisão do usuário — formato e "
        "regras em `_ferramentas/skills/rotina-de-avanco/SKILL.md`. Ao terminar, atualize "
        "o backlog e o changelog do projeto.",
        "",
        GUARDRAILS,
    ]
    return {"texto": "\n".join(linhas), "itens": [b["path"] for b in backlogs]}


def gerar(tipo, entries=None, text_cache=None, path=None, pasta=None):
    if tipo == "pendencias":
        resultado = briefing_pendencias()
    elif tipo == "classificar":
        resultado = briefing_classificar(path, text_cache)
    elif tipo == "avancar":
        resultado = briefing_avancar(pasta, entries or [], text_cache or {})
    else:
        raise ValueError(f"tipo de briefing desconhecido: {tipo}")
    resultado["tipo"] = tipo
    return resultado
