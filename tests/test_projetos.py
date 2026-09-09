"""Testes da anotação em backlog de projeto (POST /api/projeto/anotar).

O risco aqui é escrever no backlog de um repo de verdade: a linha tem que entrar
no lugar certo (antes do rodapé `## Links`, que todo índice/backlog do método
usa), sem reescrever o resto do arquivo e sem trocar o fim de linha.
"""
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402  (insere app/ no sys.path)
import projetos  # noqa: E402


BACKLOG_COM_LINKS = """# Backlog — Teste

> Itens marcados **[ESSENCIAL]** são pré-requisito.

- [x] item feito
- [ ] **[ESSENCIAL]** item aberto importante
- [ ] outro item aberto

## Links

- [CLAUDE.md](CLAUDE.md) — pai deste backlog
"""

BACKLOG_SEM_LINKS = """# Backlog — Sem rodapé

- [ ] primeiro
- [ ] segundo
"""

BACKLOG_SO_PROSA = """# Backlog — Vazio

Nenhum item ainda, só esta linha de prosa.
"""


class BaseProjeto(unittest.TestCase):
    PASTA = "PRJ-Teste_Console"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-proj-"))
        self.projeto_dir = self.tmp / self.PASTA
        self.projeto_dir.mkdir()
        apoio.aplicar(self.tmp, **apoio.qualquer_pasta_e_projeto())
        self._orig_backups = projetos.BACKUPS_DIR
        projetos.BACKUPS_DIR = self.tmp / "backups"

    def tearDown(self):
        projetos.BACKUPS_DIR = self._orig_backups
        shutil.rmtree(self.tmp, ignore_errors=True)

    def criar_backlog(self, nome, conteudo, eol="\n"):
        caminho = self.projeto_dir / nome
        with caminho.open("w", encoding="utf-8", newline="") as f:
            f.write(conteudo.replace("\n", eol))
        rel = f"{self.PASTA}/{nome}"
        entries = [{"path": rel, "type": "backlog", "title": nome, "size_bytes": 1}]
        cache = {rel: caminho.read_text(encoding="utf-8")}
        return caminho, rel, entries, cache


class TestAnotar(BaseProjeto):
    def test_insere_antes_do_rodape_de_links(self):
        caminho, rel, entries, cache = self.criar_backlog("backlog-teste.md", BACKLOG_COM_LINKS)
        r = projetos.anotar(self.PASTA, rel, "conferir tal coisa",
                            projetos.sha1(cache[rel]), entries, cache)
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        i_nova = linhas.index(r["linha"])
        i_links = next(i for i, ln in enumerate(linhas) if ln.strip() == "## Links")
        self.assertLess(i_nova, i_links)
        self.assertEqual(linhas[i_nova - 1].strip(), "- [ ] outro item aberto")
        self.assertTrue(r["linha"].startswith("- [ ] conferir tal coisa _(via console, "))
        self.assertIn(date.today().isoformat(), r["linha"])

    def test_muda_so_uma_linha(self):
        caminho, rel, entries, cache = self.criar_backlog("backlog-teste.md", BACKLOG_COM_LINKS)
        antes = caminho.read_text(encoding="utf-8").splitlines()
        projetos.anotar(self.PASTA, rel, "anotação", projetos.sha1(cache[rel]), entries, cache)
        depois = caminho.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(depois), len(antes) + 1)
        for linha in antes:
            self.assertIn(linha, depois)

    def test_sem_rodape_vai_depois_do_ultimo_checkbox(self):
        caminho, rel, entries, cache = self.criar_backlog("backlog-x.md", BACKLOG_SEM_LINKS)
        r = projetos.anotar(self.PASTA, rel, "terceiro", projetos.sha1(cache[rel]), entries, cache)
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        self.assertEqual(linhas.index(r["linha"]), linhas.index("- [ ] segundo") + 1)

    def test_backlog_sem_checkbox_nenhum(self):
        caminho, rel, entries, cache = self.criar_backlog("backlog-v.md", BACKLOG_SO_PROSA)
        r = projetos.anotar(self.PASTA, rel, "primeiro item", projetos.sha1(cache[rel]), entries, cache)
        self.assertIn(r["linha"], caminho.read_text(encoding="utf-8").splitlines())

    def test_preserva_crlf(self):
        """O sha1 tem que casar mesmo com o cache vindo do indexer, que lê com
        universal newlines (CRLF -> LF). Sem normalizar, todo backlog CRLF dava
        409 eterno — bug pego no primeiro teste ao vivo, não pelos testes."""
        caminho, rel, entries, cache = self.criar_backlog(
            "backlog-crlf.md", BACKLOG_COM_LINKS, eol="\r\n")
        cache[rel] = caminho.read_text(encoding="utf-8")  # como o indexer faz
        projetos.anotar(self.PASTA, rel, "anotação crlf",
                        projetos.sha1(cache[rel]), entries, cache)
        bruto = caminho.read_bytes()
        self.assertNotIn(b"\n", bruto.replace(b"\r\n", b""))
        self.assertIn("anotação crlf", caminho.read_text(encoding="utf-8"))

    def test_conflito_por_sha1(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        with self.assertRaises(projetos.ConflitoError):
            projetos.anotar(self.PASTA, rel, "anotação", "sha1-que-nao-bate", entries, cache)

    def test_backlog_de_outro_projeto_recusado(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        with self.assertRaises(projetos.ProjetoError):
            projetos.anotar("PRJ-Outro", rel, "anotação",
                            projetos.sha1(cache[rel]), entries, cache)

    def test_arquivo_fora_da_allow_list_recusado(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        for alvo in [f"{self.PASTA}/CLAUDE.md", "_registro.md",
                     "../fora.md", f"{self.PASTA}/../outro/backlog.md"]:
            with self.assertRaises(projetos.ProjetoError):
                projetos.anotar(self.PASTA, alvo, "anotação",
                                projetos.sha1(cache[rel]), entries, cache)

    def test_pasta_invalida(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        for pasta in ["", "naoeprojeto", "../..", "PJX"]:
            with self.assertRaises(projetos.ProjetoError):
                projetos.anotar(pasta, rel, "anotação",
                                projetos.sha1(cache[rel]), entries, cache)

    def test_texto_invalido(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        sha = projetos.sha1(cache[rel])
        for texto in ["", "ab", "x" * 501, "linha1\nlinha2", "- [ ] já com marcador", "# heading"]:
            with self.assertRaises(projetos.ProjetoError):
                projetos.anotar(self.PASTA, rel, texto, sha, entries, cache)

    def test_faz_backup(self):
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        projetos.anotar(self.PASTA, rel, "anotação", projetos.sha1(cache[rel]), entries, cache)
        self.assertEqual(len(list((self.tmp / "backups").glob("*.bak"))), 1)

    def test_nao_marca_essencial(self):
        """Anotação não é bloqueio de entrega — não pode virar [ESSENCIAL],
        senão o utilitário cobraria pendência-formulário."""
        _, rel, entries, cache = self.criar_backlog("backlog-c.md", BACKLOG_COM_LINKS)
        r = projetos.anotar(self.PASTA, rel, "anotação", projetos.sha1(cache[rel]), entries, cache)
        self.assertNotIn("[ESSENCIAL]", r["linha"])


if __name__ == "__main__":
    unittest.main()
