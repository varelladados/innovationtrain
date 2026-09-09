"""Briefing pra IA — o pedaço "sub-harness" do console.

A IA não mora dentro deste app: o app é o espaço de trabalho do humano, e as
sessões do Claude Code / Codex são o processador. O que faltava era a ponte —
sair daqui com o texto certo pra colar lá, já com os caminhos reais e os
guardrails do método, em vez de reescrever o pedido toda vez.

Três briefings, todos derivados do estado real do disco:
- `pendencias`  — as que o humano já respondeu no app e esperam encaminhamento;
- `classificar` — um item cru específico, contra o checklist do fluxo;
- `avancar`     — um projeto, com os itens [ESSENCIAL] abertos do backlog.

Os guardrails são **hardcoded** de propósito. Parsear `doutrina.md` pra montar o
texto deixaria o gerador quebrar em silêncio a cada edição de prosa; aqui eles
são estáveis e testáveis, e o briefing cita o caminho da doutrina pra IA ler a
íntegra quando precisar.
"""
import re
from pathlib import Path

import config
import pendencias as pendencias_mod

APP_DIR = Path(__file__).resolve().parent


def _doc(chave, fallback):
    """Caminho relativo de um documento do método, como declarado pela
    plataforma. Sem declaração, o briefing diz o nome genérico em vez de citar
    um arquivo que não existe."""
    return config.atual().get(chave) or fallback


def guardrails():
    """Bloco de regras permanentes, montado a partir do config.

    Continua **hardcoded** de propósito: só os *nomes* vêm do config. Parsear a
    prosa das regras para montar este texto o deixaria quebrar em silêncio a
    cada edição — o briefing cita o caminho para a IA ler a íntegra.
    """
    cfg = config.atual()
    doutrina = _doc("doutrina", "as regras do método")
    registro = cfg.arquivo_rel("registro") or "o registro"
    cadeia = " → ".join(cfg.siglas)
    util = cfg.get("utilitario")
    comando_id = f"`python {util} novo-id`" if util else "o utilitário da plataforma"
    return f"""## Guardrails (regras permanentes — íntegra em `{doutrina}`)

- **Apagar é sempre lógico, nunca físico.** Rebaixar/consolidar acontece em índice e `.md`; pasta de projeto não some.
- **O registro (`{registro}`) é append-only.** Nunca edite nem apague linha existente; continuação usa o mesmo ID com sufixo `-N`.
- **Nunca pule etapa:** {cadeia} em ordem, cada uma com ID próprio e linha própria no registro, mesmo que aconteçam na mesma sessão.
- **IDs só via {comando_id}** — nunca monte o ID à mão, e grave a linha do registro antes de pedir o próximo (senão dois itens nascem com o mesmo SEQ).
- **Nunca fecha pendência por inferência** — só o campo `## Resposta` explícito fecha; "Deixar para depois" incrementa `**Adiada:**` e mantém ativa.
- **Salvar é automático; publicar é decisão.** Commite local ao terminar, sem me pedir autorização — me **avise** o que entrou, não pergunte. `git add` **nominal**, nunca `git add .`. Mudança que não é sua fica de fora. **Push só com autorização explícita e separada.**
- **Artefato de sessão vive no repositório**: plano, relatório ou análise substancial é copiado pra raiz do projeto com a convenção local (`plano-<assunto>-<AAAA-MM-DD>.md`) e commitado na mesma sessão.
- O que a plataforma declarar em `excluir` fica de fora de tudo isso — nunca
  entra em stage automático."""


def _rel(p):
    try:
        return str(Path(p).relative_to(config.atual().raiz)).replace("\\", "/")
    except (ValueError, TypeError):
        return str(p).replace("\\", "/")


def _cabecalho(titulo):
    return (f"# {titulo}\n\nContexto: você está numa sessão do Claude Code com "
            f"`cwd` em `{config.atual().raiz}`.")


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
            "Estação (marcou a opção no próprio arquivo). Processe cada uma: "
            "aplique a decisão, renomeie o arquivo pra `pendencia-resolvida-*`, "
            "escreva o bloco `## Resolvida em <data>` explicando o que foi feito, "
            "e regenere o `sem-destino` da plataforma.", "",
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
    linhas.append(guardrails())
    return {"texto": "\n".join(linhas), "itens": [c["path"] for c in respondidas]}


def briefing_classificar(path, text_cache=None):
    """Classificar um item do primeiro estágio pelo checklist do método."""
    cfg = config.atual()
    e1, e2 = cfg.estagios[0], cfg.estagios[1]
    if not path:
        raise ValueError(f"informe o caminho d{'a' if e1['nome'][-1] == 'a' else 'o'} {e1['nome']}")
    rel = _rel(path)
    if e1["pasta"] not in rel:
        raise ValueError(f"o caminho não está em {e1['pasta']}")

    trecho = ""
    if text_cache:
        bruto = text_cache.get(rel, "")
        corpo = re.sub(r"^---\r?\n.*?\r?\n---\r?\n?", "", bruto, flags=re.DOTALL)
        trecho = " ".join(corpo.split())[:400]

    linhas = [
        _cabecalho(f"Classificar: {e1['nome']} → {e2['nome']}"), "",
        f"Item: `{rel}`",
    ]
    if trecho:
        linhas += ["", f"> {trecho}…"]
    checklist = _doc("checklist", "o checklist de classificação")
    fluxo = _doc("fluxo", "o documento do fluxo")
    util = cfg.get("utilitario") or "o utilitário da plataforma"
    tipos = "|".join(cfg.tipos) if cfg.tipos else "tipo"
    linhas += [
        "",
        f"O item já tem ID e linha no registro. Aplique o checklist de "
        f"`{checklist}` — os 4 critérios (forma definida · serve de input sem reprocessar · "
        "é decisão/v1/resumo com próximos passos · deixou de ser ambíguo). **2 ou mais "
        f"\"sim\" promovem a {e2['nome']}**; menos que isso, o item fica onde está, e dúvida "
        f"genuína vira pendência. O fluxo inteiro está em `{fluxo}`.",
        "",
        f"Se promover: gere o ID novo com `{util} novo-id --etapa {e2['sigla']} --tipo <{tipos}>`, "
        f"crie o arquivo em `{e2['pasta']}/` com `origem:`, acrescente a **linha nova** "
        f"no registro e o marcador `→<ID-{e2['sigla']}>` na linha de origem, e mova o "
        f"arquivo original para `{e1['pasta']}/{cfg.historico}/`.",
        "",
        guardrails(),
    ]
    return {"texto": "\n".join(linhas), "itens": [rel]}


def briefing_avancar(pasta, entries, text_cache):
    """Avançar um projeto: o que está aberto e marcado como essencial."""
    from projetos import _pasta_valida  # import tardio: evita ciclo no boot
    if not _pasta_valida(pasta):
        raise ValueError("pasta não é um projeto desta plataforma")

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
    pend = config.atual().get("pendencias")
    onde_regras = f"`{Path(pend).parent.as_posix()}/SKILL.md`" if pend else "o método da plataforma"
    linhas += [
        "",
        "Avance o que der sozinho (código, doc, pesquisa) e transforme em "
        "pendência-formulário só o que depender de decisão do usuário — formato e "
        f"regras em {onde_regras}. Ao terminar, atualize "
        "o backlog e o changelog do projeto.",
        "",
        guardrails(),
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
