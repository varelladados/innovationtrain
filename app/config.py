"""Configuração da plataforma ativa.

Antes do Trecho 3 a Estação assumia que morava *dentro* da plataforma: a raiz
era `PROJECT_DIR.parent` e cada módulo repetia caminhos de uma plataforma
específica como constante literal. Este módulo é o que desfaz isso.

Duas coisas moram aqui:

1. **A taxonomia** — nomes de estágio, siglas, arquivos de sistema, tipos de
   projeto. Os padrões abaixo são a cópia executável de `metodo/taxonomia.md`,
   que é a fonte única. Uma plataforma pode sobrescrever qualquer chave no seu
   `plataforma.json`; uma plataforma que não pode receber arquivo novo — uma
   pasta lida em modo somente-leitura, por exemplo — sobrescreve pelo
   `estacao.json` do hub em vez disso.

2. **A resolução da raiz**, nesta ordem: `--raiz` → `ESTACAO_PLATAFORMA` →
   plataforma ativa no `estacao.json` do hub → erro claro em português. Não há
   fallback para `PROJECT_DIR.parent`: fora da plataforma em que a Estação
   nasceu ele não faz sentido, e mascara erro de configuração como se fosse
   árvore vazia.

A configuração ativa é estado de módulo (`aplicar`/`atual`) e é lida **na hora
da chamada**, nunca no import — é isso que faz o seletor de plataforma trocar
de raiz sem reiniciar o servidor.
"""
import json
import os
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent          # a raiz do repositório
#: **A raiz do repositório é o hub.** Até a unificação de 2026-09-09 o hub era a
#: pasta acima (o app vivia num repositório próprio dentro dele); agora `app/`,
#: `metodo/` e `plataformas/` são irmãos na mesma raiz, e é ali que vive o
#: `estacao.json`. Quem quiser separar as coisas de novo usa `ESTACAO_HUB`.
HUB_DIR = PROJECT_DIR

#: A porta do servidor local. **Fonte única.** O `server.py` importa daqui e o
#: `iniciar-estacao.bat` pergunta ao Python em vez de repetir o número. O único
#: lugar que continua literal é o `.claude/launch.json`, que é JSON lido pelo
#: harness e não pode chamar código — e por isso tem um teste que cobra que os
#: dois digam a mesma coisa.
PORTA = 8744

ESTACAO_JSON = "estacao.json"
PLATAFORMA_JSON = "plataforma.json"


# ---------------------------------------------------------------- padrões

