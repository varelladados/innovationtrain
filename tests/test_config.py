"""Testes do config — a peça de que os outros onze módulos dependem.

O risco aqui não é o app quebrar: é ele **funcionar apontando para o lugar
errado**. Era isso que o fallback `PROJECT_DIR.parent` fazia — fora do `plataforma de origem`
ele resolvia para uma pasta qualquer e o erro de configuração aparecia como
"árvore vazia". Por isso o primeiro teste é que esse fallback não voltou.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent


class TestResolucaoDaRaiz(unittest.TestCase):
    """--raiz → ESTACAO_PLATAFORMA → estacao.json → erro claro. Nessa ordem."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="config-raiz-"))
        self._env = os.environ.pop("ESTACAO_PLATAFORMA", None)
        self._hub = os.environ.get("ESTACAO_HUB")
        os.environ["ESTACAO_HUB"] = str(self.tmp / "hub-vazio")

    def tearDown(self):
        if self._env is not None:
            os.environ["ESTACAO_PLATAFORMA"] = self._env
        else:
            os.environ.pop("ESTACAO_PLATAFORMA", None)
        if self._hub is not None:
            os.environ["ESTACAO_HUB"] = self._hub
        else:
            os.environ.pop("ESTACAO_HUB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_argumento_vence(self):
        os.environ["ESTACAO_PLATAFORMA"] = str(self.tmp / "pelo-env")
        raiz, _, origem = config.resolver(["--raiz", str(self.tmp / "pelo-arg")])
        self.assertEqual(raiz, self.tmp / "pelo-arg")
        self.assertEqual(origem, "--raiz")

    def test_argumento_com_igual(self):
        raiz, _, _ = config.resolver([f"--raiz={self.tmp}"])
        self.assertEqual(raiz, self.tmp)

    def test_env_vence_o_estacao_json(self):
        os.environ["ESTACAO_PLATAFORMA"] = str(self.tmp / "pelo-env")
        raiz, _, origem = config.resolver([])
        self.assertEqual(raiz, self.tmp / "pelo-env")
        self.assertEqual(origem, "ESTACAO_PLATAFORMA")

    def test_sem_nada_levanta_com_texto_em_portugues(self):
        """E o texto tem que dizer as três saídas — é o que a pessoa lê."""
        with self.assertRaises(config.RaizNaoResolvida) as ctx:
            config.resolver([])
        msg = str(ctx.exception)
        self.assertIn("--raiz", msg)
        self.assertIn("ESTACAO_PLATAFORMA", msg)
        self.assertIn("estacao.json", msg)
        self.assertIn("Embarque", msg)

    def test_iniciar_sem_nada_NAO_levanta(self):
        """O caso de quem acabou de clonar. `resolver()` levanta — é a função
        que responde "onde fica?" —, mas `iniciar()` tem que devolver a config de
        sem-plataforma, para o servidor subir e a aba Embarque abrir. Era o
        contrário disso, e um clone recém-feito morria no boot com um texto de
        erro: o primeiro contato com o produto era uma parede."""
        anterior = config._ATUAL
        try:
            cfg = config.iniciar([])
            self.assertEqual(cfg.origem, config.SEM_PLATAFORMA)
            self.assertFalse(cfg.ok())
            self.assertTrue(config.definida(), "config.atual() precisa funcionar")
            # e tudo que os endpoints chamam tem que responder, não levantar
            self.assertIsInstance(cfg.siglas, list)
            self.assertIsNotNone(cfg.arquivo_rel("registro"))
        finally:
            config.aplicar(anterior) if anterior else None

    def test_o_fallback_project_dir_parent_nao_voltou(self):
        """Sem plataforma indicada, tem que ERRAR — nunca cair numa pasta
        qualquer e indexar a árvore errada em silêncio."""
        with self.assertRaises(config.RaizNaoResolvida):
            config.resolver([])


class TestCarregar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="config-carga-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sem_arquivo_usa_os_padroes(self):
        cfg = config.carregar(self.tmp)
        self.assertEqual(cfg.siglas, ["CAP", "NOT", "IDE", "PRJ"])
        self.assertEqual(cfg.marcador, "_indice.md")
        self.assertEqual(cfg.origem, "padrões")

    def test_plataforma_json_sobrescreve(self):
        (self.tmp / "plataforma.json").write_text(json.dumps({
            "nome": "Outra", "marcador": "porta.md",
            "estagios": [{"n": 1, "pasta": "a", "nome": "A", "sigla": "AAA"}],
        }), encoding="utf-8")
        cfg = config.carregar(self.tmp)
        self.assertEqual(cfg.nome, "Outra")
        self.assertEqual(cfg.marcador, "porta.md")
        self.assertEqual(cfg.siglas, ["AAA"])
        # o que não foi sobrescrito continua vindo dos padrões
        self.assertEqual(cfg.historico, "_historico")

    def test_inline_vence_o_arquivo(self):
        """É assim que o `plataforma de origem` é lido sem receber nenhum arquivo novo."""
        (self.tmp / "plataforma.json").write_text('{"nome": "do arquivo"}', encoding="utf-8")
        cfg = config.carregar(self.tmp, {"nome": "do estacao.json"})
        self.assertEqual(cfg.nome, "do estacao.json")
        self.assertEqual(cfg.origem, "estacao.json")

    def test_json_invalido_diz_qual_arquivo(self):
        (self.tmp / "plataforma.json").write_text("{ isto não é json", encoding="utf-8")
        with self.assertRaises(RuntimeError) as ctx:
            config.carregar(self.tmp)
        self.assertIn("plataforma.json", str(ctx.exception))

    def test_merge_de_arquivos_e_um_nivel_mais_fundo(self):
        cfg = config.carregar(self.tmp, {"arquivos": {"registro": "outro.md"}})
        self.assertEqual(cfg.arquivo_rel("registro"), "outro.md")
        self.assertEqual(cfg.arquivo_rel("indice"), "_indice.md")   # não sumiu

    def test_ok_depende_do_marcador(self):
        cfg = config.carregar(self.tmp)
        self.assertFalse(cfg.ok())
        (self.tmp / "_indice.md").write_text("#", encoding="utf-8")
        self.assertTrue(cfg.ok())


class TestRegex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="config-re-"))
        self.cfg = config.carregar(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_id_re_reconhece_prefixo_de_nome(self):
        self.assertTrue(self.cfg.id_re.match("26.09.08-CAP-001-slug-a3f2"))
        self.assertFalse(self.cfg.id_re.match("26.09.08-SBC-001-slug-a3f2"))

    def test_identificador_re_acha_no_meio_do_texto(self):
        m = self.cfg.identificador_re.search("veio de 26.09.08-IDE-002-x-b3a9 ontem")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "IDE")

    def test_etapa_re_so_casa_sigla_declarada(self):
        self.assertTrue(self.cfg.etapa_re.search("PRJ-app"))
        self.assertIsNone(self.cfg.etapa_re.search("SBZ-DIG"))

    def test_estagio_dir(self):
        self.assertEqual(self.cfg.estagio_dir(4), self.tmp / "4-projetos")
        self.assertIsNone(self.cfg.estagio_dir(9))


