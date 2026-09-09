"""Versões — leitura do estado do git, e só leitura.

A Estação **lê** o git e **gera o texto**; quem executa é a sessão de IA, com o
humano olhando. Não é timidez: automatismo de commit mora onde a IA está, não
numa interface web onde um botão um dia é clicado sem querer.

Este módulo é o espelho invertido dos endpoints de escrita. Lá a disciplina é
allow-list de caminho, trava de concorrência e backup; aqui é **allow-list de
subcomando**: nenhum comando fora da lista roda, nunca com `shell=True`, sempre
com argumentos em lista, `--no-pager`, `timeout` e `cwd` explícito.

E **degrada, não estoura**. Git fora do PATH, pasta que não é repositório,
repositório sem remoto, remoto inacessível: cada um é um estado normal com
mensagem própria em português. Nenhum vira traceback, porque a aba que mostra
isso é justamente a que precisa funcionar quando as coisas não estão bem.
"""
import datetime
import subprocess
from pathlib import Path

TIMEOUT = 10

#: Nada fora daqui roda. A chave é o nome interno; o valor, os argumentos
#: exatos. Nenhum deles escreve: `status`, `log`, `branch --show-current`,
#: `rev-list --count`, `remote -v` e `diff --stat` são todos de leitura.
COMANDOS = {
    "status": ["status", "--porcelain=v1", "-b"],
    "log": ["log", "-n", "{k}", "--format=%H%x1f%ad%x1f%an%x1f%s", "--date=iso-strict"],
    "log_arquivos": ["log", "-n", "{k}", "--format=%x1e%H%x1f%ad%x1f%an%x1f%s",
                     "--date=iso-strict", "--name-only"],
    "branch": ["branch", "--show-current"],
    "nao_enviados": ["rev-list", "--count", "@{u}..HEAD"],
    "nao_trazidos": ["rev-list", "--count", "HEAD..@{u}"],
    "remote": ["remote", "-v"],
    "diff_stat": ["diff", "--stat"],
}

SEM_GIT = "git não está instalado (ou não está no PATH deste computador)"
NAO_E_REPO = "esta pasta não é um repositório — nada aqui está sendo versionado"
SEM_UPSTREAM = "esta linha de trabalho ainda não tem par na nuvem"


class Resultado:
    """Saída de um comando: `ok`, `saida`, `erro`. Nunca levanta."""

    __slots__ = ("ok", "saida", "erro")

    def __init__(self, ok, saida="", erro=None):
        self.ok, self.saida, self.erro = ok, saida, erro


