"""Configuração da estação ativa.

Antes do Trecho 3 o app assumia que morava *dentro* da estação: a raiz
era `PROJECT_DIR.parent` e cada módulo repetia caminhos de uma estação
específica como constante literal. Este módulo é o que desfaz isso.

Duas coisas moram aqui:

1. **A taxonomia** — nomes de estágio, siglas, arquivos de sistema, tipos de
   projeto. Os padrões abaixo são a cópia executável de `metodo/taxonomia.md`,
   que é a fonte única. Uma estação pode sobrescrever qualquer chave no seu
   `estacao.json`; uma estação que não pode receber arquivo novo — uma
   pasta lida em modo somente-leitura, por exemplo — sobrescreve pelo
   `central.json` do hub em vez disso.

2. **A resolução da raiz**, nesta ordem: `--raiz` → `CENTRAL_ESTACAO` →
   estação ativa no `central.json` do hub → erro claro em português. Não há
   fallback para `PROJECT_DIR.parent`: fora da estação em que a Central
   nasceu ele não faz sentido, e mascara erro de configuração como se fosse
   árvore vazia.

A configuração ativa é estado de módulo (`aplicar`/`atual`) e é lida **na hora
da chamada**, nunca no import — é isso que faz o seletor de estação trocar
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
#: `metodo/` e `estacoes/` são irmãos na mesma raiz, e é ali que vive o
#: `central.json`. Quem quiser separar as coisas de novo usa `CENTRAL_DIR`.
HUB_DIR = PROJECT_DIR

#: A porta do servidor local. **Fonte única.** O `server.py` importa daqui e o
#: `iniciar-central.bat` pergunta ao Python em vez de repetir o número. O único
#: lugar que continua literal é o `.claude/launch.json`, que é JSON lido pelo
#: harness e não pode chamar código — e por isso tem um teste que cobra que os
#: dois digam a mesma coisa.
PORTA = 8744

CENTRAL_JSON = "central.json"
#: O nome do `central.json` até a 0.9. Ainda é lido, mas só quando tem formato de
#: Central (uma lista de registros): a partir da 0.10 `estacao.json` é também o
#: nome da config de cada estação, e as duas coisas não podem se confundir.
CENTRAL_JSON_ANTIGO = "estacao.json"
ESTACAO_JSON = "estacao.json"
#: O nome do `estacao.json` até a 0.9. Continua lido quando é o único que existe:
#: há estações de fora deste repositório que ainda o usam.
ESTACAO_JSON_ANTIGO = "plataforma.json"


# ---------------------------------------------------------------- padrões

#: Cópia executável de `metodo/taxonomia.md`. Mudou lá, muda aqui.
PADROES = {
    "nome": "Estação",
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
    #: Cada tipo é uma sigla (string) ou `{"sigla", "nome"}` — o nome é o que o
    #: Painel mostra ao lado da sigla, e sem ele mostra só a sigla.
    "tipos": ["app", "dados", "serviço", "curso"],
    #: Cópia executável da seção "Glossário" de `metodo/taxonomia.md`: os nomes
    #: que o produto usa para as próprias peças, cada um com o id pelo qual uma
    #: estação pode trocá-lo. `artigo` é o do rótulo genérico; `metafora` marca
    #: os sete termos ferroviários. Os estágios não entram aqui — já têm casa em
    #: `estagios`. Mudou lá, muda aqui (há um teste que compara).
    "vocabulario": {
        "central":     {"rotulo": "Central", "plural": "Central", "artigo": "a", "metafora": True,
                        "nota": "a aplicação, o que se abre no navegador"},
        "estacao":     {"rotulo": "estação", "plural": "estações", "artigo": "a", "metafora": True,
                        "nota": "um espaço de trabalho: uma pasta, com as suas ideias"},
        "projeto":     {"rotulo": "projeto", "plural": "projetos", "artigo": "o", "metafora": True,
                        "nota": "um trabalho que ganhou corpo próprio dentro da estação"},
        "trem":        {"rotulo": "trem", "plural": "trens", "artigo": "o", "metafora": True,
                        "nota": "a fila de pendências, passando uma por vez"},
        "embarque":    {"rotulo": "embarque", "plural": "embarque", "artigo": "o", "metafora": True,
                        "nota": "os primeiros passos: a aba que cria as estações"},
        "trilho":      {"rotulo": "trilho", "plural": "trilho", "artigo": "o", "metafora": True,
                        "nota": "a barra lateral, onde as abas se enfileiram"},
        "linha":       {"rotulo": "linha", "plural": "linha", "artigo": "a", "metafora": True,
                        "nota": "a sequência dos estágios, do primeiro ao último"},
        "registro":    {"rotulo": "registro", "plural": "registro", "artigo": "o", "metafora": False,
                        "nota": "o arquivo append-only, uma linha por item"},
        "indice":      {"rotulo": "índice", "plural": "índices", "artigo": "o", "metafora": False,
                        "nota": "o arquivo de orquestra de uma pasta; o da estação é o marcador"},
        "sem_destino": {"rotulo": "sem destino", "plural": "sem destino", "artigo": "o", "metafora": False,
                        "nota": "a lista do que está no registro e ainda não avançou"},
        "historico":   {"rotulo": "histórico", "plural": "histórico", "artigo": "o", "metafora": False,
                        "nota": "a subpasta de cada estágio com o que já avançou"},
        "pendencia":   {"rotulo": "pendência", "plural": "pendências", "artigo": "a", "metafora": False,
                        "nota": "uma decisão aberta, que só quem usa fecha"},
        "briefing":    {"rotulo": "briefing", "plural": "briefings", "artigo": "o", "metafora": False,
                        "nota": "o texto pronto para colar numa sessão de IA"},
        "capturar":    {"rotulo": "Capturar", "plural": "Capturar", "artigo": "", "metafora": False,
                        "nota": "o verbo do botão e do atalho que criam um item do primeiro estágio"},
        "tipo":        {"rotulo": "tipo", "plural": "tipos", "artigo": "o", "metafora": False,
                        "nota": "a classificação livre de um projeto"},
    },
    #: Um markdown da estação com os termos próprios dela por extenso — pode
    #: estar fora da raiz, como `trilha` e `fluxo`. A aba Fluxo o abre; o produto
    #: nunca o edita.
    "glossario": None,
    #: Nomes de campo de frontmatter que a estação usa. Não são caminhos: são
    #: chaves que o produto **lê e escreve**. Ficam aqui, e não literais no
    #: código, pelo mesmo motivo da raiz — uma estação com convenção própria
    #: declara a dela e continua sendo lida sem receber arquivo nenhum.
    "frontmatter": {
        "processado": "registro-id",  # o item já tem linha no registro
        "nucleo": None,               # marca "isto é maquinário, não conteúdo"
        "origem": [],                 # campos de linhagem no CLAUDE.md do projeto
    },
    "projetos": {"pasta": "5-projetos", "prefixo_re": None},
    #: Qual dos `MODELOS` esta estação segue. Sem estágio de projetos, a estação
    #: declara `"projetos": null` — que é diferente de `"pasta": ""` (os projetos
    #: morando na raiz).
    "modelo": "plataforma",
    #: Estação privada não sai daqui: exportação recusa e a aba Versões não oferece
    #: git. Ausente, vale o que o modelo diz.
    "privada": None,
    #: Siglas de uma taxonomia anterior, mapeadas para o número do estágio a que
    #: correspondem hoje (ex.: `{"SBC": 2, "SBI": 3, "SBZ": 5}`). Existe para uma
    #: estação que **já tinha acervo** quando adotou a Central: os
    #: identificadores antigos continuam válidos, reconhecidos e agrupados no
    #: estágio certo, sem reescrever registro (que é append-only) nem renomear
    #: pasta. Identificador **novo** nunca usa sigla legada — o utilitário recusa.
    "siglas_legadas": {},
    "excluir": [".git", "node_modules", "__pycache__", ".claude", "dist", "build"],
    # Caminhos opcionais: quando ausentes, a aba correspondente degrada em vez
    # de estourar. Uma estação madura preenche vários; uma recém-criada,
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
    #: Quem assina a vitrine — o nome e as personas que aparecem no topo dela.
    #: É de quem usa, não do produto: sem a chave a linha some, em vez de sair
    #: com um nome escrito no código.
    "assinatura": None,
    #: Pasta com uma cópia intacta desta estação, para `estacao.py
    #: reiniciar` devolvê-la ao estado de origem. **Só as estações de exemplo
    #: declaram isto**, e a ausência dela é o que torna reiniciar impossível numa
    #: estação de verdade: sem a chave, o comando recusa antes de olhar disco.
    "estado_inicial": None,
    #: Os instantâneos seguintes da trilha de exemplo — cada um é a estação
    #: inteira num estado adiante. Só as de exemplo declaram.
    "tutorial": None,
}

#: As estações com que toda Central começa — cópia executável da seção "As
#: estações de uma Central" de `metodo/taxonomia.md`, na ordem em que o Embarque
#: as oferece. As três são trens: o que muda é o tamanho e para que servem.
#: `esfera` é a da triagem que cada uma recebe — a matriz de destino de
#: `metodo/triagem.md` —, e é por ela que o Embarque escreve a chave `triagem`.
MODELOS = {
    "plataforma": {
        "nome": "Plataforma",
        "pasta": "plataforma",
        "estagios": 5,
        "projetos": True,
        "privada": False,
        "esfera": "profissional",
        "resumo": "o trem de inovação",
        "proposito": "O trem de inovação: ideias que podem virar funcionalidade, projeto e solução para outras pessoas.",
    },
    "admin_empresa": {
        "nome": "Admin_empresa",
        "pasta": "admin_empresa",
        "estagios": 3,
        "projetos": False,
        "privada": False,
        "esfera": "administrativo",
        "resumo": "a burocracia da empresa",
        "proposito": "A burocracia da empresa: RH, impostos, jurídico, contábil e tributário, financeiro.",
    },
    "vida_pessoal": {
        "nome": "Vida_Pessoal",
        "pasta": "vida_pessoal",
        "estagios": 3,
        "projetos": False,
        "privada": True,
        "esfera": "pessoal",
        "resumo": "a vida fora do trabalho",
        "proposito": "A vida fora do trabalho: deveres civis, família, tarefas, rotinas, lazer, amigos, a festa aqui em casa.",
    },
}
#: O modelo de quem não declara `modelo` — o que toda estação era antes dos outros dois.
MODELO_PADRAO = "plataforma"
#: A espera da triagem: a pasta, **dentro da estação privada**, onde o bruto
#: aguarda até se saber de quem é o assunto (`metodo/triagem.md`, regra 1). Não é
#: padrão de leitura — cada estação diz onde fica a dela em `triagem.espera`; é o
#: nome que o Embarque escreve ali.
ESPERA = "_triagem"


class Config:
    """Configuração resolvida de uma estação. Só leitura."""

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
        """Só as siglas, na ordem — o que entra no identificador e no filtro.

        Um tipo pode vir como string ou como `{"sigla", "nome"}`; aqui as duas
        formas viram a sigla, e quem quer o nome usa `tipos_detalhe`.
        """
        return [t["sigla"] for t in self.tipos_detalhe]

    @property
    def tipos_detalhe(self):
        """`[{"sigla", "nome"}]` — `nome` é None quando a estação não o declarou."""
        saida = []
        for t in self._d.get("tipos") or []:
            if isinstance(t, dict):
                sigla = str(t.get("sigla") or "").strip()
                if sigla:
                    saida.append({"sigla": sigla, "nome": t.get("nome") or None})
            elif str(t).strip():
                saida.append({"sigla": str(t).strip(), "nome": None})
        return saida

    def tipos_nome(self, sigla):
        """O que a sigla quer dizer, ou None — nunca um significado inventado."""
        for t in self.tipos_detalhe:
            if t["sigla"] == sigla:
                return t["nome"]
        return None

    # -- vocabulário ------------------------------------------------------
    @property
    def vocabulario(self):
        """O de-para dos nomes das peças, já mesclado com o padrão do método.

        `{id: {rotulo, plural, artigo, nota, metafora, generico, generico_plural,
        proprio}}`. `proprio` diz se a estação trocou o nome — é o que decide se
        a tela mostra o tooltip e se o briefing imprime os dois. Só os ids da
        tabela do método entram: id desconhecido é ignorado, de propósito.
        """
        declarado = self._d.get("vocabulario") or {}
        saida = {}
        for id_, gen in PADROES["vocabulario"].items():
            v = _normalizar_termo(declarado.get(id_))
            rotulo = v["rotulo"] if v else gen["rotulo"]
            proprio = bool(v) and rotulo != gen["rotulo"]
            plural = (v.get("plural") if v else None) or (gen["plural"] if not proprio else rotulo)
            artigo = v.get("artigo") if v else None
            if artigo is None:
                artigo = gen["artigo"] if not proprio else _artigo_de(rotulo)
            saida[id_] = {
                "rotulo": rotulo,
                "plural": plural,
                "artigo": artigo,
                "nota": (v.get("nota") if v else None) or gen["nota"],
                "metafora": gen["metafora"],
                "generico": gen["rotulo"],
                "generico_plural": gen["plural"],
                "proprio": proprio,
            }
        return saida

    def termo(self, id_, plural=False):
        """Como esta estação chama a peça `id_`; o id cru se ele não existe."""
        v = self.vocabulario.get(id_)
        if not v:
            return id_
        return v["plural"] if plural else v["rotulo"]

    def termo_duplo(self, id_, plural=False):
        """`Rótulo (genérico)` quando a estação trocou o nome; só o genérico se não.

        É o que o briefing imprime: a IA vai ler os documentos do método e
        precisa casar as duas palavras.
        """
        v = self.vocabulario.get(id_)
        if not v:
            return id_
        proprio = v["plural"] if plural else v["rotulo"]
        if not v["proprio"]:
            return proprio
        return f"{proprio} ({v['generico_plural'] if plural else v['generico']})"

    def artigo(self, id_):
        v = self.vocabulario.get(id_)
        return v["artigo"] if v else "o"

    def artigo_estagio(self, n):
        """O artigo do nome do estágio `n`: o declarado, senão deduzido do nome."""
        for e in self.estagios:
            if e["n"] == n:
                return e.get("artigo") or _artigo_de(e["nome"])
        return "o"

    def estagio_duplo(self, n, plural=False):
        """`Nome (padrão)` quando a estação renomeou o estágio em relação ao
        método; só o nome se não — o par de `termo_duplo` para os estágios."""
        for e in self.estagios:
            if e["n"] == n:
                nome = (e.get("plural") or e["nome"]) if plural else e["nome"]
                padrao = next((p for p in PADROES["estagios"] if p["n"] == n), None)
                if padrao:
                    nome_padrao = (padrao.get("plural") or padrao["nome"]) if plural else padrao["nome"]
                    if nome_padrao != nome:
                        return f"{nome} ({nome_padrao})"
                return nome
        return ""

    @property
    def excluir(self):
        return list(self._d.get("excluir") or [])

    def fm(self, qual):
        """Nome do campo de frontmatter `qual`, como esta estação o chama.

        `processado` sempre devolve algo (o padrão); `nucleo` devolve `None`
        quando a estação não tem esse conceito, e quem chama some com a
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
    def tem_projetos(self):
        """`"projetos": null` quer dizer "esta estação não tem projetos"."""
        return self._d.get("projetos") is not None

    @property
    def modelo(self):
        return self._d.get("modelo") or MODELO_PADRAO

    @property
    def privada(self):
        """A chave explícita vence; sem ela, vale o que o modelo diz."""
        valor = self._d.get("privada")
        if valor is None:
            valor = (MODELOS.get(self.modelo) or {}).get("privada", False)
        return bool(valor)

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
        """{sigla antiga: número do estágio}, da estação que já tinha acervo."""
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

        Reconhece também as legadas: um registro anterior à adoção da Central
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
        """A raiz aponta mesmo para uma estação?"""
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
            "arquivos": {k: self.arquivo_rel(k) for k in ("indice", "registro", "sem_destino")},
            "entrada": self.get("entrada"),
            "historico": self.historico,
            "siglas_legadas": self.siglas_legadas,
            # O vocabulário é da estação, não dado pessoal: viaja para a tela
            # e para o snapshot. O glossário é um caminho relativo à raiz dela.
            "vocabulario": self.vocabulario,
            "tipos_detalhe": self.tipos_detalhe,
            "glossario": self.get("glossario"),
            "ok": self.ok(),
            "modelo": self.modelo,
            "privada": self.privada,
            "tem_projetos": self.tem_projetos,
            # A interface só oferece "reiniciar" onde ele existe. Uma estação
            # de verdade não declara `estado_inicial`, e o botão nem aparece —
            # a mesma chave que faz o utilitário recusar.
            "exemplo": bool(self.get("estado_inicial")),
        }


