"""Testes do Embarque — a tela de quem ainda não tem estação nenhuma.

Duas coisas que este módulo não pode errar. A primeira: **ele não pode escrever
em disco.** Ele gera um texto; quem cria estação é a sessão de IA onde o
texto é colado, com a pessoa olhando. A segunda: **o prompt tem que produzir
estações que abrem.** Por isso o teste não confere o texto por leitura — ele
executa o que o texto manda, e depois carrega o resultado com o config e o
utilitário de verdade.

Desde a 0.10 o texto cria as estações padrão de uma Central, lado a lado.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402
import embarque  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent
PADRAO = {"tem_conteudo": "vazia", "destino": "claude-code"}


def gerar(base, **extra):
    return embarque.gerar(dict(PADRAO, caminho=str(base) if base is not None else "", **extra))


def so(*modelos, **existentes):
    """Escolha de estações: cria as de `modelos`, registra as de `existentes`."""
    escolha = {}
    for m in config.MODELOS:
        if m in modelos:
            escolha[m] = {"criar": True}
        else:
            escolha[m] = {"criar": False, "caminho": existentes.get(m, "")}
    return escolha


class TestNaoEscreveNada(unittest.TestCase):
    """`gerar()` é gerador puro. Se um dia alguém fizer ele criar a pasta
    'só para adiantar', este teste cai."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="embarque-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_pasta_base_continua_sem_existir(self):
        alvo = self.tmp / "nao-deve-nascer"
        gerar(alvo)
        self.assertFalse(alvo.exists())

    def test_nao_mexe_na_pasta_que_ja_existe(self):
        (self.tmp / "meu.txt").write_text("intacto", encoding="utf-8")
        gerar(self.tmp)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["meu.txt"])
        self.assertEqual((self.tmp / "meu.txt").read_text(encoding="utf-8"), "intacto")


class TestValidacao(unittest.TestCase):
    def test_caminho_vazio(self):
        for caminho in ("", "   ", None):
            with self.assertRaises(ValueError):
                embarque.gerar(dict(PADRAO, caminho=caminho))

    def test_caminho_curto_demais(self):
        with self.assertRaises(ValueError):
            gerar("ab")

    def test_nenhuma_estacao_escolhida(self):
        with self.assertRaises(ValueError):
            gerar(r"C:\x\y", estacoes=so())

    def test_so_registrar_nao_exige_pasta_base(self):
        r = gerar(None, estacoes=so(plataforma=r"C:\x\minha"))
        self.assertEqual([(e["modelo"], e["criar"]) for e in r["estacoes"]],
                         [("plataforma", False)])


class TestGuardrails(unittest.TestCase):
    """Os do Embarque são OUTROS: aqui a estação ainda não existe, e o risco
    é apagar coisa da pessoa numa pasta que ela escolheu."""

    REGRAS = ["Não apague e não sobrescreva", "Se a pasta já tiver conteúdo, pare",
              "Não commite e não rode `git init`", "caminhos absolutos",
              "Não invente arquivo"]

    def test_todo_prompt_leva_os_guardrails(self):
        texto = gerar(r"C:\x\y")["texto"]
        for regra in self.REGRAS:
            self.assertIn(regra, texto, f"guardrail ausente: {regra}")

    def test_pasta_com_conteudo_muda_o_aviso(self):
        vazia = gerar(r"C:\x\y")["texto"]
        cheia = gerar(r"C:\x\y", tem_conteudo="tem")["texto"]
        self.assertIn("espere eu responder", cheia)
        self.assertNotIn("espere eu responder", vazia)

    def test_os_comandos_de_conferencia_usam_barra_normal(self):
        """O texto é colado em PowerShell, cmd ou shell POSIX — barra invertida
        vira escape em um deles."""
        texto = gerar(r"C:\x\y")["texto"]
        bloco = re.search(r"## Passo 4 —.*?```\n(.*?)```", texto, re.S).group(1)
        comandos = [l for l in bloco.splitlines() if "verificar" in l]
        self.assertEqual(len(comandos), len(config.MODELOS))
        for c in comandos:
            self.assertNotIn("\\", c)

    def test_a_estacao_que_ja_existe_nao_e_tocada(self):
        texto = gerar(r"C:\x\y", estacoes=so("admin_empresa", "vida_pessoal",
                                             plataforma=r"C:\x\minha"))["texto"]
        self.assertIn("Não mexa nelas", texto)
        self.assertIn(r"C:\x\minha", texto)
        self.assertNotIn("### `plataforma/", texto)


