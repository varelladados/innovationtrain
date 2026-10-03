"""A guarda do servidor local (0.16.2).

O servidor escuta só em loopback, mas qualquer página aberta no navegador
consegue mandar pedido para `127.0.0.1` — e um POST "simples" (`text/plain`)
nem dispara o pré-voo do CORS. Estes testes sobem um servidor **de verdade**,
numa porta efêmera, e conferem o que a `Handler` deixa passar e o que recusa:

- `Host` em todo pedido (a barreira contra DNS rebinding);
- `Origin` / `Sec-Fetch-Site` nos métodos que mudam estado;
- `Content-Type: application/json` em todo POST;
- os cabeçalhos de segurança em toda resposta;
- 500 genérico, com o detalhe no console e nunca no corpo;
- `/files/` sem nome de segredo;
- o HTML cru do markdown mostrado como texto, e o endereço que executa código
  neutralizado (esta parte roda o `marked` vendorizado no node, e pula se ele
  não existir).

Nenhum teste toca a porta da Central (8744) nem a de outro app.
"""
import contextlib
import html
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apoio  # noqa: E402,F401  (insere app/ no sys.path)
import config  # noqa: E402
import server  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = RAIZ_REPO / "app" / "templates" / "index.html"
MARKED = RAIZ_REPO / "app" / "templates" / "vendor" / "marked.min.js"
#: portas de outros apps que um teste nunca pode ocupar
PORTAS_DE_OUTROS = {3000, 8743, 8744, 8745, 8746, 8770, 8771}
JSON_CT = {"Content-Type": "application/json"}