# ---------------------------------------------------------------- carga

def _normalizar_termo(valor):
    """Um termo de `vocabulario` como a estação o escreveu — string ou objeto —
    vira sempre objeto com `rotulo`. Qualquer outra coisa vira None (ignorado)."""
    if isinstance(valor, str):
        valor = valor.strip()
        return {"rotulo": valor} if valor else None
    if isinstance(valor, dict) and str(valor.get("rotulo") or "").strip():
        return {**valor, "rotulo": str(valor["rotulo"]).strip()}
    return None


def _artigo_de(palavra):
    """O artigo definido de um nome, deduzido da terminação — para o rótulo que
    a estação declarou sem dizer o artigo, e para o nome dos estágios."""
    p = (palavra or "").strip().lower()
    p = p.split()[-1] if p.split() else p
    if p.endswith(("a", "ção", "são", "ade", "agem", "ice", "ência")):
        return "a"
    return "o"


def _fundir(base: dict, extra: dict) -> dict:
    """Merge raso, com um nível a mais em `arquivos`, `projetos`, `frontmatter`
    e `vocabulario` — a estação que declara um termo mantém os outros."""
    saida = dict(base)
    for k, v in (extra or {}).items():
        if k in ("arquivos", "projetos", "frontmatter", "vocabulario") and isinstance(v, dict):
            saida[k] = {**base.get(k, {}), **v}
        else:
            saida[k] = v
    return saida