#: Cópia executável de `metodo/taxonomia.md`. Mudou lá, muda aqui.
PADROES = {
    "nome": "Plataforma",
    "marcador": "_indice.md",
    "estagios": [
        {"n": 1, "pasta": "1-capturas", "nome": "Captura", "plural": "Capturas", "sigla": "CAP"},
        {"n": 2, "pasta": "2-notas", "nome": "Nota", "plural": "Notas", "sigla": "NOT"},
        {"n": 3, "pasta": "3-ideias", "nome": "Ideia", "plural": "Ideias", "sigla": "IDE"},
        {"n": 4, "pasta": "4-funcionalidades", "nome": "Funcionalidade", "plural": "Funcionalidades", "sigla": "FUN"},
        {"n": 5, "pasta": "5-projetos", "nome": "Projeto", "plural": "Projetos", "sigla": "PRJ"},
    ],
    "historico": "_historico",
    "arquivos": {
        "indice": "_indice.md",
        "registro": "_registro.md",
        "sem_destino": "_sem-destino.md",
    },
    "tipos": ["app", "dados", "serviço", "curso"],
    #: Nomes de campo de frontmatter que a plataforma usa. Não são caminhos: são
    #: chaves que o produto **lê e escreve**. Ficam aqui, e não literais no
    #: código, pelo mesmo motivo da raiz — uma plataforma com convenção própria
    #: declara a dela e continua sendo lida sem receber arquivo nenhum.
    "frontmatter": {
        "processado": "registro-id",  # o item já tem linha no registro
        "nucleo": None,               # marca "isto é maquinário, não conteúdo"
        "origem": [],                 # campos de linhagem no CLAUDE.md do projeto
    },
    "projetos": {"pasta": "5-projetos", "prefixo_re": None},
    #: Siglas de uma taxonomia anterior, mapeadas para o número do estágio a que
    #: correspondem hoje (ex.: `{"SBC": 2, "SBI": 3, "SBZ": 5}`). Existe para uma
    #: plataforma que **já tinha acervo** quando adotou a Estação: os
    #: identificadores antigos continuam válidos, reconhecidos e agrupados no
    #: estágio certo, sem reescrever registro (que é append-only) nem renomear
    #: pasta. Identificador **novo** nunca usa sigla legada — o utilitário recusa.
    "siglas_legadas": {},
    "excluir": [".git", "node_modules", "__pycache__", ".claude", "dist", "build"],
    # Caminhos opcionais: quando ausentes, a aba correspondente degrada em vez
    # de estourar. Uma plataforma madura preenche vários; uma recém-criada,
    # nenhum — e o app funciona nos dois casos.
    "perfis": None,             # pasta com os .json de maturidade do Portfólio
    "pendencias": None,         # pasta com pendencia-ativa-*.md
    "avanco_historico": None,   # historico.md da rotina de avanço
    "utilitario": None,         # script que gera identificador (novo-id)
    "trilha": None,             # documento da aba Tour
    "indice_projetos": None,    # índice canônico de projetos, se houver
    "indice_prefixo": None,     # prefixo que marca "isto é um índice de pasta"
    "entrada": None,            # onde nasce um item novo (padrão: estágio 1)
    "comando_sem_destino": "gerar-sem-destino",  # subcomando do utilitário
    "metricas_pastas": None,    # pastas contadas no Dashboard (padrão: os estágios)
    "ciclo_vida": [],           # subpastas de triagem dentro de um estágio
    "doutrina": None,           # documentos citados pelo briefing
    "checklist": None,
    "fluxo": None,
    "manifesto": None,          # documento com a frase-tese, usado pela vitrine
    "manifesto_marca": None,    # o rótulo que precede a frase dentro dele
    #: Pasta com uma cópia intacta desta plataforma, para `plataforma.py
    #: reiniciar` devolvê-la ao estado de origem. **Só as plataformas de exemplo
    #: declaram isto**, e a ausência dela é o que torna reiniciar impossível numa
    #: plataforma de verdade: sem a chave, o comando recusa antes de olhar disco.
    "estado_inicial": None,
    #: Os instantâneos seguintes da trilha de exemplo — cada um é a plataforma
    #: inteira num estado adiante. Só as de exemplo declaram.
    "tutorial": None,
}


