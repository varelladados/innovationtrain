"""O índice canônico de projetos, lido por quem quer que more onde.

O link de cada linha é resolvido a partir da pasta do próprio índice. Até a
0.13.0 só a forma `](../pasta/CLAUDE.md)` era reconhecida — a de um índice que
mora ao lado das pastas de projeto. Com o índice **dentro** da pasta de
projetos o link vira `](pasta/CLAUDE.md)`, e todo projeto aparecia "fora do
índice" e sumia da vitrine.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402  (insere app/ no sys.path)
import config  # noqa: E402
import indexer  # noqa: E402
import portfolio  # noqa: E402

CABECALHO = "| Pasta | Git | CLAUDE.md | Status | Resumo |\n|---|---|---|---|---|\n"


class _Estacao(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="indice-projetos-"))
        self._anterior = config._ATUAL

    def tearDown(self):
        config._ATUAL = self._anterior
        shutil.rmtree(self.tmp, ignore_errors=True)

    def projeto(self, base, nome):
        pasta = self.tmp / base / nome
        pasta.mkdir(parents=True)
        (pasta / "CLAUDE.md").write_text(f"# {nome}\n", encoding="utf-8")
        return pasta

    def listados(self):
        return {p["pasta"] for p in portfolio.build_portfolio()["projetos"] if p["listada"]}

    def orfaos(self):
        entries, _ = indexer.build_index()
        return {e["path"] for e in entries if e["orphaned"]}


class TestIndiceDentroDaPastaDeProjetos(_Estacao):
    def setUp(self):
        super().setUp()
        for nome in ("horta", "receitas-da-avó", "caderno de campo", "sem-linha"):
            self.projeto("5-projetos", nome)
        (self.tmp / "5-projetos" / "o-projetos.md").write_text(
            "# Projetos\n\n" + CABECALHO
            + "| [5-projetos/horta](horta/CLAUDE.md) | sim | completo | ativo | uma horta |\n"
            + "| [5-projetos/receitas-da-avó](receitas-da-avó/CLAUDE.md) | não | completo | **pausado** | receitas |\n"
            + "| [5-projetos/caderno de campo](<caderno de campo/CLAUDE.md>) | sim | completo | ativo | anotações |\n",
            encoding="utf-8")
        apoio.aplicar(self.tmp, projetos={"pasta": "5-projetos", "prefixo_re": None},
                      indice_projetos="5-projetos/o-projetos.md")

    def test_o_link_sem_ponto_ponto_barra_e_lido(self):
        self.assertEqual(self.listados(), {"horta", "receitas-da-avó", "caderno de campo"})

    def test_status_e_resumo_vem_da_linha(self):
        pj = {p["pasta"]: p for p in portfolio.build_portfolio()["projetos"]}
        self.assertEqual(pj["receitas-da-avó"]["status"], "pausado")
        self.assertEqual(pj["horta"]["resumo"], "uma horta")

    def test_so_a_pasta_fora_do_indice_e_orfa(self):
        self.assertEqual(self.orfaos(), {"5-projetos/sem-linha/CLAUDE.md"})


class TestIndiceAoLadoDasPastas(_Estacao):
    """A forma de antes continua valendo: índice numa pasta, projetos na raiz."""

    def setUp(self):
        super().setUp()
        for nome in ("horta", "sem-linha"):
            self.projeto("", nome)
        (self.tmp / "indice").mkdir()
        (self.tmp / "indice" / "o-projetos.md").write_text(
            "# Projetos\n\n" + CABECALHO
            + "| [horta](../horta/CLAUDE.md) | sim | completo | ativo | uma horta |\n",
            encoding="utf-8")
        apoio.aplicar(self.tmp, projetos={"pasta": "", "prefixo_re": None},
                      indice_projetos="indice/o-projetos.md")

    def test_o_link_com_ponto_ponto_barra_continua_lido(self):
        self.assertIn("horta", self.listados())
        self.assertNotIn("sem-linha", self.listados())


class TestLinkQueNaoEProjeto(_Estacao):
    def test_link_para_fora_da_pasta_de_projetos_nao_lista_ninguem(self):
        self.projeto("5-projetos", "horta")
        self.projeto("", "fora")
        (self.tmp / "5-projetos" / "o-projetos.md").write_text(
            "# Projetos\n\n" + CABECALHO
            + "| [fora](../fora/CLAUDE.md) | sim | completo | ativo | não é projeto desta pasta |\n"
            + "| [longe](horta/sub/CLAUDE.md) | sim | completo | ativo | fundo demais |\n"
            + "| [web](https://exemplo.org/horta/CLAUDE.md) | sim | completo | ativo | endereço |\n",
            encoding="utf-8")
        apoio.aplicar(self.tmp, projetos={"pasta": "5-projetos", "prefixo_re": None},
                      indice_projetos="5-projetos/o-projetos.md")
        self.assertEqual(self.listados(), set())
        self.assertEqual(indexer.projetos_listados(), set())

    def test_espaco_escrito_como_porcento_20(self):
        self.projeto("5-projetos", "caderno de campo")
        indice = self.tmp / "5-projetos" / "o-projetos.md"
        indice.write_text("# Projetos\n\n- [caderno](caderno%20de%20campo/CLAUDE.md)\n", encoding="utf-8")
        cfg = apoio.aplicar(self.tmp, projetos={"pasta": "5-projetos", "prefixo_re": None},
                            indice_projetos="5-projetos/o-projetos.md")
        self.assertEqual(indexer.projetos_listados(cfg), {"caderno de campo"})


class TestSemIndice(_Estacao):
    """Sem índice declarado não existe "estar fora dele"."""

    def setUp(self):
        super().setUp()
        for nome in ("horta", "pomar"):
            self.projeto("5-projetos", nome)
        apoio.aplicar(self.tmp, projetos={"pasta": "5-projetos", "prefixo_re": None})

    def test_todo_projeto_conta_como_listado(self):
        self.assertEqual(self.listados(), {"horta", "pomar"})

    def test_ninguem_e_orfao(self):
        self.assertEqual(self.orfaos(), set())
        self.assertIsNone(indexer.projetos_listados())


if __name__ == "__main__":
    unittest.main()
