"""Testes do gerador de briefing pra IA.

O que importa aqui: o bloco de guardrails nunca pode sumir de um briefing (é o
que impede a sessão de IA de commitar sozinha, apagar fisicamente ou fechar
pendência por inferência), e os caminhos citados têm que ser os reais.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import briefing  # noqa: E402
import pendencias  # noqa: E402


PEND_RESPONDIDA = """# Pendência: decidir o formato

**Fonte:** orquestra:x.md#y
**Adiada:** 0
**Categoria:** 💡 Incremento

## Contexto
Contexto.

## Pergunta
Qual formato?

## Resposta (marque uma opção)
- [x] A — o formato curto
- [ ] B — o formato longo
- [ ] Outra resposta: _______________
- [ ] Deixar para depois
"""

PEND_ADIADA = PEND_RESPONDIDA.replace("- [x] A — o formato curto", "- [ ] A — o formato curto") \
                             .replace("- [ ] Deixar para depois", "- [x] Deixar para depois")

BACKLOG = """# Backlog — Teste

- [ ] **[ESSENCIAL]** publicar a primeira versão
- [ ] item comum aberto
- [x] item fechado

## Links
"""


class TestGuardrails(unittest.TestCase):
    REGRAS = ["append-only", "Nunca pule etapa", "Nunca commite automaticamente",
              "por inferência", "Apagar é sempre lógico", "plataforma.py novo-id",
              "vive no repositório", ".Biblioteca"]

    def _checar(self, texto):
        for regra in self.REGRAS:
            self.assertIn(regra, texto, f"guardrail ausente: {regra}")
        self.assertIn("_metodo/doutrina.md", texto)

    def test_guardrails_em_pendencias(self):
        self._checar(briefing.briefing_pendencias()["texto"])

    def test_guardrails_em_classificar(self):
        self._checar(briefing.briefing_classificar("1-capturas/.pendente/x.md")["texto"])

    def test_guardrails_em_avancar(self):
        self._checar(briefing.briefing_avancar("PRJ-Teste_X", [], {})["texto"])


class TestPendencias(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="plataformaexp-brf-"))
        self._orig = pendencias.EXECUCAO_DIR
        pendencias.EXECUCAO_DIR = self.tmp

    def tearDown(self):
        pendencias.EXECUCAO_DIR = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escrever(self, slug, conteudo):
        (self.tmp / f"pendencia-ativa-2026-09-08-{slug}.md").write_text(conteudo, encoding="utf-8")

    def test_lista_so_as_respondidas(self):
        self.escrever("resp", PEND_RESPONDIDA)
        self.escrever("adiada", PEND_ADIADA)
        r = briefing.briefing_pendencias()
        self.assertEqual(len(r["itens"]), 1)
        self.assertIn("o formato curto", r["texto"])
        self.assertIn("1 está(ão) com \"Deixar para depois\"", r["texto"])

    def test_sem_respondidas(self):
        self.escrever("adiada", PEND_ADIADA)
        r = briefing.briefing_pendencias()
        self.assertEqual(r["itens"], [])
        self.assertIn("Nenhuma pendência respondida", r["texto"])

    def test_cita_a_fonte_como_chave(self):
        self.escrever("resp", PEND_RESPONDIDA)
        texto = briefing.briefing_pendencias()["texto"]
        self.assertIn("orquestra:x.md#y", texto)
        self.assertIn("não altere", texto)


class TestClassificar(unittest.TestCase):
    def test_recusa_caminho_fora_da_captura(self):
        for path in ["", "PRJ-Qualquer/CLAUDE.md", "_metodo/doutrina.md"]:
            with self.assertRaises(ValueError):
                briefing.briefing_classificar(path)

    def test_cita_checklist_e_regra_dos_dois_criterios(self):
        r = briefing.briefing_classificar("1-capturas/.pendente/26.09.08-SBC-001-x-ab12.md")
        self.assertIn("checklist-classificacao.md", r["texto"])
        self.assertIn("2 ou mais", r["texto"])
        self.assertIn("26.09.08-SBC-001-x-ab12.md", r["texto"])

    def test_inclui_trecho_do_conteudo(self):
        rel = "1-capturas/.pendente/x.md"
        cache = {rel: "---\nid: x\n---\n\n## Conteúdo bruto\n\nA ideia crua aqui."}
        r = briefing.briefing_classificar(rel, cache)
        self.assertIn("A ideia crua aqui", r["texto"])
        self.assertNotIn("id: x", r["texto"])  # frontmatter fica de fora


class TestAvancar(unittest.TestCase):
    def test_destaca_essenciais(self):
        rel = "PRJ-Teste_X/backlog-teste.md"
        entries = [{"path": rel, "type": "backlog", "title": "Backlog", "size_bytes": 1}]
        r = briefing.briefing_avancar("PRJ-Teste_X", entries, {rel: BACKLOG})
        self.assertIn("publicar a primeira versão", r["texto"])
        self.assertIn("**2**", r["texto"])  # 2 abertos
        self.assertIn("**1** marcados", r["texto"])
        self.assertIn("CLAUDE.md", r["texto"])

    def test_pasta_invalida(self):
        for pasta in ["", "naoeprojeto", "../.."]:
            with self.assertRaises(ValueError):
                briefing.briefing_avancar(pasta, [], {})

    def test_projeto_sem_backlog(self):
        r = briefing.briefing_avancar("PRJ-Teste_X", [], {})
        self.assertIn("nenhum backlog indexado", r["texto"])


class TestGerar(unittest.TestCase):
    def test_tipo_desconhecido(self):
        with self.assertRaises(ValueError):
            briefing.gerar("inventado")

    def test_devolve_o_tipo(self):
        self.assertEqual(briefing.gerar("pendencias")["tipo"], "pendencias")


if __name__ == "__main__":
    unittest.main()