class Config:
    """Configuração resolvida de uma plataforma. Só leitura."""

    def __init__(self, raiz: Path, dados: dict, origem: str = "padrões"):
        self.raiz = Path(raiz)
        self.origem = origem
        self._d = dados

    # -- acesso cru -------------------------------------------------------
    def get(self, chave, padrao=None):
        return self._d.get(chave, padrao)

    @property
    def nome(self):
        return self._d.get("nome") or self.raiz.name

    @property
    def marcador(self):
        return self._d["marcador"]

    @property
    def estagios(self):
        return self._d["estagios"]

    @property
    def historico(self):
        return self._d["historico"]

    @property
    def tipos(self):
        return list(self._d.get("tipos") or [])

    @property
    def excluir(self):
        return list(self._d.get("excluir") or [])

    def fm(self, qual):
        """Nome do campo de frontmatter `qual`, como esta plataforma o chama.

        `processado` sempre devolve algo (o padrão); `nucleo` devolve `None`
        quando a plataforma não tem esse conceito, e quem chama some com a
        métrica em vez de contar zero como se fosse informação; `origem`
        devolve uma lista, possivelmente vazia.
        """
        fm = self._d.get("frontmatter") or {}
        if qual == "origem":
            return list(fm.get("origem") or [])
        valor = fm.get(qual)
        if qual == "processado":
            return valor or PADROES["frontmatter"]["processado"]
        return valor

    # -- caminhos ---------------------------------------------------------
    def caminho(self, chave):
        """Caminho absoluto de uma chave opcional do config, ou None."""
        rel = self._d.get(chave)
        if not rel:
            return None
        return self.raiz / str(rel).replace("\\", "/")

    def arquivo(self, qual):
        """Caminho absoluto de um arquivo de sistema (indice/registro/sem_destino)."""
        rel = self._d["arquivos"].get(qual)
        if not rel:
            return None
        return self.raiz / str(rel).replace("\\", "/")

    def arquivo_rel(self, qual):
        rel = self._d["arquivos"].get(qual)
        return str(rel).replace("\\", "/") if rel else None

    @property
    def projetos_dir(self):
        pasta = (self._d.get("projetos") or {}).get("pasta")
        return self.raiz / pasta if pasta else self.raiz

    @property
    def projetos_prefixo_re(self):
        """Regex que reconhece pasta de projeto pelo nome, ou None.

        `None` significa "qualquer pasta dentro de projetos_dir é um projeto" —
        que é o caso da taxonomia nova, onde o prefixo foi eliminado.
        """
        p = (self._d.get("projetos") or {}).get("prefixo_re")
        return re.compile(p) if p else None

    def estagio_dir(self, n):
        for e in self.estagios:
            if e["n"] == n:
                return self.raiz / e["pasta"]
        return None

    # -- derivados --------------------------------------------------------
    @property
    def siglas(self):
        """As siglas **canônicas**, uma por estágio, na ordem.

        É esta lista que a interface mostra, que o briefing imprime como cadeia
        e da qual sai a sigla de todo identificador novo. Sigla legada não entra
        aqui de propósito — ela é reconhecida na leitura, nunca emitida.
        """
        return [e["sigla"] for e in self.estagios]

    @property
    def siglas_legadas(self):
        """{sigla antiga: número do estágio}, da plataforma que já tinha acervo."""
        d = self._d.get("siglas_legadas") or {}
        return {str(k): int(v) for k, v in d.items() if str(k) not in self.siglas}

    @property
    def siglas_todas(self):
        """Canônicas + legadas — o que as regex de leitura precisam reconhecer.

        As mais longas primeiro: numa alternância de regex, `SB` casaria antes de
        `SBC` e truncaria a captura. Ordenar por tamanho decrescente é o que
        garante que a sigla inteira vença.
        """
        return sorted(self.siglas + list(self.siglas_legadas),
                      key=lambda s: (-len(s), s))

    def estagio_de_sigla(self, sigla):
        """Número do estágio de uma sigla, canônica ou legada. None se não é sigla."""
        for e in self.estagios:
            if e["sigla"] == sigla:
                return e["n"]
        return self.siglas_legadas.get(sigla)

    def sigla_canonica(self, sigla):
        """A sigla de hoje para um estágio — traduz a legada, devolve a canônica
        intacta, e devolve a desconhecida como veio (quem chama decide o que fazer)."""
        n = self.estagio_de_sigla(sigla)
        if n is None:
            return sigla
        for e in self.estagios:
            if e["n"] == n:
                return e["sigla"]
        return sigla

    def _alt_siglas(self):
        return "|".join(re.escape(s) for s in self.siglas_todas)

    @property
    def etapa_re(self):
        """Regex que casa a sigla de estágio (ex.: \\b(CAP|NOT|IDE|FUN|PRJ)\\b).

        Reconhece também as legadas: um registro anterior à adoção da Estação
        continua sendo lido, e é isso que impede 154 linhas de virarem "outro".
        """
        return re.compile(r"\b(" + self._alt_siglas() + r")\b")

    @property
    def id_re(self):
        """Regex que reconhece um nome de arquivo já identificado (prefixo)."""
        return re.compile(
            r"^\d{2}\.\d{2}\.\d{2}-(?:" + self._alt_siglas() + r")(?:-[A-Z]{3})?-\d+-")

    @property
    def identificador_re(self):
        """Regex do identificador inteiro, para achar dentro de um texto.

        Mesma forma que o utilitário gera — data, sigla, tipo opcional,
        sequência do dia, slug e hash. É por ela que as métricas reconhecem uma
        linha de registro de verdade.
        """
        return re.compile(
            r"\b(\d{2}\.\d{2}\.\d{2})-(" + self._alt_siglas() + r")(?:-([A-Z]{2,4}))?"
            r"-(\d{3})-([a-z0-9-]+)-([a-f0-9]{4,5})\b")

    def ok(self):
        """A raiz aponta mesmo para uma plataforma?"""
        return (self.raiz / self.marcador).exists()

    def resumo(self):
        return {
            "nome": self.nome,
            "caminho": str(self.raiz),
            "origem": self.origem,
            "marcador": self.marcador,
            "estagios": self.estagios,
            "tipos": self.tipos,
            "trilha": self.get("trilha"),
            "registro": self.arquivo_rel("registro"),
            "historico": self.historico,
            "siglas_legadas": self.siglas_legadas,
            "ok": self.ok(),
            # A interface só oferece "reiniciar" onde ele existe. Uma plataforma
            # de verdade não declara `estado_inicial`, e o botão nem aparece —
            # a mesma chave que faz o utilitário recusar.
            "exemplo": bool(self.get("estado_inicial")),
        }


