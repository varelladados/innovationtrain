"""Embarque — os primeiros passos de quem ainda não tem plataforma nenhuma.

Módulo **próprio**, e não mais um tipo dentro de `briefing.py`, por um motivo
concreto: os guardrails de lá pressupõem uma plataforma existente ("linha no
registro", "identificador pelo utilitário", "nunca pule etapa"). Aqui é
exatamente isso que ainda não existe. Os guardrails são outros — os de quem vai
criar arquivo numa pasta que talvez já tenha coisa dentro.

`gerar()` é **gerador puro: não escreve nada em disco**. O endpoint
`POST /api/embarque/prompt` é POST porque a entrada é um objeto de respostas
vindo do cliente, não porque escreve. Quem cria plataforma é a sessão de IA
onde o texto é colado, com a pessoa olhando.
"""
import json
import re
from pathlib import Path

import config

#: O que cada resposta do passo 3 acrescenta à plataforma.
USOS = {
    "notas": {
        "rotulo": "Guardar e organizar ideias",
        "sempre": True,
    },
    "decisoes": {
        "rotulo": "Registrar decisões que dependem de mim",
        "pastas": ["_pendencias"],
        "config": {"pendencias": "_pendencias"},
    },
    "projetos": {
        "rotulo": "Tocar projetos",
        "estagio_projetos": True,
    },
    "portfolio": {
        "rotulo": "Ver num só lugar tudo que já roda",
        "precisa": "projetos",
    },
}

DESTINOS = {
    "claude-code": "Claude Code",
    "codex": "Codex",
    "outro": "outra ferramenta",
}

GUARDRAILS = """## Guardrails deste setup — leia antes de criar qualquer coisa

- **Não apague e não sobrescreva nada que já exista nessa pasta.** Nenhum
  arquivo, nenhuma pasta, por nenhum motivo.
- **Se a pasta já tiver conteúdo, pare.** Liste o que tem e me mostre antes de
  criar qualquer coisa. Só siga depois que eu disser para seguir.
- **Não commite e não rode `git init`.** Eu quero olhar o que foi criado antes
  de a primeira versão existir.
- **Use caminhos absolutos** em tudo. Nada de `cd` no meio do caminho e nada de
  caminho relativo a um `cwd` que eu não sei qual é.
- **Não invente arquivo que não está na lista abaixo.** Se você achar que falta
  alguma coisa, me diga em vez de criar."""


def _slug(texto, limite=40):
    t = re.sub(r"[^A-Za-z0-9\-_ ]", "", texto or "").strip()
    t = re.sub(r"\s+", "-", t).lower()
    return t[:limite].strip("-") or "plataforma"


def _estagios(usos):
    """Os estágios da plataforma nova. Sem 'projetos', são três — e o produto
    inteiro aguenta isso: o config aceita N estágios e a aba Fluxo mostra N-1
    passagens."""
    base = [dict(e) for e in config.PADROES["estagios"]]
    if "projetos" not in usos:
        base = [e for e in base if e["n"] != 4]
    return base


def taxonomia(respostas):
    """O `plataforma.json` que o prompt vai mandar criar."""
    usos = set(respostas.get("usos") or []) | {"notas"}
    estagios = _estagios(usos)
    d = {
        "nome": (respostas.get("nome") or "").strip() or "Minha plataforma",
        "marcador": config.PADROES["marcador"],
        "estagios": estagios,
        "historico": config.PADROES["historico"],
        "arquivos": dict(config.PADROES["arquivos"]),
        "projetos": {"pasta": "4-projetos" if "projetos" in usos else "", "prefixo_re": None},
        "excluir": [".git", "node_modules", "__pycache__", ".claude"],
        "entrada": estagios[0]["pasta"],
    }
    if "projetos" in usos:
        d["tipos"] = list(config.PADROES["tipos"])
    for nome in usos:
        extra = (USOS.get(nome) or {}).get("config")
        if extra:
            d.update(extra)
    return d


def _pastas(respostas):
    usos = set(respostas.get("usos") or []) | {"notas"}
    hist = config.PADROES["historico"]
    pastas = []
    for e in _estagios(usos):
        pastas.append(f"{e['pasta']}/")
        pastas.append(f"{e['pasta']}/{hist}/")
    for nome in usos:
        for p in (USOS.get(nome) or {}).get("pastas", []):
            pastas.append(f"{p}/")
    return pastas