def rodar(pasta, nome, **fmt):
    """Roda um comando da allow-list. Fora dela, levanta — é bug de código,
    não estado de usuário."""
    if nome not in COMANDOS:
        raise KeyError(f"comando fora da allow-list: {nome}")
    # substituicao literal, nao str.format: os argumentos do git contem chaves
    # de verdade (`@{u}..HEAD`), e format() as leria como placeholder.
    args = list(COMANDOS[nome])
    for chave, valor in fmt.items():
        alvo = "{" + chave + "}"
        args = [a.replace(alvo, str(valor)) for a in args]
    try:
        p = subprocess.run(["git", "--no-pager", "-C", str(pasta), *args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT)
    except FileNotFoundError:
        return Resultado(False, erro=SEM_GIT)
    except subprocess.TimeoutExpired:
        return Resultado(False, erro=f"o git demorou mais de {TIMEOUT}s e foi interrompido")
    except OSError as e:
        return Resultado(False, erro=f"não consegui chamar o git: {e}")
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip().splitlines()
        msg = msg[0] if msg else f"git {nome} falhou (código {p.returncode})"
        return Resultado(False, erro=msg)
    return Resultado(True, p.stdout)


def e_repositorio(pasta: Path):
    return (Path(pasta) / ".git").exists()


# ---------------------------------------------------------------- parsers

def _parse_status(texto):
    """`--porcelain=v1 -b`: a primeira linha é `## branch...ahead 2, behind 1`,
    as demais são `XY caminho`."""
    branch, arquivos = None, []
    for i, linha in enumerate(texto.splitlines()):
        if i == 0 and linha.startswith("## "):
            branch = linha[3:].split("...")[0].split(" ")[0].strip()
            continue
        if len(linha) < 4:
            continue
        estado, caminho = linha[:2], linha[3:].strip()
        if " -> " in caminho:                    # renomeado
            caminho = caminho.split(" -> ", 1)[1]
        arquivos.append({
            "caminho": caminho.strip('"'),
            "estado": estado,
            "rotulo": _rotulo_estado(estado),
            "novo": "?" in estado,
        })
    return branch, arquivos


def _rotulo_estado(estado):
    if "?" in estado:
        return "arquivo novo, nunca salvo"
    if "D" in estado:
        return "apagado"
    if "A" in estado:
        return "acrescentado"
    if "R" in estado:
        return "renomeado"
    return "modificado"


def _parse_log(texto):
    saida = []
    for bloco in texto.split("\x1e"):
        bloco = bloco.strip("\n")
        if not bloco:
            continue
        linhas = bloco.split("\n")
        partes = linhas[0].split("\x1f")
        if len(partes) < 4:
            continue
        h, data, autor, assunto = partes[:4]
        arquivos = [x for x in linhas[1:] if x.strip()]
        saida.append({"hash": h[:8], "data": data, "autor": autor,
                      "mensagem": assunto, "arquivos": arquivos,
                      "quantos_arquivos": len(arquivos),
                      "ha_quanto": _ha_quanto(data)})
    return saida


def _ha_quanto(data_iso):
    """"há 3 dias" comunica risco; um hash não comunica nada."""
    try:
        d = datetime.datetime.fromisoformat(data_iso)
    except (TypeError, ValueError):
        return None
    agora = datetime.datetime.now(d.tzinfo) if d.tzinfo else datetime.datetime.now()
    seg = (agora - d).total_seconds()
    if seg < 0:
        return "agora mesmo"
    if seg < 90:
        return "agora mesmo"
    if seg < 3600:
        return f"há {int(seg // 60)} min"
    if seg < 86400:
        h = int(seg // 3600)
        return f"há {h} hora" + ("s" if h > 1 else "")
    dias = int(seg // 86400)
    if dias == 1:
        return "ontem"
    if dias < 30:
        return f"há {dias} dias"
    meses = dias // 30
    return f"há {meses} " + ("mês" if meses == 1 else "meses")


# ---------------------------------------------------------------- backups

def backups(cache_dir: Path):
    """A camada de proteção que o usuário já tem e não sabe que tem."""
    pasta = Path(cache_dir) / "backups"
    if not pasta.is_dir():
        return {"quantos": 0, "desde": None, "pasta": str(pasta)}
    try:
        arqs = [p for p in pasta.iterdir() if p.is_file()]
    except OSError:
        return {"quantos": 0, "desde": None, "pasta": str(pasta)}
    if not arqs:
        return {"quantos": 0, "desde": None, "pasta": str(pasta)}
    mais_velho = min(p.stat().st_mtime for p in arqs)
    return {
        "quantos": len(arqs),
        "desde": datetime.datetime.fromtimestamp(mais_velho).strftime("%Y-%m-%d"),
        "pasta": str(pasta),
    }


# ---------------------------------------------------------------- o retrato

def estado(pasta, k=10):
    """Foto do momento da consulta — nunca verdade contínua.

    A automação do usuário pode commitar entre uma consulta e outra, e o VS Code
    também mexe. Por isso a saída carrega `consultado_em`: a aba mostra a hora,
    e quem lê sabe que está olhando uma foto.
    """
    pasta = Path(pasta)
    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    base = {"pasta": str(pasta), "consultado_em": agora, "e_repo": False,
            "erro": None, "branch": None, "sujos": [], "commits": [],
            "nao_enviados": None, "nao_trazidos": None, "remoto": None,
            "tem_remoto": False, "ultimo": None}

    if not pasta.exists():
        base["erro"] = "esta pasta não existe"
        return base
    if not e_repositorio(pasta):
        base["erro"] = NAO_E_REPO
        return base
    base["e_repo"] = True

    st = rodar(pasta, "status")
    if not st.ok:
        base["erro"] = st.erro
        return base
    branch, sujos = _parse_status(st.saida)
    base["branch"] = branch or None
    base["sujos"] = sujos

    if not base["branch"]:
        b = rodar(pasta, "branch")
        base["branch"] = b.saida.strip() if b.ok and b.saida.strip() else None

    lg = rodar(pasta, "log_arquivos", k=str(k))
    if lg.ok:
        base["commits"] = _parse_log(lg.saida)
        base["ultimo"] = base["commits"][0] if base["commits"] else None
    elif "does not have any commits" in (lg.erro or "") or "unknown revision" in (lg.erro or ""):
        base["commits"] = []      # repositório recém-criado, sem nenhum ponto salvo
    else:
        base["erro_log"] = lg.erro

    rm = rodar(pasta, "remote")
    base["tem_remoto"] = bool(rm.ok and rm.saida.strip())
    if base["tem_remoto"]:
        primeira = rm.saida.strip().splitlines()[0].split()
        base["remoto"] = primeira[1] if len(primeira) > 1 else None

    # `@{u}` FALHA com erro quando não há upstream — não assumir que devolve 0
    ne = rodar(pasta, "nao_enviados")
    if ne.ok and ne.saida.strip().isdigit():
        base["nao_enviados"] = int(ne.saida.strip())
    else:
        base["nao_enviados"] = None
        base["sem_upstream"] = True
    nt = rodar(pasta, "nao_trazidos")
    base["nao_trazidos"] = int(nt.saida.strip()) if nt.ok and nt.saida.strip().isdigit() else None

    return base


def semaforo(e):
    """Verde, âmbar ou vermelho para a pergunta que importa: tem trabalho meu
    que ainda não está salvo em lugar nenhum?"""
    if not e.get("e_repo"):
        return {"cor": "cinza", "titulo": "Esta pasta não é versionada",
                "texto": "Nada aqui tem ponto salvo. Uma sessão de IA cria o "
                         "repositório em um comando, quando você quiser."}
    novos = [a for a in e["sujos"] if a["novo"]]
    if not e["sujos"]:
        return {"cor": "verde", "titulo": "Tudo salvo",
                "texto": "Nenhuma mudança fora de um ponto salvo."}
    if novos:
        return {"cor": "vermelho",
                "titulo": f"{len(e['sujos'])} mudança(s) sem salvar, {len(novos)} em arquivo novo",
                "texto": "Arquivo novo nunca salvo é o único caso em que o "
                         "conteúdo não existe em lugar nenhum além do disco."}
    return {"cor": "ambar", "titulo": f"{len(e['sujos'])} mudança(s) sem salvar",
            "texto": "São alterações em arquivos que já têm histórico — a versão "
                     "anterior está guardada, a de agora não."}

# ---------------------------------------------------------------- prompts
#
# Os botões da aba geram texto; **não executam git**. O princípio é o do
# Trecho 8 do itinerário: a Estação lê o estado e escreve o pedido, quem executa
# é a sessão de IA com o humano olhando. Um botão numa interface web um dia é
# clicado sem querer; uma sessão de IA mostra o que vai fazer antes.

GUARDRAILS = """## Guardrails — valem sempre, e não são negociáveis

- **`git add` nominal.** Liste os arquivos e me peça confirmação antes de
  adicionar qualquer um. **Nunca `git add .`, nunca `git add -A`** — eles engolem
  arquivo que não devia entrar.
- **Não dê push** a menos que este pedido seja explicitamente sobre isso.
- **Nunca commite segredo** (chave, senha, `.env`, token). Sai do arquivo mas
  fica no histórico; é o único erro sem desfazer barato.
- **Não use `reset --hard`, `checkout -- .` nem `push --force`.** Os dois
  primeiros apagam trabalho não salvo e não têm desfazer; o terceiro reescreve o
  que está na nuvem e pode apagar trabalho de outra máquina.
- **Arquivo que eu não pedi fica de fora.** Se aparecer mudança que não é do que
  estamos fazendo, liste separado e não inclua."""


def _bloco_estado(e):
    linhas = [f"Repositório: `{e['pasta']}`",
              f"Linha de trabalho: `{e.get('branch') or '—'}`",
              f"Consultado em: {e['consultado_em']} (é uma foto: pode ter mudado desde então)", ""]
    if e.get("ultimo"):
        u = e["ultimo"]
        linhas.append(f"Último ponto salvo: {u['ha_quanto']} — `{u['hash']}` \"{u['mensagem']}\"")
    else:
        linhas.append("Ainda não existe nenhum ponto salvo neste repositório.")
    if e.get("nao_enviados"):
        linhas.append(f"Pontos salvos que ainda não subiram para a nuvem: {e['nao_enviados']}")
    elif e.get("sem_upstream"):
        linhas.append(f"{SEM_UPSTREAM.capitalize()} — nada foi enviado ainda.")
    linhas += ["", "O que está mudado agora (saída real do `git status`):", "", "```"]
    if e["sujos"]:
        for a in e["sujos"]:
            linhas.append(f"{a['estado']} {a['caminho']}   ({a['rotulo']})")
    else:
        linhas.append("(nada mudado — a árvore está limpa)")
    linhas.append("```")
    return "\n".join(linhas)


def prompt(tipo, e):
    """Texto para colar numa sessão de IA. `e` é a saída de `estado()`."""
    if tipo == "salvar":
        corpo = [
            "# Salvar um ponto neste repositório",
            "",
            "Quero guardar o trabalho que está aqui num ponto salvo (commit), para "
            "poder voltar nele depois. Não quero mandar nada para a nuvem agora.",
            "",
            _bloco_estado(e),
            "",
            "## O que eu quero que você faça",
            "",
            "1. Olhe o que mudou de verdade — use `git diff` se precisar — e "
            "**escreva a mensagem a partir disso**, não a partir do meu pedido. "
            "Uma linha dizendo o que mudou e por quê.",
            "2. **Me mostre a lista de arquivos que você vai incluir e espere eu "
            "confirmar.** Só depois disso rode o `git add`, nominalmente.",
            "3. Faça o commit e me diga a mensagem e quantos arquivos entraram.",
            "4. **Não dê push.**",
            "",
            GUARDRAILS,
        ]
    elif tipo == "nuvem":
        corpo = [
            "# Mandar os pontos salvos para a nuvem",
            "",
            "Quero publicar o que já está salvo aqui. Isto é uma decisão minha, "
            "e é a única operação desta lista que sai do meu computador.",
            "",
            _bloco_estado(e),
            "",
            "## O que eu quero que você faça",
            "",
            "1. Confirme comigo **qual remoto e qual linha de trabalho** vão "
            "receber, e **quantos pontos salvos** vão subir.",
            "2. Se houver mudança sem salvar na lista acima, **me avise antes** — "
            "ela não vai junto, e talvez seja isso que eu queria publicar.",
            "3. Só então dê o push. **Nunca com `--force`.**",
            "4. Se o remoto recusar (porque tem coisa lá que eu não tenho), "
            "**pare e me explique** em vez de forçar ou reescrever histórico.",
            "",
            GUARDRAILS,
        ]
    elif tipo == "linha":
        corpo = [
            "# Começar uma linha de trabalho nova",
            "",
            "Quero experimentar uma coisa sem mexer no que já está funcionando.",
            "",
            _bloco_estado(e),
            "",
            "## O que eu quero que você faça",
            "",
            "1. Se houver mudança sem salvar acima, **resolva isso primeiro**: "
            "ou salvamos um ponto, ou você me explica por que dá para levar junto.",
            "2. Sugira um nome curto para a linha nova, a partir do que eu quero "
            "fazer, e **confirme comigo** antes de criar.",
            "3. Crie e me diga como eu volto para a linha anterior quando quiser.",
            "",
            "> Uma observação honesta: linha de trabalho paralela resolve um "
            "problema que talvez eu ainda não tenha. Se uma só resolve, me diga "
            "isso em vez de criar a segunda.",
            "",
            GUARDRAILS,
        ]
    else:
        raise ValueError(f"tipo de prompt desconhecido: {tipo}")
    return "\n".join(corpo)
