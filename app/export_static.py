"""Exporta a Estação como UM arquivo HTML estático, somente leitura.

Pra quando o servidor local não alcança quem precisa ver (celular, remote
control, alguém de fora): o mesmo index.html, com os endpoints /api/* trocados
por um `fetch` falso que responde a partir de um snapshot embutido do corpus
(índice + texto dos .md/.txt/.py, .html truncados em 3000 chars como a UI já
mostra) — árvore, busca, LOG, dashboard e aba Tour funcionam; toggle de backlog
e reindexar respondem "somente leitura".

Saída: dist/estacao-static.html (sem <html>/<head>/<body>, no formato que
o publicador de Artifacts do Claude espera — abre também direto no navegador,
que tolera a ausência dessas tags).

    python app/export_static.py            # gera dist/estacao-static.html
    python app/export_static.py --full     # inclui o <html>/<head>/<body> pra abrir sozinho
"""
import json
import re
import sys
import time
from pathlib import Path

import config
import indexer
import log_parser
import metrics
import portfolio as portfolio_mod
import workflow as workflow_mod
import avanco as avanco_mod

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
TEMPLATE_PATH = APP_DIR / "templates" / "index.html"
DIST_DIR = PROJECT_DIR / "dist"
OUT_PATH = DIST_DIR / "estacao-static.html"

HTML_TRUNCATE = 3000  # mesmo corte que renderFile() aplica a .html
MARKED_CDN = "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"
MERMAID_CDN = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"


def build_snapshot():
    entries, cache = indexer.build_index()
    raw = {}
    for e in entries:
        txt = cache.get(e["path"], "")
        if e["path"].lower().endswith((".html", ".htm")) and len(txt) > HTML_TRUNCATE:
            txt = txt[:HTML_TRUNCATE]
        raw[e["path"]] = txt
    registro = config.atual().arquivo_rel("registro") or ""
    log_rows = log_parser.parse_log_tables(cache.get(registro, ""))
    return {
        "gerado_em": time.strftime("%Y-%m-%d %H:%M"),
        "entries": entries,
        "raw": raw,
        "log_rows": log_rows,
        "metricas": metrics.compute_metrics(),
        "portfolio": portfolio_mod.build_portfolio(),
        # v0.6: as abas Workflow e o card de Avanço também viajam no snapshot,
        # em modo leitura — responder pendência e anotar continuam só no local.
        "workflow": workflow_mod.build_workflow(entries),
        "avanco": avanco_mod.ultima_rodada(),
    }


SHIM = r"""
// ---- modo estático: fetch falso sobre o snapshot embutido ----
(function(){
  const D = window.ESTACAO_STATIC;
  const resp = (obj, status) => ({ok: (status||200) < 300, status: status||200, json: async () => obj});
  function search(q){
    const ql = (q||"").trim().toLowerCase();
    if (!ql) return [];
    const out = [];
    for (const e of D.entries){
      const raw = D.raw[e.path] || "";
      const t = (e.title||"").toLowerCase(), p = e.path.toLowerCase(), c = raw.toLowerCase();
      let score = 0;
      if (t.includes(ql)) score += 3;
      if (p.includes(ql)) score += 2;
      const i = c.indexOf(ql);
      if (i >= 0) score += 1;
      if (!score) continue;
      let snippet = e.snippet || "";
      if (i >= 0){
        const a = Math.max(0, i - 80), b = Math.min(raw.length, i + ql.length + 120);
        snippet = (a > 0 ? "…" : "") + raw.slice(a, b).replace(/\s+/g, " ") + (b < raw.length ? "…" : "");
      }
      out.push({title: e.title, type: e.type, path: e.path, snippet, score});
    }
    out.sort((x, y) => y.score - x.score || x.path.localeCompare(y.path));
    return out.slice(0, 60);
  }
  window.fetch = async function(url){
    const u = new URL(url, "http://static.local");
    const p = u.pathname, qs = u.searchParams;
    if (p === "/api/index") return resp({count: D.entries.length, entries: D.entries});
    if (p === "/api/file"){
      const path = qs.get("path");
      const e = D.entries.find(x => x.path === path);
      if (!e) return resp({error: "not found"}, 404);
      return resp({entry: e, raw: D.raw[path] || ""});
    }
    if (p === "/api/search") return resp({query: qs.get("q"), results: search(qs.get("q"))});
    if (p === "/api/log") return resp({rows: D.log_rows});
    if (p === "/api/metricas") return resp(D.metricas);
    if (p === "/api/portfolio") return resp(D.portfolio);
    if (p === "/api/launch") return resp({error: "snapshot estático: abrir executáveis só na Estação local"}, 400);
    if (p === "/api/reindex") return resp({count: D.entries.length});
    if (p === "/api/backlog/toggle") return resp({error: "snapshot estático, somente leitura — edite na Estação local"}, 400);
    if (p === "/api/workflow") return resp(D.workflow);
    if (p === "/api/avanco") return resp(D.avanco);
    if (p === "/api/projeto") return resp({error: "snapshot estático: a view de projeto só existe na Estação local"}, 400);
    if (p === "/api/nota/nova" || p === "/api/pendencia/responder" || p === "/api/projeto/anotar")
      return resp({error: "snapshot estático, somente leitura — escreva na Estação local"}, 400);
    return resp({error: "not found"}, 404);
  };
})();
"""

