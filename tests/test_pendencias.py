"""Testes do parser e da escrita de pendência-formulário.

Rodar: python -m unittest discover tests   (na raiz do PRJ-Estacao)

Cobre o que é arriscado regredir em silêncio: as variantes de formato que
existem de fato na pasta execucao/ (se o parser voltar a exigir o heading
canônico, pendência some da tela sem erro nenhum), a preservação de CRLF, e as
regras de escrita — só a linha pedida muda, e conflito vira 409.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402  (insere app/ no sys.path)
import pendencias  # noqa: E402


CANONICA = """# Pendência: título de teste

**Item relacionado:** `algum/caminho.md`
**Fonte:** orquestra:algum/caminho.md#slug
**Criada em:** 2026-09-08 (rodada 99)
**Adiada:** 0
**Categoria:** 💡 Incremento
**Tipo de decisão:** uma frase
**Essencial pra rodar:** não
**Revisar quando:** o teste passar a falhar

## Contexto
Duas frases de contexto.

## Pergunta
A pergunta objetiva?

## Resposta (marque uma opção)
- [ ] A — primeira opção
- [ ] B — segunda opção
- [ ] Outra resposta: _______________
- [ ] Deixar para depois
"""

RESPOSTA_NUA = """# Pendência: heading sem parêntese

**Fonte:** processo:teste#nu
**Adiada:** 2
**Categoria:** 🔧 Sustentação
**Essencial pra concluir o processo:** sim

## Contexto
Contexto.

## Pergunta
Pergunta?

## Resposta
- [ ] Sim
- [ ] Não
"""

MULTI_PERGUNTA = """# Pendência: três decisões de uma vez

**Fonte:** orquestra:x.md#y
**Adiada:** 0
**Categoria:** 💡 Incremento

## Contexto
Contexto do lote.

## Pergunta 1 — piso de promoção?
- [ ] A — manter 3
- [ ] B — baixar para 2
- [ ] Deixar para depois

## Pergunta 2 — adotar o template?
- [x] A — adotar como está
- [ ] B — ajustar pesos
- [ ] Outra resposta: _______________
"""

SUB_PERGUNTA = """# Pendência: formato antigo com sub-headings

**Fonte:** backlog:x.md#y
**Adiada:** 0

## Contexto
Contexto.

## Perguntas

### 1. Primeira?
- [ ] Abrir todos
- [x] Nenhum por enquanto

### 2. Segunda?
- [ ] Só LinkedIn
"""

SEM_BLOCO = """# Pendência: sem bloco de resposta

**Fonte:** processo:teste#sem
**Adiada:** 0

