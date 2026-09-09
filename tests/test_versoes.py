"""Testes da leitura do git (aba Versões).

Dois riscos aqui. O primeiro é o parse: `--porcelain=v1 -b` é um formato
estável, mas ler errado significa dizer "tudo salvo" quando não está — que é a
única mentira que este módulo não pode contar. O segundo são os estados
degradados: git ausente, pasta que não é repositório, repositório sem remoto,
linha de trabalho sem par na nuvem. Cada um tem que virar mensagem em português,
nunca traceback — a aba que mostra isso é justamente a que precisa funcionar
quando as coisas não estão bem.

Se o `git` não estiver no PATH do ambiente de teste, os casos que precisam dele
**pulam**; não falham.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import versoes  # noqa: E402


def tem_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


TEM_GIT = tem_git()
PRECISA_GIT = unittest.skipUnless(TEM_GIT, "git não está no PATH deste ambiente")


def git(pasta, *args):
    return subprocess.run(["git", "-C", str(pasta), *args],
                          capture_output=True, text=True, timeout=20)


class TestAllowList(unittest.TestCase):
    """Nada fora da lista roda — nem por engano, nem por caminho novo."""

    def test_comando_fora_da_lista_levanta(self):
        with self.assertRaises(KeyError):
            versoes.rodar(".", "push")
        with self.assertRaises(KeyError):
            versoes.rodar(".", "commit")

    def test_a_lista_so_tem_comando_de_leitura(self):
        proibidos = {"commit", "push", "pull", "merge", "reset", "checkout",
                     "add", "rm", "clean", "rebase", "fetch", "init", "clone"}
        for nome, args in versoes.COMANDOS.items():
            self.assertNotIn(args[0], proibidos,
                             f"'{nome}' começa com um subcomando que escreve")

    def test_chaves_de_git_nao_viram_placeholder(self):
        """`@{u}..HEAD` tem chaves de verdade; formatar com str.format quebrava."""
        self.assertIn("@{u}..HEAD", versoes.COMANDOS["nao_enviados"])


class TestParseStatus(unittest.TestCase):
    def test_branch_e_arquivos(self):
        saida = ("## master...origin/master [ahead 2]\n"
                 " M app/server.py\n"
                 "?? app/novo.py\n"
                 " D docs/velho.md\n")
        branch, arquivos = versoes._parse_status(saida)
        self.assertEqual(branch, "master")
        self.assertEqual([a["caminho"] for a in arquivos],
                         ["app/server.py", "app/novo.py", "docs/velho.md"])
        self.assertEqual([a["novo"] for a in arquivos], [False, True, False])
        self.assertEqual(arquivos[2]["rotulo"], "apagado")

    def test_renomeado_fica_com_o_nome_novo(self):
        _, arquivos = versoes._parse_status("## master\nR  velho.md -> novo.md\n")
        self.assertEqual(arquivos[0]["caminho"], "novo.md")

    def test_arvore_limpa(self):
        branch, arquivos = versoes._parse_status("## master\n")
        self.assertEqual(branch, "master")
        self.assertEqual(arquivos, [])

    def test_branch_sem_upstream(self):
        branch, _ = versoes._parse_status("## linha-nova\n")
        self.assertEqual(branch, "linha-nova")


class TestSemaforo(unittest.TestCase):
    """A pergunta que importa: tem trabalho meu que não está salvo?"""

    def test_limpo_e_verde(self):
        s = versoes.semaforo({"e_repo": True, "sujos": []})
        self.assertEqual(s["cor"], "verde")

    def test_modificado_e_ambar(self):
        s = versoes.semaforo({"e_repo": True, "sujos": [{"novo": False}]})
        self.assertEqual(s["cor"], "ambar")

    def test_arquivo_novo_e_vermelho(self):
        """Arquivo nunca salvo é o único caso em que o conteúdo não existe em
        lugar nenhum além do disco — por isso é mais grave que modificado."""
        s = versoes.semaforo({"e_repo": True, "sujos": [{"novo": True}]})
        self.assertEqual(s["cor"], "vermelho")

    def test_pasta_sem_git_e_cinza(self):
        s = versoes.semaforo({"e_repo": False, "sujos": []})
        self.assertEqual(s["cor"], "cinza")


class TestDegradado(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="versoes-deg-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pasta_que_nao_existe(self):
        e = versoes.estado(self.tmp / "nao-existe")
        self.assertFalse(e["e_repo"])
        self.assertIn("não existe", e["erro"])

    def test_pasta_que_nao_e_repositorio(self):
        e = versoes.estado(self.tmp)
        self.assertFalse(e["e_repo"])
        self.assertEqual(e["erro"], versoes.NAO_E_REPO)
        self.assertEqual(e["sujos"], [])      # nunca None: a UI itera nisso

    def test_backups_em_pasta_sem_backup(self):
        b = versoes.backups(self.tmp)
        self.assertEqual(b["quantos"], 0)
        self.assertIsNone(b["desde"])

    def test_backups_conta_e_data(self):
        (self.tmp / "backups").mkdir()
        (self.tmp / "backups" / "a.bak").write_text("x", encoding="utf-8")
        (self.tmp / "backups" / "b.bak").write_text("y", encoding="utf-8")
        b = versoes.backups(self.tmp)
        self.assertEqual(b["quantos"], 2)
        self.assertRegex(b["desde"], r"^\d{4}-\d{2}-\d{2}$")


@PRECISA_GIT
class TestRepositorioDeVerdade(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="versoes-repo-"))
        git(self.tmp, "init", "-b", "master")
        git(self.tmp, "config", "user.email", "teste@exemplo")
        git(self.tmp, "config", "user.name", "Teste")
        (self.tmp / "salvo.md").write_text("conteúdo\n", encoding="utf-8")
        git(self.tmp, "add", "salvo.md")
        git(self.tmp, "commit", "-m", "primeiro ponto salvo")
        # deixa a árvore suja: um arquivo modificado e um nunca salvo
        (self.tmp / "salvo.md").write_text("conteúdo mudado\n", encoding="utf-8")
        (self.tmp / "novo.md").write_text("nunca salvo\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_le_o_estado_real(self):
        e = versoes.estado(self.tmp)
        self.assertTrue(e["e_repo"])
        self.assertEqual(e["branch"], "master")
        caminhos = sorted(a["caminho"] for a in e["sujos"])
        self.assertEqual(caminhos, ["novo.md", "salvo.md"])
        self.assertEqual(len(e["commits"]), 1)
        self.assertEqual(e["ultimo"]["mensagem"], "primeiro ponto salvo")
        self.assertEqual(e["ultimo"]["arquivos"], ["salvo.md"])
        self.assertIsNotNone(e["ultimo"]["ha_quanto"])

    def test_semaforo_vermelho_com_arquivo_novo(self):
        self.assertEqual(versoes.semaforo(versoes.estado(self.tmp))["cor"], "vermelho")

    def test_sem_remoto(self):
        e = versoes.estado(self.tmp)
        self.assertFalse(e["tem_remoto"])
        self.assertIsNone(e["remoto"])

    def test_sem_upstream_nao_estoura(self):
        """`@{u}` FALHA com erro quando não há par na nuvem — o módulo tem que
        tratar isso, não assumir que devolve 0."""
        e = versoes.estado(self.tmp)
        self.assertIsNone(e["nao_enviados"])
        self.assertTrue(e.get("sem_upstream"))

    def test_repositorio_sem_nenhum_commit(self):
        vazio = Path(tempfile.mkdtemp(prefix="versoes-vazio-"))
        try:
            git(vazio, "init", "-b", "master")
            e = versoes.estado(vazio)
            self.assertTrue(e["e_repo"])
            self.assertEqual(e["commits"], [])
            self.assertIsNone(e["ultimo"])
        finally:
            shutil.rmtree(vazio, ignore_errors=True)

    def test_com_remoto_declarado(self):
        git(self.tmp, "remote", "add", "origin", "https://exemplo.invalido/x.git")
        e = versoes.estado(self.tmp)
        self.assertTrue(e["tem_remoto"])
        self.assertIn("exemplo.invalido", e["remoto"])


@PRECISA_GIT
class TestPrompts(unittest.TestCase):
    """Nenhum prompt sai sem os guardrails — mesmo contrato do briefing."""

    REGRAS = ["`git add` nominal", "Nunca `git add .`", "Nunca commite segredo",
              "reset --hard", "push --force"]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="versoes-prompt-"))
        git(self.tmp, "init", "-b", "master")
        git(self.tmp, "config", "user.email", "teste@exemplo")
        git(self.tmp, "config", "user.name", "Teste")
        (self.tmp / "a.md").write_text("a\n", encoding="utf-8")
        git(self.tmp, "add", "a.md")
        git(self.tmp, "commit", "-m", "inicial")
        (self.tmp / "b.md").write_text("b\n", encoding="utf-8")
        self.estado = versoes.estado(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_todos_levam_os_guardrails(self):
        for tipo in ("salvar", "nuvem", "linha"):
            texto = versoes.prompt(tipo, self.estado)
            for regra in self.REGRAS:
                self.assertIn(regra, texto, f"guardrail ausente em '{tipo}': {regra}")

    def test_o_status_real_vai_embutido(self):
        """A IA escreve a mensagem a partir do que mudou de verdade — para isso,
        o que mudou precisa estar no texto."""
        texto = versoes.prompt("salvar", self.estado)
        self.assertIn("b.md", texto)
        self.assertIn("inicial", texto)          # o último ponto salvo
        self.assertIn("é uma foto", texto)       # nunca vender como verdade contínua

    def test_salvar_proibe_push(self):
        self.assertIn("Não dê push", versoes.prompt("salvar", self.estado))

    def test_tipo_desconhecido(self):
        with self.assertRaises(ValueError):
            versoes.prompt("apagar-tudo", self.estado)


if __name__ == "__main__":
    unittest.main()
