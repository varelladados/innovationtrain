"""Vocabulário próprio da estação — a chave `vocabulario`, o `glossario` e os
tipos com nome (decisão 8 de `metodo/taxonomia.md`).

O princípio 5 diz que o nome próprio é identidade e o mecanismo é do produto.
Até a 0.17 isso valia para estágios, siglas, arquivos de sistema e campos de
frontmatter; o resto — estação, registro, pendência, índice… — estava escrito
no código. A chave `vocabulario` é um de-para por placeholders: a estação troca
o nome, o produto guarda o genérico ao lado. A regra que estes testes fixam:

    na tela, o rótulo da estação substitui e o genérico vai para o tooltip
    no briefing saem os dois, lado a lado
    chave ausente, id ausente, id desconhecido: vale o termo do método

Os termos das fixtures são inventados (uma oficina), e assim devem continuar:
este repositório é público.
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

RAIZ_REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = RAIZ_REPO / "app" / "templates" / "index.html"

#: Uma estação que chama as coisas do seu jeito — e só algumas delas.
VOCABULARIO = {
    "estacao": "Oficina",
    "projeto": {"rotulo": "Obra", "plural": "Obras", "artigo": "a", "nota": "o que já saiu da bancada"},
    "registro": "Diário",
    "sem_destino": "Na bancada",
    "pendencia": "Dúvida",
    "trem": "trem",                      # igual ao genérico: não conta como próprio
    "bilhete": "Bilhete",                # id que não existe: ignorado
    "estagio.2": "Esboço",               # estágio não entra aqui: ignorado
    "capturar": "",                      # vazio: vale o genérico
}
TIPOS = [{"sigla": "FER", "nome": "Ferramenta"}, "MAQ", {"sigla": " ", "nome": "sem sigla"}]


def montar(raiz: Path, **extra):
    tax = {
        "nome": "Oficina de testes",
        "marcador": "_indice.md",
        "tipos": TIPOS,
        "vocabulario": dict(VOCABULARIO),
        "glossario": "glossario.md",
        "entrada": "1-capturas",
    }
    tax.update(extra)
    (raiz / "_indice.md").write_text("# oficina\n", encoding="utf-8")
    (raiz / "glossario.md").write_text("# Glossário da oficina\n\n**Obra** — o que saiu da bancada.\n",
                                        encoding="utf-8")
    (raiz / "estacao.json").write_text(json.dumps(tax, ensure_ascii=False, indent=2), encoding="utf-8")
    return tax


class _ComEstacao(unittest.TestCase):
    extra = {}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vocab-"))
        montar(self.tmp, **self.extra)
        self._anterior = config._ATUAL
        self.cfg = config.aplicar(config.carregar(self.tmp))

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestSemAChave(_ComEstacao):
    """Uma estação que nunca ouviu falar de `vocabulario`."""
    extra = {"vocabulario": None, "glossario": None, "tipos": ["app", "dados"]}

    def test_vale_o_termo_do_metodo(self):
        self.assertEqual(self.cfg.termo("estacao"), "estação")
        self.assertEqual(self.cfg.termo("estacao", plural=True), "estações")
        self.assertEqual(self.cfg.termo_duplo("estacao"), "estação")
        self.assertFalse(self.cfg.vocabulario["estacao"]["proprio"])

    def test_todos_os_ids_do_metodo_estao_la(self):
        self.assertEqual(set(self.cfg.vocabulario), set(config.PADROES["vocabulario"]))
        self.assertEqual(set(self.cfg.resumo()["vocabulario"]), set(config.PADROES["vocabulario"]))

    def test_o_artigo_generico_e_o_declarado_no_metodo(self):
        self.assertEqual(self.cfg.artigo("estacao"), "a")
        self.assertEqual(self.cfg.artigo("registro"), "o")
        self.assertEqual(self.cfg.artigo("pendencia"), "a")

    def test_tipos_em_string_continuam_valendo(self):
        self.assertEqual(self.cfg.tipos, ["app", "dados"])
        self.assertIsNone(self.cfg.tipos_nome("app"))
        self.assertEqual(self.cfg.tipos_detalhe, [{"sigla": "app", "nome": None},
                                                  {"sigla": "dados", "nome": None}])

    def test_sem_glossario(self):
        self.assertIsNone(self.cfg.resumo()["glossario"])
        self.assertIsNone(self.cfg.caminho("glossario"))

    def test_estagio_com_o_nome_do_metodo_nao_vem_em_dobro(self):
        self.assertEqual(self.cfg.estagio_duplo(2), "Nota")
        self.assertEqual(self.cfg.estagio_duplo(2, plural=True), "Notas")


class TestComAChave(_ComEstacao):
    """A oficina: alguns termos trocados, os outros do método."""

    def test_o_rotulo_substitui_e_o_generico_fica_ao_lado(self):
        v = self.cfg.vocabulario["estacao"]
        self.assertEqual(self.cfg.termo("estacao"), "Oficina")
        self.assertEqual(v["generico"], "estação")
        self.assertTrue(v["proprio"])
        self.assertEqual(self.cfg.termo_duplo("estacao"), "Oficina (estação)")

    def test_igual_ao_generico_nao_e_proprio(self):
        self.assertFalse(self.cfg.vocabulario["trem"]["proprio"])
        self.assertEqual(self.cfg.termo_duplo("trem"), "trem")

    def test_plural(self):
        # string simples: o plural repete o rótulo
        self.assertEqual(self.cfg.termo("estacao", plural=True), "Oficina")
        self.assertEqual(self.cfg.termo_duplo("estacao", plural=True), "Oficina (estações)")
        # objeto: o declarado
        self.assertEqual(self.cfg.termo("projeto", plural=True), "Obras")
        self.assertEqual(self.cfg.termo_duplo("projeto", plural=True), "Obras (projetos)")

    def test_artigo_declarado_vence_e_sem_ele_vale_a_terminacao(self):
        self.assertEqual(self.cfg.artigo("projeto"), "a")     # declarado
        self.assertEqual(self.cfg.artigo("estacao"), "a")     # "Oficina" termina em a
        self.assertEqual(self.cfg.artigo("registro"), "o")    # "Diário"
        self.assertEqual(self.cfg.artigo("sem_destino"), "a")  # "Na bancada": a última palavra

    def test_nota_declarada_vence_e_a_metafora_e_do_metodo(self):
        self.assertEqual(self.cfg.vocabulario["projeto"]["nota"], "o que já saiu da bancada")
        self.assertEqual(self.cfg.vocabulario["registro"]["nota"],
                         config.PADROES["vocabulario"]["registro"]["nota"])
        self.assertTrue(self.cfg.vocabulario["projeto"]["metafora"])
        self.assertFalse(self.cfg.vocabulario["registro"]["metafora"])

    def test_id_desconhecido_estagio_e_vazio_sao_ignorados(self):
        self.assertNotIn("bilhete", self.cfg.vocabulario)
        self.assertNotIn("estagio.2", self.cfg.vocabulario)
        self.assertEqual(self.cfg.termo("bilhete"), "bilhete")
        self.assertEqual(self.cfg.termo("capturar"), "Capturar")
        self.assertFalse(self.cfg.vocabulario["capturar"]["proprio"])

    def test_os_nao_declarados_continuam_do_metodo(self):
        declarados = {"estacao", "projeto", "registro", "sem_destino", "pendencia"}
        for id_, v in self.cfg.vocabulario.items():
            self.assertEqual(v["proprio"], id_ in declarados, id_)
        self.assertEqual(self.cfg.termo("embarque"), "embarque")
        self.assertEqual(self.cfg.termo("pendencia", plural=True), "Dúvida")

    def test_tipos_com_nome(self):
        self.assertEqual(self.cfg.tipos, ["FER", "MAQ"])          # a sigla vazia cai fora
        self.assertEqual(self.cfg.tipos_nome("FER"), "Ferramenta")
        self.assertIsNone(self.cfg.tipos_nome("MAQ"))
        self.assertIsNone(self.cfg.tipos_nome("XYZ"))
        self.assertEqual(self.cfg.tipos_detalhe, [{"sigla": "FER", "nome": "Ferramenta"},
                                                  {"sigla": "MAQ", "nome": None}])

    def test_resumo_leva_o_que_a_tela_precisa(self):
        r = self.cfg.resumo()
        self.assertEqual(r["vocabulario"]["estacao"]["rotulo"], "Oficina")
        self.assertEqual(r["tipos_detalhe"][0]["nome"], "Ferramenta")
        self.assertEqual(r["arquivos"], {"indice": "_indice.md", "registro": "_registro.md",
                                         "sem_destino": "_sem-destino.md"})
        self.assertEqual(r["entrada"], "1-capturas")
        self.assertEqual(r["glossario"], "glossario.md")
        self.assertEqual(self.cfg.caminho("glossario"), self.tmp / "glossario.md")
        json.dumps(r)   # tudo serializável

    def test_inline_pelo_central_json_vale_igual(self):
        cfg = config.carregar(self.tmp, inline={"vocabulario": {"registro": "Livro"}})
        self.assertEqual(cfg.termo("registro"), "Livro")
        self.assertEqual(cfg.termo("estacao"), "estação")   # o inline substitui o arquivo inteiro


class TestEstagiosRenomeados(_ComEstacao):
    extra = {"estagios": [
        {"n": 1, "pasta": "1-capturas", "nome": "Achado", "plural": "Achados", "sigla": "CAP"},
        {"n": 2, "pasta": "2-notas", "nome": "Nota", "plural": "Notas", "sigla": "NOT", "artigo": "o"},
        {"n": 3, "pasta": "3-ideias", "nome": "Esboço", "sigla": "IDE"},
    ]}

    def test_estagio_duplo_so_quando_diverge_do_metodo(self):
        self.assertEqual(self.cfg.estagio_duplo(1), "Achado (Captura)")
        self.assertEqual(self.cfg.estagio_duplo(1, plural=True), "Achados (Capturas)")
        self.assertEqual(self.cfg.estagio_duplo(2), "Nota")
        self.assertEqual(self.cfg.estagio_duplo(3, plural=True), "Esboço (Ideias)")
        self.assertEqual(self.cfg.estagio_duplo(9), "")

    def test_artigo_do_estagio(self):
        self.assertEqual(self.cfg.artigo_estagio(1), "o")    # Achado
        self.assertEqual(self.cfg.artigo_estagio(2), "o")    # declarado, mesmo que estranho
        self.assertEqual(self.cfg.artigo_estagio(3), "o")    # Esboço
        self.assertEqual(config._artigo_de("Captura"), "a")
        self.assertEqual(config._artigo_de("Funcionalidade"), "a")
        self.assertEqual(config._artigo_de("Pergunta ao cozinheiro"), "o")


class TestFonteUnica(unittest.TestCase):
    """`PADROES["vocabulario"]` é a cópia executável do Glossário da taxonomia."""

    def test_cada_termo_do_metodo_esta_no_glossario_escrito(self):
        doc = RAIZ_REPO / "metodo" / "taxonomia.md"
        texto = doc.read_text(encoding="utf-8")
        glossario = texto[texto.index("## Glossário"):]
        for id_, v in config.PADROES["vocabulario"].items():
            self.assertIn(f"`{id_}`", glossario, f"id {id_} não está no Glossário")
            self.assertIn(v["rotulo"], glossario, f"rótulo {v['rotulo']} não está no Glossário")

    def test_a_metafora_tem_sete_termos_e_sao_os_marcados(self):
        texto = (RAIZ_REPO / "metodo" / "taxonomia.md").read_text(encoding="utf-8")
        marcados = {k for k, v in config.PADROES["vocabulario"].items() if v["metafora"]}
        self.assertEqual(marcados, {"central", "estacao", "projeto", "trem", "embarque", "trilho", "linha"})
        paragrafo = texto[texto.index("**Metáfora ferroviária"):]
        paragrafo = paragrafo[:paragrafo.index("---")]
        for termo in ("Central", "estação", "projeto", "trem", "embarque", "trilho", "linha"):
            self.assertIn(f"*{termo}*", paragrafo, termo)


if __name__ == "__main__":
    unittest.main()