class ServidorDeVerdade(unittest.TestCase):
    """Um `ThreadingHTTPServer` com a `Handler` real, numa porta livre."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="central-guarda-"))
        # o central.json do usuário nunca é lido nem escrito: o hub é a pasta temporária
        cls._hub = os.environ.get("CENTRAL_DIR")
        os.environ["CENTRAL_DIR"] = str(cls.tmp / "hub")
        cls._atual = config._ATUAL
        cls.estacao = cls.tmp / "estacao"
        cls.estacao.mkdir()
        apoio.aplicar(cls.estacao)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.porta = cls.httpd.server_address[1]
        assert cls.porta not in PORTAS_DE_OUTROS
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        config._ATUAL = cls._atual
        if cls._hub is not None:
            os.environ["CENTRAL_DIR"] = cls._hub
        else:
            os.environ.pop("CENTRAL_DIR", None)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- apoio

    def pedir(self, metodo, caminho, corpo=None, headers=None):
        """(status, cabeçalhos em minúsculas, corpo) de um pedido de verdade."""
        con = HTTPConnection("127.0.0.1", self.porta, timeout=15)
        try:
            con.request(metodo, caminho, body=corpo, headers=headers or {})
            r = con.getresponse()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
        finally:
            con.close()

    def crua(self, requisicao: bytes):
        """Fala direto no socket: o que o `http.client` não deixa escrever."""
        with socket.create_connection(("127.0.0.1", self.porta), timeout=15) as s:
            s.sendall(requisicao)
            dados = b""
            while True:
                pedaco = s.recv(65536)
                if not pedaco:
                    break
                dados += pedaco
        cabeca, _, corpo = dados.partition(b"\r\n\r\n")
        return int(cabeca.split(b" ", 2)[1]), corpo

    def origem(self, host="127.0.0.1"):
        return f"http://{host}:{self.porta}"

    def post_json(self, caminho, obj, **headers):
        return self.pedir("POST", caminho, json.dumps(obj), dict(JSON_CT, **headers))

    GET_INOFENSIVO = "/api/embarque/modelos"   # só lê config.MODELOS


class TestHost(ServidorDeVerdade):
    """Em todo pedido, GET inclusive: é o que barra o DNS rebinding."""

    def test_host_estranho_e_recusado(self):
        for host in ("evil.example", "evil.example:80", f"127.0.0.1:{self.porta + 1}",
                     f"localhost.evil.example:{self.porta}",
                     f"127.0.0.1.evil.example:{self.porta}", "127.0.0.1", "", "[::2]:1"):
            st, h, corpo = self.pedir("GET", self.GET_INOFENSIVO, headers={"Host": host})
            self.assertEqual(st, 403, f"Host {host!r} devia ser recusado")
            self.assertTrue(h["content-type"].startswith("text/plain"))
            self.assertNotIn(b"modelos", corpo)

    def test_hosts_de_loopback_passam(self):
        for host in (f"127.0.0.1:{self.porta}", f"localhost:{self.porta}",
                     f"LOCALHOST:{self.porta}", f"[::1]:{self.porta}"):
            st, _, _ = self.pedir("GET", self.GET_INOFENSIVO, headers={"Host": host})
            self.assertEqual(st, 200, f"Host {host!r} devia passar")

    def test_sem_host_passa(self):
        """HTTP/1.0 de script não manda `Host`."""
        st, corpo = self.crua(b"GET " + self.GET_INOFENSIVO.encode() + b" HTTP/1.0\r\n\r\n")
        self.assertEqual(st, 200)
        self.assertIn(b"modelos", corpo)

    def test_dois_hosts_um_deles_estranho_e_recusado(self):
        req = (f"GET {self.GET_INOFENSIVO} HTTP/1.1\r\nHost: 127.0.0.1:{self.porta}\r\n"
               "Host: evil.example\r\n\r\n").encode()
        st, _ = self.crua(req)
        self.assertEqual(st, 403)

    def test_host_estranho_recusado_em_toda_rota_e_metodo(self):
        for metodo, caminho in (("GET", "/"), ("GET", "/api/index"), ("GET", "/files/x.txt"),
                                ("GET", "/app/templates/vendor/marked.min.js"),
                                ("POST", "/api/reindex"), ("PUT", "/api/reindex"),
                                ("DELETE", "/api/reindex"), ("OPTIONS", "/api/reindex")):
            st, _, _ = self.pedir(metodo, caminho, "{}" if metodo != "GET" else None,
                                  dict(JSON_CT, Host="evil.example"))
            self.assertEqual(st, 403, f"{metodo} {caminho} com Host estranho")


class TestOrigem(ServidorDeVerdade):
    """Nos métodos que mudam estado. Endpoint de prova: `/api/embarque/prompt`,
    que gera texto e não escreve nada — 400 (faltou o caminho) é "chegou lá"."""

    ALVO = "/api/embarque/prompt"

    def test_origin_de_fora_e_recusado(self):
        for origin in ("https://evil.example", "http://evil.example", "null",
                       f"http://127.0.0.1:{self.porta + 1}", "http://127.0.0.1",
                       f"http://localhost.evil.example:{self.porta}",
                       f"https://127.0.0.1:{self.porta}"):
            st, _, corpo = self.post_json(self.ALVO, {}, Origin=origin)
            self.assertEqual(st, 403, f"Origin {origin!r} devia ser recusada")
            self.assertNotIn(b"informe onde", corpo, "o endpoint não pode ter sido executado")

    def test_sec_fetch_site_de_fora_sem_origin_e_recusado(self):
        for site in ("cross-site", "same-site", "Cross-Site"):
            st, _, _ = self.post_json(self.ALVO, {}, **{"Sec-Fetch-Site": site})
            self.assertEqual(st, 403, f"Sec-Fetch-Site {site!r}")

    def test_sec_fetch_site_da_propria_origem_passa(self):
        for site in ("same-origin", "none"):
            st, _, _ = self.post_json(self.ALVO, {}, **{"Sec-Fetch-Site": site})
            self.assertEqual(st, 400, f"Sec-Fetch-Site {site!r} devia chegar ao endpoint")

    def test_post_legitimo_com_origin_da_propria_porta_passa(self):
        for host in ("127.0.0.1", "localhost", "[::1]"):
            st, _, corpo = self.post_json(self.ALVO, {"caminho": str(self.tmp)},
                                          Origin=self.origem(host))
            self.assertEqual(st, 200, f"Origin de {host}")
            self.assertIn("texto", json.loads(corpo))

    def test_post_sem_origin_passa(self):
        """curl, script local, app nativo."""
        st, _, corpo = self.post_json(self.ALVO, {"caminho": str(self.tmp)})
        self.assertEqual(st, 200)
        self.assertIn("texto", json.loads(corpo))

    def test_get_nao_exige_origin(self):
        st, _, _ = self.pedir("GET", self.GET_INOFENSIVO, headers={"Origin": "https://evil.example"})
        self.assertEqual(st, 200, "GET só é cobrado pelo Host")

    def test_recusa_nao_executa_a_escrita(self):
        """O ponto de tudo: pedido de fora **não grava** no central.json."""
        central = config.central_json()
        self.assertFalse(central.exists())
        self.addCleanup(lambda: central.exists() and central.unlink())
        alvo = self.tmp / "estacao-falsa"
        alvo.mkdir()
        (alvo / "estacao.json").write_text("{}\n", encoding="utf-8")
        corpo = json.dumps({"caminho": str(alvo), "nome": "Falsa"})
        for headers in ({"Origin": "https://evil.example", "Content-Type": "text/plain"},
                        {"Origin": "https://evil.example", **JSON_CT},
                        {"Sec-Fetch-Site": "cross-site", "Content-Type": "text/plain"},
                        {"Content-Type": "text/plain"}):
            st, _, _ = self.pedir("POST", "/api/embarque/registrar", corpo, headers)
            self.assertIn(st, (403, 415), headers)
        self.assertFalse(central.exists(), "nada pode ter sido gravado no central.json")
        # e o mesmo pedido, legítimo, grava — a recusa acima foi pela guarda e não por acaso
        st, _, _ = self.pedir("POST", "/api/embarque/registrar", corpo,
                              dict(JSON_CT, Origin=self.origem()))
        self.assertEqual(st, 200)
        self.assertTrue(central.exists())

    def test_put_patch_delete_passam_pela_mesma_guarda(self):
        for metodo in ("PUT", "PATCH", "DELETE"):
            st, _, _ = self.pedir(metodo, "/api/reindex", "{}", dict(JSON_CT, Origin="https://evil.example"))
            self.assertEqual(st, 403, metodo)
            st, h, corpo = self.pedir(metodo, "/api/reindex", "{}", JSON_CT)
            self.assertEqual(st, 405, metodo)
            self.assertEqual(json.loads(corpo)["error"], "método não suportado")


class TestEscopoDoWorkflow(ServidorDeVerdade):
    """`GET /api/workflow?escopo=`: a tela inicial (Hoje) pede só a estação aberta."""

    def test_sem_parametro_vale_todas(self):
        st, _, corpo = self.pedir("GET", "/api/workflow")
        self.assertEqual(st, 200)
        self.assertIn("pendencias", json.loads(corpo))

    def test_escopo_estacao_passa(self):
        st, _, corpo = self.pedir("GET", "/api/workflow?escopo=estacao")
        self.assertEqual(st, 200)
        dados = json.loads(corpo)
        self.assertIn("cards", dados["pendencias"])
        # só a estação aberta: nenhum card de outra origem
        for card in dados["pendencias"]["cards"]:
            self.assertEqual(card["origem"], dados["pendencias"]["cards"][0]["origem"])

    def test_escopo_desconhecido_e_400(self):
        # (`?escopo=` vazio cai no padrão: parse_qs descarta valor vazio)
        for escopo in ("publicavel", "privadas", "x"):
            st, _, corpo = self.pedir("GET", f"/api/workflow?escopo={escopo}")
            self.assertEqual(st, 400, escopo)
            self.assertIn("escopo", json.loads(corpo)["error"])


class TestCorpoJson(ServidorDeVerdade):
    ALVO = "/api/embarque/prompt"

    def test_text_plain_num_endpoint_json_e_recusado(self):
        corpo = json.dumps({"caminho": str(self.tmp)})
        for ct in ("text/plain", "text/plain;charset=UTF-8", "application/x-www-form-urlencoded",
                   "multipart/form-data; boundary=x", "application/jsonx", ""):
            st, _, resp = self.pedir("POST", self.ALVO, corpo, {"Content-Type": ct} if ct else {})
            self.assertEqual(st, 415, f"Content-Type {ct!r}")
            self.assertNotIn("texto", json.loads(resp))

    def test_application_json_com_charset_passa(self):
        corpo = json.dumps({"caminho": str(self.tmp)})
        for ct in ("application/json", "application/json; charset=utf-8",
                   "Application/JSON;charset=UTF-8"):
            st, _, _ = self.pedir("POST", self.ALVO, corpo, {"Content-Type": ct})
            self.assertEqual(st, 200, ct)

    def test_json_invalido_e_corpo_que_nao_e_objeto(self):
        st, _, _ = self.pedir("POST", self.ALVO, "{nao e json", JSON_CT)
        self.assertEqual(st, 400)
        for nao_objeto in ("[1, 2]", '"texto"', "42", "null"):
            st, _, _ = self.pedir("POST", self.ALVO, nao_objeto, JSON_CT)
            self.assertEqual(st, 400, nao_objeto)

    def test_corpo_vazio_com_json_vale_como_objeto_vazio(self):
        st, _, corpo = self.pedir("POST", self.ALVO, None, dict(JSON_CT, **{"Content-Length": "0"}))
        self.assertEqual(st, 400)
        self.assertIn("informe onde", json.loads(corpo)["error"])   # chegou ao endpoint, com {}

    def test_content_length_absurdo_e_recusado_sem_ler(self):
        st, _ = self.crua((f"POST {self.ALVO} HTTP/1.0\r\nContent-Type: application/json\r\n"
                           "Content-Length: 99999999999\r\n\r\n").encode())
        self.assertEqual(st, 413)
        st, _ = self.crua((f"POST {self.ALVO} HTTP/1.0\r\nContent-Type: application/json\r\n"
                           "Content-Length: abc\r\n\r\n").encode())
        self.assertEqual(st, 400)


class TestCabecalhos(ServidorDeVerdade):
    def confere(self, h, onde):
        self.assertEqual(h.get("x-content-type-options"), "nosniff", onde)
        self.assertEqual(h.get("x-frame-options"), "DENY", onde)
        self.assertEqual(h.get("referrer-policy"), "same-origin", onde)

    def test_em_toda_resposta(self):
        (self.estacao / "leia.txt").write_text("oi", encoding="utf-8")
        casos = [
            ("GET", "/", None, {}),                                       # HTML
            ("GET", self.GET_INOFENSIVO, None, {}),                       # JSON
            ("GET", "/api/nao-existe", None, {}),                         # 404 JSON
            ("GET", "/app/templates/vendor/marked.min.js", None, {}),     # estático
            ("GET", "/files/leia.txt", None, {}),                         # arquivo servido
            ("GET", "/files/.env", None, {}),                             # 404 de /files/
            ("GET", self.GET_INOFENSIVO, None, {"Host": "evil.example"}), # 403
            ("POST", "/api/reindex", "{}", {"Content-Type": "text/plain"}),                # 415
            ("POST", "/api/reindex", "{}", dict(JSON_CT, Origin="https://evil.example")),  # 403
            ("POST", "/api/nao-existe", "{}", JSON_CT),                   # 404 de POST
            ("PUT", "/api/reindex", "{}", JSON_CT),                       # 405
        ]
        for metodo, caminho, corpo, headers in casos:
            _, h, _ = self.pedir(metodo, caminho, corpo, headers)
            self.confere(h, f"{metodo} {caminho} {headers}")

    def test_no_store_nas_respostas_de_api(self):
        for metodo, caminho, corpo, headers in (
                ("GET", self.GET_INOFENSIVO, None, {}),
                ("GET", "/api/nao-existe", None, {}),
                ("POST", "/api/embarque/prompt", "{}", JSON_CT)):
            _, h, _ = self.pedir(metodo, caminho, corpo, headers)
            self.assertEqual(h.get("cache-control"), "no-store", f"{metodo} {caminho}")
            self.assertTrue(h["content-type"].startswith("application/json"))

    def test_recusa_de_host_e_origem_e_texto_puro(self):
        _, h, corpo = self.pedir("GET", "/", headers={"Host": "evil.example"})
        self.assertTrue(h["content-type"].startswith("text/plain"))
        self.assertLess(len(corpo), 200, "uma frase curta")
        _, h, corpo = self.post_json("/api/reindex", {}, Origin="https://evil.example")
        self.assertTrue(h["content-type"].startswith("text/plain"))
        self.assertLess(len(corpo), 200)

    def test_o_header_server_traz_a_versao_do_arquivo_VERSION(self):
        versao = (RAIZ_REPO / "VERSION").read_text(encoding="utf-8").strip()
        _, h, _ = self.pedir("GET", self.GET_INOFENSIVO)
        self.assertTrue(h["server"].startswith(f"Central/{versao}"), h["server"])


class TestErroGenerico(ServidorDeVerdade):
    """500 é "erro interno" para o navegador; o detalhe vai para o console."""

    SEGREDO = "caminho-secreto-C:/Users/alguem/coisa.json"

    def com_log_capturado(self):
        return contextlib.redirect_stderr(io.StringIO())

    def test_excecao_no_post_vira_500_generico(self):
        with self.com_log_capturado() as log, mock.patch.object(
                server.embarque_mod, "gerar", side_effect=RuntimeError(self.SEGREDO)):
            st, h, corpo = self.post_json("/api/embarque/prompt", {})
        self.assertEqual(st, 500)
        self.assertEqual(json.loads(corpo), {"error": "erro interno"})
        self.assertNotIn(self.SEGREDO.encode(), corpo)
        self.assertEqual(h.get("x-content-type-options"), "nosniff")
        self.assertIn(self.SEGREDO, log.getvalue(), "o detalhe tem de ir para o console")
        self.assertIn("RuntimeError", log.getvalue())

    def test_excecao_no_get_vira_500_generico_e_nao_derruba_a_conexao(self):
        with self.com_log_capturado() as log, mock.patch.object(
                server, "get_metrics", side_effect=RuntimeError(self.SEGREDO)):
            st, _, corpo = self.pedir("GET", "/api/metricas")
        self.assertEqual(st, 500)
        self.assertEqual(json.loads(corpo), {"error": "erro interno"})
        self.assertIn(self.SEGREDO, log.getvalue())

    def test_os_500_que_ja_existiam_tambem_ficam_genericos(self):
        with self.com_log_capturado(), mock.patch.object(
                server.triagem_mod, "estado", side_effect=OSError(self.SEGREDO)):
            st, _, corpo = self.pedir("GET", "/api/triagem")
        self.assertEqual(st, 500)
        self.assertNotIn(self.SEGREDO.encode(), corpo)
        with self.com_log_capturado(), mock.patch.object(
                server.embarque_mod, "registrar", side_effect=OSError(self.SEGREDO)):
            st, _, corpo = self.post_json("/api/embarque/registrar", {"caminho": "x"})
        self.assertEqual(st, 500)
        self.assertNotIn(self.SEGREDO.encode(), corpo)

    def test_o_servidor_continua_de_pe_depois_do_erro(self):
        with self.com_log_capturado(), mock.patch.object(
                server, "get_metrics", side_effect=RuntimeError("x")):
            self.pedir("GET", "/api/metricas")
        st, _, _ = self.pedir("GET", self.GET_INOFENSIVO)
        self.assertEqual(st, 200)


class TestArquivosSensiveis(ServidorDeVerdade):
    """`/files/` serve a raiz da estação — e nunca um nome de segredo."""

    LIBERADOS = ["leia.md", "sub/dados.json", "environment.md", "central.exemplo.json",
                 "chave.md", "keyboard.txt", "pem.txt", "rsa.txt", "dados.keynote"]
    BARRADOS = [".env", ".env.local", ".ENV", "sub/.env.production", ".envrc",
                "central.json", "Central.JSON", "sub/central.json", "central.json.bak",
                "cofre/segredo.txt", "COFRE/segredo.txt", "sub/cofre/a/b.txt",
                "chave.pem", "CHAVE.PEM", "sub/privada.key", "id_rsa", "id_rsa.pub",
                "sub/id_rsa", "id_ed25519", "id_ecdsa", ".git/config", "node_modules/x.js"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for rel in cls.LIBERADOS + cls.BARRADOS:
            f = cls.estacao / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("conteudo de " + rel, encoding="utf-8")

    def test_nomes_de_segredo_dao_404(self):
        for rel in self.BARRADOS:
            st, _, corpo = self.pedir("GET", "/files/" + rel)
            self.assertEqual(st, 404, f"/files/{rel} não pode ser servido")
            self.assertNotIn(b"conteudo de", corpo)

    def test_o_resto_continua_servido(self):
        for rel in self.LIBERADOS:
            st, _, corpo = self.pedir("GET", "/files/" + rel)
            self.assertEqual(st, 200, f"/files/{rel} devia ser servido")
            self.assertEqual(corpo.decode("utf-8"), "conteudo de " + rel)

    def test_formas_disfarcadas(self):
        for url in ("/files/%2eenv", "/files/sub/%2E%2E/.env", "/files/.env%20",
                    "/files/.env.", "/files/.env::$DATA", "/files/central.json::$DATA",
                    "/files/cofre%2Fsegredo.txt", "/files/cofre\\segredo.txt",
                    "/files//.env"):
            st, _, corpo = self.pedir("GET", url)
            self.assertEqual(st, 404, url)
            self.assertNotIn(b"conteudo de", corpo)

    def test_link_simbolico_para_segredo_nao_passa(self):
        alvo = self.estacao / ".env"
        link = self.estacao / "inocente.txt"
        try:
            link.symlink_to(alvo)
        except (OSError, NotImplementedError):
            self.skipTest("sem permissão para criar link simbólico nesta máquina")
        self.addCleanup(link.unlink)
        self.assertIsNone(server.resolver_arquivo_seguro("inocente.txt"))
        st, _, _ = self.pedir("GET", "/files/inocente.txt")
        self.assertEqual(st, 404)

    def test_nome_sensivel_direto(self):
        for nome in (".env", ".ENV", ".env.local", "central.json", "cofre", "Cofre",
                     "a.pem", "a.KEY", "id_rsa", "id_rsa.pub", ".git", "node_modules",
                     "__pycache__", ".env.", "x:y"):
            self.assertTrue(server.nome_sensivel(nome), nome)
        for nome in ("leia.md", "environment.md", "central.exemplo.json", "keyboard.txt",
                     "pem.txt", "dados.keynote", "", "..", "sub"):
            self.assertFalse(server.nome_sensivel(nome), repr(nome))

    def test_a_funcao_que_o_launcher_usa_tambem_barra(self):
        """O launcher resolve o arquivo pela mesma função: nome de segredo também não abre."""
        self.assertIsNone(server.resolver_arquivo_seguro(".env"))
        self.assertIsNone(server.resolver_arquivo_seguro("cofre/segredo.txt"))
        self.assertIsNotNone(server.resolver_arquivo_seguro("leia.md"))


# ------------------------------------------------------------------ markdown


class _Coletor(HTMLParser):
    """O que um navegador veria: as tags e os atributos, com entidade decodificada."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


