"""Embarque — os primeiros passos de quem ainda não tem estação nenhuma.

Módulo **próprio**, e não mais um tipo dentro de `briefing.py`, por um motivo
concreto: os guardrails de lá pressupõem uma estação existente ("linha no
registro", "identificador pelo utilitário", "nunca pule etapa"). Aqui é
exatamente isso que ainda não existe. Os guardrails são outros — os de quem vai
criar arquivo numa pasta que talvez já tenha coisa dentro.

Desde a 0.10 o Embarque cria **as estações padrão de uma Central**, uma pasta
cada, lado a lado. Quais são, quantos estágios cada uma tem e para que servem
mora em `config.MODELOS`; aqui só se monta o texto. Desde a 0.13.2 elas nascem
ligadas pela triagem: cada `estacao.json` já diz onde ficam a estação privada e a
espera dentro dela (`_triagem`).

`gerar()` é **gerador puro: não escreve nada em disco**. O endpoint
`POST /api/embarque/prompt` é POST porque a entrada é um objeto de respostas
vindo do cliente, não porque escreve. Quem cria estação é a sessão de IA
onde o texto é colado, com a pessoa olhando.
"""
import json
import re
from pathlib import Path

import config

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


def _barra_normal(caminho):
    r"""Caminho com barra normal, venha de onde vier.

    `Path.as_posix()` NAO serve aqui: em POSIX ele nao reconhece `\` como
    separador e devolve o caminho do Windows intacto, com as barras invertidas
    que este texto existe para eliminar. O comando abaixo e' colado em
    PowerShell, cmd ou shell POSIX, e em um deles `\` vira escape.
    """
    return str(caminho).replace("\\", "/")


def _slug(texto, limite=40):
    t = re.sub(r"[^A-Za-z0-9\-_ ]", "", texto or "").strip()
    t = re.sub(r"\s+", "-", t).lower()
    return t[:limite].strip("-") or "estacao"


def taxonomia(modelo, nome=None, juntas=None):
    """O `estacao.json` de uma estação do modelo `modelo`.

    Os estágios são os primeiros N da taxonomia padrão: uma estação de três é
    captura → nota → ideia, e o produto inteiro aguenta isso — o config aceita N
    estágios e a aba Fluxo mostra N-1 passagens. Sem estágio de projetos, a
    chave `projetos` vai **nula**, que é o que diz "não há projetos" (uma pasta
    vazia diria "os projetos moram na raiz").

    `juntas` são os modelos que nascem na mesma pasta, este inclusive — por
    padrão, todos. É deles que sai a chave `triagem` (ver `_triagem`).
    """
    m = config.MODELOS[modelo]
    estagios = [dict(e) for e in config.PADROES["estagios"] if e["n"] <= m["estagios"]]
    d = {
        "nome": (nome or "").strip() or m["nome"],
        "modelo": modelo,
        "marcador": config.PADROES["marcador"],
        "estagios": estagios,
        "historico": config.PADROES["historico"],
        "arquivos": dict(config.PADROES["arquivos"]),
        "projetos": ({"pasta": estagios[-1]["pasta"], "prefixo_re": None}
                     if m["projetos"] else None),
        "excluir": [".git", "node_modules", "__pycache__", ".claude"],
        "entrada": estagios[0]["pasta"],
        "pendencias": "_pendencias",
    }
    if m["projetos"]:
        d["tipos"] = list(config.PADROES["tipos"])
    if m["privada"]:
        d["privada"] = True
    triagem = _triagem(modelo, list(config.MODELOS) if juntas is None else juntas)
    if triagem:
        d["triagem"] = triagem
    return d


