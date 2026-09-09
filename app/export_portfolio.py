"""Portfólio público do Bruno (Seu Beira) — página estática gerada do inventário.

Diferente do export_static.py (a Estação inteiro, pra uso interno), isto é a
VITRINE: só o que faz sentido alguém de fora ver. Regras de publicação:

- Todo projeto listado em _indice-projetos.md aparece (nome, tipo, status, resumo) — o
  resumo é o texto canônico da tabela, sem editar.
- Link só se for público de verdade: URL "no ar" (portfolio.json `estavel` ou host
  público detectado) ou repositório GitHub marcado como público em
  portfolio.json (`"repo_publico": true`). Repositório privado vira texto
  "repositório privado", sem link.
- Nada de protótipo/launcher local (isso é a aba Portfólio interna).
- Sem dados pessoais além do nome e das personas (Seu Beira, mR.bRiNk — decisão do
  usuário em 2026-09-03: nenhum e-mail/link de contato por enquanto).

Saída: dist/portfolio-seu-beira.html (formato Artifact: sem <html>/<head>/<body>);
--full gera a variante autocontida.

    python app/export_portfolio.py [--full]
"""
import html
import json
import re
import sys
import time
from pathlib import Path

import portfolio as portfolio_mod

import config

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DIST_DIR = PROJECT_DIR / "dist"

TIPO_LABEL = {"DIG": "digital", "DAD": "dados", "CON": "consultoria", "ADE": "ensino", "—": "em definição"}
STATUS_ORDEM = {"ativo": 0, "early": 2, "idea": 3, "adormec": 4}
VERSAO_RE = re.compile(r"^v\d")  # "v0.2", "v1" — não qualquer status que contenha a letra v


def esc(s):
    return html.escape(str(s or ""), quote=True)


def _ler(p, limit=200_000):
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def frase_manifesto():
    """A frase-tese, do pocket show (N0 da trilha) — fonte única, não reescrever aqui."""
    txt = _ler(config.atual().raiz / "_metodo" / "manifesto.md")
    m = re.search(r"\*\*\.Método, de cabo a rabo:\*\*\s*(.+)", txt)
    t = m.group(1).strip() if m else ""
    return (t[:1].upper() + t[1:]) if t else t


def limpar_resumo(r):
    r = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", r)     # links markdown -> texto
    r = re.sub(r"`([^`]*)`", r"\1", r)                   # código inline
    r = r.replace("**", "")
    return r.strip()


def status_grupo(status):
    s = (status or "").lower()
    if VERSAO_RE.match(s):
        return 1
    for k, v in STATUS_ORDEM.items():
        if s.startswith(k) or k in s:
            return v
    return 5


def status_label(status):
    s = (status or "").lower()
    if s.startswith("ativo"): return "em atividade"
    if VERSAO_RE.match(s): return f"versão {status}"
    if "early" in s: return "começando"
    if "idea" in s: return "em concepção"
    if "adormec" in s: return "em pausa"
    return status or "sem status"


