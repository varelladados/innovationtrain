"""Siglas legadas — a plataforma que já tinha acervo quando adotou a Estação.

O caso que motivou isto é concreto: um sistema pessoal com 154 identificadores
já emitidos em três siglas próprias, num registro que é **append-only por
doutrina** e com o identificador embutido em nome de pasta. Reescrever tudo
custaria caro e mentiria sobre o histórico; ignorar as siglas antigas faria as
154 linhas virarem "estágio desconhecido" no dia da migração.

A saída é uma chave de configuração: `siglas_legadas` mapeia cada sigla antiga
para o **número do estágio** a que ela corresponde hoje. A regra que estes
testes fixam é a fronteira entre ler e escrever:

    lê tudo (registro, nome de arquivo, sem-destino, verificar, métricas)
    escreve só o vocabulário de hoje (novo-id recusa sigla legada)

Sem essa fronteira, um item novo nasceria com a sigla que a migração veio
aposentar, e a taxonomia antiga nunca terminaria de sair.
"""
import json
import re
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
UTIL = RAIZ_REPO / "metodo" / "plataforma.py"

#: A forma do caso real: três siglas antigas, cinco estágios novos. A do meio
#: (`SBI`) cai em ideias; a última (`SBZ`) pula para projetos, porque o estágio
#: de funcionalidade não existia na taxonomia antiga — e é justamente esse
#: "buraco" que o mapa por NÚMERO resolve e um mapa por posição não resolveria.
LEGADAS = {"SBC": 2, "SBI": 3, "SBZ": 5}


def taxonomia(**extra):
    d = {
        "nome": "Plataforma com acervo",
        "marcador": "_indice.md",
        "estagios": [dict(e) for e in config.PADROES["estagios"]],
        "historico": "_historico",
        "arquivos": {"indice": "_indice.md", "registro": "_registro.md",
                     "sem_destino": "_sem-destino.md"},
        "tipos": ["DIG", "DAD"],
        "projetos": {"pasta": "5-projetos", "prefixo_re": None},
        "siglas_legadas": dict(LEGADAS),
    }
    d.update(extra)
    return d


CABECA = ("| ID | Data | Etapa/Tipo | Local | Resumo | Link |\n"
          "|---|---|---|---|---|---|\n")

#: Duas linhas com sigla legada (uma já avançada, uma sem destino) e uma com a
#: sigla de hoje — a mistura permanente que a migração produz de propósito.
REGISTRO = (
    "# Registro\n\n## Entradas 2026-08-31\n\n" + CABECA +
    "| 26.08.31-SBC-001-ideia-antiga-a1b2 | 2026-08-31 | SBC | `2-notas/` | uma crua que ficou | [arquivo](<2-notas/26.08.31-SBC-001-ideia-antiga-a1b2.md>) |\n"
    "| 26.08.31-SBI-DIG-002-output-lapidado-c3d4 | 2026-08-31 | SBI-DIG →26.09.01-SBZ-DIG-001-projeto-velho-e5f6 | `3-ideias/` | virou projeto | [arquivo](<3-ideias/26.08.31-SBI-DIG-002-output-lapidado-c3d4.md>) |\n"
    "\n## Entradas 2026-09-01\n\n" + CABECA +
    "| 26.09.01-SBZ-DIG-001-projeto-velho-e5f6 | 2026-09-01 | SBZ-DIG | `5-projetos/velho/` | projeto da taxonomia antiga | [CLAUDE.md](<5-projetos/velho/CLAUDE.md>) |\n"
    "\n## Entradas 2026-09-10\n\n" + CABECA +
    "| 26.09.10-CAP-001-captura-nova-9f8e | 2026-09-10 | CAP | `1-capturas/` | a primeira com o vocabulário de hoje | [arquivo](<1-capturas/26.09.10-CAP-001-captura-nova-9f8e.md>) |\n"
)


