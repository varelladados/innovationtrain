"""Guarda-corpo da publicação: o que é privado não entra num repositório público.

Este repositório é **público**. Ele nasceu de um fork de um sistema pessoal, e a
publicação exigiu tirar os papéis de trabalho de toda a história — planos,
propostas, análises, backlogs e a curadoria de portfólio de quem o escreveu.

Sem um teste, isso volta. Um `git add` distraído, um documento colado na raiz
"só por um minuto", e o que era privado está publicado — e história não desfaz.
É a mesma ideia do `test_design_tokens.py`: a regra vira build.

**Este arquivo não nomeia nada que seja privado.** Ele cobra a *forma* — o
formato de nome de pasta de projeto do sistema de origem — e mantém uma lista do
que é permitido, que é curta e só tem nome deste projeto. Um teste que listasse
os nomes proibidos publicaria exatamente o que deveria proteger.
"""
import hashlib
import re
import subprocess
import sys
import unicodedata
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

#: Nomes de pasta do sistema de origem têm a forma `PJx-Nome` / `PRx-Nome`.
#: Qualquer coisa com essa forma que não esteja na lista de permitidos é um
#: vazamento em potencial.
#:
#: O lookbehind separa **nome de pasta** de **identificador**: em
#: `26.09.09-PRJ-APP-001-assunto-87eb` a parte depois da data é sigla + tipo +
#: sequência desta taxonomia, não pasta de projeto de terceiro.
#:
#: (E repare que o exemplo acima **precisa** vir com a data: escrito sem ela,
#: este próprio comentário derruba o teste. Foi o que aconteceu ao escrevê-lo.)
#: Sem ele, avançar um item para projeto com tipo declarado quebrava o
#: build — descoberto exercitando a ação avançar, não em revisão.
FORMA_PROJETO = re.compile(
    r"(?<!\d{2}\.\d{2}\.\d{2}-)\b(?:PJ|PR)[A-Z]-[A-Za-z][A-Za-z0-9_-]{2,}")

#: O que pode aparecer com essa forma. Tudo aqui é deste projeto ou genérico.
PERMITIDOS = {
    "PRJ-Estacao",        # o nome da pasta deste projeto antes do fork
    "PRJ-Explorer",       # um nome antigo deste projeto
    "PRJ-Teste_Console",  # fixture de teste
    "PRJ-Teste_X",        # fixture de teste (histórico)
    "PRJ-Qualquer",       # exemplo genérico (histórico)
    "PRJ-Outro",          # exemplo genérico em documentação
}
#: A sigla do quarto estágio combinada com um tipo declarado (`PRJ-app`) ou com
#: a sequência do dia (`PRJ-001`) — taxonomia do produto, não nome de pasta.
PERMITIDO_RE = re.compile(r"^PRJ-(?:[a-z]+|\d{3})$")

#: Papel de trabalho: plano, proposta, análise, backlog, curadoria de portfólio.
#: Casado por forma de nome, na raiz do repositório.
PAPEIS = [re.compile(p) for p in (
    r"^plano-.*\.md$", r"^propostas-.*\.md$", r"^analise-.*\.md$",
    r"^backlog-.*\.md$", r"^portfolio\.json$", r"^\.design/",
    r"^docs/backlog-", r"^docs/projeto-tecnico-", r"^docs/plano-",
)]

#: Configuração e decisões de quem usa — nunca versionadas.
NUNCA_VERSIONADO = ("estacao.json", "pendencias/")

TEXTO = {".py", ".md", ".html", ".htm", ".txt", ".json", ".bat", ".css", ".js"}


def git(*args):
    try:
        r = subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


RASTREADOS = git("ls-files")
PRECISA_GIT = unittest.skipIf(RASTREADOS is None,
                              "não é um repositório git, ou git fora do PATH")


