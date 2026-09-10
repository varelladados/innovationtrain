"""Testes do gerador de briefing pra IA.

O que importa aqui: o bloco de guardrails nunca pode sumir de um briefing (é o
que impede a sessão de IA de commitar sozinha, apagar fisicamente ou fechar
pendência por inferência), e os caminhos citados têm que ser os **reais da
plataforma ativa** — desde o Trecho 3 eles saem do config, então o teste monta
uma plataforma temporária em vez de depender de uma plataforma real existir.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402  (insere app/ no sys.path)
import briefing  # noqa: E402
import pendencias  # noqa: E402


DOUTRINA = "metodo/regras.md"
CHECKLIST = "metodo/classificar.md"
UTILITARIO = "metodo/plataforma.py"


def plataforma_de_teste(raiz, **extra):
    """Plataforma temporária com os documentos do método declarados, mais uma
    pasta de projeto — é o mínimo que os três briefings citam."""
    raiz = Path(raiz)
    (raiz / "1-capturas").mkdir(exist_ok=True)
    (raiz / "5-projetos" / "projeto-de-teste").mkdir(parents=True, exist_ok=True)
    return apoio.aplicar(
        raiz,
        doutrina=DOUTRINA, checklist=CHECKLIST, fluxo="metodo/taxonomia.md",
        utilitario=UTILITARIO, pendencias="pendencias",
        **extra)


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
    # A regra de salvar mudou de sentido no Trecho 8 (doutrina, regra 6): o que
    # o briefing tem que mandar agora é commitar sozinho e pedir autorização só
    # para o push. O teste cobra as duas metades, porque afirmar só uma deixaria
    # passar exatamente a versão antiga.
    REGRAS = ["append-only", "Nunca pule etapa",
              "Salvar é automático; publicar é decisão",
              "sem me pedir autorização",
              "Push só com autorização explícita e separada",
              "nunca `git add .`",
              "por inferência", "Apagar é sempre lógico", "novo-id",
              "vive no repositório", "declarar em `excluir`"]

    def test_nao_manda_mais_esperar_autorizacao_pra_commitar(self):
        """O erro que custou trabalho perdido não pode voltar por descuido."""
        for texto in (briefing.briefing_pendencias()["texto"],
                      briefing.briefing_classificar("1-capturas/x.md")["texto"],
                      briefing.briefing_avancar("projeto-de-teste", [], {})["texto"]):
            self.assertNotIn("Nunca commite automaticamente", texto)
            self.assertNotIn("só commite depois", texto.lower())

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-brf-gr-"))
        plataforma_de_teste(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _checar(self, texto):
        for regra in self.REGRAS:
            self.assertIn(regra, texto, f"guardrail ausente: {regra}")
        # os caminhos citados são os que a plataforma declara, não literais
        self.assertIn(DOUTRINA, texto)
        self.assertIn(UTILITARIO, texto)
        self.assertIn("CAP → NOT → IDE → FUN → PRJ", texto)

    def test_guardrails_em_pendencias(self):
        self._checar(briefing.briefing_pendencias()["texto"])

    def test_guardrails_em_classificar(self):
        self._checar(briefing.briefing_classificar("1-capturas/x.md")["texto"])

    def test_guardrails_em_avancar(self):
        self._checar(briefing.briefing_avancar("projeto-de-teste", [], {})["texto"])


class TestPendencias(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-brf-"))
        self.pend = self.tmp / "pendencias"
        self.pend.mkdir()
        plataforma_de_teste(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escrever(self, slug, conteudo):
        (self.pend / f"pendencia-ativa-2026-09-08-{slug}.md").write_text(conteudo, encoding="utf-8")

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
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-brf-cl-"))
        plataforma_de_teste(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_recusa_caminho_fora_do_primeiro_estagio(self):
        for path in ["", "5-projetos/qualquer/CLAUDE.md", "metodo/regras.md"]:
            with self.assertRaises(ValueError):
                briefing.briefing_classificar(path)

    def test_cita_checklist_e_regra_dos_dois_criterios(self):
        r = briefing.briefing_classificar("1-capturas/26.09.08-CAP-001-x-ab12.md")
        self.assertIn(CHECKLIST, r["texto"])
        self.assertIn("2 ou mais", r["texto"])
        self.assertIn("26.09.08-CAP-001-x-ab12.md", r["texto"])
        # o destino da promoção é o estágio seguinte, tirado do config
        self.assertIn("--etapa NOT", r["texto"])
        self.assertIn("1-capturas/_historico/", r["texto"])

    def test_inclui_trecho_do_conteudo(self):
        rel = "1-capturas/x.md"
        cache = {rel: "---\nid: x\n---\n\n## Conteúdo bruto\n\nA ideia crua aqui."}
        r = briefing.briefing_classificar(rel, cache)
        self.assertIn("A ideia crua aqui", r["texto"])
        self.assertNotIn("id: x", r["texto"])  # frontmatter fica de fora


class TestAvancar(unittest.TestCase):
    PASTA = "projeto-de-teste"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-brf-av-"))
        plataforma_de_teste(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_destaca_essenciais(self):
        rel = f"{self.PASTA}/backlog-teste.md"
        entries = [{"path": rel, "type": "backlog", "title": "Backlog", "size_bytes": 1}]
        r = briefing.briefing_avancar(self.PASTA, entries, {rel: BACKLOG})
        self.assertIn("publicar a primeira versão", r["texto"])
        self.assertIn("**2**", r["texto"])  # 2 abertos
        self.assertIn("**1** marcados", r["texto"])
        self.assertIn("CLAUDE.md", r["texto"])

    def test_pasta_invalida(self):
        # pasta vazia, pasta que não existe, e travessia de caminho
        for pasta in ["", "naoexiste", "../..", "5-projetos/projeto-de-teste"]:
            with self.assertRaises(ValueError):
                briefing.briefing_avancar(pasta, [], {})

    def test_projeto_sem_backlog(self):
        r = briefing.briefing_avancar(self.PASTA, [], {})
        self.assertIn("nenhum backlog indexado", r["texto"])


class TestGerar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="estacao-brf-ge-"))
        plataforma_de_teste(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tipo_desconhecido(self):
        with self.assertRaises(ValueError):
            briefing.gerar("inventado")

    def test_devolve_o_tipo(self):
        self.assertEqual(briefing.gerar("pendencias")["tipo"], "pendencias")


if __name__ == "__main__":
    unittest.main()
