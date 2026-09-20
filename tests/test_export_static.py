"""Testes da máscara de dado pessoal do snapshot estático.

Rodar: python -m unittest discover tests   (na raiz da Central)

Por que só a máscara: o resto do `export_static` é montagem de HTML, que quebra
alto e na cara de quem roda. A máscara é o oposto — falha em silêncio e o
prejuízo é dado de outra pessoa publicado num link. O caso do
`test_nao_deixa_cauda_visivel` é uma regressão real, achada conferindo o arquivo
gerado antes de publicar: a primeira versão do filtro não ancorava as bordas,
casava dentro de uma sequência maior e trocava só o fim dela, deixando o começo
do telefone visível ao lado do rótulo de removido.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import export_static  # noqa: E402


class TestMascara(unittest.TestCase):
    def mascarar(self, texto):
        return export_static.mascarar(texto)[0]

    def test_telefone_com_ddd(self):
        for entrada in ("(61) 99876-5432", "61 99876-5432", "+55 61 99876-5432",
                        "99876-5432", "998765432"):
            with self.subTest(entrada=entrada):
                self.assertNotIn("9876", self.mascarar(f"ligar para {entrada} hoje"))

    def test_telefone_fixo(self):
        self.assertNotIn("3322", self.mascarar("fixo (61) 3322-4455"))

    def test_nao_deixa_cauda_visivel(self):
        """A regressão: sem borda, a máscara comia o fim e deixava o começo."""
        saida = self.mascarar("o outro é 21 9998299829, anota")
        self.assertNotIn("21 9998", saida)
        self.assertNotIn("9998299829", saida)
        self.assertIn("[telefone removido]", saida)

    def test_poupa_identificador_hexadecimal(self):
        """Id do OneNote e hash de imagem têm letra grudada no dígito: não são
        telefone, e mascarar quebraria a rastreabilidade do acervo."""
        onenote = "onenote-id: 0-1c37efde3fe4497b8359201289065d0b!1-F21DCC7A"
        self.assertEqual(self.mascarar(onenote), onenote)

    def test_email_cpf_cnpj(self):
        saida = self.mascarar("fulano@exemplo.com.br, 123.456.789-00, 12.345.678/0001-99")
        self.assertNotIn("fulano", saida)
        self.assertNotIn("123.456", saida)
        self.assertNotIn("0001-99", saida)

    def test_conta_o_que_removeu(self):
        _, contagem = export_static.mascarar("(61) 99876-5432 e outro@x.com")
        self.assertEqual(contagem["[telefone removido]"], 1)
        self.assertEqual(contagem["[e-mail removido]"], 1)

    def test_texto_limpo_passa_intacto(self):
        texto = "Uma nota sem dado pessoal nenhum, com o número 42 e a data 2026-09-20."
        self.assertEqual(self.mascarar(texto), texto)

    def test_nao_quebra_o_json(self):
        """A máscara roda sobre o JSON já serializado: o rótulo não pode ter
        aspas nem barra, senão o `window.CENTRAL_STATIC` não parseia."""
        import json
        original = json.dumps({"nota": "ligar (61) 99876-5432", "ok": True}, ensure_ascii=False)
        mascarado = self.mascarar(original)
        self.assertEqual(json.loads(mascarado)["ok"], True)
        self.assertNotIn("9876", json.loads(mascarado)["nota"])


if __name__ == "__main__":
    unittest.main()