# ---------------------------------------------------------------- sementes

def _indice(tax, respostas):
    linhas = [f"# {tax['nome']}", "", "> A porta de entrada desta plataforma. Quem chega aqui — pessoa ou",
              "> sessão de IA — lê este arquivo primeiro.", "",
              "## Em 30 segundos", "",
              "<escreva aqui, em três frases: o que esta plataforma guarda e o que ela não é>",
              "", "## Os estágios", "",
              "| Pasta | O que tem aqui |", "|---|---|"]
    for e in tax["estagios"]:
        linhas.append(f"| `{e['pasta']}/` | {e['nome'].lower()} — <uma linha> |")
    linhas += ["",
               f"Dentro de cada uma, `{tax['historico']}/` guarda o que já avançou dali.",
               "", "## Onde estão as coisas", "",
               "| Arquivo | O que é |", "|---|---|",
               f"| `{tax['arquivos']['registro']}` | a linha do tempo de tudo. Append-only: nunca se apaga |",
               f"| `{tax['arquivos']['sem_destino']}` | gerado — o que ainda não avançou |",
               "| `plataforma.json` | os nomes: estágios, siglas, tipos |"]
    if "pendencias" in tax:
        linhas.append(f"| `{tax['pendencias']}/` | as decisões esperando por você |")
    linhas += ["", "## Como trabalhar aqui", "",
               "1. **Capturar é a operação mais barata:** cole e siga em frente.",
               "   Organizar é uma etapa própria, depois.",
               "2. **Nunca monte identificador à mão** — use o utilitário.",
               "3. **Nada é apagado.** Avançar move o original para o histórico do estágio.",
               ""]
    return "\n".join(linhas)


def _registro(tax):
    return "\n".join([
        "# Registro", "",
        "> **A linha do tempo desta plataforma.** Toda entrada aparece aqui uma",
        "> vez, no dia em que nasceu. Este arquivo é **append-only**: linha",
        "> nenhuma é editada ou apagada, nunca. Quando um item avança, a linha",
        "> dele ganha o marcador `→` com o destino, e o item novo ganha uma linha",
        "> própria.", "",
        "A tabela abaixo está vazia porque a plataforma acabou de nascer. A",
        "primeira linha entra quando você criar a primeira nota.", "",
        "| ID | Data | Etapa/Tipo | Local | Resumo | Link |",
        "|---|---|---|---|---|---|", "",
    ])


def _sem_destino(tax):
    linhas = ["# Sem destino", "",
              "> **Arquivo gerado.** Os blocos entre os marcadores são reescritos pelo",
              "> utilitário — não edite dentro deles. Fora dos marcadores é seu.", "",
              "O que está no registro e **ainda não avançou**.", ""]
    for e in tax["estagios"]:
        chave = e["sigla"].lower()
        # o corpo tem que ser o mesmo que o utilitario escreveria com zero
        # itens; senao o `verificar` acusa "desatualizado" numa plataforma que
        # acabou de nascer, e o primeiro contato com o sistema e' um alarme falso
        linhas += [f"## {e.get('plural') or e['nome']}", "",
                   f"<!-- gerado:{chave}:inicio -->",
                   "*(nada nesta etapa no momento)*",
                   f"<!-- gerado:{chave}:fim -->", ""]
    return "\n".join(linhas)