class TestModelos(unittest.TestCase):
    def test_as_estacoes_padrao_na_ordem(self):
        r = gerar(r"C:\x\y")
        self.assertEqual([e["modelo"] for e in r["estacoes"]], list(config.MODELOS))
        for e in r["estacoes"]:
            self.assertEqual(Path(e["caminho"]).name, config.MODELOS[e["modelo"]]["pasta"])

    def test_a_plataforma_tem_cinco_estagios_e_projetos(self):
        tax = embarque.taxonomia("plataforma")
        self.assertEqual([e["sigla"] for e in tax["estagios"]],
                         ["CAP", "NOT", "IDE", "FUN", "PRJ"])
        self.assertEqual(tax["projetos"]["pasta"], "5-projetos")
        self.assertIn("tipos", tax)
        self.assertNotIn("privada", tax)

    def test_as_de_tres_estagios_nao_tem_projetos(self):
        for modelo in ("admin_empresa", "vida_pessoal"):
            tax = embarque.taxonomia(modelo)
            self.assertEqual([e["sigla"] for e in tax["estagios"]], ["CAP", "NOT", "IDE"])
            self.assertIsNone(tax["projetos"], "projetos: null é o que diz 'não há'")
            self.assertNotIn("tipos", tax)

    def test_so_a_vida_pessoal_e_privada(self):
        self.assertTrue(embarque.taxonomia("vida_pessoal").get("privada"))
        self.assertFalse(embarque.taxonomia("admin_empresa").get("privada"))

    def test_toda_estacao_tem_pendencias(self):
        for modelo in config.MODELOS:
            self.assertEqual(embarque.taxonomia(modelo)["pendencias"], "_pendencias")

    def test_nome_vazio_ganha_o_do_modelo(self):
        self.assertEqual(embarque.taxonomia("vida_pessoal", "  ")["nome"], "Vida_Pessoal")

    def test_desmarcada_sem_caminho_nao_entra(self):
        r = gerar(r"C:\x\y", estacoes=so("plataforma"))
        self.assertEqual([e["modelo"] for e in r["estacoes"]], ["plataforma"])


