"""Testes do design system — a regra de ouro, cobrada pelo build.

O furo que estes testes existem para não deixar voltar: em 2026-09-08 havia
**17 valores de cor escritos fora do bloco de tokens** do `index.html`,
incluindo o azul da paleta anterior à migração de agosto. Nenhum deles trocava
no modo escuro, e ninguém percebeu porque ninguém tinha aberto o modo escuro.

Sem um teste, o furo volta em duas semanas. Ver `app/docs/design-system.md`.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEX = RAIZ / "app" / "templates" / "index.html"
FONTES_DIR = RAIZ / "app" / "templates" / "vendor" / "fonts"

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FIM_DOS_TOKENS = ':root[data-tema="areia"][data-theme="dark"]'


def _html():
    return INDEX.read_text(encoding="utf-8")


def _css(html):
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    assert m, "bloco <style> não encontrado no index.html"
    return m.group(1)


def _fim_do_bloco(texto, inicio):
    """Índice logo depois da chave que fecha o bloco começado em `inicio`."""
    abre = texto.index("{", inicio)
    nivel = 0
    for i in range(abre, len(texto)):
        if texto[i] == "{":
            nivel += 1
        elif texto[i] == "}":
            nivel -= 1
            if nivel == 0:
                return i + 1
    raise AssertionError("bloco de tokens não fecha")


def _regiao_de_tokens(html):
    """(região dos tokens, tudo o que vem depois dela no arquivo inteiro)."""
    ini = html.index(":root{")
    fim = _fim_do_bloco(html, html.rindex(FIM_DOS_TOKENS))
    return html[ini:fim], html[fim:]


class TestRegraDeOuro(unittest.TestCase):
    """Nenhum valor literal de cor fora do bloco de tokens."""

    def test_nenhum_hex_depois_dos_tokens(self):
        html = _html()
        _, depois = _regiao_de_tokens(html)
        achados = HEX_RE.findall(depois)
        self.assertEqual(
            achados, [],
            "cor literal fora do :root — ela não troca no modo escuro. "
            f"Use um token (ver app/docs/design-system.md). Achados: {achados}")

    def test_nenhum_hex_antes_dos_tokens(self):
        """O <head> também não pode carregar cor (theme-color, favicon inline…)."""
        html = _html()
        antes = html[:html.index(":root{")]
        self.assertEqual(HEX_RE.findall(antes), [])

    def test_javascript_nao_conhece_cor(self):
        """A bolinha da árvore sai de classe, não de style inline com hex."""
        html = _html()
        self.assertNotIn("TYPE_COLORS", html,
                         "o mapa de cores em JS voltou; a cor tem que sair de --tipo-*")
        self.assertIn('class="type-dot t-${e.type}"', html)


class TestParesClaroEscuro(unittest.TestCase):
    """Todo token de cor precisa existir nos quatro blocos de tema."""

    def _blocos(self):
        html = _html()
        regiao, _ = _regiao_de_tokens(html)
        blocos = {}
        for seletor, marca in (
            (":root{", "padrao-claro"),
            (':root[data-theme="dark"]{', "padrao-escuro"),
            (':root[data-tema="areia"]{', "areia-claro"),
            (':root[data-tema="areia"][data-theme="dark"]{', "areia-escuro"),
        ):
            i = regiao.index(seletor)
            corpo = regiao[i:_fim_do_bloco(regiao, i)]
            blocos[marca] = set(re.findall(r"(--[a-z0-9-]+)\s*:", corpo))
        return blocos

    def test_os_quatro_blocos_existem(self):
        self.assertEqual(len(self._blocos()), 4)

    def test_mesma_paleta_nos_quatro(self):
        blocos = self._blocos()
        # a escala (espaço/raio/tipo) só existe no :root — não muda com o tema.
        # a paleta de tipo de arquivo é compartilhada pelos dois temas.
        def paleta(nomes):
            return {n for n in nomes
                    if not n.startswith(("--tipo-", "--sp-", "--r-", "--fs-"))}

        base = paleta(blocos["padrao-claro"])
        for marca, nomes in blocos.items():
            self.assertEqual(
                paleta(nomes), base,
                f"o bloco {marca} não declara os mesmos tokens de cor que o padrão claro — "
                "o que faltar não troca de tema e vira bug visual")

    def test_escala_de_maturidade_tem_quatro_degraus(self):
        for marca, nomes in self._blocos().items():
            for n in range(1, 5):
                self.assertIn(f"--estagio-{n}", nomes, f"faltando em {marca}")


class TestTokensUsadosExistem(unittest.TestCase):
    def test_todo_var_referenciado_esta_declarado(self):
        html = _html()
        css = _css(html)
        regiao, _ = _regiao_de_tokens(html)
        declarados = set(re.findall(r"(--[a-z0-9-]+)\s*:", regiao))
        declarados.add("--est")  # variável local, definida pelas classes est-N
        usados = set(re.findall(r"var\((--[a-z0-9-]+)", css))
        faltando = sorted(usados - declarados)
        self.assertEqual(faltando, [], f"var() sem token declarado: {faltando}")


class TestFontesVendorizadas(unittest.TestCase):
    """O app abre igual com a rede desligada."""

    def test_sem_cdn_de_fonte(self):
        html = _html()
        for host in ("fonts.googleapis.com", "fonts.gstatic.com"):
            self.assertNotIn(host, html, f"{host} voltou ao index.html")

    def test_arquivos_existem(self):
        html = _html()
        srcs = re.findall(r"url\('([^']+\.woff2)'\)", html)
        self.assertTrue(srcs, "nenhum @font-face local no index.html")
        for src in srcs:
            nome = src.rsplit("/", 1)[-1]
            self.assertTrue((FONTES_DIR / nome).is_file(),
                            f"@font-face aponta para arquivo ausente: {nome}")

    def test_licencas_registradas(self):
        licencas = FONTES_DIR / "LICENCAS.md"
        self.assertTrue(licencas.is_file(),
                        "fonte vendorizada sem LICENCAS.md ao lado")
        texto = licencas.read_text(encoding="utf-8")
        for fonte in ("Fraunces", "Public Sans", "IBM Plex Mono"):
            self.assertIn(fonte, texto)

    def test_pilha_de_fallback_declarada(self):
        """Vendorizar não dispensa o fallback: o arquivo pode faltar num fork."""
        css = _css(_html())
        for familia in ('"Fraunces",serif',
                        '"Public Sans",-apple-system',
                        '"IBM Plex Mono",ui-monospace,monospace'):
            self.assertIn(familia, css, f"sem fallback para {familia}")


if __name__ == "__main__":
    unittest.main()