def carregar(raiz, inline=None) -> Config:
    """Config de uma estação.

    `inline` é a taxonomia declarada no `central.json` do hub — é assim que uma
    estação é lida sem receber nenhum arquivo novo. Quando não há inline, lê o
    `estacao.json` da própria raiz — ou o `plataforma.json`, o nome até a 0.9,
    quando é o único que existe. Sem nenhum dos dois, valem os padrões.
    """
    raiz = Path(raiz)
    if inline:
        return Config(raiz, _fundir(PADROES, inline), origem=CENTRAL_JSON)

    arquivo = raiz / ESTACAO_JSON
    if not arquivo.exists() and (raiz / ESTACAO_JSON_ANTIGO).exists():
        arquivo = raiz / ESTACAO_JSON_ANTIGO
    if arquivo.exists():
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise RuntimeError(
                f"{arquivo} existe mas não pôde ser lido como JSON: {e}"
            ) from e
        return Config(raiz, _fundir(PADROES, dados), origem=arquivo.name)

    return Config(raiz, dict(PADROES), origem="padrões")


# ---------------------------------------------------------------- hub

def hub_dir() -> Path:
    """A pasta da Central. `ESTACAO_HUB` é o nome que a variável tinha até a 0.9."""
    env = os.environ.get("CENTRAL_DIR") or os.environ.get("ESTACAO_HUB")
    return Path(env) if env else HUB_DIR


