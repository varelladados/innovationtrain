"""Configuração da plataforma ativa.

Antes do Trecho 3 a Estação assumia que morava *dentro* da plataforma: a raiz
era `PROJECT_DIR.parent` e cada módulo repetia caminhos do `C:\\Plataforma` como
constante literal. Este módulo é o que desfaz isso.

Duas coisas moram aqui:

1. **A taxonomia** — nomes de estágio, siglas, arquivos de sistema, tipos de
   projeto. Os padrões abaixo são a cópia executável de `metodo/taxonomia.md`,
   que é a fonte única. Uma plataforma pode sobrescrever qualquer chave no seu
   `plataforma.json`; o `plataforma de origem` sobrescreve pelo `estacao.json` do hub,
   justamente para não receber arquivo novo.

2. **A resolução da raiz**, nesta ordem: `--raiz` → `ESTACAO_PLATAFORMA` →
   plataforma ativa no `estacao.json` do hub → erro claro em português. Não há
   fallback para `PROJECT_DIR.parent`: fora do `plataforma de origem` ele não faz sentido e
   mascara erro de configuração como se fosse árvore vazia.

A configuração ativa é estado de módulo (`aplicar`/`atual`) e é lida **na hora
da chamada**, nunca no import — é isso que faz o seletor de plataforma trocar
de raiz sem reiniciar o servidor.
"""
import json
import os
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent          # o repositório da aplicação
HUB_DIR = PROJECT_DIR.parent          # o hub, onde vive o estacao.json

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
        {"n": 4, "pasta": "4-projetos", "nome": "Projeto", "plural": "Projetos", "sigla": "PRJ"},
    ],
    "historico": "_historico",
    "arquivos": {
        "indice": "_indice.md",
        "registro": "_registro.md",
        "sem_destino": "_sem-destino.md",
    },
    "tipos": ["app", "dados", "serviço", "curso"],
    "projetos": {"pasta": "4-projetos", "prefixo_re": None},
    "excluir": [".git", "node_modules", "__pycache__", ".claude", "dist", "build"],
    # Caminhos opcionais: quando ausentes, a aba correspondente degrada em vez
    # de estourar. O `plataforma de origem` preenche todos; uma plataforma nova, nenhum.
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
        return [e["sigla"] for e in self.estagios]

    @property
    def etapa_re(self):
        """Regex que casa a sigla de estágio (ex.: \\b(CAP|NOT|IDE|PRJ)\\b)."""
        return re.compile(r"\b(" + "|".join(re.escape(s) for s in self.siglas) + r")\b")

    @property
    def id_re(self):
        """Regex que reconhece um nome de arquivo já identificado (prefixo)."""
        siglas = "|".join(re.escape(s) for s in self.siglas)
        return re.compile(r"^\d{2}\.\d{2}\.\d{2}-(?:" + siglas + r")(?:-[A-Z]{3})?-\d+-")

    @property
    def identificador_re(self):
        """Regex do identificador inteiro, para achar dentro de um texto.

        Mesma forma que o utilitário gera — data, sigla, tipo opcional,
        sequência do dia, slug e hash. É por ela que as métricas reconhecem uma
        linha de registro de verdade.
        """
        siglas = "|".join(re.escape(s) for s in self.siglas)
        return re.compile(
            r"\b(\d{2}\.\d{2}\.\d{2})-(" + siglas + r")(?:-([A-Z]{2,4}))?"
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
            "ok": self.ok(),
        }


# ---------------------------------------------------------------- carga

def _fundir(base: dict, extra: dict) -> dict:
    """Merge raso, com um nível a mais em `arquivos` e `projetos`."""
    saida = dict(base)
    for k, v in (extra or {}).items():
        if k in ("arquivos", "projetos") and isinstance(v, dict):
            saida[k] = {**base.get(k, {}), **v}
        else:
            saida[k] = v
    return saida


def carregar(raiz, inline=None) -> Config:
    """Config de uma plataforma.

    `inline` é a taxonomia declarada no `estacao.json` do hub — é assim que o
    `plataforma de origem` é lido sem receber nenhum arquivo novo. Quando não há inline, lê o
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


def iniciar(argv=None) -> Config:
    """Resolve a raiz, carrega o config e o marca como ativo."""
    r, inline, origem = resolver(argv)
    cfg = carregar(r, inline)
    cfg.origem = f"{origem} · {cfg.origem}"
    return aplicar(cfg)