@PRECISA_GIT
class TestNadaPrivadoRastreado(unittest.TestCase):
    def setUp(self):
        self.arquivos = [l for l in RASTREADOS.splitlines() if l.strip()]

    def test_nenhum_papel_de_trabalho(self):
        achados = [f for f in self.arquivos if any(p.search(f) for p in PAPEIS)]
        self.assertEqual(achados, [], f"papel de trabalho versionado: {achados}")

    def test_configuracao_e_decisoes_fora(self):
        for alvo in NUNCA_VERSIONADO:
            achados = [f for f in self.arquivos
                       if f == alvo or f.startswith(alvo.rstrip("/") + "/")]
            self.assertEqual(achados, [], f"`{alvo}` não pode ser versionado: {achados}")

    def test_o_gitignore_cobre_o_que_precisa(self):
        """Não basta não estar versionado hoje: tem que ser difícil entrar."""
        texto = (RAIZ / ".gitignore").read_text(encoding="utf-8")
        for padrao in ("estacao.json", "pendencias/", "plano-", "propostas-",
                       "analise-", "portfolio.json"):
            self.assertIn(padrao, texto, f".gitignore não cobre `{padrao}`")


@PRECISA_GIT
class TestNenhumNomeDeProjetoAlheio(unittest.TestCase):
    """A forma `PJx-Nome`/`PRx-Nome` só pode aparecer para coisas deste projeto."""

    def _fora(self, texto):
        return {m for m in FORMA_PROJETO.findall(texto)
                if m not in PERMITIDOS and not PERMITIDO_RE.match(m)}

    def test_historico_inteiro(self):
        """A árvore de hoje não basta: um `git revert` traria a de ontem de volta.

        Esta era a metade que faltava. O portao da publicação cobria a história;
        o teste, só o topo — e um teste que só olha o topo passa no dia seguinte
        à restauração do commit que ele deveria ter barrado.
        """
        saida = git("log", "--all", "-p", "--format=")
        if saida is None:
            self.skipTest("não consegui ler o histórico")
        self.assertEqual(self._fora(saida), set(),
                         "pasta de projeto alheio em algum commit")

    def test_arquivos_rastreados(self):
        fora = {}
        for rel in RASTREADOS.splitlines():
            rel = rel.strip()
            if not rel or Path(rel).suffix.lower() not in TEXTO:
                continue
            if rel.startswith("app/templates/vendor/"):
                continue          # biblioteca de terceiro, não é nosso texto
            caminho = RAIZ / rel
            if not caminho.is_file():
                continue
            for m in self._fora(caminho.read_text(encoding="utf-8", errors="replace")):
                fora.setdefault(m, []).append(rel)
        self.assertEqual(
            fora, {},
            "nome com forma de pasta de projeto do sistema de origem. Se for "
            "legítimo deste projeto, acrescente a PERMITIDOS; se não, ele não "
            "pode entrar num repositório público.")


@PRECISA_GIT
class TestHistoricoLimpo(unittest.TestCase):
    """A história foi reescrita uma vez para publicar. Isto verifica que ela
    continua limpa — e falha alto se alguém restaurar um commit antigo."""

    def test_nenhum_papel_de_trabalho_em_commit_nenhum(self):
        saida = git("log", "--all", "--name-only", "--format=")
        if saida is None:
            self.skipTest("não consegui ler o histórico")
        caminhos = {l.strip() for l in saida.splitlines() if l.strip()}
        achados = sorted(c for c in caminhos if any(p.search(c) for p in PAPEIS))
        self.assertEqual(achados, [],
                         f"papel de trabalho aparece no histórico: {achados}")


#: Radicais de vocabulário que não pode entrar aqui — os nomes próprios de uma
#: plataforma privada, que descreveriam o sistema de origem mesmo sem citar
#: projeto nenhum. Guardados por **hash**, e não em claro, pelo mesmo motivo da
#: lista de permitidos acima: um teste que escrevesse as palavras proibidas
#: publicaria exatamente o que deveria proteger.
#:
#: Cada entrada é o SHA-256 de um radical em minúsculas e sem acento. O teste
#: hasheia os prefixos de cada palavra que encontra, o que pega toda flexão sem
#: precisar listá-las.
RADICAIS_PROIBIDOS = {
    "18d195be01bd565c04f805f908c506083cf54cd365a5ab2996d1774d3e83bc8e",
    "ce68803976b2e4de4e8a1380b8a74f8c084e7a34e4a93cefce503cfbc96ee67b",
}
PREFIXO_MIN, PREFIXO_MAX = 4, 8

PALAVRA_RE = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