TAGS_PROIBIDAS = {"script", "iframe", "style", "svg", "object", "embed", "form", "link",
                  "meta", "base", "math", "audio", "video", "details", "textarea", "frame"}
ESQUEMA_PERIGOSO = re.compile(r"^(?:javascript|vbscript|data):", re.I)
RASTER = re.compile(r"^data:image/(?:png|jpe?g|gif|webp|avif|bmp)[;,]", re.I)


def problemas_de_seguranca(saida_html):
    """Tudo que, no HTML que o marked devolveu, executaria código ao ser colocado
    num `innerHTML`: tag proibida, atributo `on*`, endereço de esquema perigoso.
    Lista vazia = limpo."""
    c = _Coletor()
    c.feed(saida_html)
    achados = []
    for tag, attrs in c.tags:
        if tag in TAGS_PROIBIDAS:
            achados.append(f"tag <{tag}>")
        for nome, valor in attrs.items():
            if nome.lower().startswith("on"):
                achados.append(f"atributo {nome} em <{tag}>")
            if nome.lower() in ("href", "src", "xlink:href", "action", "formaction", "srcset", "style"):
                v = re.sub(r"[\x00-\x20\x7f-\x9f]", "", valor or "")
                if nome.lower() == "style":
                    achados.append(f"style em <{tag}>")
                elif ESQUEMA_PERIGOSO.match(v) and not (tag == "img" and RASTER.match(v)):
                    achados.append(f"{nome}={valor!r} em <{tag}>")
    return achados