# ---------------------------------------------------------------- carga

def _fundir(base: dict, extra: dict) -> dict:
    """Merge raso, com um nível a mais em `arquivos`, `projetos` e `frontmatter`."""
    saida = dict(base)
    for k, v in (extra or {}).items():
        if k in ("arquivos", "projetos", "frontmatter") and isinstance(v, dict):
            saida[k] = {**base.get(k, {}), **v}
        else:
            saida[k] = v
    return saida


def carregar(raiz, inline=None) -> Config:
    """Config de uma plataforma.

    `inline` é a taxonomia declarada no `estacao.json` do hub — é assim que uma
    plataforma é lida sem receber nenhum arquivo novo. Quando não há inline, lê o
    `plataforma.json` da própria raiz. Sem nenhum dos dois, valem os padrões.
    """
    raiz = Path(raiz)
    if inline:
        return Config(raiz, _fundir(PADROES, inline), origem="estacao.json")

    arquivo = raiz / PLATAFORMA_JSON
    if arquivo.exists():
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise RuntimeError(
                f"{arquivo} existe mas não pôde ser lido como JSON: {e}"
            ) from e
        return Config(raiz, _fundir(PADROES, dados), origem=PLATAFORMA_JSON)

    return Config(raiz, dict(PADROES), origem="padrões")


# ---------------------------------------------------------------- hub

def hub_dir() -> Path:
    env = os.environ.get("ESTACAO_HUB")
    return Path(env) if env else HUB_DIR


def estacao_json() -> Path:
    return hub_dir() / ESTACAO_JSON


def ler_estacao() -> dict:
    """Conteúdo do estacao.json do hub. Ausente ou ilegível vira lista vazia —
    isso é um estado normal (hub recém-criado), não um erro."""
    p = estacao_json()
    if not p.exists():
        return {"plataformas": []}
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"plataformas": []}
    if not isinstance(dados.get("plataformas"), list):
        dados["plataformas"] = []
    return dados


def escrever_estacao(dados: dict):
    p = estacao_json()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def plataformas() -> list:
    """As plataformas registradas, na ordem do arquivo."""
    return ler_estacao().get("plataformas", [])


def plataforma_ativa():
    """A entrada marcada `ativa`, ou a primeira, ou None."""
    regs = plataformas()
    for r in regs:
        if r.get("ativa"):
            return r
    return regs[0] if regs else None