def central_json() -> Path:
    return hub_dir() / CENTRAL_JSON


def _ler_json(p: Path):
    """JSON de um arquivo, ou None se ele não existe ou não se lê."""
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ler_central() -> dict:
    """Conteúdo do central.json. Ausente ou ilegível vira lista vazia — isso é
    um estado normal (Central recém-criada), não um erro.

    Sem `central.json`, vale o `estacao.json` da mesma pasta **se tiver formato
    de Central**. É o formato que separa os dois, porque `estacao.json` é também
    a config de uma estação: sem essa checagem, a taxonomia de alguém seria lida
    como lista de registros. A escrita vai sempre para o nome novo.
    """
    dados = _ler_json(central_json())
    if dados is None and not central_json().exists():
        antigo = _ler_json(hub_dir() / CENTRAL_JSON_ANTIGO)
        if isinstance(antigo, dict) and isinstance(antigo.get("plataformas"), list):
            dados = antigo
    if not isinstance(dados, dict):
        return {"estacoes": []}
    # a lista se chamava `plataformas` até a 0.9; a próxima escrita já sai com o nome novo
    if "estacoes" not in dados and isinstance(dados.get("plataformas"), list):
        dados["estacoes"] = dados.pop("plataformas")
    if not isinstance(dados.get("estacoes"), list):
        dados["estacoes"] = []
    return dados


