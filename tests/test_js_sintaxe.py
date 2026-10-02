"""O `<script>` embutido da página é JavaScript válido.

Era um passo à mão ("se mexer no `<script>` de `index.html`, `node --check` no
trecho extraído"); um erro de sintaxe ali não aparece em nenhum teste de Python e
deixa a página inteira sem funcionar. Pula se o node não estiver instalado.
"""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

INDEX = pathlib.Path(__file__).absolute().parents[1] / "app" / "templates" / "index.html"
BLOCO = re.compile(r"<script>(.*?)</script>", re.S)


@unittest.skipUnless(shutil.which("node"), "node não está instalado")
class TestScriptEmbutido(unittest.TestCase):
    def test_o_script_da_pagina_compila(self):
        blocos = BLOCO.findall(INDEX.read_text(encoding="utf-8"))
        self.assertTrue(blocos, "nenhum <script> embutido achado no index.html")
        with tempfile.TemporaryDirectory() as tmp:
            for n, codigo in enumerate(blocos, 1):
                arq = pathlib.Path(tmp) / f"bloco{n}.js"
                arq.write_text(codigo, encoding="utf-8")
                r = subprocess.run(["node", "--check", str(arq)], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                self.assertEqual(r.returncode, 0, f"bloco {n}: {r.stderr[-800:]}")


if __name__ == "__main__":
    unittest.main()
