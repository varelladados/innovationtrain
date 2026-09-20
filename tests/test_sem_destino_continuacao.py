"""`gerar-sem-destino` lê a ÚLTIMA linha de cada grão, não a primeira.

Por que isso importa: o registro é **append-only por doutrina** — linha
existente não se reescreve. Mas fechar a linhagem de um item significa dizer
para onde ele foi, e isso é uma informação que só aparece *depois* da linha
original. As duas regras só convivem de um jeito: quem fecha acrescenta uma
**linha de continuação** (`<id>-N`, a convenção que evita identificador
repetido) com o `→destino` na coluna `Etapa/Tipo`.

Se o gerador lesse só a primeira linha, essa continuação não valeria nada, e
fechar um item passaria a exigir editar a linha original — ou seja, violar o
append-only para satisfazer o gerador. Estes testes fixam a saída correta:
base e continuação são o mesmo grão, e a continuação é quem manda.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent
UTIL = RAIZ_REPO / "metodo" / "estacao.py"

CABECA = ("| ID | Data | Etapa/Tipo | Local | Resumo | Link |\n"
          "|---|---|---|---|---|---|\n")

#: Quatro grãos, um por situação:
#: A) só a linha original, sem destino        -> tem que aparecer
#: B) original + continuação com `→destino`   -> NÃO pode aparecer
#: C) fechado já na própria linha original    -> NÃO pode aparecer (jeito antigo)
#: D) fechado e depois reaberto sem seta      -> tem que aparecer de novo
REGISTRO = (
    "# Registro\n\n## Entradas 2026-08-09\n\n" + CABECA +
    "| 26.08.09-IDE-001-segue-aberta-a1b2 | 2026-08-09 | IDE | `3-ideias/` | ninguem consumiu | [arquivo](<a.md>) |\n"
    "| 26.08.09-IDE-002-vira-skill-c3d4 | 2026-08-09 | IDE | `3-ideias/` | consumida depois | [arquivo](<b.md>) |\n"
    "| 26.08.09-IDE-003-fechada-na-origem-e5f6 | 2026-08-09 | IDE →destino-qualquer | `3-ideias/` | fechada no jeito antigo | [arquivo](<c.md>) |\n"
    "| 26.08.09-IDE-004-reaberta-depois-9a0b | 2026-08-09 | IDE →destino-errado | `3-ideias/` | fechada cedo demais | [arquivo](<d.md>) |\n"
    "\n## Entradas 2026-09-20\n\n" + CABECA +
    "| 26.08.09-IDE-002-vira-skill-c3d4-1 | 2026-09-20 | IDE → skill | `../skills/` | continuacao: fecha a linhagem | [SKILL.md](<s.md>) |\n"
    "| 26.08.09-IDE-004-reaberta-depois-9a0b-1 | 2026-09-20 | IDE | `3-ideias/` | continuacao: o destino nao vingou, volta a fila | [arquivo](<d.md>) |\n"
)

TAXONOMIA = {
    "nome": "Estacao de teste",
    "marcador": "_indice.md",
    # os estagios padrao, copiados: trazem a chave `n` que o estagio_de_sigla le
    "estagios": [dict(e) for e in config.PADROES["estagios"]],
    "historico": "_historico",
    "arquivos": {"indice": "_indice.md", "registro": "_registro.md",
                 "sem_destino": "_sem-destino.md"},
    "tipos": ["DIG"],
    "projetos": None,
}


def montar(raiz: Path):
    for e in TAXONOMIA["estagios"]:
        (raiz / e["pasta"] / TAXONOMIA["historico"]).mkdir(parents=True, exist_ok=True)
    (raiz / "_indice.md").write_text("# estacao\n", encoding="utf-8")
    (raiz / "estacao.json").write_text(
        json.dumps(TAXONOMIA, ensure_ascii=False, indent=2), encoding="utf-8")
    (raiz / "_registro.md").write_text(REGISTRO, encoding="utf-8")
    blocos = ["# Sem destino\n"]
    for e in TAXONOMIA["estagios"]:
        chave = e["sigla"].lower()
        blocos.append(f"\n## {e['plural']}\n\n"
                      f"<!-- gerado:{chave}:inicio -->\n"
                      "*(nada nesta etapa no momento)*\n"
                      f"<!-- gerado:{chave}:fim -->\n")
    (raiz / "_sem-destino.md").write_text("".join(blocos), encoding="utf-8")


class TestContinuacaoFechaLinhagem(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sem-destino-"))
        montar(self.tmp)
        r = subprocess.run([sys.executable, str(UTIL), "gerar-sem-destino",
                            "--raiz", str(self.tmp)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.gerado = (self.tmp / "_sem-destino.md").read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_continuacao_com_seta_tira_o_grao_da_lista(self):
        """O caso que motivou a mudança: a linhagem fecha por acréscimo.

        O grão B tem a linha original **sem** seta e uma continuação **com**
        seta. Lendo a primeira linha, ele apareceria como sem destino para
        sempre; lendo a última, sai da lista — que é o certo, porque ele foi
        consumido.
        """
        self.assertNotIn("26.08.09-IDE-002-vira-skill-c3d4", self.gerado)

    def test_grao_sem_nenhuma_seta_continua_na_lista(self):
        """O contraponto: a mudança não pode esvaziar a lista por acidente."""
        self.assertIn("26.08.09-IDE-001-segue-aberta-a1b2", self.gerado)

    def test_fechado_na_propria_linha_original_segue_fora(self):
        """Compatibilidade: o jeito antigo de fechar (seta na própria linha)
        continua valendo — há dezenas de itens assim no acervo real."""
        self.assertNotIn("26.08.09-IDE-003-fechada-na-origem-e5f6", self.gerado)

    def test_continuacao_sem_seta_depois_de_uma_com_seta(self):
        """Reabrir é gesto legítimo: o grão volta para a lista.

        Decisão do dono (2026-09-20): um grão fechado que recebe **depois**
        uma continuação **sem** seta volta a aparecer em `_sem-destino.md`.
        O caso real é o destino que não vingou — a ideia virou skill, a skill
        foi abandonada, e o item precisa voltar à fila em vez de sumir.

        A alternativa descartada era "uma vez fechado, sempre fechado", que
        obrigaria a abrir um grão novo para retomar trabalho antigo — caro, e
        pior: quebraria a linhagem justamente no ponto em que ela interessa.

        O custo aceito: um acréscimo distraído reabre um item resolvido. Como
        o registro é append-only, desfazer isso é acrescentar `-2` com a seta
        de volta — o que está certo, porque a hesitação também é história.
        """
        self.assertIn("26.08.09-IDE-004-reaberta-depois-9a0b", self.gerado)


if __name__ == "__main__":
    unittest.main()
