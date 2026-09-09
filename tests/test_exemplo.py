"""O indexer rodando contra plataforma de exemplo.

A plataforma de exemplo é conteúdo, não código — e a tentação de gerá-la rápido
e mal é real. Este teste é o que impede: se alguém quebrar uma cadeia, apagar um
`_historico/` ou deixar um item sem linha no registro, ele cai.

Ele roda contra os arquivos de verdade em `plataformas/exemplo`. Se a plataforma
não estiver ao lado deste repositório (num clone só do app, por exemplo), os
casos **pulam**.
"""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402
import indexer  # noqa: E402
import workflow  # noqa: E402

PLATAFORMAS = Path(__file__).resolve().parent.parent / "plataformas"
RAIZ_REPO = Path(__file__).resolve().parent.parent
EXEMPLO = PLATAFORMAS / "exemplo"
PRECOS = PLATAFORMAS / "exemplo-precos"


def _existe(raiz):
    return unittest.skipUnless((raiz / "plataforma.json").exists(),
                               f"{raiz.name} não está ao lado do app")


class _Exemplo:
    """A mesma bateria, contra qualquer plataforma de exemplo.

    Isto é um mixin de propósito: sem herdar de `TestCase` ele não é coletado
    sozinho, e cada plataforma vira uma subclasse que declara só a própria
    `RAIZ`. Um exemplo novo entra com três linhas e ganha a bateria inteira —
    que é o ponto: exemplo não coberto por teste apodrece em silêncio, porque
    ninguém roda um exemplo.

    Nada aqui pode presumir nomes de estágio: tudo sai de `config.atual()`.
    """

    RAIZ = None

    @classmethod
    def setUpClass(cls):
        cls._anterior = config._ATUAL
        config.aplicar(config.carregar(cls.RAIZ))
        cls.entries, cls.cache = indexer.build_index()

    @classmethod
    def tearDownClass(cls):
        if cls._anterior is not None:
            config.aplicar(cls._anterior)

    # -- estrutura ---------------------------------------------------------
    def test_o_indexer_sobe(self):
        self.assertTrue(config.atual().ok())
        self.assertGreater(len(self.entries), 8)

    def test_toda_pasta_declarada_sobrevive_a_um_clone(self):
        """Git não versiona pasta vazia — e uma plataforma de exemplo com
        `_historico/` vazio chega **quebrada** na máquina de quem clonar.

        O teste anterior conferia as pastas em disco, e por isso passava aqui e
        falhava no CI, que parte de um clone. Este confere o que o git realmente
        guarda: cada pasta declarada precisa ter ao menos um arquivo versionado.
        """
        import subprocess
        r = subprocess.run(["git", "-C", str(RAIZ_REPO), "ls-files", str(self.RAIZ)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            self.skipTest("não é um repositório git, ou git fora do PATH")
        versionados = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        if not versionados:
            self.skipTest("esta plataforma não está versionada")
        rel_raiz = self.RAIZ.relative_to(RAIZ_REPO).as_posix()
        cfg = config.atual()
        for e in cfg.estagios:
            for pasta in (e["pasta"], f"{e['pasta']}/{cfg.historico}"):
                prefixo = f"{rel_raiz}/{pasta}/"
                self.assertTrue(any(v.startswith(prefixo) for v in versionados),
                                f"{pasta}/ não tem arquivo versionado: some no clone")

    def _frontmatter(self, caminho):
        """Usado pelos dois lados — por isso mora no mixin comum, não no da
        plataforma madura, onde ele nasceu e onde a versão anterior o deixou."""
        fm, _ = indexer.split_frontmatter(caminho.read_text(encoding="utf-8"))
        return fm

    def test_declara_estado_inicial(self):
        """Sem isto, nem reiniciar nem avançar existem — e um exemplo em que não
        se pode mexer sem medo não serve para aprender."""
        rel = config.atual().get("estado_inicial")
        self.assertTrue(rel, f"{self.RAIZ.name} não declara `estado_inicial`")
        snap = (self.RAIZ / str(rel).replace("\\", "/")).resolve()
        self.assertTrue((snap / "plataforma.json").is_file(),
                        f"o instantâneo de {self.RAIZ.name} não existe: {snap}")
        self.assertNotIn(self.RAIZ, snap.parents,
                         "o instantâneo está dentro da plataforma: seria apagado junto")

    def test_os_quatro_estagios_existem_e_tem_historico(self):
        cfg = config.atual()
        self.assertEqual(len(cfg.estagios), 4)
        for e in cfg.estagios:
            self.assertTrue((self.RAIZ / e["pasta"]).is_dir(), e["pasta"])
            self.assertTrue((self.RAIZ / e["pasta"] / cfg.historico).is_dir(),
                            f"{e['pasta']}/{cfg.historico}")


class _Madura:
    """O que só uma plataforma povoada pode prometer.

    A de exemplo crua não tem nota, ideia nem projeto — de propósito, porque
    ela existe para ser dirigida. Cobrar dela uma cadeia inteira seria cobrar
    que ela não fosse o que é.
    """

    def test_cada_estagio_tem_pelo_menos_dois_itens_ativos(self):
        """É o que o itinerário pede: 2 por estágio, contados e não afirmados."""
        cfg = config.atual()
        for e in cfg.estagios[:3]:
            ativos = [p for p in (self.RAIZ / e["pasta"]).glob("*.md")]
            self.assertGreaterEqual(len(ativos), 2, f"{e['pasta']} tem {len(ativos)}")
        projetos = indexer.pastas_de_projeto()
        self.assertGreaterEqual(len(projetos), 2, projetos)

    def test_a_cadeia_1_2_3_4_esta_inteira(self):
        """Um mesmo grão do primeiro estágio até um projeto. Se isto quebrar, a
        plataforma deixa de cumprir o propósito dela."""
        cfg = config.atual()
        primeiro = cfg.estagios[0]["pasta"]
        inicios = sorted((c for c in (self.RAIZ / primeiro / cfg.historico).glob("*.md")
                          if self._frontmatter(c).get("avancou_para")), key=lambda c: c.name)
        self.assertTrue(inicios, "nenhuma captura no histórico aponta para frente")

        # Percorre TODAS as capturas que apontam para frente, não a primeira que o
        # `glob` devolver: a ordem dele muda entre sistemas de arquivos, e a
        # versão anterior deste teste passava no Windows e falhava no Linux por
        # começar numa cadeia curta. O que a plataforma promete é ter **uma**
        # cadeia inteira, não que toda captura tenha uma.
        cadeias = [self._percorrer(c) for c in inicios]
        inteiras = [c for c in cadeias if len(c) >= 4]
        self.assertTrue(inteiras,
                        f"nenhuma cadeia chega ao quarto estágio: {cadeias}")
        for visitados in inteiras:
            self.assertTrue(visitados[0].startswith(("26.", "25.")))
            siglas = [v.split("-")[1] for v in visitados if len(v.split("-")) > 1]
            self.assertEqual(siglas[:3], ["CAP", "NOT", "IDE"], visitados)

    def _percorrer(self, inicio):
        """Segue `avancou_para` do começo até onde a linhagem levar."""
        atual, visitados = inicio, [inicio.stem]
        for _ in range(5):
            destino_id = self._frontmatter(atual).get("avancou_para")
            if not destino_id:
                break
            achados = sorted(self.RAIZ.rglob(f"{destino_id}.md"))
            if not achados:
                # o último salto é para uma PASTA de projeto, não um .md
                pasta = next((p for p in sorted(config.atual().projetos_dir.iterdir())
                              if p.is_dir() and (p / "CLAUDE.md").exists()
                              and destino_id in (p / "CLAUDE.md").read_text(encoding="utf-8")),
                             None)
                self.assertIsNotNone(pasta, f"destino não encontrado: {destino_id}")
                visitados.append(pasta.name)
                break
            atual = achados[0]
            visitados.append(atual.stem)
        return visitados


class _Comum2:
    """Continuação do mixin comum, depois do bloco da plataforma madura."""

    def test_todo_link_de_linhagem_aponta_para_arquivo_que_existe(self):
        import re
        quebrados = []
        for arq in self.RAIZ.rglob("*.md"):
            if ".git" in arq.parts:
                continue
            for m in re.finditer(r"\]\(<([^>]+)>\)", arq.read_text(encoding="utf-8")):
                if not (arq.parent / m.group(1)).exists():
                    quebrados.append(f"{arq.name} -> {m.group(1)}")
        self.assertEqual(quebrados, [])

    # -- registro ----------------------------------------------------------
    def test_todo_item_tem_linha_no_registro(self):
        cfg = config.atual()
        registro = cfg.arquivo("registro").read_text(encoding="utf-8")
        for e in cfg.estagios:
            for arq in (self.RAIZ / e["pasta"]).rglob("*.md"):
                if cfg.id_re.match(arq.stem):
                    self.assertIn(arq.stem, registro, f"sem linha no registro: {arq.name}")

    def test_o_registro_nao_repete_identificador(self):
        import re
        cfg = config.atual()
        texto = cfg.arquivo("registro").read_text(encoding="utf-8")
        ids = [l.split("|")[1].strip() for l in texto.splitlines()
               if l.startswith("|") and cfg.identificador_re.search(l.split("|")[1] if "|" in l else "")]
        repetidos = [k for k, v in Counter(ids).items() if v > 1]
        self.assertEqual(repetidos, [])


class _Abas:
    """As abas contra uma plataforma povoada."""

    def test_o_kanban_usa_os_estagios_e_todos_tem_carta(self):
        wf = workflow.build_workflow(self.entries)
        cfg = config.atual()
        self.assertEqual(list(wf["colunas"].keys()), [e["pasta"] for e in cfg.estagios])
        for pasta, itens in wf["colunas"].items():
            self.assertTrue(itens, f"coluna vazia: {pasta}")

    def test_ha_uma_decisao_aberta(self):
        import pendencias
        dados = pendencias.listar_pendencias_ativas()
        self.assertIsNone(dados["erro"])
        self.assertGreaterEqual(len(dados["cards"]), 1)
        card = dados["cards"][0]
        self.assertTrue(card["perguntas"], "a pendência não tem opções para marcar")

    def test_o_portfolio_enxerga_os_dois_projetos(self):
        import portfolio
        pf = portfolio.build_portfolio()
        pastas = sorted(p["pasta"] for p in pf["projetos"])
        self.assertEqual(len(pastas), 2, pastas)
        self.assertTrue(all(p.startswith("exemplo-") for p in pastas), pastas)
        self.assertTrue(any(p["tipo"] != "—" for p in pf["projetos"]),
                        "nenhum projeto declara tipo")


class _Trilha:
    def test_a_trilha_do_tour_existe(self):
        trilha = config.atual().caminho("trilha")
        self.assertIsNotNone(trilha, f"{self.RAIZ.name} não declara trilha")
        self.assertTrue(trilha.exists())


class _Crua:
    """O que só a plataforma que começa vazia promete.

    Ela é o tutorial: nada avançou ainda, e há material de sobra para avançar.
    Se isto quebrar, ou alguém povoou o exemplo sem querer, ou o `reiniciar`
    parou de devolver o estado de origem.
    """

    def test_nada_avancou_ainda(self):
        cfg = config.atual()
        # só o que está em pasta de estágio: a trilha *fala* de `avancou_para`
        # em prosa, e a primeira versão deste teste caiu por causa disso.
        itens = [a for e in cfg.estagios for a in (self.RAIZ / e["pasta"]).rglob("*.md")]
        com_destino = [a.name for a in itens
                       if self._frontmatter(a).get("avancou_para")]
        self.assertEqual(com_destino, [], "algo já avançou nesta plataforma")
        for e in cfg.estagios:
            hist = self.RAIZ / e["pasta"] / cfg.historico
            # só ITEM conta: o `_leia-me.md` do histórico é documentação da
            # pasta, e ele existe desde antes de qualquer coisa avançar.
            itens_hist = [h.name for h in hist.glob("*.md") if cfg.id_re.match(h.stem)]
            self.assertEqual(itens_hist, [],
                             f"{e['pasta']}/{cfg.historico} deveria estar vazio")

    def test_o_registro_nao_tem_nenhuma_seta(self):
        texto = config.atual().arquivo("registro").read_text(encoding="utf-8")
        self.assertNotIn("→", texto.split("## Entradas")[1] if "## Entradas" in texto else "")

    def test_ha_material_de_sobra_no_primeiro_estagio(self):
        """Uma plataforma para ser dirigida precisa de matéria-prima."""
        cfg = config.atual()
        primeiro = self.RAIZ / cfg.estagios[0]["pasta"]
        ativos = [a for a in primeiro.glob("*.md")]
        self.assertGreaterEqual(len(ativos), 5, f"só {len(ativos)} capturas para avançar")

    def test_o_trem_conta_so_conteudo(self):
        """Arquivo de sistema não é carta.

        O `_` do começo do nome significa "maquinário, não conteúdo seu"
        (`metodo/taxonomia.md`, parada 5). Quando os `_leia-me.md` foram
        acrescentados aos `_historico/` — para as pastas sobreviverem a um clone
        — eles viraram carta no trem, e a primeira coluna passou a dizer 10 onde
        havia 9. Contagem errada num painel é pior que painel nenhum.
        """
        cfg = config.atual()
        wf = workflow.build_workflow(self.entries)
        primeiro = cfg.estagios[0]["pasta"]
        itens = [a for a in (self.RAIZ / primeiro).glob("*.md")
                 if not a.name.startswith("_")]
        self.assertEqual(wf["totais"][primeiro], len(itens),
                         "a coluna do primeiro estágio não bate com os arquivos")
        for coluna in wf["colunas"].values():
            for carta in coluna:
                self.assertFalse(Path(carta["path"]).name.startswith("_"),
                                 f"arquivo de sistema virou carta: {carta['path']}")

    def test_a_trilha_tem_passos(self):
        """Sem passos, a plataforma crua não ensina nada — fica só vazia."""
        import trilha
        estado = trilha.estado()
        self.assertTrue(estado["tem"], "esta plataforma não declara trilha")
        self.assertGreaterEqual(estado["total"], 3, estado)
        self.assertEqual(estado["passo"], 0,
                         "a plataforma versionada tem que estar no passo 0 da trilha")
        for p in trilha.passos()[1:]:
            pasta = (self.RAIZ / str(p["pasta"]).replace("\\", "/")).resolve()
            self.assertTrue((pasta / "plataforma.json").is_file(),
                            f"instantâneo ausente: {pasta}")


@_existe(EXEMPLO)
class TestExemploCozinha(_Exemplo, _Comum2, _Trilha, _Crua, unittest.TestCase):
    """Cozinha e fotografia: a que começa vazia, para ser dirigida."""
    RAIZ = EXEMPLO


@_existe(PRECOS)
class TestExemploPrecos(_Exemplo, _Madura, _Comum2, _Abas, _Trilha, unittest.TestCase):
    """Preços e lojas clone: a que já rodou, para ser lida."""
    RAIZ = PRECOS


if __name__ == "__main__":
    unittest.main()
