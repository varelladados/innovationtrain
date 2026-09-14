"""As estações padrão de uma Central — Plataforma, Admin_empresa e Vida_Pessoal.

O que não pode errar aqui: a Vida_Pessoal **não sai do computador** — nem por
exportação, nem pela aba Versões, nem por um `git add` distraído na Central —,
e uma estação sem estágio de projetos não inventa projeto a partir das pastas
de estágio.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402  (insere app/ no sys.path)
import config  # noqa: E402
import embarque  # noqa: E402
import export_portfolio  # noqa: E402
import export_static  # noqa: E402
import indexer  # noqa: E402
import metrics  # noqa: E402
import portfolio  # noqa: E402
import versoes  # noqa: E402
import workflow  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent


class _ComTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacoes-padrao-"))
        self._anterior = config._ATUAL

    def tearDown(self):
        config._ATUAL = self._anterior
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestModelos(unittest.TestCase):
    def test_sao_tres_na_ordem_em_que_foram_pedidas(self):
        self.assertEqual(list(config.MODELOS), ["plataforma", "admin_empresa", "vida_pessoal"])

    def test_batem_com_a_taxonomia_escrita(self):
        """`config.MODELOS` é cópia executável de `metodo/taxonomia.md`."""
        texto = (RAIZ_REPO / "metodo" / "taxonomia.md").read_text(encoding="utf-8")
        for m in config.MODELOS.values():
            self.assertIn(m["nome"], texto)
            self.assertIn(f"`{m['pasta']}/`", texto)
            self.assertIn(m["proposito"], texto)

    def test_so_a_vida_pessoal_e_privada(self):
        self.assertEqual([k for k, m in config.MODELOS.items() if m["privada"]], ["vida_pessoal"])

    def test_so_a_plataforma_tem_projetos(self):
        self.assertEqual([k for k, m in config.MODELOS.items() if m["projetos"]], ["plataforma"])


class TestConfig(_ComTmp):
    def test_sem_a_chave_modelo_vale_plataforma(self):
        cfg = config.carregar(self.tmp)
        self.assertEqual(cfg.modelo, "plataforma")
        self.assertFalse(cfg.privada)
        self.assertTrue(cfg.tem_projetos)

    def test_a_vida_pessoal_e_privada_mesmo_sem_a_chave(self):
        self.assertTrue(config.carregar(self.tmp, {"modelo": "vida_pessoal"}).privada)

    def test_a_chave_explicita_vence_o_modelo(self):
        cfg = config.carregar(self.tmp, {"modelo": "vida_pessoal", "privada": False})
        self.assertFalse(cfg.privada)

    def test_o_resumo_leva_o_que_a_interface_precisa(self):
        resumo = config.carregar(self.tmp, {"projetos": None}).resumo()
        self.assertFalse(resumo["tem_projetos"])
        for chave in ("modelo", "privada"):
            self.assertIn(chave, resumo)


class TestSemProjetos(_ComTmp):
    def test_as_pastas_de_estagio_nao_viram_projeto(self):
        for pasta in ("1-capturas", "2-notas", "3-ideias", "_pendencias"):
            (self.tmp / pasta).mkdir()
        apoio.aplicar(self.tmp, projetos=None)
        self.assertEqual(indexer.pastas_de_projeto(), set())

    def test_pasta_vazia_continua_querendo_dizer_raiz(self):
        (self.tmp / "um-projeto").mkdir()
        apoio.aplicar(self.tmp, **apoio.qualquer_pasta_e_projeto())
        self.assertIn("um-projeto", indexer.pastas_de_projeto())

    def test_a_estacao_de_tres_estagios_abre_inteira(self):
        """Índice, Dashboard, Workflow e Portfólio sobre uma Vida_Pessoal recém-criada."""
        tax = embarque.taxonomia("vida_pessoal")
        for p in embarque._pastas(tax):
            (self.tmp / p).mkdir(parents=True, exist_ok=True)
        for rel, conteudo in embarque.sementes(tax):
            (self.tmp / rel).write_text(conteudo, encoding="utf-8")
        config.aplicar(config.carregar(self.tmp))
        entries, _ = indexer.build_index()
        self.assertTrue(entries)
        self.assertIsNone(metrics.compute_metrics()["erro"])
        workflow.build_workflow(entries)
        self.assertEqual(portfolio.build_portfolio()["projetos"], [])


class TestPrivadaNaoSai(_ComTmp):
    def test_o_snapshot_estatico_recusa(self):
        apoio.aplicar(self.tmp, modelo="vida_pessoal")
        with self.assertRaises(config.EstacaoPrivada):
            export_static.build_snapshot()

    def test_a_vitrine_recusa(self):
        apoio.aplicar(self.tmp, modelo="vida_pessoal")
        with self.assertRaises(config.EstacaoPrivada):
            export_portfolio.montar()

    def test_a_aba_versoes_nao_oferece_git(self):
        s = versoes.semaforo({"e_repo": False, "privada": True})
        self.assertEqual(s["titulo"], "Não versionada, de propósito")

    def test_uma_estacao_comum_continua_podendo(self):
        self.assertEqual(versoes.semaforo({"e_repo": False})["titulo"],
                         "Esta pasta não é versionada")


def _git_ok():
    try:
        return subprocess.run(["git", "-C", str(RAIZ_REPO), "rev-parse"],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@unittest.skipUnless(_git_ok(), "não é um repositório git, ou git fora do PATH")
class TestVersionamentoDaCentral(unittest.TestCase):
    """As estações de quem usa moram dentro da Central, que é um repositório
    público. O `.gitignore` é o que as mantém fora — sem esconder os exemplos."""

    def ignorado(self, rel):
        return subprocess.run(["git", "-C", str(RAIZ_REPO), "check-ignore", "-q", rel],
                              capture_output=True).returncode == 0

    def test_as_estacoes_de_quem_usa_ficam_fora(self):
        for m in config.MODELOS.values():
            self.assertTrue(self.ignorado(f"estacoes/{m['pasta']}/_registro.md"), m["pasta"])

    def test_os_exemplos_continuam_dentro(self):
        for rel in ("estacoes/exemplo/novo.md", "estacoes/exemplo-precos/novo.md",
                    "estacoes/_inicial/novo.md", "estacoes/_passos/novo.md"):
            self.assertFalse(self.ignorado(rel), rel)


if __name__ == "__main__":
    unittest.main()