def _sem_acento(p):
    return unicodedata.normalize("NFKD", p.lower()).encode("ascii", "ignore").decode()


def _radicais_em(texto):
    """Radicais proibidos encontrados em `texto`, como hash (nunca como palavra).

    Devolve hash de propósito: nem a mensagem de falha reescreve a palavra que
    o arquivo existe para manter fora. Quem investigar procura o hash.
    """
    achados = set()
    for palavra in PALAVRA_RE.findall(texto):
        p = _sem_acento(palavra)
        for n in range(PREFIXO_MIN, min(len(p), PREFIXO_MAX) + 1):
            h = hashlib.sha256(p[:n].encode()).hexdigest()
            if h in RADICAIS_PROIBIDOS:
                achados.add(h[:12])
    return achados


@PRECISA_GIT
class TestVocabularioPrivado(unittest.TestCase):
    """O produto é genérico. Nome próprio de plataforma de alguém não entra.

    Isto não é preciosismo de estilo: o vocabulário estava em *código vivo* —
    chave de frontmatter que o app grava, caminho de arquivo de sistema, rótulo
    de métrica na interface. Tirar as palavras sem mover essas coisas para
    configuração teria quebrado a leitura da plataforma de origem; por isso a
    correção foi configuração, e por isso este teste vale a pena: ele falha no
    momento em que alguém volta a escrever no código o que é de uma plataforma.
    """

    def test_arquivos_rastreados(self):
        fora = {}
        for rel in RASTREADOS.splitlines():
            rel = rel.strip()
            if not rel or Path(rel).suffix.lower() not in TEXTO:
                continue
            if rel.startswith("app/templates/vendor/"):
                continue          # biblioteca de terceiro, não é nosso texto
            caminho = RAIZ / rel
            if not caminho.is_file():
                continue
            for h in _radicais_em(caminho.read_text(encoding="utf-8", errors="replace")):
                fora.setdefault(h, []).append(rel)
        self.assertEqual(
            fora, {},
            "vocabulário de uma plataforma privada em arquivo rastreado. O que o "
            "app lê e escreve tem que vir do config (`frontmatter`, `arquivos`, "
            "os caminhos opcionais), nunca escrito no código.")

    def test_mensagens_de_commit(self):
        saida = git("log", "--all", "--format=%B")
        if saida is None:
            self.skipTest("não consegui ler o histórico")
        achados = _radicais_em(saida)
        self.assertEqual(achados, set(),
                         "vocabulário de plataforma privada em mensagem de commit")

    def test_historico_inteiro(self):
        """Cobra a história, não só o topo: um `git revert` traria tudo de volta."""
        saida = git("log", "--all", "-p", "--format=")
        if saida is None:
            self.skipTest("não consegui ler o histórico")
        achados = _radicais_em(saida)
        self.assertEqual(achados, set(),
                         "vocabulário de plataforma privada em algum commit")


class TestOQueUmRepositorioPublicoPrecisa(unittest.TestCase):
    def test_licenca(self):
        lic = RAIZ / "LICENSE"
        self.assertTrue(lic.is_file(), "sem LICENSE, ninguém pode usar o código")
        texto = lic.read_text(encoding="utf-8")
        self.assertIn("Apache License", texto)
        self.assertNotIn("[name of copyright owner]", texto,
                         "o titular do copyright não foi preenchido")

    def test_readme(self):
        readme = RAIZ / "README.md"
        self.assertTrue(readme.is_file(), "sem README.md, o GitHub não tem porta de entrada")
        texto = readme.read_text(encoding="utf-8")
        self.assertIn("python app/server.py", texto, "o README não diz como rodar")

    def test_template_de_configuracao(self):
        """Quem clona precisa de um ponto de partida para o `estacao.json`."""
        import json
        exemplo = RAIZ / "estacao.exemplo.json"
        self.assertTrue(exemplo.is_file())
        dados = json.loads(exemplo.read_text(encoding="utf-8"))
        self.assertIn("plataformas", dados)
        for p in dados["plataformas"]:
            caminho = p.get("caminho", "")
            self.assertFalse(re.match(r"^[A-Za-z]:[\\/]", caminho),
                             f"caminho absoluto de outra máquina no template: {caminho}")


if __name__ == "__main__":
    unittest.main()