def _claude_md(tax):
    cadeia = " → ".join(e["sigla"] for e in tax["estagios"])
    nomes = " → ".join((e.get("plural") or e["nome"]).lower() for e in tax["estagios"])
    return "\n".join([
        f"# CLAUDE.md — {tax['nome']}", "",
        "> Este arquivo é lido automaticamente por qualquer sessão do Claude Code",
        "> que abrir nesta pasta. O que estiver aqui vale como contexto; o que",
        "> não estiver, a sessão não sabe.", "",
        "## O que é esta pasta", "",
        f"Uma plataforma da Estação: {nomes}. Toda ideia entra crua no primeiro",
        "estágio e vai amadurecendo. A porta de entrada é o `_indice.md`.", "",
        "## As regras que valem aqui", "",
        "- **O registro é append-only.** Nunca edite nem apague linha existente;",
        "  continuação usa o mesmo identificador com sufixo `-N`.",
        "- **Apagar é lógico, nunca físico.** Encerrar é mover para o",
        f"  `{tax['historico']}/` do estágio, não remover.",
        f"- **Nenhum item pula estágio:** {cadeia} em ordem, cada um com",
        "  identificador próprio e linha própria no registro.",
        "- **Identificador só pelo utilitário**, nunca montado à mão.",
        "- **Nenhuma decisão se fecha por inferência** — só a marcação explícita",
        "  da pessoa fecha uma pendência.", "",
        "## Como esta sessão salva o trabalho", "",
        "**Salvar é automático; publicar é decisão.**", "",
        "- **Commite sem pedir autorização** ao terminar um artefato e ao encerrar",
        "  a sessão. **Avise** numa linha o que entrou — não pergunte.",
        "- Adicione os arquivos **nominalmente**. Nunca `git add .`, nunca",
        "  `git add -A`.",
        "- Mudança que não foi você quem fez: liste no aviso e **deixe de fora**.",
        "- **Push só com autorização explícita e separada**, uma por vez.",
        "- Nunca commite segredo (chave, senha, `.env`, token) — sai do arquivo",
        "  mas fica no histórico.",
        "- **Nunca encerre a sessão deixando mudança sua sem commit.**", "",
        "Isto não é zelo excessivo: a regra oposta (\"só commite depois que eu",
        "mandar\") já custou trabalho perdido. Commit local não publicado se desfaz",
        "inteiro com `git reset --soft HEAD~1`, que mantém tudo no lugar — o custo",
        "de um commit a mais é zero.", "",
    ])


GITIGNORE = "\n".join([
    "cache/", "__pycache__/", "*.pyc", ".env", "*.log",
    "", "# temporários de editor", "*~", ".DS_Store", "Thumbs.db", "",
])


def sementes(tax, respostas):
    """(caminho relativo, conteúdo) de cada arquivo que o prompt manda criar."""
    arq = tax["arquivos"]
    return [
        ("plataforma.json", json.dumps(tax, ensure_ascii=False, indent=2) + "\n"),
        (arq["indice"], _indice(tax, respostas)),
        (arq["registro"], _registro(tax)),
        (arq["sem_destino"], _sem_destino(tax)),
        ("CLAUDE.md", _claude_md(tax)),
        (".gitignore", GITIGNORE),
    ]


# ---------------------------------------------------------------- o prompt

