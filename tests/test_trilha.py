"""A trilha de exemplo: restaurar instantâneos, e o portão que a limita a exemplos.

Dois riscos justificam este arquivo, e nenhum é hipotético:

1. **A trilha apodrece em silêncio.** Ninguém *roda* um exemplo; se um
   instantâneo sair do lugar ou o `plataforma.json` deixar de declarar os passos,
   nada quebra até alguém clicar — e aí é tarde.
2. **`reiniciar` apaga arquivos.** O que impede o comando de tocar numa
   plataforma de verdade é uma chave de configuração, e uma chave é fácil de
   afrouxar sem perceber. O teste do portão existe para que afrouxar quebre o
   build.
"""
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402
import trilha  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent
PLATAFORMAS = RAIZ_REPO / "plataformas"
EXEMPLO = PLATAFORMAS / "exemplo"
PRECOS = PLATAFORMAS / "exemplo-precos"

PRECISA = unittest.skipUnless((EXEMPLO / "plataforma.json").exists(),
                              "plataformas/exemplo não está ao lado do app")


class _ComConfig(unittest.TestCase):
    """Aplica uma config e a devolve ao fim — o estado é de módulo."""

    RAIZ = EXEMPLO

    def setUp(self):
        self._anterior = config._ATUAL
        config.aplicar(config.carregar(self.RAIZ))

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)


@PRECISA
class TestPortao(_ComConfig):
    """Sem `estado_inicial`, a trilha não existe — nem para ler, nem para agir."""

    RAIZ = PRECOS

    def test_a_plataforma_de_precos_so_tem_o_passo_zero(self):
        estado = trilha.estado()
        self.assertTrue(estado["tem"])
        self.assertEqual(estado["total"], 0, "esta plataforma não declara passos")

    def test_restaurar_um_passo_que_nao_existe_recusa(self):
        with self.assertRaises(trilha.TrilhaError):
            trilha.restaurar(3)


class TestPortaoSemChave(unittest.TestCase):
    """Uma plataforma de verdade não pode ser restaurada, e nem sabe da trilha."""

    def setUp(self):
        self._anterior = config._ATUAL
        # uma config sem `estado_inicial`: é o que qualquer plataforma real é
        cfg = config.carregar(EXEMPLO)
        dados = dict(cfg._d)
        dados.pop("estado_inicial", None)
        dados.pop("tutorial", None)
        config.aplicar(config.Config(cfg.raiz, dados, "teste"))

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)

    def test_nao_ha_trilha(self):
        self.assertEqual(trilha.passos(), [])
        self.assertFalse(trilha.estado()["tem"])

    def test_restaurar_recusa_sem_tocar_em_nada(self):
        with self.assertRaises(trilha.TrilhaError):
            trilha.restaurar(0)


@PRECISA
class TestPassos(_ComConfig):
    def test_a_plataforma_versionada_esta_no_passo_zero(self):
        """Se isto cair, alguém commitou o exemplo no meio da trilha."""
        self.assertEqual(trilha.estado()["passo"], 0)

    def test_todo_passo_declarado_existe_em_disco(self):
        for p in trilha.passos()[1:]:
            pasta = (EXEMPLO / str(p["pasta"]).replace("\\", "/")).resolve()
            self.assertTrue((pasta / "plataforma.json").is_file(),
                            f"instantâneo ausente: {pasta}")
            self.assertNotIn(EXEMPLO, pasta.parents,
                             "instantâneo dentro da plataforma: seria apagado junto")

    def test_os_arquivos_constantes_nao_derivaram(self):
        """O que não muda entre passos tem que ser igual em todos.

        Sem isto, editar o `_indice.md` do exemplo e esquecer de propagar faz o
        primeiro clique em "voltar ao início" desfazer a edição — em silêncio.
        """
        constantes = ["_indice.md", "_trilha.md", "CLAUDE.md", "plataforma.json"]
        for p in trilha.passos():
            pasta = (EXEMPLO / str(p["pasta"]).replace("\\", "/")).resolve()
            for rel in constantes:
                self.assertEqual(
                    (pasta / rel).read_bytes(), (EXEMPLO / rel).read_bytes(),
                    f"{rel} do passo {p['n']} divergiu da plataforma")


@PRECISA
class TestPercurso(unittest.TestCase):
    """Percorre a trilha inteira e volta — numa cópia, nunca no exemplo versionado.

    A cópia mora dentro de `plataformas/` de propósito: os passos são declarados
    por caminho relativo (`../_passos/...`), e de fora deles nada resolveria.
    """

    COPIA = PLATAFORMAS / "_teste-trilha"

    @classmethod
    def setUpClass(cls):
        if not (EXEMPLO / "plataforma.json").exists():
            raise unittest.SkipTest("sem plataforma de exemplo")
        shutil.rmtree(cls.COPIA, ignore_errors=True)
        shutil.copytree(EXEMPLO, cls.COPIA)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.COPIA, ignore_errors=True)

    def setUp(self):
        self._anterior = config._ATUAL
        config.aplicar(config.carregar(self.COPIA))

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)

    @staticmethod
    def _impressao(base):
        return {str(f.relative_to(base)).replace("\\", "/"): f.read_bytes()
                for f in sorted(base.rglob("*")) if f.is_file()}

    def test_percorre_e_volta_identico(self):
        antes = self._impressao(self.COPIA)
        total = trilha.estado()["total"]
        self.assertGreaterEqual(total, 3)

        for n in range(1, total + 1):
            trilha.restaurar(n)
            self.assertEqual(trilha.estado()["passo"], n,
                             f"o passo {n} não foi reconhecido depois de restaurado")

        # no último passo a plataforma tem que ter mudado de verdade
        self.assertNotEqual(self._impressao(self.COPIA), antes,
                            "percorrer a trilha inteira não mudou nada")

        trilha.restaurar(0)
        self.assertEqual(self._impressao(self.COPIA), antes,
                         "voltar ao início não devolveu o estado exato")

    def test_o_registro_ganha_setas_ao_longo_da_trilha(self):
        """A trilha existe para mostrar a linhagem aparecendo. Se as setas não
        aparecem, os instantâneos foram montados errado."""
        setas = []
        for n in range(0, trilha.estado()["total"] + 1):
            trilha.restaurar(n)
            texto = config.atual().arquivo("registro").read_text(encoding="utf-8")
            # só linha de tabela: o cabeçalho do registro *explica* o marcador
            # `→` em prosa, e contar o arquivo inteiro dava 3 no passo 0.
            setas.append(sum(1 for l in texto.splitlines()
                             if l.startswith("|") and "→" in l))
        trilha.restaurar(0)
        self.assertEqual(setas, sorted(setas), f"as setas não crescem: {setas}")
        self.assertEqual(setas[0], 0, "o passo 0 não pode ter seta nenhuma")
        self.assertGreater(setas[-1], 0, "o último passo não tem linhagem marcada")


if __name__ == "__main__":
    unittest.main()
