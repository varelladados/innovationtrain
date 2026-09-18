"""A triagem dentro da Central: o portão da aba Nota e a lista de lotes na espera.

A captura pela interface era a última porta de entrada que escrevia **direto** no
primeiro estágio de uma estação versionada — o método diz que ninguém entra sem
responder de quem é o assunto, se carrega dado pessoal de terceiro e se carrega
segredo (`metodo/triagem.md`, regra 9 de `metodo/regras.md`).

Este módulo não decide nada: ele **confere** e devolve o que achou, mascarado. Quem
decide é quem está na tela, com as três saídas que o método prevê — guardar na
espera, mandar para a estação pessoal, ou seguir como captura profissional quando
não há dado de ninguém no meio.

O motor é o mesmo `metodo/triagem.py` da linha de comando: importado, não copiado.
Uma segunda implementação dos detectores seria uma segunda verdade para divergir.
"""
import datetime
import json
import re
import sys
from pathlib import Path

import config
import notas

APP_DIR = Path(__file__).resolve().parent
METODO_DIR = APP_DIR.parent / "metodo"
if str(METODO_DIR) not in sys.path:
    sys.path.insert(0, str(METODO_DIR))

import triagem as motor  # noqa: E402


class TriagemUIError(Exception):
    pass


def cfg():
    return config.atual().get("triagem") or {}


def _caminho(chave):
    """O caminho de `triagem.<chave>`, relativo à raiz da estação. None se não declarado."""
    rel = (cfg() or {}).get(chave)
    if not rel:
        return None
    p = Path(rel)
    return p if p.is_absolute() else (config.atual().raiz / p).resolve()


def pessoal():
    return _caminho("pessoal")


def espera():
    return _caminho("espera")


def _slug(texto, palavras=4):
    limpo = re.sub(r"[^\w\s-]", " ", (texto or ""), flags=re.UNICODE)
    partes = [p for p in re.split(r"[\s_-]+", limpo) if p][:palavras]
    return motor.normalizar(" ".join(partes)).replace(" ", "-") or "nota"


def conferir(texto):
    """O que a triagem vê neste texto. Valores sempre mascarados: isto vai para a tela."""
    texto = texto or ""
    c = cfg()
    sinais = motor.detectar(texto)
    voc = motor.vocabulario(texto, c.get("palavras_pessoais") or (), c.get("palavras_profissionais") or ())
    achados = motor.apelidos_em(texto, c.get("projetos") or {})
    projetos = {k: dict(v, esfera=((c.get("projetos") or {}).get(k) or {}).get("esfera"))
                for k, v in achados.items()}
    cats = {s["categoria"] for s in sinais}
    esferas = {p.get("esfera") for p in projetos.values()}
    if cats & motor.CATEGORIAS_SEGREDO:
        veredito = "segredo"
    elif cats & motor.CATEGORIAS_TERCEIRO:
        veredito = "terceiro"
    elif "saude" in voc or "pessoal" in voc or "pessoal" in esferas:
        veredito = "pessoal"
    else:
        veredito = "limpo"
    return {
        "veredito": veredito,
        "sinais": [{"categoria": s["categoria"], "rotulo": s["rotulo"], "linha": s["linha"],
                    "valor": motor.mascarar(s["categoria"], s["valor"]), "origem": s.get("origem", "conteúdo")}
                   for s in sinais],
        "vocabulario": voc,
        "projetos": projetos,
        "pessoal": str(pessoal()) if pessoal() else None,
        "espera": str(espera()) if espera() else None,
    }


