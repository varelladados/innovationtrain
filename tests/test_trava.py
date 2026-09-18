"""A trava do registro, entre processos — e as capturas que ela protege.

A corrida foi medida antes da trava existir: dois processos capturando juntos na
mesma estação deram SEQ repetido, linha perdida no registro (mais arquivos que
linhas) e, no Windows, um dos dois morto por `PermissionError` no `os.replace` do
registro que o outro lia. As capturas abaixo repetem aquele experimento pelos
três caminhos que gravam — a nota da interface, a captura pessoal da interface e
o `capturar` da linha de comando — e conferem o contrário: toda captura com a sua
linha, nenhuma sequência repetida, e nenhuma trava deixada para trás.

Tudo em pasta temporária: nada toca a estação de exemplo nem o `cache/`.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parent.parent
METODO = RAIZ_REPO / "metodo"
sys.path.insert(0, str(METODO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import embarque  # noqa: E402
import trava  # noqa: E402

ID_RE = re.compile(r"^(\d{2}\.\d{2}\.\d{2})-CAP-(\d{3})-")

#: Segura a trava até aparecer o arquivo `solta` — ou até ser morto.
SEGURA = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import trava
registro, pasta = Path(sys.argv[2]), Path(sys.argv[3])
with trava.do_registro(registro, espera=10):
    (pasta / "segurando").write_text("")
    while not (pasta / "solta").exists():
        time.sleep(0.01)
'''

#: Captura `n` vezes pelo caminho pedido. Todos os filhos largam juntos: cada um
#: avisa que está pronto e espera o `vai`.
CAPTURA = r'''
import random, sys, time
from pathlib import Path
repo, tag, modo, raiz, n, pasta = sys.argv[1:7]
repo, raiz, n, pasta = Path(repo), Path(raiz), int(n), Path(pasta)
sys.path[:0] = [str(repo / "app"), str(repo / "metodo")]
if modo == "linha":
    import triagem
else:
    import config, notas, triagem_ui
    config.aplicar(config.carregar(raiz))
    notas.BACKUPS_DIR = pasta / "backups"
(pasta / ("pronto-" + tag)).write_text("")
while not (pasta / "vai").exists():
    time.sleep(0.005)
for i in range(n):
    texto = f"captura {tag} numero {i}"
    if modo == "nota":
        novo = notas.criar_captura_crua(texto)["id"]
    elif modo == "pessoal":
        novo = triagem_ui.captura_pessoal(texto)["id"]
    else:
        novo, _ = triagem.capturar(raiz, texto, texto, lote="-", trecho="-")
    print(novo, flush=True)
    time.sleep(random.uniform(0, 0.03))   # uma folga entre capturas, para a fila se revezar
'''


def _estacao(raiz, **extra):
    raiz.mkdir(parents=True, exist_ok=True)
    cfg = {"nome": raiz.name,
           "estagios": [{"n": 1, "pasta": "1-capturas", "nome": "Captura", "plural": "Capturas", "sigla": "CAP"}],
           "arquivos": {"indice": "_indice.md", "registro": "_registro.md", "sem_destino": "_sem-destino.md"},
           "entrada": "1-capturas", "utilitario": (METODO / "estacao.py").as_posix()}
    cfg.update(extra)
    (raiz / "estacao.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (raiz / "_indice.md").write_text("# estação de teste\n", encoding="utf-8")
    (raiz / "_registro.md").write_text("# Registro\n\n## Pendente\n\nnada\n", encoding="utf-8")
    (raiz / "_sem-destino.md").write_text(
        "# Sem destino\n\n<!-- gerado:cap:inicio -->\n<!-- gerado:cap:fim -->\n", encoding="utf-8")
    return raiz


class _ComFilhos(unittest.TestCase):
    """Pasta temporária e processos filhos, que nunca sobrevivem ao teste."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self._tmp.name)
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.communicate()
        self._tmp.cleanup()

    def _filho(self, script, *args):
        p = subprocess.Popen([sys.executable, "-c", script, *map(str, args)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", errors="replace",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.procs.append(p)
        return p

    def _esperar(self, pronto, rotulo, limite=60):
        """Espera `pronto()`; falha na hora se algum filho morreu antes."""
        fim = time.monotonic() + limite
        while not pronto():
            for p in self.procs:
                if p.poll() is not None:
                    self.fail(f"{rotulo}: um filho saiu antes, com {p.returncode}:\n{p.communicate()[1]}")
            if time.monotonic() > fim:
                self.fail(f"{rotulo}: passou de {limite} s")
            time.sleep(0.01)


class Trava(_ComFilhos):
    def setUp(self):
        super().setUp()
        self.registro = self.pasta / "_registro.md"
        self.registro.write_text("# Registro\n", encoding="utf-8")

    def _outro_processo_segurando(self):
        filho = self._filho(SEGURA, METODO, self.registro, self.pasta)
        self._esperar(lambda: (self.pasta / "segurando").exists(), "o filho não pegou a trava")
        return filho

    def test_o_arquivo_so_existe_enquanto_alguem_grava(self):
        with trava.do_registro(self.registro) as alvo:
            self.assertEqual(alvo, self.pasta / "_registro.md.trava")
            self.assertTrue(alvo.exists())
        self.assertFalse(alvo.exists(), "a trava ficou na pasta depois de solta")

    def test_pasta_que_nao_existe_falha_sem_esperar(self):
        inicio = time.monotonic()
        with self.assertRaises(trava.TravaErro) as ctx:
            with trava.do_registro(self.pasta / "nao-existe" / "_registro.md", espera=5):
                pass
        self.assertNotIsInstance(ctx.exception, trava.TravaOcupada)
        self.assertLess(time.monotonic() - inicio, 2)

    def test_outro_processo_espera_ou_desiste(self):
        filho = self._outro_processo_segurando()
        with self.assertRaises(trava.TravaOcupada):
            with trava.do_registro(self.registro, espera=0.3):
                self.fail("dois processos com a trava ao mesmo tempo")
        (self.pasta / "solta").write_text("")
        with trava.do_registro(self.registro, espera=15):
            pass
        self.assertEqual(filho.wait(timeout=30), 0)
        self.assertFalse(trava.caminho(self.registro).exists())

    def test_processo_que_morre_nao_deixa_a_estacao_travada(self):
        """A trava abandonada: quem solta é o sistema, sem idade nem PID para adivinhar."""
        filho = self._outro_processo_segurando()
        filho.kill()
        filho.wait(timeout=30)
        alvo = trava.caminho(self.registro)
        self.assertTrue(alvo.exists(), "o processo morto devia ter deixado o arquivo para trás")
        with trava.do_registro(self.registro, espera=10):
            pass
        self.assertFalse(alvo.exists(), "a captura seguinte devia ter levado o arquivo que sobrou")

    def test_confere_que_o_arquivo_travado_e_o_do_caminho(self):
        """A conferência que torna seguro apagar a trava no Linux — exercitada em todo sistema."""
        a, b = self.pasta / "a.trava", self.pasta / "b.trava"
        b.write_text("")
        fd = os.open(a, os.O_RDWR | os.O_CREAT)
        try:
            self.assertTrue(trava._mesmo_arquivo(fd, a))
            self.assertFalse(trava._mesmo_arquivo(fd, b))
            self.assertFalse(trava._mesmo_arquivo(fd, self.pasta / "sumiu.trava"))
            if sys.platform != "win32":     # no Windows, arquivo aberto não se apaga
                os.unlink(a)
                a.write_text("")
                self.assertFalse(trava._mesmo_arquivo(fd, a), "não percebeu o arquivo trocado")
        finally:
            os.close(fd)


class ForaDoGit(unittest.TestCase):
    """O arquivo é passageiro; o `.gitignore` cobre o instante em que ele existe."""

    def test_as_estacoes_do_embarque_ignoram(self):
        self.assertIn("*.trava", embarque.GITIGNORE.splitlines())

    def test_a_central_ignora_nos_exemplos(self):
        alvo = trava.caminho("estacoes/exemplo/_registro.md").as_posix()
        try:
            r = subprocess.run(["git", "-C", str(RAIZ_REPO), "check-ignore", "-q", alvo],
                               capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git fora do PATH")
        if r.returncode not in (0, 1):
            self.skipTest("não é um repositório git")
        self.assertEqual(r.returncode, 0, f"{alvo} não está coberto pelo .gitignore da Central")


class CapturasSimultaneas(_ComFilhos):
    """Dois processos capturando ao mesmo tempo na mesma estação."""

    N = 6

    def setUp(self):
        super().setUp()
        self.privada = _estacao(self.pasta / "privada")
        self.prof = _estacao(self.pasta / "plataforma", triagem={"pessoal": "../privada"})

    def _capturar_juntos(self, *filhos):
        for tag, modo, raiz in filhos:
            self._filho(CAPTURA, RAIZ_REPO, tag, modo, raiz, self.N, self.pasta)
        self._esperar(lambda: len(list(self.pasta.glob("pronto-*"))) == len(filhos),
                      "os filhos não ficaram prontos")
        (self.pasta / "vai").write_text("")
        ids = []
        for p in self.procs:
            saida, erro = p.communicate(timeout=300)
            self.assertEqual(p.returncode, 0, erro)
            ids.append(saida.split())
        return ids

    def _confere(self, estacao, por_filho):
        self.assertEqual([len(l) for l in por_filho], [self.N] * len(por_filho))
        ids = [i for l in por_filho for i in l]
        self.assertEqual(len(set(ids)), len(ids), f"identificador repetido: {ids}")

        registro = (estacao / "_registro.md").read_text(encoding="utf-8")
        celulas = [l.split("|")[1].strip() for l in registro.splitlines() if l.startswith("| ")]
        self.assertEqual(sorted(c for c in celulas if ID_RE.match(c)), sorted(ids),
                         "linha perdida (ou a mais) no registro")

        por_dia = {}
        for i in ids:
            m = ID_RE.match(i)
            por_dia.setdefault(m.group(1), []).append(int(m.group(2)))
        for dia, seqs in por_dia.items():
            self.assertEqual(sorted(seqs), list(range(1, len(seqs) + 1)),
                             f"SEQ repetido ou pulado em {dia}")

        self.assertEqual(sorted(p.stem for p in (estacao / "1-capturas").glob("*.md")), sorted(ids))
        sem_destino = (estacao / "_sem-destino.md").read_text(encoding="utf-8")
        self.assertEqual([i for i in ids if i not in sem_destino], [],
                         "o sem-destino regenerado por último não viu todas as capturas")
        self.assertFalse(trava.caminho(estacao / "_registro.md").exists(), "a trava ficou para trás")

    def test_nota_da_interface_e_linha_de_comando(self):
        self._confere(self.prof, self._capturar_juntos(("a", "nota", self.prof),
                                                       ("b", "linha", self.prof)))

    def test_captura_pessoal_da_interface_e_linha_de_comando(self):
        self._confere(self.privada, self._capturar_juntos(("a", "pessoal", self.prof),
                                                          ("b", "linha", self.privada)))


if __name__ == "__main__":
    unittest.main()
