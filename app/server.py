"""PRJ-Estacao — servidor local (stdlib puro).

Navegador/portfólio pra C:\\Plataforma inteiro: orquestras, backlogs, LOG central.
Modelo arquitetural: outro-app-local/app/server.py (ThreadingHTTPServer,
roteamento manual, template lido fresco do disco a cada request).

Endpoints de escrita (todos com a mesma disciplina — allow-list de destino,
concorrência otimista, backup antes de gravar, preserva LF/CRLF):

| endpoint                  | escreve o quê                          | módulo        |
|---------------------------|----------------------------------------|---------------|
| POST /api/backlog/toggle  | `- [ ]`/`- [x]` numa linha de backlog  | aqui          |
| POST /api/nota/nova       | SBC em .pendente/ + linha no LOG       | notas.py      |
| POST /api/pendencia/responder | opção/“Outra resposta” de pendência | pendencias.py |

POST /api/launch abre executável local (efeito colateral, não escreve arquivo).
"""
import json
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import indexer
import search as search_mod
import log_parser
import metrics
import portfolio as portfolio_mod
import notas as notas_mod
import workflow as workflow_mod
import avanco as avanco_mod
import pendencias as pendencias_mod
import projetos as projetos_mod
import noar as noar_mod
import briefing as briefing_mod
import mimetypes
import subprocess
import sys

PORT = 8744
APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
ROOT = PROJECT_DIR.parent
TEMPLATE_PATH = APP_DIR / "templates" / "index.html"
VENDOR_DIR = APP_DIR / "templates" / "vendor"
CACHE_DIR = PROJECT_DIR / "cache"
BACKUPS_DIR = CACHE_DIR / "backups"

STATE_LOCK = threading.Lock()
STATE = {"entries": [], "text_cache": {}, "portfolio": None, "metricas": None}

CHECKBOX_RE_UNCHECKED = "- [ ] "
CHECKBOX_RE_CHECKED = "- [x] "


def reindex():
    entries, text_cache = indexer.build_index()
    indexer.save_index(entries)
    pf = portfolio_mod.build_portfolio()
    mt = metrics.compute_metrics()
    with STATE_LOCK:
        STATE["entries"] = entries
        STATE["text_cache"] = text_cache
        STATE["portfolio"] = pf
        STATE["metricas"] = mt
    noar_mod.aquecer_em_background(pf)  # selo "no ar" fora do caminho do request
    return entries


def _cached(key, build):
    """Portfólio e métricas custam varredura de disco: calculados no reindex, servidos do STATE."""
    with STATE_LOCK:
        val = STATE[key]
    if val is None:
        val = build()
        with STATE_LOCK:
            STATE[key] = val
    return val


def get_portfolio():
    """Portfólio do STATE, com o selo "no ar" que a thread de checagem já tiver
    preenchido (nunca faz rede aqui — ver noar.py)."""
    return noar_mod.enriquecer(_cached("portfolio", portfolio_mod.build_portfolio))


def get_metrics():
    return _cached("metricas", metrics.compute_metrics)


FILES_PREFIX = "/files/"
FILES_FORBIDDEN_PARTS = {".git", "node_modules", "__pycache__"}


def resolver_arquivo_seguro(rel: str):
    """Resolve um caminho relativo a C:\\Plataforma pra servir em /files/<path>. Só leitura,
    só dentro da raiz, nunca .git/node_modules. Devolve Path ou None."""
    rel = rel.replace("\\", "/").lstrip("/")
    if not rel or any(p in FILES_FORBIDDEN_PARTS for p in rel.split("/")):
        return None
    try:
        full = (ROOT / rel).resolve()
        full.relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return None
    if not full.is_file():
        return None
    return full


def get_state():
    with STATE_LOCK:
        return STATE["entries"], STATE["text_cache"]


