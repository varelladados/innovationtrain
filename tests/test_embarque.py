"""Testes do Embarque — a tela de quem ainda não tem plataforma nenhuma.

Duas coisas que este módulo não pode errar. A primeira: **ele não pode escrever
em disco.** Ele gera um texto; quem cria plataforma é a sessão de IA onde o
texto é colado, com a pessoa olhando. A segunda: **o prompt tem que produzir uma
plataforma que abre.** Por isso o teste não confere o texto por leitura — ele
executa o que o texto manda, e depois carrega o resultado com o config de
verdade.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402
import embarque  # noqa: E402

COMPLETO = {"usos": ["notas", "decisoes", "projetos", "portfolio"],
            "tem_conteudo": "vazia", "destino": "claude-code"}


class TestNaoEscreveNada(unittest.TestCase):
    """`gerar()` é gerador puro. Se um dia alguém fizer ele criar a pasta
    'só para adiantar', este teste cai."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="embarque-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_pasta_alvo_continua_sem_existir(self):
        alvo = self.tmp / "nao-deve-nascer"
        embarque.gerar(dict(COMPLETO, caminho=str(alvo), nome="X"))
        self.assertFalse(alvo.exists())

    def test_nao_mexe_na_pasta_que_ja_existe(self):
        (self.tmp / "meu.txt").write_text("intacto", encoding="utf-8")
        embarque.gerar(dict(COMPLETO, caminho=str(self.tmp), nome="X"))
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["meu.txt"])
        self.assertEqual((self.tmp / "meu.txt").read_text(encoding="utf-8"), "intacto")


class TestValidacao(unittest.TestCase):
    def test_caminho_vazio(self):
        for caminho in ("", "   ", None):
            with self.assertRaises(ValueError):
                embarque.gerar(dict(COMPLETO, caminho=caminho))

    def test_caminho_curto_demais(self):
        with self.assertRaises(ValueError):
            embarque.gerar(dict(COMPLETO, caminho="ab"))


class TestGuardrails(unittest.TestCase):
    """Os do Embarque são OUTROS: aqui a plataforma ainda não existe, e o risco
    é apagar coisa da pessoa numa pasta que ela escolheu."""

    REGRAS = ["Não apague e não sobrescreva", "Se a pasta já tiver conteúdo, pare",
              "Não commite e não rode `git init`", "caminhos absolutos",
              "Não invente arquivo"]

    def test_todo_prompt_leva_os_guardrails(self):
        texto = embarque.gerar(dict(COMPLETO, caminho=r"C:\x\y", nome="X"))["texto"]
        for regra in self.REGRAS:
            self.assertIn(regra, texto, f"guardrail ausente: {regra}")

    def test_pasta_com_conteudo_muda_o_aviso(self):
        vazia = embarque.gerar(dict(COMPLETO, caminho=r"C:\x\y", nome="X"))["texto"]
        cheia = embarque.gerar(dict(COMPLETO, caminho=r"C:\x\y", nome="X",
                                    tem_conteudo="tem"))["texto"]
        self.assertIn("espere eu responder", cheia)
        self.assertNotIn("espere eu responder", vazia)

    def test_o_comando_de_conferencia_usa_barra_normal(self):
        """O texto é colado em PowerShell, cmd ou shell POSIX — barra invertida
        vira escape em um deles."""
        texto = embarque.gerar(dict(COMPLETO, caminho=r"C:\x\y", nome="X"))["texto"]
        comando = re.search(r"```\n(python .*verificar.*)\n```", texto).group(1)
        self.assertNotIn("\\", comando)


class TestTaxonomia(unittest.TestCase):
    def test_sem_projetos_a_plataforma_tem_tres_estagios(self):
        tax = embarque.taxonomia({"usos": ["notas"], "nome": "X"})
        self.assertEqual([e["sigla"] for e in tax["estagios"]], ["CAP", "NOT", "IDE"])
        self.assertEqual(tax["projetos"]["pasta"], "")
        self.assertNotIn("tipos", tax)

    def test_com_projetos_tem_quatro(self):
        tax = embarque.taxonomia({"usos": ["notas", "projetos"], "nome": "X"})
        self.assertEqual(len(tax["estagios"]), 4)
        self.assertEqual(tax["projetos"]["pasta"], "4-projetos")

    def test_decisoes_declara_a_pasta_de_pendencias(self):
        tax = embarque.taxonomia({"usos": ["notas", "decisoes"], "nome": "X"})
        self.assertEqual(tax["pendencias"], "_pendencias")
        self.assertNotIn("pendencias", embarque.taxonomia({"usos": ["notas"], "nome": "X"}))

    def test_nome_vazio_ganha_padrao(self):
        self.assertEqual(embarque.taxonomia({"nome": "  "})["nome"], "Minha plataforma")