def gerar(respostas):
    """Devolve {'texto', 'caminho', 'nome', 'taxonomia'}. Não escreve nada."""
    respostas = respostas or {}
    caminho = (respostas.get("caminho") or "").strip()
    if not caminho:
        raise ValueError("informe onde a plataforma vai ficar")
    if len(caminho) < 3:
        raise ValueError("o caminho parece curto demais para ser uma pasta de verdade")

    tax = taxonomia(respostas)
    destino = DESTINOS.get(respostas.get("destino"), DESTINOS["outro"])
    tem_conteudo = respostas.get("tem_conteudo") == "tem"
    usos = set(respostas.get("usos") or []) | {"notas"}
    hub = config.hub_dir()
    util = hub / "metodo" / "plataforma.py"
    p = Path(caminho)

    L = [
        f"# Criar minha plataforma da Estação em `{p}`",
        "",
        f"Contexto: eu uso a **Estação**, um app local que organiza ideias em "
        f"estágios — do que acabou de chegar até o que virou projeto. Ela opera "
        f"*plataformas*, e eu ainda não tenho nenhuma. Você vai criar a primeira.",
        "",
        f"Não precisa entender o método inteiro para fazer isto: tudo que vai "
        f"dentro de cada arquivo está escrito abaixo, literal. O que eu preciso é "
        f"que a estrutura fique exatamente assim, para o app conseguir abrir.",
        "",
        GUARDRAILS,
        "",
        "## Passo 1 — confira a pasta antes de criar",
        "",
        f"```",
        f"{p}",
        f"```",
        "",
        "Liste o que existe aí dentro (inclusive arquivos ocultos) e me diga.",
    ]
    if tem_conteudo:
        L += ["",
              "**Eu já avisei que essa pasta tem trabalho começado.** Então: me "
              "mostre o que tem, e **espere eu responder** antes de criar "
              "qualquer coisa. Nada do que já está lá pode ser movido, renomeado "
              "ou apagado."]
    else:
        L += ["",
              "Eu acho que ela está vazia (ou nem existe ainda). Se tiver "
              "qualquer coisa dentro, **pare e me mostre** — eu me enganei, e aí "
              "a conversa é outra."]

    L += ["", "## Passo 2 — crie esta árvore", "", "```", f"{p.name}/"]
    for rel, _ in sementes(tax, respostas):
        L.append(f"├── {rel}")
    for pasta in _pastas(respostas):
        L.append(f"├── {pasta}")
    L += ["```", "",
          "As pastas ficam vazias por enquanto — isso é esperado. Se a sua "
          "ferramenta não guardar pasta vazia, tudo bem: o app cria o que faltar "
          "quando precisar.", "",
          "## Passo 3 — o conteúdo de cada arquivo", ""]

    for rel, conteudo in sementes(tax, respostas):
        lang = "json" if rel.endswith(".json") else ("" if rel == ".gitignore" else "markdown")
        L += [f"### `{rel}`", "", f"```{lang}", conteudo.rstrip("\n"), "```", ""]

    L += ["## Passo 4 — confira o que você fez", "",
          "Rode isto e me mostre a saída inteira:", "",
          "```",
          f"python {util.as_posix()} verificar --raiz {p.as_posix()}",
          "```", "",
          "O esperado é `tudo certo.` — ou, no máximo, avisos sobre pasta de "
          "estágio que não existe, se a sua ferramenta não criou pasta vazia.",
          "**Se aparecer PROBLEMA, não tente consertar sozinho: me mostre.**", "",
          "## Passo 5 — o que eu faço depois", "",
          "Quando terminar, me diga estas três coisas, nesta ordem:", "",
          f"1. que a plataforma está em `{p}` e já aparece no seletor da Estação;",
          "2. que o próximo passo é **abrir o app e criar a primeira nota** pela "
          "aba 📝 Nota — é a operação mais barata do sistema, e é assim que o "
          "registro ganha a primeira linha;",
          "3. que **você não commitou nada**, de propósito, e que depois de eu "
          "olhar a estrutura basta pedir para salvar o primeiro ponto — a partir "
          f"daí o `CLAUDE.md` que você acabou de criar faz as sessões seguintes "
          "salvarem sozinhas.", ""]

    if "decisoes" in usos:
        L += ["> Sobre as decisões: a pasta `_pendencias/` fica vazia agora. "
              "Quando uma dúvida sua depender de uma escolha, ela vira um arquivo "
              "lá — uma pergunta com opções — e aparece na aba Workflow do app.", ""]
    if "portfolio" in usos and "projetos" in usos:
        L += ["> Sobre o portfólio: cada projeto pode ter um `portfolio.json` "
              "dizendo o que ele publica (link no ar, protótipo em destaque). O "
              "app monta o Portfólio a partir disso. Não crie nenhum agora — "
              "ainda não há projeto.", ""]

    L += ["---", "",
          f"*Este texto foi gerado pela aba Embarque da Estação para ser colado "
          f"em {destino}. Ele não criou nada sozinho: quem cria é você, com eu "
          f"olhando.*", ""]

    return {
        "texto": "\n".join(L),
        "caminho": str(p),
        "nome": tax["nome"],
        "taxonomia": tax,
        "slug": _slug(tax["nome"]),
    }


def registrar(caminho, nome):
    """Acrescenta plataforma ao `estacao.json` do hub e a torna ativa.

    Escreve **só no config do hub** — nunca dentro de plataforma nenhuma. É a
    mesma disciplina do `/api/plataforma/ativar`. A pasta pode não existir ainda
    (o normal, logo depois do wizard): o seletor mostra isso e não deixa ativar.
    """
    caminho = str(Path((caminho or "").strip()))
    if len(caminho) < 3:
        raise ValueError("caminho inválido")
    dados = config.ler_estacao()
    regs = dados.setdefault("plataformas", [])
    for r in regs:
        if str(Path(r.get("caminho", ""))) == caminho:
            r["nome"] = nome or r.get("nome")
            config.escrever_estacao(dados)
            return r
    novo = {"nome": nome or Path(caminho).name, "caminho": caminho, "ativa": False}
    regs.append(novo)
    config.escrever_estacao(dados)
    return novo