class Handler(BaseHTTPRequestHandler):
    server_version = "Estacao/0.7"  # header HTTP: sem acento, e acompanha o VERSION

    def log_message(self, fmt, *args):
        pass  # silencioso — evitar poluir o terminal do usuário

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, content_type="text/html; charset=utf-8", status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "not found"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---- GET ----

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            html = TEMPLATE_PATH.read_text(encoding="utf-8")
            self._send_text(html)
            return

        if path == "/app/templates/vendor/marked.min.js":
            self._send_file(VENDOR_DIR / "marked.min.js", "application/javascript; charset=utf-8")
            return

        if path == "/app/templates/vendor/mermaid.min.js":
            self._send_file(VENDOR_DIR / "mermaid.min.js", "application/javascript; charset=utf-8")
            return

        if path == "/api/index":
            entries, _ = get_state()
            type_filter = qs.get("type", [None])[0]
            q = qs.get("q", [None])[0]
            result = entries
            if type_filter:
                result = [e for e in result if e["type"] == type_filter]
            if q:
                ql = q.lower()
                result = [e for e in result if ql in e["path"].lower() or ql in e["title"].lower()]
            self._send_json({"count": len(result), "entries": result})
            return

        if path == "/api/file":
            rel_path = unquote(qs.get("path", [""])[0])
            entries, text_cache = get_state()
            entry = next((e for e in entries if e["path"] == rel_path), None)
            if entry is None:
                self._send_json({"error": "not found"}, status=404)
                return
            raw = text_cache.get(rel_path, "")
            self._send_json({"entry": entry, "raw": raw})
            return

        if path == "/api/search":
            q = qs.get("q", [""])[0]
            entries, text_cache = get_state()
            results = search_mod.search(entries, text_cache, q)
            self._send_json({"query": q, "results": results})
            return

        if path == "/api/log":
            log_rel = "1-capturas/LOG/_log.md"
            entries, text_cache = get_state()
            content = text_cache.get(log_rel, "")
            rows = log_parser.parse_log_tables(content)
            self._send_json({"rows": rows})
            return

        if path == "/api/metricas":
            self._send_json(get_metrics())
            return

        if path == "/api/portfolio":
            self._send_json(get_portfolio())
            return

        if path == "/api/workflow":
            entries, _ = get_state()
            self._send_json(workflow_mod.build_workflow(entries))
            return

        if path == "/api/avanco":
            self._send_json(avanco_mod.ultima_rodada())
            return

        if path == "/api/briefing":
            entries, text_cache = get_state()
            try:
                self._send_json(briefing_mod.gerar(
                    tipo=qs.get("tipo", ["pendencias"])[0],
                    entries=entries, text_cache=text_cache,
                    path=unquote(qs.get("path", [""])[0]),
                    pasta=qs.get("pasta", [""])[0]))
            except ValueError as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/projeto":
            entries, text_cache = get_state()
            try:
                dados = projetos_mod.detalhe(
                    qs.get("pasta", [""])[0], entries, text_cache, get_portfolio())
            except projetos_mod.ProjetoError as e:
                self._send_json({"error": str(e)}, status=404)
                return
            self._send_json(dados)
            return

        if path.startswith(FILES_PREFIX):
            # Serve qualquer arquivo da raiz (protótipos HTML abrem de verdade, com seus assets
            # relativos, em vez de aparecer como fonte). Só leitura; ver resolver_arquivo_seguro.
            full = resolver_arquivo_seguro(unquote(path[len(FILES_PREFIX):]))
            if full is None:
                self._send_json({"error": "arquivo não encontrado ou fora da raiz"}, status=404)
                return
            ctype, _ = mimetypes.guess_type(str(full))
            ctype = ctype or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            try:
                data = full.read_bytes()
            except OSError:
                self._send_json({"error": "falha lendo arquivo"}, status=500)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_json({"error": "not found"}, status=404)

    # ---- POST ----

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json({"error": "invalid json"}, status=400)
            return

        if path == "/api/reindex":
            entries = reindex()
            self._send_json({"count": len(entries)})
            return

        if path == "/api/backlog/toggle":
            self._handle_backlog_toggle(payload)
            return

        if path == "/api/launch":
            self._handle_launch(payload)
            return

        if path == "/api/nota/nova":
            self._handle_nota_nova(payload)
            return

        if path == "/api/pendencia/responder":
            self._handle_pendencia_responder(payload)
            return

        if path == "/api/projeto/anotar":
            self._handle_projeto_anotar(payload)
            return

        self._send_json({"error": "not found"}, status=404)

    def _handle_projeto_anotar(self, payload):
        """Quinto endpoint de escrita: acrescenta uma linha de checkbox no backlog
        de um projeto. Allow-list vem do índice (só backlogs daquela pasta), trava
        de concorrência por sha1 do arquivo inteiro, backup antes de gravar.
        Formato escolhido de propósito: `- [ ] ... _(via console, data)_` é o que
        plataforma.py e o snapshot do avanço já leem — a anotação volta pra IA sozinha."""
        entries, text_cache = get_state()
        try:
            resultado = projetos_mod.anotar(
                pasta=payload.get("pasta", ""),
                backlog_path=payload.get("backlog_path", ""),
                texto=payload.get("texto", ""),
                expected_sha1=payload.get("expected_sha1", ""),
                entries=entries,
                text_cache=text_cache,
            )
        except projetos_mod.ConflitoError as e:
            self._send_json({"error": str(e)}, status=409)
            return
        except projetos_mod.ProjetoError as e:
            self._send_json({"error": str(e)}, status=400)
            return
        except Exception as e:
            self._send_json({"error": f"falha inesperada: {type(e).__name__}: {e}"}, status=500)
            return

        # reindexação incremental: só este arquivo, sem varrer o corpus inteiro
        rel = payload.get("backlog_path", "")
        with STATE_LOCK:
            STATE["text_cache"][rel] = resultado.pop("conteudo")
            for e in STATE["entries"]:
                if e["path"] == rel:
                    try:
                        e["size_bytes"] = (ROOT / rel).stat().st_size
                    except OSError:
                        pass
                    break
        self._send_json(resultado)

    def _handle_pendencia_responder(self, payload):
        """Quarto endpoint de escrita: grava a resposta do usuário numa
        pendência-formulário do rotina-de-avanco, exatamente como ele faria à mão
        (marcar `[x]`, ou preencher a linha "Outra resposta"). Nada além disso —
        renomear pra `pendencia-resolvida-*`, escrever "## Resolvida em" e mexer
        em `**Adiada:**` é trabalho da skill na rodada seguinte, por contrato
        ("nunca fecha uma pendência por inferência"). Ver app/pendencias.py."""
        try:
            resultado = pendencias_mod.responder(
                ref=payload.get("ref", ""),
                line_number=payload.get("line_number"),
                expected_text=payload.get("expected_text", ""),
                acao=payload.get("acao", ""),
                texto=payload.get("texto", ""),
            )
        except pendencias_mod.ConflitoError as e:
            self._send_json({"error": str(e), "current": e.atual}, status=409)
            return
        except pendencias_mod.PendenciaError as e:
            self._send_json({"error": str(e)}, status=400)
            return
        except Exception as e:
            self._send_json({"error": f"falha inesperada: {type(e).__name__}: {e}"}, status=500)
            return
        self._send_json(resultado)

    def _handle_nota_nova(self, payload):
        """Terceiro endpoint com efeito colateral: cria uma Captura crua (SBC) a
        partir de texto solto — arquivo em 1-capturas/.pendente/ + linha no LOG
        central. Nunca classifica, nunca decide destino (mesma disciplina da skill
        encaminhando-trecho, só que via HTTP em vez de chat). Ver
        app/notas.py e plano-console-operacional-2026-09-06.md, frente 1."""
        texto = payload.get("texto", "")
        try:
            resultado = notas_mod.criar_captura_crua(texto)
        except notas_mod.NotaError as e:
            self._send_json({"error": str(e)}, status=400)
            return
        except Exception as e:
            self._send_json({"error": f"falha inesperada: {type(e).__name__}: {e}"}, status=500)
            return
        self._send_json({"ok": True, **resultado})

    def _handle_launch(self, payload):
        """Segundo endpoint com efeito colateral (o primeiro é o toggle de backlog): abre um
        executável local a partir da aba Portfólio. Regras:
        - só aceita path que o portfolio.py já classificou como launcher/binario/servidor
          (nada de rodar caminho arbitrário vindo do navegador)
        - roda com cwd na pasta do próprio arquivo, numa janela de console própria
          (`start`), sem esperar — a Estação não vira babá do processo
        - só faz sentido no servidor local; o snapshot estático responde 'somente leitura'
        """
        rel = payload.get("path", "")
        _, ex = portfolio_mod.encontrar_exec(get_portfolio(), rel)
        if ex is None or ex["kind"] not in ("launcher", "binario", "servidor"):
            self._send_json({"error": "não é um executável conhecido do portfólio"}, status=400)
            return
        full = resolver_arquivo_seguro(rel)
        if full is None:
            self._send_json({"error": "arquivo não existe"}, status=404)
            return
        ext = full.suffix.lower()
        try:
            if ext in (".bat", ".cmd"):
                cmd = ["cmd", "/c", "start", "", str(full)]
            elif ext == ".ps1":
                cmd = ["cmd", "/c", "start", "", "powershell", "-ExecutionPolicy", "Bypass", "-File", str(full)]
            elif ext == ".exe":
                cmd = ["cmd", "/c", "start", "", str(full)]
            elif ext == ".py":
                cmd = ["cmd", "/c", "start", "", sys.executable, str(full)]
            else:
                self._send_json({"error": f"extensão não suportada: {ext}"}, status=400)
                return
            subprocess.Popen(cmd, cwd=str(full.parent), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        except Exception as e:
            self._send_json({"error": f"falha ao iniciar: {e}"}, status=500)
            return
        self._send_json({"ok": True, "iniciado": rel})

    def _handle_backlog_toggle(self, payload):
        """Único endpoint de escrita do app. Regras de segurança:
        - só aceita path cujo type no índice seja 'backlog'
        - confere que a linha bate com expected_text (concorrência otimista)
        - só troca '- [ ] '/'- [x] ' naquela linha, nada mais
        - faz backup do arquivo antes de gravar
        - reindexa incrementalmente só aquele arquivo
        """
        rel_path = payload.get("path", "")
        line_number = payload.get("line_number")
        expected_text = payload.get("expected_text", "")

        entries, _ = get_state()
        entry = next((e for e in entries if e["path"] == rel_path), None)
        if entry is None or entry["type"] != "backlog":
            self._send_json({"error": "path não é um backlog conhecido"}, status=400)
            return

        full_path = ROOT / rel_path
        if not full_path.exists():
            self._send_json({"error": "arquivo não existe"}, status=404)
            return

        # newline="" nos dois lados: preserva LF/CRLF originais do arquivo. Sem isso, no
        # Windows o read traduz CRLF→LF e o write LF→CRLF, e um toggle de checkbox
        # reescrevia o arquivo inteiro com quebra de linha diferente (diff de arquivo todo).
        try:
            with full_path.open(encoding="utf-8", newline="") as f:
                lines = f.read().splitlines(keepends=True)
        except Exception as e:
            self._send_json({"error": f"falha lendo arquivo: {e}"}, status=500)
            return

        if line_number is None or not (0 <= line_number < len(lines)):
            self._send_json({"error": "line_number inválido"}, status=400)
            return

        current_line = lines[line_number]
        if current_line.rstrip("\r\n") != expected_text.rstrip("\r\n"):
            self._send_json({
                "error": "conflito: a linha mudou desde a última leitura",
                "current": current_line,
            }, status=409)
            return

        if CHECKBOX_RE_UNCHECKED in current_line:
            new_line = current_line.replace(CHECKBOX_RE_UNCHECKED, CHECKBOX_RE_CHECKED, 1)
        elif CHECKBOX_RE_CHECKED in current_line:
            new_line = current_line.replace(CHECKBOX_RE_CHECKED, CHECKBOX_RE_UNCHECKED, 1)
        else:
            self._send_json({"error": "linha não contém checkbox de backlog"}, status=400)
            return

        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        backup_name = f"{rel_path.replace('/', '_')}-{int(time.time())}.bak"
        shutil.copy2(full_path, BACKUPS_DIR / backup_name)

        lines[line_number] = new_line
        content = "".join(lines)
        with full_path.open("w", encoding="utf-8", newline="") as f:
            f.write(content)

        # reindexação incremental: só este arquivo, sem varrer tudo de novo
        with STATE_LOCK:
            STATE["text_cache"][rel_path] = content
            for e in STATE["entries"]:
                if e["path"] == rel_path:
                    e["size_bytes"] = full_path.stat().st_size
                    break

        self._send_json({"ok": True, "new_line": new_line})


def main():
    reindex()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"PRJ-Estacao rodando em http://127.0.0.1:{PORT}")
    print(f"Indexando: {ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