def _triagem(modelo, juntas):
    """A chave `triagem` de uma estação que nasce ao lado de `juntas`.

    Cada estação diz, da própria raiz, para onde vai o que a triagem manda para
    outra esfera: `pessoal` (a estação privada), `espera` (a pasta dentro dela
    onde o bruto aguarda) e `administrativo`. `.` é ela mesma. Sem a chave, as
    saídas "espera" e "pessoal" da aba Nota e a aba Triagem só funcionavam
    depois de editar o `estacao.json` à mão.

    Só entra estação criada por este mesmo texto. Irmãs na mesma pasta, o
    `../<pasta>` fica certo mesmo que a pasta de cima mude de lugar. E a espera
    só vai para uma privada que este texto criou: de uma estação que a pessoa já
    tinha ele não sabe se é mesmo privada, e o bruto nunca espera em lugar
    versionado (`metodo/triagem.md`, regra 1).
    """
    def rel(outro):
        return "." if outro == modelo else f"../{config.MODELOS[outro]['pasta']}"

    por_esfera = {config.MODELOS[m]["esfera"]: m for m in juntas}
    d = {}
    if "pessoal" in por_esfera:
        d["pessoal"] = rel(por_esfera["pessoal"])
        d["espera"] = config.ESPERA if d["pessoal"] == "." else f"{d['pessoal']}/{config.ESPERA}"
    if "administrativo" in por_esfera:
        d["administrativo"] = rel(por_esfera["administrativo"])
    return d


def _espera_aqui(tax):
    """A pasta da espera, se ela mora dentro desta estação — a privada. Senão None."""
    espera = (tax.get("triagem") or {}).get("espera")
    return espera if espera and not espera.startswith("..") else None


def _pastas(tax):
    hist = tax["historico"]
    pastas = []
    for e in tax["estagios"]:
        pastas.append(f"{e['pasta']}/")
        pastas.append(f"{e['pasta']}/{hist}/")
    pastas.append(f"{tax['pendencias']}/")
    espera = _espera_aqui(tax)
    if espera:
        pastas.append(f"{espera}/")
    return pastas


# ---------------------------------------------------------------- sementes

def _indice(tax):
    m = config.MODELOS[tax["modelo"]]
    linhas = [f"# {tax['nome']}", "", "> A porta de entrada desta estação. Quem chega aqui — pessoa ou",
              "> sessão de IA — lê este arquivo primeiro.", ""]
    if m["privada"]:
        linhas += ["> **Estação privada.** Não é versionada nem compartilhada: sem git, sem",
                   "> nuvem, sem exportação. O backup dela é cópia de pasta.", ""]
    linhas += ["## Em 30 segundos", "",
               m["proposito"], "",
               "<escreva aqui, em três frases: o que esta estação guarda e o que ela não é>",
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
               "| `estacao.json` | os nomes: estágios, siglas, tipos |",
               f"| `{tax['pendencias']}/` | as decisões esperando por você |"]
    espera = _espera_aqui(tax)
    if espera:
        linhas.append(f"| `{espera}/` | a espera da triagem, de todas as estações: "
                      "o que chegou e ainda não se sabe de quem é |")
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
        "> **A linha do tempo desta estação.** Toda entrada aparece aqui uma",
        "> vez, no dia em que nasceu. Este arquivo é **append-only**: linha",
        "> nenhuma é editada ou apagada, nunca. Quando um item avança, a linha",
        "> dele ganha o marcador `→` com o destino, e o item novo ganha uma linha",
        "> própria.", "",
        "A tabela abaixo está vazia porque a estação acabou de nascer. A",
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
        # itens; senao o `verificar` acusa "desatualizado" numa estação que
        # acabou de nascer, e o primeiro contato com o sistema e' um alarme falso
        linhas += [f"## {e.get('plural') or e['nome']}", "",
                   f"<!-- gerado:{chave}:inicio -->",
                   "*(nada nesta etapa no momento)*",
                   f"<!-- gerado:{chave}:fim -->", ""]
    return "\n".join(linhas)


SALVAR = [
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
]

NAO_VERSIONA = [
    "## Esta estação não é versionada", "",
    "**Privada: nada daqui sai daqui.**", "",
    "- **Não rode `git init`**, não commite, não crie remoto, não faça push.",
    "- Não copie nada daqui para outra estação, repositório ou serviço sem eu",
    "  pedir, item por item.",
    "- O backup desta pasta é cópia de pasta, e quem faz sou eu.", "",
]