def montar(raiz: Path, **extra):
    """Uma plataforma em disco, com registro misto e os arquivos citados."""
    tax = taxonomia(**extra)
    for e in tax["estagios"]:
        (raiz / e["pasta"] / tax["historico"]).mkdir(parents=True, exist_ok=True)
    (raiz / "_indice.md").write_text("# plataforma\n", encoding="utf-8")
    (raiz / "plataforma.json").write_text(
        json.dumps(tax, ensure_ascii=False, indent=2), encoding="utf-8")
    (raiz / "_registro.md").write_text(REGISTRO, encoding="utf-8")

    blocos = ["# Sem destino\n"]
    for e in tax["estagios"]:
        chave = e["sigla"].lower()
        blocos.append(f"\n## {e.get('plural') or e['nome']}\n\n"
                      f"<!-- gerado:{chave}:inicio -->\n"
                      "*(nada nesta etapa no momento)*\n"
                      f"<!-- gerado:{chave}:fim -->\n")
    (raiz / "_sem-destino.md").write_text("".join(blocos), encoding="utf-8")

    (raiz / "2-notas" / "26.08.31-SBC-001-ideia-antiga-a1b2.md").write_text(
        "# antiga\n", encoding="utf-8")
    (raiz / "3-ideias" / "26.08.31-SBI-DIG-002-output-lapidado-c3d4.md").write_text(
        "# lapidado\n", encoding="utf-8")
    (raiz / "1-capturas" / "26.09.10-CAP-001-captura-nova-9f8e.md").write_text(
        "# nova\n", encoding="utf-8")
    (raiz / "5-projetos" / "velho").mkdir(parents=True, exist_ok=True)
    (raiz / "5-projetos" / "velho" / "CLAUDE.md").write_text(
        "# CLAUDE.md — velho\n", encoding="utf-8")
    return tax


def util(*args):
    return subprocess.run([sys.executable, str(UTIL), *args],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


class _ComPlataforma(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="legadas-"))
        self.tax = montar(self.tmp)
        self._anterior = config._ATUAL
        self.cfg = config.aplicar(config.carregar(self.tmp))

    def tearDown(self):
        if self._anterior is not None:
            config.aplicar(self._anterior)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestConfig(_ComPlataforma):
    def test_as_canonicas_nao_mudam(self):
        """A lista que a interface mostra e da qual sai identificador novo
        continua sendo só a de hoje. Se uma legada vazasse para cá, ela
        apareceria como estágio na tela e como opção de `--etapa`."""
        self.assertEqual(self.cfg.siglas, ["CAP", "NOT", "IDE", "FUN", "PRJ"])

    def test_siglas_todas_soma_as_duas(self):
        self.assertEqual(set(self.cfg.siglas_todas),
                         set(self.cfg.siglas) | set(LEGADAS))

    def test_as_mais_longas_primeiro(self):
        """Numa alternância de regex a primeira que casa vence — uma sigla curta
        que prefixa uma longa truncaria a captura."""
        tamanhos = [len(s) for s in self.cfg.siglas_todas]
        self.assertEqual(tamanhos, sorted(tamanhos, reverse=True))

    def test_estagio_de_sigla_nas_duas_familias(self):
        self.assertEqual(self.cfg.estagio_de_sigla("IDE"), 3)
        self.assertEqual(self.cfg.estagio_de_sigla("SBI"), 3)
        self.assertEqual(self.cfg.estagio_de_sigla("SBZ"), 5)
        self.assertIsNone(self.cfg.estagio_de_sigla("XPT"))

    def test_sigla_canonica_traduz(self):
        self.assertEqual(self.cfg.sigla_canonica("SBC"), "NOT")
        self.assertEqual(self.cfg.sigla_canonica("SBZ"), "PRJ")
        self.assertEqual(self.cfg.sigla_canonica("IDE"), "IDE")

    def test_sigla_desconhecida_volta_como_veio(self):
        """Quem chama decide o que fazer com ela — o config não inventa estágio."""
        self.assertEqual(self.cfg.sigla_canonica("XPT"), "XPT")

    def test_uma_legada_que_repete_a_canonica_e_ignorada(self):
        """Declarar `IDE` como legada seria uma contradição; vence a canônica."""
        cfg = config.carregar(self.tmp, taxonomia(siglas_legadas={"IDE": 1}))
        self.assertEqual(cfg.siglas_legadas, {})
        self.assertEqual(cfg.estagio_de_sigla("IDE"), 3)

    def test_sem_a_chave_nada_muda(self):
        """Plataforma normal não declara `siglas_legadas` — e o comportamento
        tem que ser exatamente o de antes desta feature existir."""
        cfg = config.carregar(self.tmp, taxonomia(siglas_legadas={}))
        self.assertEqual(cfg.siglas_todas, sorted(cfg.siglas, key=lambda s: (-len(s), s)))
        self.assertIsNone(cfg.estagio_de_sigla("SBC"))