class TestFonteUnica(unittest.TestCase):
    """As cópias que o itinerário avisou que iam divergir."""

    def test_padroes_batem_com_a_taxonomia_escrita(self):
        """`config.PADROES` é a cópia executável de `metodo/taxonomia.md`. Se
        alguém renomear um estágio lá e esquecer aqui, isto acusa."""
        doc = RAIZ_REPO / "metodo" / "taxonomia.md"
        if not doc.exists():
            self.skipTest("metodo/taxonomia.md não está ao lado deste repositório")
        texto = doc.read_text(encoding="utf-8")
        for e in config.PADROES["estagios"]:
            self.assertIn(e["pasta"], texto, f"pasta {e['pasta']} não está na taxonomia")
            self.assertIn(e["sigla"], texto, f"sigla {e['sigla']} não está na taxonomia")

    def test_a_porta_do_launch_json_bate_com_o_config(self):
        """A porta tem uma fonte só (`config.PORTA`); o launch.json é o único
        lugar que precisa repeti-la, porque é JSON lido pelo harness."""
        launch = RAIZ_REPO / ".claude" / "launch.json"
        if not launch.exists():
            self.skipTest("sem .claude/launch.json")
        dados = json.loads(launch.read_text(encoding="utf-8"))
        portas = {c.get("port") for c in dados.get("configurations", [])}
        self.assertIn(config.PORTA, portas,
                      f"launch.json diz {portas}, config.PORTA diz {config.PORTA}")

    def test_o_bat_nao_repete_a_porta(self):
        bat = RAIZ_REPO / "iniciar-estacao.bat"
        if not bat.exists():
            self.skipTest("sem iniciar-estacao.bat")
        texto = bat.read_text(encoding="utf-8", errors="replace")
        self.assertIn("config.PORTA", texto, "o .bat tem que perguntar a porta ao config")


class TestEstacaoJson(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="config-hub-"))
        self._hub = os.environ.get("ESTACAO_HUB")
        os.environ["ESTACAO_HUB"] = str(self.tmp)

    def tearDown(self):
        if self._hub is not None:
            os.environ["ESTACAO_HUB"] = self._hub
        else:
            os.environ.pop("ESTACAO_HUB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_hub_sem_arquivo_e_estado_normal(self):
        self.assertEqual(config.plataformas(), [])
        self.assertIsNone(config.plataforma_ativa())

    def test_arquivo_ilegivel_nao_derruba(self):
        (self.tmp / "estacao.json").write_text("{{{", encoding="utf-8")
        self.assertEqual(config.plataformas(), [])

    def test_ativar_troca_a_ativa_e_grava(self):
        config.escrever_estacao({"plataformas": [
            {"nome": "a", "caminho": str(self.tmp / "a"), "ativa": True},
            {"nome": "b", "caminho": str(self.tmp / "b"), "ativa": False},
        ]})
        config.ativar(str(self.tmp / "b"))
        ativa = config.plataforma_ativa()
        self.assertEqual(ativa["nome"], "b")
        self.assertFalse(config.plataformas()[0]["ativa"])

    def test_ativar_caminho_nao_registrado_levanta(self):
        config.escrever_estacao({"plataformas": []})
        with self.assertRaises(KeyError):
            config.ativar(str(self.tmp / "nao-registrada"))


if __name__ == "__main__":
    unittest.main()