def escrever_central(dados: dict):
    p = central_json()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def estacoes() -> list:
    """As estações registradas, na ordem do arquivo."""
    return ler_central().get("estacoes", [])


def estacao_ativa():
    """A entrada marcada `ativa`, ou a primeira, ou None."""
    regs = estacoes()
    for r in regs:
        if r.get("ativa"):
            return r
    return regs[0] if regs else None


def ativar(caminho) -> dict:
    """Marca uma estação como ativa no central.json e devolve a entrada."""
    alvo = str(Path(caminho))
    dados = ler_central()
    achou = None
    for r in dados.get("estacoes", []):
        mesma = str(Path(r.get("caminho", ""))) == alvo
        r["ativa"] = mesma
        if mesma:
            achou = r
    if achou is None:
        raise KeyError(f"estação não registrada no {CENTRAL_JSON}: {caminho}")
    escrever_central(dados)
    return achou


class EstacaoPrivada(RuntimeError):
    """Pediram para tirar daqui algo de uma estação privada."""


def recusar_se_privada(cfg, acao):
    """Levanta `EstacaoPrivada` se `cfg` é privada. `acao` é o que ia sair daqui."""
    if cfg.privada:
        raise EstacaoPrivada(
            f"{cfg.nome} é uma estação privada: {acao} não a inclui. Ela não é "
            "versionada nem compartilhada, de propósito.")