class TestPromptCria(unittest.TestCase):
    """O teste que importa: executar o que o texto manda, e abrir o resultado.

    Lê o PROMPT em vez de reusar `sementes()` — se reusasse, provaria que a
    função concorda consigo mesma, não que o texto está certo.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="embarque-cria-"))
        self.raiz = self.tmp / "plataforma"
        self.texto = embarque.gerar(dict(COMPLETO, caminho=str(self.raiz),
                                         nome="Plataforma do teste"))["texto"]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _executar(self):
        bloco = re.search(r"## Passo 2 —.*?```\n(.*?)```", self.texto, re.S).group(1)
        pastas = [l.strip("├─ ").strip() for l in bloco.splitlines()
                  if l.strip().endswith("/") and "├" in l]
        self.raiz.mkdir(parents=True)
        for p in pastas:
            (self.raiz / p).mkdir(parents=True, exist_ok=True)
        parte = self.texto.split("## Passo 3", 1)[1].split("## Passo 4", 1)[0]
        criados = []
        for m in re.finditer(r"### `([^`]+)`\n\n```[a-z]*\n(.*?)\n```", parte, re.S):
            rel, corpo = m.group(1), m.group(2)
            (self.raiz / rel).write_text(corpo + "\n", encoding="utf-8")
            criados.append(rel)
        return pastas, criados

    def test_a_estrutura_criada_e_uma_plataforma_valida(self):
        pastas, criados = self._executar()
        self.assertIn("plataforma.json", criados)
        self.assertIn("_indice.md", criados)
        cfg = config.carregar(self.raiz)
        self.assertTrue(cfg.ok(), "o marcador não foi criado — a Estação não abriria")
        self.assertEqual(cfg.nome, "Plataforma do teste")
        for e in cfg.estagios:
            self.assertTrue((self.raiz / e["pasta"]).is_dir(), e["pasta"])
            self.assertTrue((self.raiz / e["pasta"] / cfg.historico).is_dir())

    def test_o_plataforma_json_criado_e_json_valido(self):
        self._executar()
        dados = json.loads((self.raiz / "plataforma.json").read_text(encoding="utf-8"))
        self.assertIn("estagios", dados)
        self.assertIn("arquivos", dados)

    def test_o_claude_md_nasce_com_a_regra_de_salvar(self):
        """É isto que faz a IA do usuário commitar sozinha desde o dia um."""
        self._executar()
        texto = (self.raiz / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Salvar é automático; publicar é decisão", texto)
        self.assertIn("sem pedir autorização", texto)
        self.assertIn("nunca `git add .`", texto.lower())
        self.assertIn("Push só com autorização explícita e separada", texto)

    def test_o_gitignore_nasce_junto(self):
        """Plataforma nova sem .gitignore é como o segredo entra no histórico."""
        self._executar()
        texto = (self.raiz / ".gitignore").read_text(encoding="utf-8")
        for padrao in ("cache/", "__pycache__/", ".env", "*.log"):
            self.assertIn(padrao, texto)

    def test_o_sem_destino_nasce_ja_sincronizado(self):
        """Senão o `verificar` acusa 'desatualizado' numa plataforma com um
        minuto de vida, e o primeiro contato com o sistema é um alarme falso."""
        self._executar()
        texto = (self.raiz / "_sem-destino.md").read_text(encoding="utf-8")
        for e in config.carregar(self.raiz).estagios:
            chave = e["sigla"].lower()
            bloco = texto.split(f"<!-- gerado:{chave}:inicio -->")[1] \
                         .split(f"<!-- gerado:{chave}:fim -->")[0]
            self.assertIn("nada nesta etapa", bloco)


class TestRegistrar(unittest.TestCase):
    """Escreve só no config do hub — nunca dentro de plataforma nenhuma."""

    def setUp(self):
        import os
        self.tmp = Path(tempfile.mkdtemp(prefix="embarque-reg-"))
        self._hub = os.environ.get("ESTACAO_HUB")
        os.environ["ESTACAO_HUB"] = str(self.tmp)

    def tearDown(self):
        import os
        if self._hub is not None:
            os.environ["ESTACAO_HUB"] = self._hub
        else:
            os.environ.pop("ESTACAO_HUB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_registra_e_aparece(self):
        embarque.registrar(r"C:\x\minha", "Minha")
        nomes = [p["nome"] for p in config.plataformas()]
        self.assertEqual(nomes, ["Minha"])

    def test_registrar_de_novo_nao_duplica(self):
        embarque.registrar(r"C:\x\minha", "Minha")
        embarque.registrar(r"C:\x\minha", "Renomeada")
        regs = config.plataformas()
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0]["nome"], "Renomeada")

    def test_nao_nasce_ativa(self):
        """A pasta pode nem existir ainda — ativar sem estrutura só daria erro."""
        embarque.registrar(r"C:\x\minha", "Minha")
        self.assertFalse(config.plataformas()[0]["ativa"])

    def test_caminho_invalido(self):
        with self.assertRaises(ValueError):
            embarque.registrar("", "X")


if __name__ == "__main__":
    unittest.main()