## Contexto
Só contexto, nenhuma opção — formato pré-canônico.
"""


class BaseTemp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-test-"))
        self.exec_dir = self.tmp / "execucao"
        self.exec_dir.mkdir()
        self.backups = self.tmp / "backups"
        # a pasta de pendências vem do config da plataforma ativa, não de uma
        # constante de módulo — é o mesmo caminho que o servidor percorre
        apoio.aplicar(self.tmp, pendencias="execucao")
        self._orig_backup = pendencias.BACKUPS_DIR
        pendencias.BACKUPS_DIR = self.backups

    def tearDown(self):
        pendencias.BACKUPS_DIR = self._orig_backup
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escrever(self, slug, conteudo, eol="\n", data="2026-09-08"):
        caminho = self.exec_dir / f"pendencia-ativa-{data}-{slug}.md"
        with caminho.open("w", encoding="utf-8", newline="") as f:
            f.write(conteudo.replace("\n", eol))
        return caminho


class TestParse(BaseTemp):
    def test_canonica(self):
        c = pendencias.parse_pendencia(self.escrever("canonica", CANONICA))
        self.assertEqual(c["title"], "título de teste")
        self.assertEqual(c["ref"], "2026-09-08-canonica")
        self.assertEqual(c["categoria"], "Incremento")
        self.assertEqual(c["estado"], "aberta")
        self.assertFalse(c["essencial"])
        self.assertEqual(c["revisar_quando"], "o teste passar a falhar")
        self.assertEqual(c["fonte"], "orquestra:algum/caminho.md#slug")
        self.assertEqual(len(c["perguntas"]), 1)
        opcoes = c["perguntas"][0]["opcoes"]
        self.assertEqual([o["kind"] for o in opcoes], ["opcao", "opcao", "outra", "adiar"])
        self.assertEqual(opcoes[0]["label"], "A")
        self.assertEqual(opcoes[0]["reason"], "primeira opção")
        self.assertEqual(c["perguntas"][0]["texto"], "A pergunta objetiva?")

    def test_resposta_sem_parenteses(self):
        """Variante real na pasta — o parser antigo do trem descartava o card."""
        c = pendencias.parse_pendencia(self.escrever("nua", RESPOSTA_NUA))
        self.assertTrue(c["parse_ok"])
        self.assertEqual(len(c["perguntas"][0]["opcoes"]), 2)
        self.assertEqual(c["adiada"], 2)
        self.assertTrue(c["essencial"])
        self.assertEqual(c["categoria"], "Sustentação")

    def test_multi_pergunta(self):
        c = pendencias.parse_pendencia(self.escrever("multi", MULTI_PERGUNTA))
        self.assertEqual(len(c["perguntas"]), 2)
        self.assertIn("piso de promoção", c["perguntas"][0]["titulo"])
        self.assertEqual(c["estado"], "respondida")  # pergunta 2 tem [x]

    def test_sub_pergunta(self):
        c = pendencias.parse_pendencia(self.escrever("sub", SUB_PERGUNTA))
        self.assertEqual(len(c["perguntas"]), 2)
        self.assertEqual(c["estado"], "respondida")

    def test_sem_bloco_vira_card_cru(self):
        """Nunca esconder pendência: sem opções, ainda aparece com o texto."""
        c = pendencias.parse_pendencia(self.escrever("sem", SEM_BLOCO))
        self.assertFalse(c["parse_ok"])
        self.assertEqual(c["estado"], "nao-parseavel")
        self.assertIn("pré-canônico", c["raw"])

    def test_adiar_marcado_nao_conta_como_respondida(self):
        texto = CANONICA.replace("- [ ] Deixar para depois", "- [x] Deixar para depois")
        c = pendencias.parse_pendencia(self.escrever("adiada", texto))
        self.assertEqual(c["estado"], "adiada-marcada")

    def test_outra_preenchida_conta_como_respondida(self):
        texto = CANONICA.replace(
            "- [ ] Outra resposta: _______________",
            "- [ ] Outra resposta: fazer de outro jeito")
        c = pendencias.parse_pendencia(self.escrever("outra", texto))
        self.assertEqual(c["estado"], "respondida")

    def test_ignora_arquivo_resolvido(self):
        (self.exec_dir / "pendencia-resolvida-2026-09-08-x.md").write_text(CANONICA, encoding="utf-8")
        self.assertEqual(len(pendencias.listar_pendencias_ativas()["cards"]), 0)

    def test_listar_ordena_adiadas_primeiro(self):
        self.escrever("zzz", CANONICA)
        self.escrever("aaa", RESPOSTA_NUA)  # Adiada: 2
        cards = pendencias.listar_pendencias_ativas()["cards"]
        self.assertEqual(cards[0]["slug"], "aaa")


class TestResponder(BaseTemp):
    def _opcao(self, ref, indice=0, pergunta=0):
        card = pendencias.parse_pendencia(
            self.exec_dir / f"pendencia-ativa-{ref}.md")
        return card["perguntas"][pergunta]["opcoes"][indice]

    def test_marcar_muda_uma_linha_so(self):
        caminho = self.escrever("m", CANONICA)
        antes = caminho.read_text(encoding="utf-8").splitlines()
        op = self._opcao("2026-09-08-m", 0)
        r = pendencias.responder("2026-09-08-m", op["line_number"], op["text"], "marcar")
        self.assertEqual(r["estado"], "respondida")
        depois = caminho.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(antes), len(depois))
        diferentes = [i for i, (a, b) in enumerate(zip(antes, depois)) if a != b]
        self.assertEqual(diferentes, [op["line_number"]])
        self.assertTrue(depois[op["line_number"]].startswith("- [x] A —"))

    def test_preserva_crlf(self):
        caminho = self.escrever("crlf", CANONICA, eol="\r\n")
        op = self._opcao("2026-09-08-crlf", 1)
        pendencias.responder("2026-09-08-crlf", op["line_number"], op["text"], "marcar")
        bruto = caminho.read_bytes()
        # nenhum LF solto: tirando os CRLF, não pode sobrar \n nenhum
        self.assertNotIn(b"\n", bruto.replace(b"\r\n", b""))
        self.assertIn(b"- [x] B \xe2\x80\x94 segunda", bruto)

    def test_desmarcar(self):
        caminho = self.escrever("d", CANONICA)
        op = self._opcao("2026-09-08-d", 0)
        pendencias.responder("2026-09-08-d", op["line_number"], op["text"], "marcar")
        op2 = self._opcao("2026-09-08-d", 0)
        pendencias.responder("2026-09-08-d", op2["line_number"], op2["text"], "desmarcar")
        self.assertEqual(pendencias.parse_pendencia(caminho)["estado"], "aberta")

    def test_outra_resposta_grava_texto(self):
        caminho = self.escrever("o", CANONICA)
        op = self._opcao("2026-09-08-o", 2)
        r = pendencias.responder("2026-09-08-o", op["line_number"], op["text"], "outra",
                                 texto="fazer do meu jeito")
        self.assertEqual(r["estado"], "respondida")
        self.assertIn("- [x] Outra resposta: fazer do meu jeito",
                      caminho.read_text(encoding="utf-8"))

    def test_adiar_e_alias_de_marcar(self):
        caminho = self.escrever("a", CANONICA)
        op = self._opcao("2026-09-08-a", 3)
        r = pendencias.responder("2026-09-08-a", op["line_number"], op["text"], "adiar")
        self.assertEqual(r["estado"], "adiada-marcada")
        self.assertIn("- [x] Deixar para depois", caminho.read_text(encoding="utf-8"))

    def test_conflito_quando_linha_mudou(self):
        self.escrever("c", CANONICA)
        op = self._opcao("2026-09-08-c", 0)
        with self.assertRaises(pendencias.ConflitoError):
            pendencias.responder("2026-09-08-c", op["line_number"],
                                 "- [ ] A — texto que não é o do disco", "marcar")

    def test_linha_fora_do_bloco_de_resposta(self):
        self.escrever("f", CANONICA)
        with self.assertRaises(pendencias.PendenciaError):
            pendencias.responder("2026-09-08-f", 0, "# Pendência: título de teste", "marcar")

    def test_ref_invalido(self):
        for ref in ["../../etc/passwd", "sem-data", "2026-09-08-x/../y", ""]:
            with self.assertRaises(pendencias.PendenciaError):
                pendencias.responder(ref, 1, "x", "marcar")

    def test_texto_multilinha_recusado(self):
        self.escrever("ml", CANONICA)
        op = self._opcao("2026-09-08-ml", 2)
        with self.assertRaises(pendencias.PendenciaError):
            pendencias.responder("2026-09-08-ml", op["line_number"], op["text"], "outra",
                                 texto="linha1\nlinha2")

    def test_outra_em_linha_que_nao_e_outra(self):
        self.escrever("x", CANONICA)
        op = self._opcao("2026-09-08-x", 0)
        with self.assertRaises(pendencias.PendenciaError):
            pendencias.responder("2026-09-08-x", op["line_number"], op["text"], "outra",
                                 texto="algo")

    def test_faz_backup_antes_de_gravar(self):
        self.escrever("b", CANONICA)
        op = self._opcao("2026-09-08-b", 0)
        pendencias.responder("2026-09-08-b", op["line_number"], op["text"], "marcar")
        self.assertEqual(len(list(self.backups.glob("*.bak"))), 1)

    def test_nao_toca_em_fonte_nem_adiada(self):
        caminho = self.escrever("z", RESPOSTA_NUA)
        op = self._opcao("2026-09-08-z", 0)
        pendencias.responder("2026-09-08-z", op["line_number"], op["text"], "marcar")
        texto = caminho.read_text(encoding="utf-8")
        self.assertIn("**Fonte:** processo:teste#nu", texto)
        self.assertIn("**Adiada:** 2", texto)
        self.assertNotIn("Resolvida", texto)


if __name__ == "__main__":
    unittest.main()
