"""A versão tem uma fonte só (`VERSION`), e o resto tem de concordar com ela.

Três lugares repetem o número: o cabeçalho do `CENTRAL.md`, o topo do
`changelog-central.md` e o header HTTP `Server` (que o servidor lê do arquivo).
Esquecer um deles é o erro mais comum de um lançamento de correção — o
`Central/0.14` que ficou no header até a 0.16.1 é o exemplo.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import server  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
VERSAO = (RAIZ / "VERSION").read_text(encoding="utf-8").strip()


class TestVersao(unittest.TestCase):
    def test_formato(self):
        self.assertRegex(VERSAO, r"^\d+\.\d+\.\d+$")

    def test_cabecalho_do_central_md(self):
        texto = (RAIZ / "CENTRAL.md").read_text(encoding="utf-8")
        m = re.search(r"\*\*Documento\*\*\s*·\s*v(\d+\.\d+\.\d+)", texto)
        self.assertIsNotNone(m, "o cabeçalho `**Documento** · vX.Y.Z` do CENTRAL.md sumiu")
        self.assertEqual(m.group(1), VERSAO, "CENTRAL.md e VERSION discordam")

    def test_topo_do_changelog(self):
        texto = (RAIZ / "changelog-central.md").read_text(encoding="utf-8")
        m = re.search(r"^## (\d+\.\d+\.\d+)\b", texto, re.M)
        self.assertIsNotNone(m, "o changelog não tem entrada de versão")
        self.assertEqual(m.group(1), VERSAO, "o topo do changelog e VERSION discordam")

    def test_header_http_acompanha_o_arquivo(self):
        self.assertEqual(server.versao(), VERSAO)
        self.assertEqual(server.Handler.server_version, f"Central/{VERSAO}")


if __name__ == "__main__":
    unittest.main()
