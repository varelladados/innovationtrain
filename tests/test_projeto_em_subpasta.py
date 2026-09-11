"""Projeto que mora em subpasta — o caso da taxonomia padrão.

Este arquivo existe por causa de um bug que passou por 200 testes: a view de
projeto e o briefing de avanço montavam o caminho dos arquivos como
`<nome-da-pasta>/...`, quando o índice guarda `5-projetos/<nome-da-pasta>/...`.
Com a taxonomia padrão, a tela de projeto abria sem nenhum backlog e sem
`CLAUDE.md`, e o briefing dizia "nenhum backlog indexado" para todo projeto.

O que escondeu o bug foi o fixture: `apoio.qualquer_pasta_e_projeto()` põe
`projetos.pasta = ""`, ou seja, a suíte exercitava só a plataforma em que o
projeto está na raiz — que é a exceção, não o padrão. Aqui é o contrário: a
pasta de projetos é declarada, como numa plataforma de verdade.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import briefing  # noqa: E402
import config  # noqa: E402
import projetos  # noqa: E402

PASTA = "meu-projeto"
BACKLOG = f"5-projetos/{PASTA}/backlog-assunto.md"
CLAUDE = f"5-projetos/{PASTA}/CLAUDE.md"

CONTEUDO = """# Backlog

- [ ] **[ESSENCIAL]** publicar a primeira versão
- [ ] escrever o leia-me
- [x] escolher o nome

## Links

- [CLAUDE.md](CLAUDE.md)
"""

CLAUDE_RAW = "# CLAUDE.md — meu projeto\n"


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="proj-subpasta-"))
        (self.tmp / "5-projetos" / PASTA).mkdir(parents=True)
        (self.tmp / BACKLOG).write_text(CONTEUDO, encoding="utf-8")
        (self.tmp / CLAUDE).write_text(CLAUDE_RAW, encoding="utf-8")
        self._anterior = config._ATUAL
        apoio.aplicar(self.tmp,
                      projetos={"pasta": "5-projetos", "prefixo_re": None},
                      doutrina="metodo/regras.md",
                      utilitario="metodo/plataforma.py",
                      checklist="metodo/classificar.md")
        self.entries = [
            {"path": BACKLOG, "title": "Backlog", "type": "backlog",
             "size_bytes": len(CONTEUDO)},
            {"path": CLAUDE, "title": "meu projeto", "type": "orquestra",
             "size_bytes": len(CLAUDE_RAW)},
        ]
        self.cache = {BACKLOG: CONTEUDO, CLAUDE: CLAUDE_RAW}
        self.pf = {"projetos": [{"pasta": PASTA, "nome": "Meu projeto"}]}

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestPrefixo(_Base):
    def test_o_prefixo_inclui_a_pasta_de_projetos(self):
        self.assertEqual(projetos.prefixo_do_projeto(PASTA), f"5-projetos/{PASTA}")

    def test_sem_pasta_declarada_o_prefixo_e_so_o_nome(self):
        """O caso antigo continua valendo — é o que a suíte já cobria."""
        apoio.aplicar(self.tmp, **apoio.qualquer_pasta_e_projeto())
        self.assertEqual(projetos.prefixo_do_projeto(PASTA), PASTA)


class TestDetalhe(_Base):
    def test_acha_o_backlog_do_projeto(self):
        d = projetos.detalhe(PASTA, self.entries, self.cache, portfolio=self.pf)
        self.assertEqual([b["path"] for b in d["backlogs"]], [BACKLOG])
        self.assertEqual(d["backlogs"][0]["abertos"], 2)

    def test_acha_o_claude_md(self):
        d = projetos.detalhe(PASTA, self.entries, self.cache, portfolio=self.pf)
        self.assertEqual(d["claude_path"], CLAUDE)


class TestBriefing(_Base):
    def test_o_briefing_de_avancar_enxerga_o_backlog(self):
        r = briefing.briefing_avancar(PASTA, self.entries, self.cache)
        self.assertIn(BACKLOG, r["texto"])
        self.assertNotIn("nenhum backlog indexado", r["texto"])
        self.assertIn("publicar a primeira versão", r["texto"])

    def test_cita_o_claude_md_no_caminho_certo(self):
        r = briefing.briefing_avancar(PASTA, self.entries, self.cache)
        self.assertIn(CLAUDE, r["texto"])


class TestAnotar(_Base):
    def test_anota_no_backlog_dentro_da_subpasta(self):
        r = projetos.anotar(PASTA, BACKLOG, "um item novo",
                            projetos.sha1(CONTEUDO), self.entries, self.cache)
        self.assertTrue(r["ok"])
        texto = (self.tmp / BACKLOG).read_text(encoding="utf-8")
        self.assertIn("- [ ] um item novo", texto)
        # o rodapé de links continua sendo o último bloco
        self.assertLess(texto.index("um item novo"), texto.index("## Links"))

    def test_recusa_backlog_de_fora_do_projeto(self):
        outro = "5-projetos/outro/backlog-x.md"
        with self.assertRaises(projetos.ProjetoError):
            projetos.anotar(PASTA, outro, "tentativa", None, self.entries, self.cache)


if __name__ == "__main__":
    unittest.main()
