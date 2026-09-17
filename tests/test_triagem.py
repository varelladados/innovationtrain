"""Triagem: os sinais que ela levanta, os que ela não pode levantar, e a máscara.

Todo dado aqui é fictício. CPF e CNPJ são números de teste com dígito
verificador válido, de uso público em exemplos; telefones usam o prefixo de
DDD 99, que não existe.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "metodo"))

import triagem  # noqa: E402


def cats(texto):
    return [s["categoria"] for s in triagem.detectar(texto)]


class Telefone(unittest.TestCase):
    def test_formatos_de_telefone(self):
        for t in ("ligar para +55 99 9123-4567 amanhã", "(99) 99999-8888", "99.91234.5678",
                  "99 3344-5566", "celular 98765-4321"):
            with self.subTest(t=t):
                self.assertIn("telefone", cats(t))

    def test_nao_confunde_preco_data_codigo_nem_hash(self):
        for t in ("R$ 2.640.000,00", "R$1.550.000,00", "2026-09-14", "SAN 1185545",
                  "22.59.10", "26.09.11-CAP-001-assunto-65aa", "1789424448804930700",
                  "de 2025-2026", "79m² - 2 quartos"):
            with self.subTest(t=t):
                self.assertNotIn("telefone", cats(t))

    def test_telefone_no_nome_de_arquivo(self):
        self.assertIn("telefone", cats("+55 99 9123-4567.zip"))


class Documentos(unittest.TestCase):
    def test_cpf_so_com_digito_valido(self):
        self.assertIn("cpf", cats("CPF 529.982.247-25"))
        self.assertNotIn("cpf", cats("CPF 529.982.247-24"))
        self.assertNotIn("cpf", cats("pedido 52998224725"))  # sem formato nem palavra-chave

    def test_cnpj(self):
        self.assertIn("cnpj", cats("empresa 11.444.777/0001-61"))
        self.assertNotIn("telefone", cats("empresa 11.444.777/0001-61"))

    def test_email_cep_registro_link(self):
        c = cats("fale com ana@exemplo.com.br, CEP 70000-000, CRECI 12345, https://exemplo.com/a?b=1")
        for esperado in ("email", "cep", "registro", "link"):
            self.assertIn(esperado, c)


class Segredo(unittest.TestCase):
    def test_palavra_chave_e_formato_conhecido(self):
        self.assertIn("segredo", cats("senha: gato4213verde"))
        self.assertIn("segredo", cats("chave sk-ABCDEFGHIJKLMNOPQRSTUVWX12"))

    def test_palavra_chave_em_prosa_nao_e_senha(self):
        self.assertIn("segredo", cats("senha: minhasenhaforte"))
        for t in ("C — Não é senha: registrar como falso positivo",
                  "- **Segredo:** avisar para trocar",
                  "o token: veja a documentação"):
            with self.subTest(t=t):
                self.assertNotIn("segredo", cats(t))

    def test_linha_solta_com_cara_de_senha(self):
        self.assertIn("segredo", cats("ideias do dia\n\ngato4213verde\n\nmais ideias"))

    def test_o_que_nao_e_senha(self):
        for linha in ("26.09.11-CAP-001-assunto-65aa", "d46afa6e9b", "relatorio-2026.md",
                      "ECDWCWC", "braindump-do-onibus", "14/09/2026", "https://exemplo.com/x1"):
            with self.subTest(linha=linha):
                self.assertNotIn("segredo", cats(linha))


class Vocabulario(unittest.TestCase):
    def test_pessoal_saude_e_profissional(self):
        v = triagem.vocabulario("Levar minha sobrinha ao dentista e depois a reunião com o cliente")
        self.assertIn("sobrinha", v["pessoal"])
        self.assertIn("dentista", v["saude"])
        self.assertIn("cliente", v["profissional"])

    def test_extra_da_config(self):
        v = triagem.vocabulario("o bolo da vovó", extra_pessoais=["vovó"])
        self.assertIn("vovo", v["pessoal"])


class Apelidos(unittest.TestCase):
    PROJETOS = {"Fotolivro": {"esfera": "profissional", "apelidos": ["foto livro"]},
                "Horta": {"esfera": "pessoal", "apelidos": ["hortinha"]}}

    def test_exato(self):
        a = triagem.apelidos_em("hoje mexi no Foto-Livro", self.PROJETOS)
        self.assertEqual(a["Fotolivro"]["modo"], "exato")

    def test_aproximado_pega_erro_de_transcricao(self):
        a = triagem.apelidos_em("vou discutir os próximos passos do foto e livro", self.PROJETOS)
        self.assertEqual(a["Fotolivro"]["modo"], "aproximado")

    def test_nao_inventa(self):
        self.assertEqual(triagem.apelidos_em("nada a ver com isso", self.PROJETOS), {})


class Conversa(unittest.TestCase):
    def test_tres_formatos_de_export(self):
        textos = [
            "[5/7/26, 5:24:14 PM] Você: oi\n[5/7/26, 5:25:00 PM] Fulana Tal: Mensagem apagada\n",
            "17/09/2026 17:24 - Você: oi\n17/09/2026 17:25 - Fulana Tal: <Mídia oculta>\n",
            "[17:24] **Você:** oi\n\n[17:25] **Fulana Tal:** _Mensagem apagada_\n",
        ]
        for t in textos:
            with self.subTest(t=t[:12]):
                c = triagem.ler_conversa(t)
                self.assertEqual(c["mensagens"], 2)
                self.assertEqual(c["suas"], 1)
                self.assertEqual(list(c["participantes"]), ["Fulana Tal"])

    def test_texto_comum_nao_e_conversa(self):
        self.assertIsNone(triagem.ler_conversa("uma nota\ncom duas linhas: sem forma de conversa"))


class Mascara(unittest.TestCase):
    def test_mascaras(self):
        self.assertEqual(triagem.mascarar("telefone", "+55 99 9123-4567"), "+•• •• ••••-••67")
        self.assertEqual(triagem.mascarar("participante", "Fulana de Tal"), "F. D. T.")
        self.assertEqual(triagem.mascarar("email", "ana@exemplo.com"), "a•••@exemplo.com")
        self.assertNotIn("gato", triagem.mascarar("segredo", "gato4213verde"))

    def test_mascarar_texto(self):
        self.assertEqual(triagem.mascarar_texto("+55 99 9123-4567/chat.md"), "+•• •• ••••-••67/chat.md")


class Levantamento(unittest.TestCase):
    def test_lote_misto_de_ponta_a_ponta(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "estacao.json").write_text(json.dumps({"triagem": {
                "projetos": {"Fotolivro": {"esfera": "profissional", "apelidos": ["foto livro"]}}}}),
                encoding="utf-8")
            lote = raiz / "lote"
            (lote / "+55 99 9123-4567").mkdir(parents=True)
            (lote / "+55 99 9123-4567" / "chat.txt").write_text(
                "[5/7/26, 5:24:14 PM] Você: oi\n[5/7/26, 5:25:00 PM] Fulana Tal: tudo bem?\n",
                encoding="utf-8")
            (lote / "ditado.md").write_text(
                "---\nmotor: local\n---\nReunião do foto e livro e depois aniversário da minha sobrinha.\n",
                encoding="utf-8")
            (lote / "a.jpg").write_bytes(b"\xff\xd8mesma")
            (lote / "b.jpg").write_bytes(b"\xff\xd8mesma")
            (lote / "dump.txt").write_text("ideias\n\ngato4213verde\n", encoding="utf-8")

            r = triagem.levantar([lote], triagem.carregar_config(raiz))
            por_nome = {it["nome"]: it for it in r["itens"]}

            conversa = por_nome["+55 99 9123-4567/chat.txt"]
            self.assertEqual(conversa["midia"], "conversa")
            self.assertTrue(conversa["sugestao"].startswith("espera"))

            ditado = por_nome["ditado.md"]
            self.assertEqual(ditado["midia"], "transcricao")
            self.assertIn("Fotolivro", ditado["projetos"])
            self.assertTrue(ditado["sugestao"].startswith("misto"))

            self.assertTrue(por_nome["a.jpg"]["sugestao"].startswith("ler antes"))
            self.assertEqual(len(r["duplicatas"]), 1)
            self.assertTrue(por_nome["dump.txt"]["sugestao"].startswith("alerta"))

            md = triagem.markdown(r, "teste")
            self.assertNotIn("9123-4567", md)
            self.assertNotIn("Fulana", md)
            self.assertNotIn("gato4213verde", md)
            self.assertIn("9123-4567", triagem.markdown(r, "teste", mostrar=True))

    def test_estrito_sai_com_1(self):
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / "n.txt"
            arq.write_text("ligar (99) 99999-8888", encoding="utf-8")
            self.assertEqual(triagem.main([str(arq), "--raiz", d, "--estrito", "--saida",
                                           str(Path(d) / "r.md")]), 1)
            arq.write_text("só uma ideia sem dado nenhum", encoding="utf-8")
            self.assertEqual(triagem.main([str(arq), "--raiz", d, "--estrito", "--saida",
                                           str(Path(d) / "r.md")]), 0)


def _estacao(raiz, triagem=None):
    raiz.mkdir(parents=True, exist_ok=True)
    cfg = {"nome": raiz.name,
           "estagios": [{"n": 1, "pasta": "1-capturas", "nome": "Captura", "plural": "Capturas", "sigla": "CAP"}],
           "arquivos": {"indice": "_indice.md", "registro": "_registro.md", "sem_destino": "_sem-destino.md"},
           "entrada": "1-capturas"}
    if triagem is not None:
        cfg["triagem"] = triagem
    (raiz / "estacao.json").write_text(json.dumps(cfg), encoding="utf-8")
    (raiz / "_indice.md").write_text("# teste\n", encoding="utf-8")
    (raiz / "_registro.md").write_text("# Registro\n\n## Pendente\n\nnada\n", encoding="utf-8")


def _decisoes(lote):
    d = {
        "lote": "2099-01-01-teste", "versao": 1, "nota_versao": "primeira leitura",
        "chegou_em": "2099-01-01", "origem": "pasta de teste",
        "em_uma_frase": "um ditado misto",
        "trechos": [
            {"id": "A", "descricao": "reunião do projeto", "esfera": "duvida", "terceiro": ["nome"],
             "motivo": "não se sabe se é trabalho", "depende_de": ["P1", "P2"], "removido": ["nome"]},
            {"id": "B", "descricao": "compromisso de família", "esfera": "pessoal", "motivo": "família",
             "depende_de": [], "saidas": [{"destino": "pessoal", "texto": "trechos/b.md", "slug": "familia"}]},
        ],
        "secoes": [{"titulo": "Só no completo", "texto": "ligar para (99) 99999-8888", "privado": True}],
        "alertas": [],
        "perguntas": [
            {"id": "P1", "titulo": "A reunião é trabalho?", "opcoes": [
                {"id": "A", "texto": "sim", "efeitos": [{"trecho": "A", "esfera": "profissional",
                                                         "saidas": [{"destino": "profissional",
                                                                     "texto": "trechos/a-{P2}.md",
                                                                     "slug": "reuniao projeto"}]}]},
                {"id": "B", "texto": "não, encerrar", "efeitos": [{"trecho": "A", "saidas": [{"destino": "encerrar"}]}]}]},
            {"id": "P2", "titulo": "Quão estrito?", "opcoes": [
                {"id": "A", "texto": "tira nome"}, {"id": "B", "texto": "deixa nome"}]},
        ],
        "seguiu": [],
    }
    (lote / "trechos").mkdir(parents=True)
    (lote / "trechos" / "a-a.md").write_text("Reunião de próximos passos do Fotolivro.", encoding="utf-8")
    (lote / "trechos" / "a-b.md").write_text("Reunião com Fulana, (99) 99999-8888.", encoding="utf-8")
    (lote / "trechos" / "b.md").write_text("Aniversário da sobrinha.", encoding="utf-8")
    (lote / "decisoes.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


class DecidirEAplicar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.prof = base / "plataforma"
        _estacao(self.prof, {"pessoal": "../privada"})
        _estacao(base / "privada")
        self.priv = base / "privada"
        self.lote = self.priv / "_triagem" / "2099-01-01-teste"
        _decisoes(self.lote)

    def tearDown(self):
        self.tmp.cleanup()

    def test_decidir_gera_os_dois_e_o_mascarado_nao_tem_o_privado(self):
        masc = Path(self.tmp.name) / "masc.md"
        self.assertEqual(triagem.cmd_decidir(self.lote, masc), 0)
        completo = (self.lote / "relatorio-v1.md").read_text(encoding="utf-8")
        self.assertIn("99999-8888", completo)
        texto = masc.read_text(encoding="utf-8")
        self.assertNotIn("Só no completo", texto)
        self.assertIn("### P1 — A reunião é trabalho?", texto)

    def test_decidir_recusa_mascarado_que_vaza(self):
        d = json.loads((self.lote / "decisoes.json").read_text(encoding="utf-8"))
        d["alertas"] = ["senha: gato4213verde"]
        (self.lote / "decisoes.json").write_text(json.dumps(d), encoding="utf-8")
        masc = Path(self.tmp.name) / "masc.md"
        with self.assertRaises(triagem.TriagemErro):
            triagem.cmd_decidir(self.lote, masc)
        self.assertFalse(masc.exists())

    def test_simular_nao_grava_nada(self):
        antes = (self.prof / "_registro.md").read_text(encoding="utf-8")
        triagem.cmd_aplicar(self.lote, self.prof, {"P1": "A", "P2": "A"}, confirmar=False)
        self.assertEqual((self.prof / "_registro.md").read_text(encoding="utf-8"), antes)
        self.assertFalse((self.prof / "1-capturas").exists())
        self.assertIsNone(json.loads((self.lote / "decisoes.json").read_text(encoding="utf-8"))
                          ["perguntas"][0].get("resposta"))

    def test_aplicar_leva_cada_trecho_ao_destino_uma_vez(self):
        rc = triagem.cmd_aplicar(self.lote, self.prof, {"P1": "A", "P2": "A"}, confirmar=True)
        self.assertEqual(rc, 0)
        caps = list((self.prof / "1-capturas").glob("*.md"))
        self.assertEqual(len(caps), 1)
        conteudo = caps[0].read_text(encoding="utf-8")
        self.assertIn("triagem:\n  lote: 2099-01-01-teste\n  trecho: A\n  removido: [nome]", conteudo)
        self.assertIn(caps[0].stem, (self.prof / "_registro.md").read_text(encoding="utf-8"))
        self.assertEqual(len(list((self.priv / "1-capturas").glob("*.md"))), 1)
        d = json.loads((self.lote / "decisoes.json").read_text(encoding="utf-8"))
        self.assertEqual(d["versao"], 2)
        self.assertTrue((self.lote / "relatorio-v2.md").exists())
        # de novo: nada duplica
        triagem.cmd_aplicar(self.lote, self.prof, {}, confirmar=True)
        self.assertEqual(len(list((self.prof / "1-capturas").glob("*.md"))), 1)
        self.assertEqual(len(list((self.priv / "1-capturas").glob("*.md"))), 1)

    def test_recusa_texto_profissional_com_dado_de_terceiro(self):
        rc = triagem.cmd_aplicar(self.lote, self.prof, {"P1": "A", "P2": "B"}, confirmar=True)
        self.assertEqual(rc, 1)
        self.assertFalse(any((self.prof / "1-capturas").glob("*.md")) if (self.prof / "1-capturas").exists() else False)

    def test_encerrar(self):
        triagem.cmd_aplicar(self.lote, self.prof, {"P1": "B", "P2": "A"}, confirmar=True)
        d = json.loads((self.lote / "decisoes.json").read_text(encoding="utf-8"))
        self.assertIn({"trecho": "A", "destino": "encerrar", "virou": "encerrado", "onde": "—"}, d["seguiu"])

    def test_dependencia_por_saida_nao_trava_o_trecho(self):
        d = triagem.ler_decisoes(self.lote)
        d["trechos"][0]["depende_de"] = ["P1"]
        d["perguntas"][0]["opcoes"][0]["efeitos"][0]["saidas"][0]["depende_de"] = ["P2"]
        self.assertEqual([p["destino"] for p in triagem.planejar(d, {"P1": "A"})], ["pessoal"])
        d = triagem.ler_decisoes(self.lote)
        d["trechos"][0]["depende_de"] = ["P1"]
        self.assertEqual([p["destino"] for p in triagem.planejar(d, {"P1": "B"})], ["encerrar", "pessoal"])

    def test_opcao_inexistente(self):
        with self.assertRaises(triagem.TriagemErro):
            triagem.planejar(triagem.ler_decisoes(self.lote), {"P1": "Z"})


if __name__ == "__main__":
    unittest.main()