def _passagem(tax):
    """A regra de quem tem um trem menor: a ideia que serve a outras pessoas."""
    alvo = next((m["nome"] for m in config.MODELOS.values() if m["projetos"]), "de projetos")
    return [
        f"## Quando uma ideia daqui serve a outras pessoas", "",
        f"Uma ideia desta estação pode ser solução para outras pessoas. Quando for, ela",
        f"alimenta uma **captura nova na estação {alvo}** — o trem de inovação. É",
        "decisão e escrita, não cópia:", "",
        f"- a captura na {alvo} é **reescrita** para quem é de fora: nada daqui vai",
        "  literal;",
        "- ela nasce com identificador e linha próprios no registro de lá;",
        "- a linhagem cita esta estação e o identificador da ideia — e, se o",
        "  identificador disser demais sobre alguém, cita só a estação;",
        "- a ideia daqui **fica onde está**: ela não mudou de estágio.", "",
        "O critério está em `metodo/classificar.md`, na passagem entre estações.", "",
    ]


def _claude_md(tax):
    m = config.MODELOS[tax["modelo"]]
    cadeia = " → ".join(e["sigla"] for e in tax["estagios"])
    nomes = " → ".join((e.get("plural") or e["nome"]).lower() for e in tax["estagios"])
    linhas = [
        f"# CLAUDE.md — {tax['nome']}", "",
        "> Este arquivo é lido automaticamente por qualquer sessão do Claude Code",
        "> que abrir nesta pasta. O que estiver aqui vale como contexto; o que",
        "> não estiver, a sessão não sabe.", "",
        "## O que é esta pasta", "",
        f"Uma estação da Central. {m['proposito']}", "",
        f"O trem daqui: {nomes}. Toda entrada chega crua no primeiro estágio e vai",
        "amadurecendo. A porta de entrada é o `_indice.md`.", "",
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
    ]
    if not m["projetos"]:
        linhas += _passagem(tax)
    linhas += NAO_VERSIONA if m["privada"] else SALVAR
    return "\n".join(linhas)


GITIGNORE = "\n".join([
    "cache/", "__pycache__/", "*.pyc", ".env", "*.log",
    "", "# a trava de uma captura em andamento — some quando ela termina", "*.trava",
    "", "# temporários de editor", "*~", ".DS_Store", "Thumbs.db", "",
])


def sementes(tax):
    """(caminho relativo, conteúdo) de cada arquivo que o prompt manda criar."""
    arq = tax["arquivos"]
    saida = [
        ("estacao.json", json.dumps(tax, ensure_ascii=False, indent=2) + "\n"),
        (arq["indice"], _indice(tax)),
        (arq["registro"], _registro(tax)),
        (arq["sem_destino"], _sem_destino(tax)),
        ("CLAUDE.md", _claude_md(tax)),
    ]
    if not tax.get("privada"):
        # .gitignore é convite a versionar: a estação privada não recebe
        saida.append((".gitignore", GITIGNORE))
    return saida


# ---------------------------------------------------------------- o prompt

def estacoes(respostas, base):
    """As estações que o texto cria ou registra, na ordem de `config.MODELOS`.

    Cada modelo vem marcado para criar. Desmarcado **com** caminho é uma estação
    que a pessoa já tem: entra só no registro da Central, e o texto proíbe tocar
    nela. Desmarcado sem caminho não entra.
    """
    escolhas = respostas.get("estacoes") or {}
    saida = []
    for modelo, m in config.MODELOS.items():
        e = escolhas.get(modelo) or {}
        if e.get("criar", True):
            saida.append({"modelo": modelo, "nome": m["nome"], "criar": True,
                          "caminho": str(base / m["pasta"]) if base else ""})
            continue
        existente = (e.get("caminho") or "").strip()
        if existente:
            if len(existente) < 3:
                raise ValueError(f"o caminho da {m['nome']} parece curto demais")
            saida.append({"modelo": modelo, "nome": m["nome"], "criar": False,
                          "caminho": str(Path(existente))})
    return saida