def montar(full=False):
    pf = portfolio_mod.build_portfolio()
    projetos = [p for p in pf["projetos"] if p["listada"]]
    for p in projetos:
        # curadoria (portfolio.json) já foi lida pelo portfolio.py — tags e repo_publico vêm de lá
        # Artifact do claude.ai é privado (exige login) — não conta como "no ar" pra quem é de fora
        p["_no_ar"] = [l for l in p["links"] if l["kind"] == "no-ar" and "claude.ai/code/artifact" not in l["url"]]
        repo = next((l for l in p["links"] if l["kind"] == "repo"), None)
        p["_repo"] = repo["url"] if (repo and p["repo_publico"]) else None
        p["_repo_privado"] = bool(repo) and not p["repo_publico"]
        p["_resumo"] = limpar_resumo(p["resumo"])
        p["_tags"] = [t for t in p["tags"] if t != "no ar"]
        p["_ordem"] = (0 if p["_no_ar"] else 1, status_grupo(p["status"]), -(p["git"]["commits"] or 0))
    projetos.sort(key=lambda p: p["_ordem"])
    no_ar = [p for p in projetos if p["_no_ar"]]
    construcao = [p for p in projetos if not p["_no_ar"]]
    gerado = time.strftime("%Y-%m-%d")
    tese = frase_manifesto()
    n_tipos = {}
    for p in projetos:
        n_tipos[p["tipo"]] = n_tipos.get(p["tipo"], 0) + 1

    def card(p, destaque=False):
        eyebrow = f'<span class="tipo">{esc(TIPO_LABEL.get(p["tipo"], p["tipo"]))}</span><span class="dot">·</span><span class="st st-{status_grupo(p["status"])}">{esc(status_label(p["status"]))}</span>'
        if p["git"]["ultimo_commit"]:
            eyebrow += f'<span class="dot">·</span><span class="git">{esc(p["git"]["ultimo_commit"])}</span>'
        links = ""
        for l in p["_no_ar"]:
            host = re.sub(r"^https?://", "", l["url"]).split("/")[0]
            links += f'<a class="lk lk-ar" href="{esc(l["url"])}" target="_blank" rel="noopener">abrir no ar <span class="host">{esc(host)}</span></a>'
        if p["_repo"]:
            links += f'<a class="lk" href="{esc(p["_repo"])}" target="_blank" rel="noopener">código no GitHub</a>'
        elif p["_repo_privado"]:
            links += '<span class="lk lk-off" title="repositório existe, ainda não aberto ao público">repositório privado</span>'
        tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in p["_tags"])
        return (f'<article class="proj{" destaque" if destaque else ""}" id="{esc(p["pasta"])}">'
                f'<div class="eyebrow">{eyebrow}</div>'
                f'<h3>{esc(p["nome"])}</h3>'
                f'<p class="resumo">{esc(p["_resumo"])}</p>'
                f'{("<div class=\"tags\">" + tags + "</div>") if tags else ""}'
                f'{("<div class=\"links\">" + links + "</div>") if links else ""}'
                f'</article>')

    style = """
<style>
:root{
  --bg:#F2ECDE; --surface:#FBF8F0; --surface-2:#EFE7D2; --line:rgba(27,22,15,.16);
  --text:#1B160F; --text-2:#6E6555; --accent:#9C7A3C; --accent-bg:#F0E6CC;
  --ok:#4C6B2F; --ok-bg:#E7EDD9; --warn:#7A5E2C; --warn-bg:#EFE7D2; --mute:#A8A69C;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#16130E; --surface:#1E1A13; --surface-2:#2A2418; --line:rgba(242,236,222,.16);
    --text:#F2ECDE; --text-2:#B2A98F; --accent:#CBA25A; --accent-bg:#34301F;
    --ok:#9BB579; --ok-bg:#232A1C; --warn:#E0B876; --warn-bg:#2A2418; --mute:#6E6555;
  }
}
:root[data-theme="dark"]{
  --bg:#16130E; --surface:#1E1A13; --surface-2:#2A2418; --line:rgba(242,236,222,.16);
  --text:#F2ECDE; --text-2:#B2A98F; --accent:#CBA25A; --accent-bg:#34301F;
  --ok:#9BB579; --ok-bg:#232A1C; --warn:#E0B876; --warn-bg:#2A2418; --mute:#6E6555;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Public Sans",-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.55}
a{color:var(--accent)}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 64px;display:grid;grid-template-columns:280px 1fr;gap:48px}
@media (max-width:820px){.wrap{grid-template-columns:1fr;gap:28px}.rail{position:static}}
.rail{position:sticky;top:24px;align-self:start;display:flex;flex-direction:column;gap:20px}
.rail .quem{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2)}
.rail h1{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:38px;line-height:1.02;margin:6px 0 0;text-wrap:balance;letter-spacing:-.01em}
.rail h1 em{font-style:italic;font-weight:400;color:var(--accent)}
.rail .tese{font-size:14.5px;color:var(--text-2);margin:0;max-width:34ch}
.rail .tese strong{color:var(--text);font-weight:600}
.contadores{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.cont{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.cont .n{font-family:"Fraunces",Georgia,serif;font-size:26px;font-weight:600;color:var(--accent);line-height:1;font-variant-numeric:tabular-nums}
.cont .l{font-size:11px;color:var(--text-2);margin-top:4px;letter-spacing:.04em;text-transform:uppercase}
.rail nav{display:flex;flex-direction:column;gap:6px;font-size:13.5px;border-top:1px solid var(--line);padding-top:16px}
.rail nav a{color:var(--text);text-decoration:none;display:flex;justify-content:space-between;gap:8px}
.rail nav a:hover{color:var(--accent)}
.rail nav a .k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;color:var(--text-2)}
.rail .metodo{font-size:12.5px;color:var(--text-2);border-top:1px solid var(--line);padding-top:16px}
.rail .metodo code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11.5px;background:var(--surface-2);padding:1px 5px;border-radius:4px}
main{display:flex;flex-direction:column;gap:40px;min-width:0}
section h2{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:22px;margin:0 0 4px;display:flex;align-items:baseline;gap:10px}
section h2 .k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;font-weight:400;color:var(--text-2);letter-spacing:.04em}
section .sub{margin:0 0 18px;color:var(--text-2);font-size:13.5px;max-width:62ch}
.lista{display:grid;grid-template-columns:1fr;gap:0;border-top:1px solid var(--line)}
.proj{padding:20px 0 22px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:1fr;gap:8px}
.proj.destaque{background:linear-gradient(90deg,var(--accent-bg),transparent 70%);margin:0 -16px;padding-left:16px;padding-right:16px;border-radius:8px;border-bottom:1px solid var(--line)}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;color:var(--text-2);display:flex;flex-wrap:wrap;gap:6px;align-items:center;letter-spacing:.02em}
.eyebrow .tipo{text-transform:uppercase;letter-spacing:.08em;color:var(--accent)}
.eyebrow .dot{color:var(--mute)}
.st-0{color:var(--ok)} .st-1{color:var(--accent)} .st-2,.st-3{color:var(--warn)} .st-4{color:var(--mute)}
.proj h3{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:24px;margin:0;line-height:1.15;text-wrap:balance}
.proj .resumo{margin:0;color:var(--text);max-width:68ch;font-size:14.5px}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;color:var(--text-2);border:1px solid var(--line);border-radius:999px;padding:2px 9px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}
.lk{display:inline-flex;align-items:center;gap:6px;font-size:13px;padding:6px 12px;border-radius:6px;border:1px solid var(--line);text-decoration:none;color:var(--text);background:var(--surface)}
.lk:hover{border-color:var(--accent)}
.lk-ar{background:var(--ok-bg);border-color:var(--ok);color:var(--ok);font-weight:600}
.lk .host{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;font-weight:400;opacity:.85}
.lk-off{color:var(--mute);border-style:dashed;cursor:default}
footer{grid-column:1/-1;border-top:1px solid var(--line);padding-top:16px;font-size:12px;color:var(--text-2);display:flex;flex-wrap:wrap;gap:10px 24px}
footer code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion: no-preference){.proj{transition:background .2s}}
</style>"""

    fontes = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
              '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=Public+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

    nav = "".join(f'<a href="#{esc(p["pasta"])}"><span>{esc(p["nome"])}</span><span class="k">{esc(p["tipo"])}</span></a>' for p in projetos)
    tipos_txt = " · ".join(f"{n} {TIPO_LABEL.get(t, t)}" for t, n in sorted(n_tipos.items(), key=lambda x: -x[1]))

    body = f"""
<div class="wrap">
  <aside class="rail">
    <div>
      <div class="quem">Bruno Varella · Seu Beira · mR.bRiNk</div>
      <h1>Da ideia <em>à prateleira.</em></h1>
    </div>
    <p class="tese"><strong>Hub de inovação IA-first, MVP-first.</strong> {esc(tese)}</p>
    <div class="contadores">
      <div class="cont"><div class="n">{len(projetos)}</div><div class="l">projetos</div></div>
      <div class="cont"><div class="n">{len(no_ar)}</div><div class="l">no ar</div></div>
      <div class="cont"><div class="n">{sum(1 for p in projetos if status_grupo(p["status"]) == 0)}</div><div class="l">em atividade</div></div>
      <div class="cont"><div class="n">{sum(p["git"]["commits"] for p in projetos)}</div><div class="l">commits</div></div>
    </div>
    <nav aria-label="projetos">{nav}</nav>
    <div class="metodo">Cada projeto aqui nasceu como ideia bruta e passou pelo mesmo caminho rastreável: <code>Captura → Ideia → Projeto</code>. {esc(tipos_txt)}.</div>
  </aside>
  <main>
    <section>
      <h2>No ar <span class="k">{len(no_ar)} de {len(projetos)}</span></h2>
      <p class="sub">O que já dá pra abrir e usar agora, sem instalar nada.</p>
      <div class="lista">{"".join(card(p, destaque=True) for p in no_ar) or '<p class="sub">Nada publicado ainda.</p>'}</div>
    </section>
    <section>
      <h2>Em construção <span class="k">{len(construcao)}</span></h2>
      <p class="sub">Do protótipo que roda na minha máquina à ideia que acabou de ganhar pasta. Ordem: mais ativo primeiro.</p>
      <div class="lista">{"".join(card(p) for p in construcao)}</div>
    </section>
  </main>
  <footer>
    <span>Gerado em {esc(gerado)} a partir do inventário da Estação — a página muda quando os projetos mudam, não o contrário.</span>
    <span>Resumos são os textos canônicos de <code>_indice-projetos.md</code>.</span>
  </footer>
</div>"""

    head = f"<title>Portfólio Seu Beira</title>\n{fontes}\n{style}\n"
    page = head + body
    if full:
        page = f'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n{head}</head>\n<body>{body}</body>\n</html>\n'
    return page, projetos, no_ar


def main():
    full = "--full" in sys.argv
    page, projetos, no_ar = montar(full)
    DIST_DIR.mkdir(exist_ok=True)
    out = DIST_DIR / ("portfolio-seu-beira-full.html" if full else "portfolio-seu-beira.html")
    out.write_text(page, encoding="utf-8")
    print(f"{out} — {len(page.encode('utf-8'))/1e3:.0f} KB · {len(projetos)} projetos · {len(no_ar)} no ar")


if __name__ == "__main__":
    main()