class TestRegexes(_ComPlataforma):
    def test_id_re_reconhece_nome_de_arquivo_legado(self):
        for stem in ("26.08.31-SBC-001-ideia-antiga-a1b2",
                     "26.08.31-SBI-DIG-002-output-lapidado-c3d4",
                     "26.09.10-CAP-001-captura-nova-9f8e"):
            self.assertTrue(self.cfg.id_re.match(stem), stem)

    def test_identificador_re_captura_a_sigla_inteira(self):
        m = self.cfg.identificador_re.search(
            "veio de 26.08.31-SBI-DIG-002-output-lapidado-c3d4 hoje")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "SBI")
        self.assertEqual(m.group(3), "DIG")

    def test_etapa_re_acha_a_legada(self):
        self.assertEqual(self.cfg.etapa_re.search("SBZ-DIG").group(1), "SBZ")


class TestWorkflow(_ComPlataforma):
    def test_a_carta_legada_ganha_o_estagio_de_hoje(self):
        """Sem isto o item antigo aparece sem cor no meio dos outros — e a
        escala de maturidade passa a mentir sobre metade do acervo."""
        import workflow
        self.assertEqual(workflow._estagio_de("SBI"), 3)
        self.assertEqual(workflow._estagio_de("SBZ"), 5)
        self.assertEqual(workflow._estagio_de("CAP"), 1)
        self.assertIsNone(workflow._estagio_de("XPT"))


class TestMetricas(_ComPlataforma):
    def test_a_legada_e_contada_no_cartao_do_estagio(self):
        """Os cartões do Dashboard são os estágios declarados: uma chave `SBC`
        não teria onde aparecer, e a linha sumiria da contagem."""
        import metrics
        log = metrics._metricas_log()
        self.assertEqual(log["total_linhas_log"], 4)
        self.assertEqual(log["por_etapa"].get("NOT"), 1)   # o SBC
        self.assertEqual(log["por_etapa"].get("IDE"), 1)   # o SBI
        self.assertEqual(log["por_etapa"].get("PRJ"), 1)   # o SBZ
        self.assertEqual(log["por_etapa"].get("CAP"), 1)
        self.assertNotIn("SBC", log["por_etapa"])
        self.assertNotIn("outro", log["por_etapa"])

    def test_sem_destino_ignora_a_linha_que_ja_avancou(self):
        import metrics
        sd = metrics._metricas_log()["sem_destino_por_etapa"]
        self.assertEqual(sd.get("IDE"), None)  # o SBI tem seta
        self.assertEqual(sd.get("NOT"), 1)

    def test_o_tipo_e_lido_de_um_id_legado(self):
        import metrics
        self.assertEqual(metrics._metricas_log()["por_tipo"].get("DIG"), 2)