def gerar(respostas):
    """Devolve {'texto', 'caminho', 'estacoes'}. Não escreve nada."""
    respostas = respostas or {}
    caminho = (respostas.get("caminho") or "").strip()
    base = Path(caminho) if caminho else None
    lista = estacoes(respostas, base)
    criar = [e for e in lista if e["criar"]]
    ja_tem = [e for e in lista if not e["criar"]]
    if not lista:
        raise ValueError("escolha pelo menos uma estação para criar ou registrar")
    if criar and not caminho:
        raise ValueError("informe onde as estações vão ficar")
    if criar and len(caminho) < 3:
        raise ValueError("o caminho parece curto demais para ser uma pasta de verdade")

    destino = DESTINOS.get(respostas.get("destino"), DESTINOS["outro"])
    tem_conteudo = respostas.get("tem_conteudo") == "tem"
    util = config.hub_dir() / "metodo" / "estacao.py"
    juntas = [e["modelo"] for e in criar]
    taxs = {e["modelo"]: taxonomia(e["modelo"], e["nome"], juntas) for e in criar}
    todos = " · ".join(m["nome"] for m in config.MODELOS.values())

    L = [f"# Criar as estações da minha Central em `{base}`" if criar
         else "# Registrar as estações que eu já tenho na minha Central", "",
         "Contexto: eu uso a **Central**, um app local que organiza ideias em "
         "estágios — do que acabou de chegar até o que virou projeto. Ela opera "
         f"*estações*, e toda Central começa com estas: {todos}.", ""]
    if criar:
        L += ["Você vai criar " + ("as três" if len(criar) == 3 else "estas") + ":", ""]
        L += [f"- **{e['nome']}**, em `{e['caminho']}` — "
              f"{config.MODELOS[e['modelo']]['proposito']}" for e in criar]
        L += [""]
    if ja_tem:
        L += ["Estas eu **já tenho**. **Não mexa nelas** — nada de listar, criar ou "
              "corrigir coisa lá dentro; elas só vão ser registradas na Central:", ""]
        L += [f"- **{e['nome']}**, em `{e['caminho']}`" for e in ja_tem]
        L += [""]
    L += ["Não precisa entender o método inteiro para fazer isto: tudo que vai "
          "dentro de cada arquivo está escrito abaixo, literal. O que eu preciso é "
          "que a estrutura fique exatamente assim, para o app conseguir abrir.", "",
          GUARDRAILS, ""]

    if not criar:
        L += ["Não há nada para criar. Me confirme que as pastas acima existem e "
              "pare por aí.", ""]
        return _fim(L, destino, base, lista)

    L += ["## Passo 1 — confira a pasta antes de criar", "",
          "```", f"{base}", "```", "",
          "Liste o que existe aí dentro (inclusive arquivos ocultos) e me diga."]
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

    L += ["", "## Passo 2 — crie esta árvore", "", "```", f"{base.name}/"]
    for e in criar:
        pasta = config.MODELOS[e["modelo"]]["pasta"]
        for rel, _ in sementes(taxs[e["modelo"]]):
            L.append(f"├── {pasta}/{rel}")
        for p in _pastas(taxs[e["modelo"]]):
            L.append(f"├── {pasta}/{p}")
    L += ["```", "",
          "As pastas ficam vazias por enquanto — isso é esperado. Se a sua "
          "ferramenta não guardar pasta vazia, tudo bem: o app cria o que faltar "
          "quando precisar.", "",
          "## Passo 3 — o conteúdo de cada arquivo", ""]

    for e in criar:
        pasta = config.MODELOS[e["modelo"]]["pasta"]
        for rel, conteudo in sementes(taxs[e["modelo"]]):
            lang = "json" if rel.endswith(".json") else ("" if rel == ".gitignore" else "markdown")
            L += [f"### `{pasta}/{rel}`", "", f"```{lang}", conteudo.rstrip("\n"), "```", ""]

    L += ["## Passo 4 — confira o que você fez", "",
          "Rode isto e me mostre a saída inteira:", "", "```"]
    L += [f"python {_barra_normal(util)} verificar --raiz {_barra_normal(e['caminho'])}"
          for e in criar]
    L += ["```", "",
          "O esperado é `tudo certo.` para cada uma — ou, no máximo, avisos sobre "
          "pasta de estágio que não existe, se a sua ferramenta não criou pasta vazia.",
          "**Se aparecer PROBLEMA, não tente consertar sozinho: me mostre.**", ""]
    return _fim(L, destino, base, lista, taxs)