def ativar(caminho) -> dict:
    """Marca uma plataforma como ativa no estacao.json e devolve a entrada."""
    alvo = str(Path(caminho))
    dados = ler_estacao()
    achou = None
    for r in dados.get("plataformas", []):
        mesma = str(Path(r.get("caminho", ""))) == alvo
        r["ativa"] = mesma
        if mesma:
            achou = r
    if achou is None:
        raise KeyError(f"plataforma não registrada no {ESTACAO_JSON}: {caminho}")
    escrever_estacao(dados)
    return achou


# ---------------------------------------------------------------- resolução

class RaizNaoResolvida(RuntimeError):
    """Nenhuma das quatro fontes disse onde fica plataforma."""


def resolver(argv=None):
    """Descobre qual plataforma usar. Devolve (raiz, inline, origem).

    Ordem: --raiz → ESTACAO_PLATAFORMA → plataforma ativa no estacao.json.
    Sem nenhuma delas, levanta RaizNaoResolvida com o texto que o usuário lê.
    """
    argv = list(argv if argv is not None else [])

    for i, a in enumerate(argv):
        if a == "--raiz" and i + 1 < len(argv):
            return Path(argv[i + 1]), None, "--raiz"
        if a.startswith("--raiz="):
            return Path(a.split("=", 1)[1]), None, "--raiz"

    env = os.environ.get("ESTACAO_PLATAFORMA")
    if env:
        return Path(env), None, "ESTACAO_PLATAFORMA"

    reg = plataforma_ativa()
    if reg and reg.get("caminho"):
        return Path(reg["caminho"]), reg.get("taxonomia"), ESTACAO_JSON

    raise RaizNaoResolvida(
        "Não sei qual plataforma abrir.\n"
        "\n"
        "A Estação opera plataformas, e nenhuma foi indicada. Escolha uma destas:\n"
        f"  1. rode com --raiz C:\\caminho\\da\\plataforma\n"
        f"  2. defina a variável de ambiente ESTACAO_PLATAFORMA\n"
        f"  3. registre uma plataforma em {estacao_json()}\n"
        "\n"
        "Se você ainda não tem plataforma nenhuma, é isso que a aba Embarque cria."
    )


# ---------------------------------------------------------------- ativo

_ATUAL = None


def aplicar(cfg: Config) -> Config:
    global _ATUAL
    _ATUAL = cfg
    return cfg


def atual() -> Config:
    """A configuração ativa. Levanta se ninguém chamou `aplicar` ainda —
    o que é bug de boot, não estado de usuário."""
    if _ATUAL is None:
        raise RaizNaoResolvida(
            "Nenhuma plataforma ativa: config.aplicar() não foi chamado no boot."
        )
    return _ATUAL


def definida() -> bool:
    return _ATUAL is not None


def raiz() -> Path:
    return atual().raiz


SEM_PLATAFORMA = "nenhuma plataforma configurada"


def sem_plataforma() -> Config:
    """Config de quem ainda não tem plataforma nenhuma.

    A raiz aponta para o próprio hub, que não tem o marcador — então `ok()` é
    falso e **todo o resto degrada pelo caminho que já existe**, o mesmo da pasta
    que não é plataforma. Sem isto, `config.atual()` levantaria em cada endpoint
    e o primeiro contato com o produto seria um traceback.
    """
    cfg = carregar(hub_dir())
    cfg.origem = SEM_PLATAFORMA
    return aplicar(cfg)


def iniciar(argv=None) -> Config:
    """Resolve a raiz, carrega o config e o marca como ativo.

    Quando nada resolve — o caso de quem acabou de clonar — **não levanta**:
    devolve a config de `sem_plataforma()`, para o servidor subir e a aba
    Embarque abrir. Quem quiser o erro chama `resolver()` direto.
    """
    try:
        r, inline, origem = resolver(argv)
    except RaizNaoResolvida:
        return sem_plataforma()
    cfg = carregar(r, inline)
    cfg.origem = f"{origem} · {cfg.origem}"
    return aplicar(cfg)