CASOS_HOSTIS = [
    "<script>alert(1)</script>",
    "texto <img src=x onerror=alert(1)> fim",
    "<div onclick=alert(1)>oi</div>\n\n**negrito**",
    "<a href=\"javascript:alert(1)\">x</a>",
    "<svg onload=alert(1)>",
    "<iframe src=\"javascript:alert(1)\"></iframe>",
    "texto<style>*{display:none}</style>",
    "<!-- a --><script>alert(1)</script>",
    "<details open ontoggle=alert(1)><summary>x</summary></details>",
    "[x](javascript:alert(1))",
    "[x](JaVaScRiPt:alert(1))",
    "[x](javascript&colon;alert(1))",
    "[x](&#106;avascript:alert(1))",
    "[x](jav&#x09;ascript:alert(1))",
    "[x](<javascript:alert(1)>)",
    "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
    "[x](vbscript:msgbox(1))",
    "<javascript:alert(1)>",
    "[x][r]\n\n[r]: javascript:alert(1)",
    "![a](javascript:alert(1))",
    "![a](data:text/html,<script>alert(1)</script>)",
    "![a](data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9YWxlcnQoMSk+)",
    "![a\" onerror=\"alert(1)](x.png)",
    "![a'onerror='alert(1)](x.png)",
    "[![a\" onerror=\"alert(1)](x.png)](y.md)",
    "[x](a.md \"t\\\" onmouseover=\\\"alert(1)\")",
    "```a\" onmouseover=\"alert(1)\ncodigo\n```",
    "# Titulo <script>x</script>\n\n> cita <iframe src=x>",
    "| a |\n|---|\n| <img src=x onerror=alert(1)> |",
    "- [ ] tarefa <img src=x onerror=alert(1)>",
]