class TestUtilitario(unittest.TestCase):
    """O utilitário lê o `plataforma.json` direto — não passa pelo config."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="legadas-util-"))
        montar(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_novo_id_recusa_sigla_legada(self):
        """A fronteira desta feature: lê o antigo, escreve só o de hoje."""
        r = util("novo-id", "--raiz", str(self.tmp), "--etapa", "SBC",
                 "--slug", "nao deve nascer")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("legada", (r.stdout + r.stderr).lower())

    def test_novo_id_com_sigla_de_hoje_funciona(self):
        r = util("novo-id", "--raiz", str(self.tmp), "--etapa", "FUN",
                 "--slug", "uma funcionalidade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout.strip(),
                         r"^\d{2}\.\d{2}\.\d{2}-FUN-\d{3}-uma-funcionalidade-[a-f0-9]{4}$")

    def test_a_sequencia_do_dia_nao_colide_com_a_legada(self):
        """`SBI` e `IDE` são o mesmo estágio, mas sequências independentes —
        o identificador inteiro é que precisa ser único, e o hash garante isso."""
        r = util("novo-id", "--raiz", str(self.tmp), "--etapa", "IDE",
                 "--slug", "ideia nova", "--data", "26.08.31")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("-IDE-001-", r.stdout)

    def test_gerar_sem_destino_agrupa_a_legada_no_estagio_certo(self):
        r = util("gerar-sem-destino", "--raiz", str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.tmp / "_sem-destino.md").read_text(encoding="utf-8")

        def bloco(chave):
            m = re.search(rf"<!-- gerado:{chave}:inicio -->(.*?)<!-- gerado:{chave}:fim -->",
                          texto, re.DOTALL)
            return m.group(1)

        # o SBC sem destino cai no bloco de NOT (estágio 2), não em lugar nenhum
        self.assertIn("26.08.31-SBC-001", bloco("not"))
        # o SBZ sem destino cai no bloco de PRJ (estágio 5)
        self.assertIn("26.09.01-SBZ-DIG-001", bloco("prj"))
        # a captura nova cai no bloco dela
        self.assertIn("26.09.10-CAP-001", bloco("cap"))
        # o SBI tem seta: não é "sem destino" em bloco nenhum
        self.assertNotIn("26.08.31-SBI-DIG-002", texto)
        # e o estágio sem nada continua dizendo isso
        self.assertIn("nada nesta etapa", bloco("fun"))

    def test_verificar_nao_acusa_estagio_desconhecido(self):
        util("gerar-sem-destino", "--raiz", str(self.tmp))
        r = util("verificar", "--raiz", str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("estágio desconhecido", r.stdout)
        self.assertNotIn("PROBLEMA", r.stdout)

    def test_verificar_ainda_acusa_uma_sigla_que_ninguem_declarou(self):
        """A tolerância é só para o que a plataforma declarou como legado.

        O aviso de "estágio desconhecido" olha a coluna **Etapa/Tipo**, e só
        chega a olhá-la em linha que já foi reconhecida como linha de registro —
        o que exige um identificador válido na primeira coluna. Ou seja: o que
        ele pega de verdade é a **discordância** entre o identificador e a
        coluna, não uma linha inteiramente inventada (essa o parser descarta
        antes, e é por isso que a primeira versão deste teste passava batido).
        """
        reg = self.tmp / "_registro.md"
        reg.write_text(reg.read_text(encoding="utf-8") +
                       "| 26.09.10-CAP-002-coluna-discordante-1111 | 2026-09-10 | XPT | `1-capturas/` | ? | [x](<x>) |\n",
                       encoding="utf-8")
        (self.tmp / "1-capturas" / "26.09.10-CAP-002-coluna-discordante-1111.md").write_text(
            "# x\n", encoding="utf-8")
        r = util("verificar", "--raiz", str(self.tmp))
        self.assertIn("estágio desconhecido", r.stdout)
        self.assertIn("XPT", r.stdout)

    def test_uma_linha_com_identificador_invalido_nao_e_linha_de_registro(self):
        """O outro lado da moeda, fixado porque me enganou uma vez: uma sigla
        que não existe em lugar nenhum não gera aviso — ela nem é lida como
        linha. Quem pega esse caso é o teste de arquivo sem linha no registro."""
        reg = self.tmp / "_registro.md"
        reg.write_text(reg.read_text(encoding="utf-8") +
                       "| 26.09.10-XPT-001-sigla-inventada-0000 | 2026-09-10 | XPT | `x/` | ? | [x](<x>) |\n",
                       encoding="utf-8")
        r = util("verificar", "--raiz", str(self.tmp))
        self.assertIn("linhas no registro: 4", r.stdout)
        self.assertNotIn("estágio desconhecido", r.stdout)


if __name__ == "__main__":
    unittest.main()