class TestPromptCria(unittest.TestCase):
    """O teste que importa: executar o que o texto manda, e abrir o resultado.

    Lê o PROMPT em vez de reusar `sementes()` — se reusasse, provaria que a
    função concorda consigo mesma, não que o texto está certo.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="embarque-cria-"))
        cls.base = cls.tmp / "estacoes"
        cls.texto = gerar(cls.base)["texto"]
        bloco = re.search(r"## Passo 2 —.*?```\n(.*?)```", cls.texto, re.S).group(1)
        cls.base.mkdir(parents=True)
        for l in bloco.splitlines():
            if "├" in l and l.strip().endswith("/"):
                (cls.base / l.strip("├─ ").strip()).mkdir(parents=True, exist_ok=True)
        parte = cls.texto.split("## Passo 3", 1)[1].split("## Passo 4", 1)[0]
        cls.criados = []
        for m in re.finditer(r"### `([^`]+)`\n\n```[a-z]*\n(.*?)\n```", parte, re.S):
            destino = cls.base / m.group(1)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(m.group(2) + "\n", encoding="utf-8")
            cls.criados.append(m.group(1))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def raiz(self, modelo):
        return self.base / config.MODELOS[modelo]["pasta"]

    def claude(self, modelo):
        return (self.raiz(modelo) / "CLAUDE.md").read_text(encoding="utf-8")

    def test_as_tres_nascem_validas(self):
        for modelo, m in config.MODELOS.items():
            with self.subTest(modelo):
                cfg = config.carregar(self.raiz(modelo))
                self.assertTrue(cfg.ok(), "o marcador não foi criado — a Central não abriria")
                self.assertEqual(cfg.nome, m["nome"])
                self.assertEqual(cfg.modelo, modelo)
                self.assertEqual(len(cfg.estagios), m["estagios"])
                self.assertEqual(cfg.tem_projetos, m["projetos"])
                self.assertEqual(cfg.privada, m["privada"])
                for e in cfg.estagios:
                    self.assertTrue((self.raiz(modelo) / e["pasta"] / cfg.historico).is_dir())

    def test_o_utilitario_aprova_as_tres(self):
        for modelo in config.MODELOS:
            with self.subTest(modelo):
                r = subprocess.run([sys.executable, str(RAIZ_REPO / "metodo" / "estacao.py"),
                                    "verificar", "--raiz", str(self.raiz(modelo))],
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_o_estacao_json_criado_e_json_valido(self):
        for modelo in config.MODELOS:
            dados = json.loads((self.raiz(modelo) / "estacao.json").read_text(encoding="utf-8"))
            self.assertIn("estagios", dados)
            self.assertEqual(dados["modelo"], modelo)

    def test_quem_versiona_nasce_com_a_regra_de_salvar(self):
        """É isto que faz a IA do usuário commitar sozinha desde o dia um."""
        for modelo in ("plataforma", "admin_empresa"):
            texto = self.claude(modelo)
            self.assertIn("Salvar é automático; publicar é decisão", texto)
            self.assertIn("nunca `git add .`", texto.lower())
            self.assertIn("Push só com autorização explícita e separada", texto)

    def test_a_vida_pessoal_nunca_versiona(self):
        texto = self.claude("vida_pessoal")
        self.assertIn("Não rode `git init`", texto)
        self.assertNotIn("Salvar é automático", texto)
        self.assertFalse((self.raiz("vida_pessoal") / ".gitignore").exists(),
                         ".gitignore é convite a versionar")

    def test_o_gitignore_nasce_nas_que_versionam(self):
        for modelo in ("plataforma", "admin_empresa"):
            texto = (self.raiz(modelo) / ".gitignore").read_text(encoding="utf-8")
            for padrao in ("cache/", "__pycache__/", ".env", "*.log"):
                self.assertIn(padrao, texto)

    def test_as_de_tres_estagios_sabem_da_passagem(self):
        for modelo in ("admin_empresa", "vida_pessoal"):
            self.assertIn("captura nova na estação Plataforma", self.claude(modelo))
        self.assertNotIn("Quando uma ideia daqui serve", self.claude("plataforma"))

    def test_o_sem_destino_nasce_ja_sincronizado(self):
        """Senão o `verificar` acusa 'desatualizado' numa estação com um
        minuto de vida, e o primeiro contato com o sistema é um alarme falso."""
        for modelo in config.MODELOS:
            texto = (self.raiz(modelo) / "_sem-destino.md").read_text(encoding="utf-8")
            for e in config.carregar(self.raiz(modelo)).estagios:
                chave = e["sigla"].lower()
                bloco = texto.split(f"<!-- gerado:{chave}:inicio -->")[1] \
                             .split(f"<!-- gerado:{chave}:fim -->")[0]
                self.assertIn("nada nesta etapa", bloco)


class TestRegistrar(unittest.TestCase):
    """Escreve só no config do hub — nunca dentro de estação nenhuma."""

    def setUp(self):
        import os
        self.tmp = Path(tempfile.mkdtemp(prefix="embarque-reg-"))
        self._hub = os.environ.get("CENTRAL_DIR")
        os.environ["CENTRAL_DIR"] = str(self.tmp)

    def tearDown(self):
        import os
        if self._hub is not None:
            os.environ["CENTRAL_DIR"] = self._hub
        else:
            os.environ.pop("CENTRAL_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_registra_e_aparece(self):
        embarque.registrar(r"C:\x\minha", "Minha")
        nomes = [p["nome"] for p in config.estacoes()]
        self.assertEqual(nomes, ["Minha"])

    def test_registrar_de_novo_nao_duplica(self):
        embarque.registrar(r"C:\x\minha", "Minha")
        embarque.registrar(r"C:\x\minha", "Renomeada")
        regs = config.estacoes()
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0]["nome"], "Renomeada")

    def test_nao_nasce_ativa(self):
        """A pasta pode nem existir ainda — ativar sem estrutura só daria erro."""
        embarque.registrar(r"C:\x\minha", "Minha")
        self.assertFalse(config.estacoes()[0]["ativa"])

    def test_caminho_invalido(self):
        with self.assertRaises(ValueError):
            embarque.registrar("", "X")

    def test_as_do_embarque_de_uma_vez(self):
        r = gerar(r"C:\x\y", estacoes=so("admin_empresa", "vida_pessoal",
                                         plataforma=r"C:\x\minha"))
        embarque.registrar_varias(r["estacoes"])
        self.assertEqual(sorted(e["nome"] for e in config.estacoes()),
                         sorted(m["nome"] for m in config.MODELOS.values()))
        self.assertFalse(any(e["ativa"] for e in config.estacoes()))


if __name__ == "__main__":
    unittest.main()