STATIC_TAIL = r"""
// ---- modo estático: mermaid via host (Artifacts renderiza <pre class="mermaid">) ou cdnjs ----
function renderMermaidBlocks(container){
  const blocks = [...container.querySelectorAll("pre > code.language-mermaid")];
  if (!blocks.length) return;
  const nodes = [];
  for (const code of blocks){
    const pre = code.parentElement;
    const wrap = document.createElement("div");
    wrap.className = "tour-mermaid rendered";
    const m = document.createElement("pre");
    m.className = "mermaid";
    m.textContent = code.textContent;
    wrap.appendChild(m);
    pre.replaceWith(wrap);
    nodes.push(m);
  }
  const run = () => {
    const dark = document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    try {
      window.mermaid.initialize({startOnLoad: false, theme: dark ? "dark" : "neutral", securityLevel: "strict"});
      window.mermaid.run({nodes: nodes.filter(n => !n.querySelector("svg"))});
    } catch(e){}
  };
  setTimeout(() => {
    const pendentes = nodes.filter(n => !n.querySelector("svg"));
    if (!pendentes.length) return;            // o host já renderizou
    if (window.mermaid){ run(); return; }
    const s = document.createElement("script");
    s.src = MERMAID_CDN_URL;
    s.onload = run;
    document.head.appendChild(s);
  }, 1200);
}
document.getElementById("reindex-btn").hidden = true;
document.body.classList.add("static");
"""


def build_html(full=False):
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", tpl).group(1)
    links = "\n".join(re.findall(r"<link [^>]*>", tpl))
    style = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    body = re.search(r"<body>(.*)</body>", tpl, re.S).group(1)

    # scripts: vendor locais viram cdnjs; shim entra antes do script principal
    body = body.replace('<script src="/app/templates/vendor/marked.min.js"></script>', f'<script src="{MARKED_CDN}"></script>')
    body = body.replace('<script src="/app/templates/vendor/mermaid.min.js"></script>', "")
    snap = build_snapshot()
    # "</" escapado pra não fechar o <script>; U+FFFD literal (de arquivo com encoding ruim,
    # lido com errors="replace") quebra o publicador de Artifacts — vira escape JS
    data_js = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/").replace("�", "\\ufffd")
    shim = (f"<script>window.ESTACAO_STATIC = {data_js};\nconst MERMAID_CDN_URL = {json.dumps(MERMAID_CDN)};\n{SHIM}</script>\n")
    body = body.replace("<script>\n// ====", shim + "<script>\n// ====", 1)

    # banner de snapshot no cabeçalho da sidebar
    banner = (f'<div class="static-note">Snapshot estático · {snap["gerado_em"]} · somente leitura · '
              f'{len(snap["entries"])} arquivos</div>')
    body = body.replace("<h1>Estação</h1>", "<h1>Estação</h1>" + banner, 1)

    # cauda: sobrescreve o renderizador de mermaid e esconde o reindexar
    body = body.replace("\nloadIndex();\n</script>", "\n" + STATIC_TAIL + "\nloadIndex();\n</script>", 1)

    extra_css = ("<style>.static-note{font-family:\"IBM Plex Mono\",ui-monospace,monospace;font-size:10.5px;"
                 "color:var(--text-2);margin:-4px 0 8px;line-height:1.4}</style>")
    head = f"<title>{title}</title>\n{links}\n{style}\n{extra_css}\n"
    page = head + body
    if full:
        page = f'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n{head}</head>\n<body>{body}</body>\n</html>\n'
    return page, snap


def main():
    full = "--full" in sys.argv
    page, snap = build_html(full=full)
    DIST_DIR.mkdir(exist_ok=True)
    out = OUT_PATH if not full else DIST_DIR / "estacao-static-full.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out} — {len(page.encode('utf-8'))/1e6:.2f} MB, {len(snap['entries'])} arquivos, gerado {snap['gerado_em']}")


if __name__ == "__main__":
    main()
