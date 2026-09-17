"""A triagem dentro do app: o portão da aba Nota e a lista de lotes.

Dado fictício do começo ao fim (regra 10 de `metodo/triagem.md`): telefone com
DDD 99, que não existe, e nomes inventados.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apoio  # noqa: E402  (insere app/ no sys.path)
import triagem_ui  # noqa: E402


def _estacao(raiz, **extra):
    raiz.mkdir(parents=True, exist_ok=True)
    cfg = {"nome": raiz.name,
           "estagios": [{"n": 1, "pasta": "1-capturas", "nome": "Captura", "plural": "Capturas", "sigla": "CAP"}],
           "arquivos": {"indice": "_indice.md", "registro": "_registro.md", "sem_destino": "_sem-destino.md"},
           "entrada": "1-capturas"}
    cfg.update(extra)
    (raiz / "estacao.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (raiz / "_indice.md").write_text("# estação de teste\n", encoding="utf-8")
    (raiz / "_registro.md").write_text("# Registro\n\n## Pendente\n\nnada\n", encoding="utf-8")
    return cfg


class PortaoDaNota(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.prof = base / "plataforma"
        self.priv = base / "privada"
        _estacao(self.priv)
        _estacao(self.prof, triagem={
            "pessoal": "../privada", "espera": "../privada/_triagem",
            "projetos": {"Fotolivro": {"esfera": "profissional", "apelidos": ["foto livro"]},
                         "Horta": {"esfera": "pessoal", "apelidos": ["hortinha"]}}})
        apoio.aplicar(self.prof)

    def tearDown(self):
        self.tmp.cleanup()

    def test_texto_de_trabalho_passa_limpo(self):
        c = triagem_ui.conferir("Próximos passos do foto livro: fechar o backlog da semana.")
        self.assertEqual(c["veredito"], "limpo")
        self.assertIn("Fotolivro", c["projetos"])

    def test_para_em_dado_de_terceiro_e_mascara(self):
        c = triagem_ui.conferir("Ligar para (99) 99999-8888 e confirmar a proposta")
        self.assertEqual(c["veredito"], "terceiro")
        self.assertEqual(len(c["sinais"]), 1)
        self.assertNotIn("99999-8888", json.dumps(c, ensure_ascii=False))

    def test_para_em_segredo(self):
        self.assertEqual(triagem_ui.conferir("senha: gato4213verde")["veredito"], "segredo")

    def test_reconhece_vida_pessoal(self):
        self.assertEqual(triagem_ui.conferir("levar minha sobrinha ao dentista")["veredito"], "pessoal")
        self.assertEqual(triagem_ui.conferir("regar a hortinha no fim de semana")["veredito"], "pessoal")

    def test_espera_abre_lote_com_o_bruto(self):
        r = triagem_ui.guardar_na_espera("Ligar para (99) 99999-8888 sobre a casa")
        lote = Path(r["path"])
        self.assertTrue((lote / "bruto" / "colado.md").exists())
        self.assertIn(r["lote"], (self.priv / "_triagem" / "_lotes.md").read_text(encoding="utf-8"))
        # dois textos no mesmo dia com o mesmo começo não se sobrescrevem
        r2 = triagem_ui.guardar_na_espera("Ligar para (99) 99999-8888 sobre a casa")
        self.assertNotEqual(r["lote"], r2["lote"])

    def test_captura_pessoal_vai_para_a_estacao_privada(self):
        r = triagem_ui.captura_pessoal("Aniversário da sobrinha no sábado")
        self.assertTrue(Path(r["path"]).exists())
        self.assertEqual(Path(r["path"]).parents[1], self.priv)
        conteudo = Path(r["path"]).read_text(encoding="utf-8")
        self.assertIn("origem: nota direta pela Central, triada como pessoal", conteudo)
        self.assertIn(r["id"], (self.priv / "_registro.md").read_text(encoding="utf-8"))
        self.assertFalse((self.prof / "1-capturas").exists())

    def test_sem_configuracao_nao_inventa_destino(self):
        _estacao(Path(self.tmp.name) / "sozinha")
        apoio.aplicar(Path(self.tmp.name) / "sozinha")
        self.assertIsNone(triagem_ui.pessoal())
        self.assertIsNone(triagem_ui.espera())
        for fn in (triagem_ui.captura_pessoal, triagem_ui.guardar_na_espera):
            with self.assertRaises(triagem_ui.TriagemUIError):
                fn("qualquer coisa")
        self.assertEqual(triagem_ui.lotes(), [])


class AbaTriagem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.prof, self.priv = base / "plataforma", base / "privada"
        _estacao(self.priv)
        _estacao(self.prof, triagem={"pessoal": "../privada", "espera": "../privada/_triagem"})
        apoio.aplicar(self.prof)
        lote = self.priv / "_triagem" / "2099-01-01-teste"
        (lote / "bruto").mkdir(parents=True)
        (lote / "bruto" / "colado.md").write_text("texto", encoding="utf-8")
        (lote / "relatorio-v1.md").write_text("# r", encoding="utf-8")
        (lote / "decisoes.json").write_text(json.dumps({
            "lote": "2099-01-01-teste", "versao": 1, "em_uma_frase": "um lote de teste",
            "trechos": [{"id": "A"}, {"id": "B"}], "seguiu": [{"trecho": "B"}],
            "perguntas": [{"id": "P1", "titulo": "É trabalho?", "resposta": None,
                           "opcoes": [{"id": "A", "texto": "sim"}]},
                          {"id": "P2", "titulo": "Já respondida", "resposta": "A", "opcoes": []}],
        }, ensure_ascii=False), encoding="utf-8")
        (self.priv / "_triagem" / "_historico").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_estado_lista_o_lote_e_as_perguntas_abertas(self):
        e = triagem_ui.estado()
        self.assertEqual(len(e["lotes"]), 1)   # `_historico` não é lote
        lote = e["lotes"][0]
        self.assertTrue(lote["tem_decisoes"])
        self.assertEqual((lote["trechos"], lote["seguiu"], lote["itens_brutos"]), (2, 1, 1))
        self.assertEqual(lote["relatorios"], ["relatorio-v1.md"])
        abertas = [p for p in lote["perguntas"] if not p["resposta"]]
        self.assertEqual([p["id"] for p in abertas], ["P1"])

    def test_lote_sem_leitura_aparece_assim_mesmo(self):
        (self.priv / "_triagem" / "2099-01-02-cru" / "bruto").mkdir(parents=True)
        lotes = {l["lote"]: l for l in triagem_ui.lotes()}
        self.assertFalse(lotes["2099-01-02-cru"]["tem_decisoes"])
        self.assertEqual(lotes["2099-01-02-cru"]["perguntas"], [])

    def test_decisoes_quebrado_nao_derruba_a_aba(self):
        (self.priv / "_triagem" / "2099-01-01-teste" / "decisoes.json").write_text("{quebrado", encoding="utf-8")
        self.assertFalse(triagem_ui.lotes()[0]["tem_decisoes"])


if __name__ == "__main__":
    unittest.main()