class TestChecadorDoTeste(unittest.TestCase):
    """O checador acusa o que deve — senão o teste do markdown seria sempre verde."""

    def test_acusa_o_hostil(self):
        for ruim in ("<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
                     "<a href=\"javascript:alert(1)\">x</a>", "<a href=\"JAVA&#9;SCRIPT:x\">x</a>",
                     "<a href=\"data:text/html,x\">x</a>", "<img src=\"data:image/svg+xml,x\">",
                     "<iframe src=x></iframe>", "<p style=\"x\">a</p>"):
            self.assertTrue(problemas_de_seguranca(ruim), ruim)

    def test_deixa_passar_o_limpo(self):
        for bom in ("<p><a href=\"../a.md#x\">ok</a> <img src=\"data:image/png;base64,AA==\" alt=\"a\"></p>",
                    "<table><tr><td>1<br>2</td></tr></table><input disabled=\"\" type=\"checkbox\">",
                    "<pre><code class=\"language-mermaid\">graph TD</code></pre>"):
            self.assertEqual(problemas_de_seguranca(bom), [], bom)


@unittest.skipUnless(shutil.which("node"), "node não está instalado: o marked só roda nele")
class TestMarkdownSeguro(unittest.TestCase):
    """Roda o bloco `markdown-seguro` do `index.html` contra o `marked` vendorizado."""

    RUNNER = """
const fs = require("fs");
const [, , fonte, marked_js, casos] = process.argv;
const marked = require(marked_js);
new Function("marked", fs.readFileSync(fonte, "utf8"))(marked);
const lista = JSON.parse(fs.readFileSync(casos, "utf8"));
process.stdout.write(JSON.stringify(lista.map(c => marked.parse(c))));
"""

    @classmethod
    def setUpClass(cls):
        pagina = INDEX_HTML.read_text(encoding="utf-8")
        i, j = pagina.index("function escapeHtml"), pagina.index("// <<< markdown-seguro")
        assert "// >>> markdown-seguro" in pagina[i:j], "os marcadores do bloco sumiram"
        cls.tmp = Path(tempfile.mkdtemp(prefix="central-md-"))
        (cls.tmp / "fonte.js").write_text(pagina[i:j], encoding="utf-8")
        (cls.tmp / "runner.js").write_text(cls.RUNNER, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def renderizar(self, casos):
        (self.tmp / "casos.json").write_text(json.dumps(casos), encoding="utf-8")
        r = subprocess.run(
            ["node", str(self.tmp / "runner.js"), str(self.tmp / "fonte.js"), str(MARKED),
             str(self.tmp / "casos.json")],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def um(self, md):
        return self.renderizar([md])[0]

    def test_nada_do_que_e_hostil_sobrevive(self):
        for md, saida in zip(CASOS_HOSTIS, self.renderizar(CASOS_HOSTIS)):
            self.assertEqual(problemas_de_seguranca(saida), [], f"{md!r} -> {saida!r}")

    def test_html_cru_aparece_como_texto(self):
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", self.um("<script>alert(1)</script>"))
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", self.um("a <img src=x onerror=alert(1)> b"))
        self.assertNotIn("<img", self.um("a <img src=x onerror=alert(1)> b"))
        # e o marcador de lugar que o corpus escreve (`<raiz>`) passa a ser lido como escrito
        self.assertIn("&lt;raiz&gt;/arquivo.md", self.um("veja <raiz>/arquivo.md"))

    def test_link_perigoso_vira_so_o_texto(self):
        saida = self.um("[clique **aqui**](javascript:alert(1))")
        self.assertNotIn("href", saida)
        self.assertIn("<strong>aqui</strong>", saida)
        self.assertNotIn("href", self.um("[x](data:text/html;base64,AAAA)"))
        self.assertNotIn("href", self.um("[x](vbscript:msgbox(1))"))

    def test_entidade_no_endereco_chega_literal(self):
        # o navegador decodifica `&colon;` em atributo: o `&` tem de sair como `&amp;`
        self.assertIn('href="javascript&amp;colon;alert(1)"', self.um("[x](javascript&colon;alert(1))"))

    def test_imagem_de_dados_raster_continua_valendo(self):
        saida = self.um("![pixel](data:image/png;base64,iVBORw0KGgo=)")
        self.assertIn('src="data:image/png;base64,iVBORw0KGgo="', saida)
        self.assertNotIn("<img", self.um("![x](data:image/svg+xml;base64,AAAA)"))

    def test_alt_da_imagem_nao_escapa_do_atributo(self):
        saida = self.um('![a" onerror="alert(1)](x.png)')
        (_, attrs), = [t for t in _coletar(saida) if t[0] == "img"]
        self.assertEqual(attrs["alt"], 'a" onerror="alert(1)')
        self.assertNotIn("onerror", attrs)

    def test_o_que_a_central_usa_continua_funcionando(self):
        # link relativo (abre arquivo do corpus), âncora, http com query, esquema de aplicativo
        casos = ["[a](../outro/arquivo.md#secao)", "[b](#topo)", "[c](https://exemplo.com/?a=1&b=2)",
                 "[d](mailto:alguem@exemplo.com)", "[e](onenote:https://x/y)", "[f](a.md?x=1&amp;y=2)",
                 "<https://exemplo.com/?a=1&b=2>"]
        hrefs = [next(a for t, a in _coletar(s) if t == "a")["href"] for s in self.renderizar(casos)]
        self.assertEqual(hrefs, ["../outro/arquivo.md#secao", "#topo", "https://exemplo.com/?a=1&b=2",
                                 "mailto:alguem@exemplo.com", "onenote:https://x/y", "a.md?x=1&y=2",
                                 "https://exemplo.com/?a=1&b=2"])

    def test_tabela_codigo_e_mermaid_nao_mudam(self):
        tabela = self.um("| a | b |\n|---|---|\n| 1<br>2 | `<b>x</b>` |")
        self.assertIn("<table>", tabela)
        self.assertIn("<td>1<br>2</td>", tabela)
        self.assertIn("<code>&lt;b&gt;x&lt;/b&gt;</code>", tabela)
        mermaid = self.um('```mermaid\ngraph TD; A-->B["<b>x</b>"]\n```')
        self.assertIn('<code class="language-mermaid">', mermaid)
        self.assertIn("A--&gt;B", mermaid)
        self.assertNotIn("<b>", mermaid)

    def test_checkbox_de_backlog_continua_sendo_checkbox(self):
        saida = self.um("- [ ] aberta\n- [x] feita")
        tags = _coletar(saida)
        caixas = [a for t, a in tags if t == "input"]
        self.assertEqual([("checked" in a) for a in caixas], [False, True])
        self.assertTrue(all(a["type"] == "checkbox" for a in caixas))

    def test_comentario_html_inerte_some_e_br_continua(self):
        self.assertEqual(self.um("<!-- nota do autor -->\n\ntexto").strip(), "<p>texto</p>")
        self.assertNotIn("nota do autor", self.um("texto <!-- nota do autor --> fim"))
        self.assertIn("a<br>b<br>c<br>d", self.um("a<br>b<br/>c<BR />d"))
        # comentário colado a outra coisa NÃO some: aparece, escapado
        saida = self.um("<!-- c --><script>alert(1)</script>")
        self.assertIn("&lt;script&gt;", saida)

    def test_bloco_de_html_cru_vira_codigo_legivel(self):
        saida = self.um("<details>\n<summary>x</summary>\n\ntexto **md**\n\n</details>")
        self.assertIn("&lt;details&gt;", saida)
        self.assertIn("<strong>md</strong>", saida)

    def test_escapeHtml_escapa_aspas(self):
        # a função existente passou a ser usada em atributo (title=, data-open=)
        r = subprocess.run(
            ["node", "-e",
             "const fs=require('fs');const s=fs.readFileSync(process.argv[1],'utf8');"
             "const f=new Function(s+';return escapeHtml;')();"
             "process.stdout.write(JSON.stringify([f('<a href=\"x\" t=\\'y\\'>&'),f(null),f(0),f(undefined)]))",
             str(self.tmp / "fonte.js")],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout),
                         ["&lt;a href=&quot;x&quot; t=&#39;y&#39;&gt;&amp;", "", "0", ""])


def _coletar(saida_html):
    c = _Coletor()
    c.feed(saida_html)
    return c.tags


if __name__ == "__main__":
    unittest.main()