# ---------------------------------------------------------------- resolução

class RaizNaoResolvida(RuntimeError):
    """Nenhuma das quatro fontes disse onde fica estação."""


def resolver(argv=None):
    """Descobre qual estação usar. Devolve (raiz, inline, origem).

    Ordem: --raiz → CENTRAL_ESTACAO → estação ativa no central.json.
    Sem nenhuma delas, levanta RaizNaoResolvida com o texto que o usuário lê.
    """
    argv = list(argv if argv is not None else [])

    for i, a in enumerate(argv):
        if a == "--raiz" and i + 1 < len(argv):
            return Path(argv[i + 1]), None, "--raiz"
        if a.startswith("--raiz="):
            return Path(a.split("=", 1)[1]), None, "--raiz"

    for nome in ("CENTRAL_ESTACAO", "ESTACAO_PLATAFORMA"):   # o segundo: o nome até a 0.9
        if os.environ.get(nome):
            return Path(os.environ[nome]), None, nome

    reg = estacao_ativa()
    if reg and reg.get("caminho"):
        return Path(reg["caminho"]), reg.get("taxonomia"), CENTRAL_JSON

    raise RaizNaoResolvida(
        "Não sei qual estação abrir.\n"
        "\n"
        "A Central opera estações, e nenhuma foi indicada. Escolha uma destas:\n"
        f"  1. rode com --raiz C:\\caminho\\da\\estacao\n"
        f"  2. defina a variável de ambiente CENTRAL_ESTACAO\n"
        f"  3. registre uma estação em {central_json()}\n"
        "\n"
        "Se você ainda não tem estação nenhuma, é isso que a aba Embarque cria."
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
            "Nenhuma estação ativa: config.aplicar() não foi chamado no boot."
        )
    return _ATUAL


def definida() -> bool:
    return _ATUAL is not None


def raiz() -> Path:
    return atual().raiz


SEM_ESTACAO = "nenhuma estação configurada"


def sem_estacao() -> Config:
    """Config de quem ainda não tem estação nenhuma.

    A raiz aponta para o próprio hub, que não tem o marcador — então `ok()` é
    falso e **todo o resto degrada pelo caminho que já existe**, o mesmo da pasta
    que não é estação. Sem isto, `config.atual()` levantaria em cada endpoint
    e o primeiro contato com o produto seria um traceback.
    """
    cfg = carregar(hub_dir())
    cfg.origem = SEM_ESTACAO
    return aplicar(cfg)


def iniciar(argv=None) -> Config:
    """Resolve a raiz, carrega o config e o marca como ativo.

    Quando nada resolve — o caso de quem acabou de clonar — **não levanta**:
    devolve a config de `sem_estacao()`, para o servidor subir e a aba
    Embarque abrir. Quem quiser o erro chama `resolver()` direto.
    """
    try:
        r, inline, origem = resolver(argv)
    except RaizNaoResolvida:
        return sem_estacao()
    cfg = carregar(r, inline)
    cfg.origem = f"{origem} · {cfg.origem}"
    return aplicar(cfg)