def guardar_na_espera(texto, assunto=None):
    """Abre um lote com o texto cru — o destino de quem não decide agora."""
    alvo = espera()
    if not alvo:
        raise TriagemUIError("esta estação não declara `triagem.espera` — sem área de espera, "
                             "não há onde o bruto esperar (ver metodo/triagem.md)")
    texto = (texto or "").strip()
    if not texto:
        raise TriagemUIError("texto vazio")
    hoje = datetime.date.today().isoformat()
    nome = f"{hoje}-{_slug(assunto or texto)}"
    pasta = alvo / nome
    n = 2
    while pasta.exists():
        pasta = alvo / f"{nome}-{n}"
        n += 1
    (pasta / "bruto").mkdir(parents=True)
    (pasta / "bruto" / "colado.md").write_text(texto + "\n", encoding="utf-8")
    indice = alvo / "_lotes.md"
    if not indice.exists():
        indice.write_text("# Lotes de triagem\n\nÍndice append-only dos lotes que passaram pela espera.\n\n"
                          "| Lote | Chegou | Origem | Itens | Estado | Relatório |\n|---|---|---|---|---|---|\n",
                          encoding="utf-8")
    with indice.open("a", encoding="utf-8") as f:
        f.write(f"| {pasta.name} | {hoje} | aba Nota da Central | 1 | espera — sem leitura ainda | — |\n")
    return {"lote": pasta.name, "path": str(pasta)}


def captura_pessoal(texto):
    """Captura na estação pessoal, com a mecânica do método (id, arquivo, registro)."""
    alvo = pessoal()
    if not alvo:
        raise TriagemUIError("esta estação não declara `triagem.pessoal` — diga onde fica a estação "
                             "privada antes de mandar algo para lá")
    if not (alvo / "estacao.json").exists() and not (alvo / "plataforma.json").exists():
        raise TriagemUIError(f"{alvo} não é uma estação (falta estacao.json)")
    texto = (texto or "").strip()
    if not texto:
        raise TriagemUIError("texto vazio")
    # as mesmas duas travas da captura profissional (o novo-id lê o registro para
    # achar a sequência do dia): esta enfileira as threads do servidor, e a do
    # registro, que vale entre processos, o `capturar` pega sozinho — a linha de
    # comando do `aplicar` grava neste registro também
    with notas._LOCK:
        ident, caminho = motor.capturar(alvo, texto, _slug(texto), lote="—", trecho="—",
                                        origem="nota direta pela Central, triada como pessoal")
    return {"id": ident, "path": caminho, "estacao": str(alvo)}


def lotes():
    """Os lotes na espera, com o estado que o `decisoes.json` de cada um declara."""
    alvo = espera()
    if not alvo or not alvo.is_dir():
        return []
    saida = []
    for pasta in sorted((p for p in alvo.iterdir() if p.is_dir() and not p.name.startswith("_")),
                        key=lambda p: p.name, reverse=True):
        item = {"lote": pasta.name, "path": str(pasta), "tem_decisoes": False,
                "perguntas": [], "trechos": 0, "seguiu": 0, "versao": None, "relatorios": []}
        arq = pasta / "decisoes.json"
        if arq.exists():
            try:
                d = json.loads(arq.read_text(encoding="utf-8"))
            except ValueError:
                d = None
            if d:
                item.update({
                    "tem_decisoes": True,
                    "versao": d.get("versao"),
                    "titulo": d.get("titulo"),
                    "em_uma_frase": d.get("em_uma_frase"),
                    "trechos": len(d.get("trechos") or []),
                    "seguiu": len(d.get("seguiu") or []),
                    "perguntas": [{"id": p.get("id"), "titulo": p.get("titulo"), "resposta": p.get("resposta"),
                                   "opcoes": [{"id": o.get("id"), "texto": o.get("texto")}
                                              for o in (p.get("opcoes") or [])]}
                                  for p in (d.get("perguntas") or [])],
                })
        item["relatorios"] = sorted(p.name for p in pasta.glob("relatorio-v*.md"))
        item["itens_brutos"] = sum(1 for _ in (pasta / "bruto").rglob("*")) if (pasta / "bruto").is_dir() else 0
        saida.append(item)
    return saida


def estado():
    """O que a aba Triagem precisa saber de uma vez."""
    return {"espera": str(espera()) if espera() else None,
            "pessoal": str(pessoal()) if pessoal() else None,
            "estacao": config.atual().nome,
            "lotes": lotes()}
