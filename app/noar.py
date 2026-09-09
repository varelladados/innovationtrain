"""Checagem "está no ar?" das URLs públicas do portfólio.

Item de backlog desde a v0.4 ("badge de no ar checando se a URL responde").
Nunca bloqueia o request: o `GET /api/portfolio` só lê o cache em memória, e uma
thread daemon preenche esse cache depois do reindex. Se a checagem nunca rodou,
o link simplesmente não ganha selo — nada quebra, nada mente (regra do vazio:
sem dado, não inventa "no ar").

Só roda no servidor local; o snapshot estático (`export_static.py`) não chama
nada disso.
"""
import threading
import time
import urllib.error
import urllib.request

TTL_SEGUNDOS = 6 * 60 * 60  # 6h
TIMEOUT = 4
UA = "Estação/0.6 (checagem local de disponibilidade)"

_CACHE = {}  # url -> {"ok": bool, "status": int|None, "checked_at": float}
_LOCK = threading.Lock()


def _fresco(entrada):
    return entrada and (time.time() - entrada["checked_at"]) < TTL_SEGUNDOS


def checar(url, forcar=False):
    """HEAD na URL (cai pra GET se o servidor recusar HEAD). Nunca levanta."""
    with _LOCK:
        cache = _CACHE.get(url)
        if _fresco(cache) and not forcar:
            return cache

    resultado = {"ok": False, "status": None, "checked_at": time.time()}
    for metodo in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=metodo, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                resultado = {"ok": 200 <= resp.status < 400, "status": resp.status,
                             "checked_at": time.time()}
            break
        except urllib.error.HTTPError as e:
            if metodo == "HEAD" and e.code in (403, 405, 501):
                continue  # servidor não gosta de HEAD — tenta GET
            resultado = {"ok": False, "status": e.code, "checked_at": time.time()}
            break
        except Exception:
            resultado = {"ok": False, "status": None, "checked_at": time.time()}
            break

    with _LOCK:
        _CACHE[url] = resultado
    return resultado


def cache_de(url):
    with _LOCK:
        entrada = _CACHE.get(url)
        return dict(entrada) if _fresco(entrada) else None


def urls_do_portfolio(pf):
    urls = []
    for projeto in pf.get("projetos", []):
        for link in projeto.get("links", []):
            if link.get("kind") == "no-ar" and link.get("url", "").startswith("http"):
                urls.append(link["url"])
    return sorted(set(urls))


def enriquecer(pf):
    """Acrescenta `noar` aos links que já têm checagem em cache. Não faz rede."""
    for projeto in pf.get("projetos", []):
        for link in projeto.get("links", []):
            entrada = cache_de(link.get("url", ""))
            if entrada:
                link["noar"] = entrada
    return pf


def aquecer_em_background(pf):
    """Dispara uma thread daemon que checa as URLs públicas uma vez."""
    urls = urls_do_portfolio(pf)
    if not urls:
        return None

    def _rodar():
        for url in urls:
            checar(url)

    t = threading.Thread(target=_rodar, name="noar-aquecimento", daemon=True)
    t.start()
    return t