def _fim(L, destino, base, lista, taxs=None):
    taxs = taxs or {}
    privadas = [t["nome"] for t in taxs.values() if t.get("privada")]
    versionam = [t["nome"] for t in taxs.values() if not t.get("privada")]
    if taxs:
        L += ["## Passo 5 — o que eu faço depois", "",
              "Quando terminar, me diga estas três coisas, nesta ordem:", "",
              f"1. que as estações estão em `{base}` e já aparecem no seletor da Central;",
              "2. que o próximo passo é **abrir o app e criar a primeira nota** pela "
              "aba 📝 Nota — é a operação mais barata do sistema, e é assim que o "
              "registro ganha a primeira linha;",
              "3. que **você não commitou nada**, de propósito."]
        if versionam:
            L += ["   Para " + " e ".join(versionam) + ", basta eu pedir o primeiro ponto "
                  "salvo: a partir daí o `CLAUDE.md` de cada uma faz as sessões salvarem "
                  "sozinhas."]
        if privadas:
            L += ["   " + " e ".join(privadas) + " **nunca** é versionada — nem agora, "
                  "nem depois."]
        L += ["", "> Sobre as decisões: cada estação tem uma pasta `_pendencias/`, vazia "
              "agora. Quando uma dúvida sua depender de uma escolha, ela vira um "
              "arquivo lá — uma pergunta com opções — e aparece na aba Workflow do app.", ""]
        espera = next((f"{config.MODELOS[t['modelo']]['pasta']}/{_espera_aqui(t)}/"
                       for t in taxs.values() if _espera_aqui(t)), None)
        if espera:
            L += [f"> Sobre a triagem: o que chega sem se saber de quem é espera em `{espera}`, "
                  "dentro da estação privada — nunca numa versionada. A chave `triagem` do "
                  "`estacao.json` de cada estação aponta para lá e para as outras estações: é o "
                  "que dá à aba 📝 Nota para onde mandar o que não é trabalho, e à aba 🧴 Triagem "
                  "o que mostrar.", ""]

    L += ["---", "",
          f"*Este texto foi gerado pela aba Embarque da Central para ser colado "
          f"em {destino}. Ele não criou nada sozinho: quem cria é você, com eu "
          f"olhando.*", ""]
    return {
        "texto": "\n".join(L),
        "caminho": str(base) if base else "",
        "estacoes": lista,
    }


def registrar(caminho, nome):
    """Acrescenta estação ao `central.json` do hub. **Não** a torna ativa.

    Escreve **só no config do hub** — nunca dentro de estação nenhuma. É a
    mesma disciplina do `/api/estacao/ativar`. A pasta pode não existir ainda
    (o normal, logo depois do wizard): o seletor mostra isso e não deixa ativar.
    """
    caminho = str(Path((caminho or "").strip()))
    if len(caminho) < 3:
        raise ValueError("caminho inválido")
    dados = config.ler_central()
    regs = dados.setdefault("estacoes", [])
    for r in regs:
        if str(Path(r.get("caminho", ""))) == caminho:
            r["nome"] = nome or r.get("nome")
            config.escrever_central(dados)
            return r
    novo = {"nome": nome or Path(caminho).name, "caminho": caminho, "ativa": False}
    regs.append(novo)
    config.escrever_central(dados)
    return novo


def registrar_varias(lista):
    """As estações do Embarque de uma vez, com a mesma disciplina de `registrar`."""
    if not lista:
        raise ValueError("nenhuma estação para registrar")
    return [registrar(e.get("caminho"), e.get("nome")) for e in lista]
