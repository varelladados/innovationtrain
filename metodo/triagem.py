#!/usr/bin/env python3
"""Triagem — o passo antes da captura. Levanta sinais; não decide.

Toda entrada bruta (nota, dump, transcrição, áudio, vídeo, imagem, export de
conversa, link, documento) passa por aqui **antes** de ganhar identificador numa
estação. A pergunta é de quem é o assunto — trabalho ou vida pessoal — e se o
que chegou carrega dado pessoal de outra pessoa ou um segredo. O método está em
`triagem.md`; este script é a parte mecânica dele:

- **inventário**: que tipo de mídia é cada arquivo, o que falta extrair dele
  (transcrever, ler a imagem, olhar o quadro), duplicatas por hash;
- **sinais**: telefone, e-mail, CPF, CNPJ, CEP, registro profissional, link,
  segredo (por palavra-chave e por forma), participantes de conversa, e o
  vocabulário que costuma indicar vida pessoal ou dado sensível;
- **apelidos**: quais projetos da estação o texto cita — com tolerância a erro
  de transcrição ("foto e livro" acha o projeto "Fotolivro").

**O script não decide a esfera.** Um detector de telefone não sabe se o número é
de um fornecedor ou da mãe de alguém. A sugestão de cada item é rotulada como
sugestão; quem fecha é a leitura, de uma pessoa ou de uma sessão de IA.

**A saída mascara por padrão.** O relatório que ele escreve costuma ir para um
lugar versionado; um levantamento que republicasse os telefones que achou
seria o próprio vazamento. `--mostrar` desliga a máscara, para o relatório que
fica na área privada.

A configuração vem da chave `triagem` do `estacao.json` da raiz (ou do
`plataforma.json`, o nome até a 0.9) — ver `triagem.md`. Sem ela, os sinais
funcionam e os apelidos ficam vazios.

Stdlib puro, sem dependência — mesma regra do resto do produto. `ffprobe`, se
existir no PATH (ou em `TRIAGEM_FFPROBE`), é usado para dizer se um vídeo tem
fala, só imagem, ou uma imagem parada com música.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

LIMITE_TEXTO = 2_000_000   # bytes lidos de um arquivo de texto

MIDIAS = {
    "texto": {".txt", ".md", ".markdown"},
    "audio": {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".flac", ".amr", ".wma"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm", ".m4v"},
    "imagem": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".tif", ".tiff"},
    "documento": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".ppt", ".pptx", ".html", ".htm"},
    "planilha": {".csv", ".tsv", ".xls", ".xlsx", ".ods"},
    "link": {".url", ".webloc"},
    "pacote": {".zip"},
}

#: O que cada mídia precisa antes de poder ser lida — a especialização.
EXTRACAO = {
    "texto": "nenhuma: já é texto",
    "transcricao": "nenhuma: já é texto; conferir nomes próprios e de projeto",
    "conversa": "separar as mensagens das mídias; decidir se a conversa é de trabalho",
    "audio": "transcrever (de preferência local) e tratar como transcrição",
    "video": "ver o quadro ou transcrever — depende do que o vídeo tem",
    "imagem": "ler o texto e o conteúdo da imagem",
    "documento": "extrair o texto",
    "planilha": "ler cabeçalho e amostra; decidir se a base entra agregada",
    "link": "baixar só o texto da página, com permissão",
    "pacote": "abrir e triar cada arquivo de dentro",
    "outro": "identificar o formato",
}

# --------------------------------------------------------------------------
# normalização
# --------------------------------------------------------------------------


def normalizar(texto):
    """minúsculas, sem acento, tudo que não é letra ou dígito vira espaço."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _so_digitos(s):
    return re.sub(r"\D", "", s)


# --------------------------------------------------------------------------
# detectores
# --------------------------------------------------------------------------

TELEFONE_RE = re.compile(
    r"(?<![\w.,/])(?:\+?55[\s.-]?)?\(?[1-9]{2}\)?[\s.-]?9?[\s.]?\d{4}[\s.-]?\d{4}(?![\w,]|\.\d)")
#: Celular sem DDD só com hífen e o nove na frente — sem isso "2025-2026" seria telefone.
CELULAR_SEM_DDD_RE = re.compile(r"(?<![\w.,/-])9\d{4}-\d{4}(?![\w,-]|\.\d)")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CPF_RE = re.compile(r"(?<![\d./-])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d./-])")
CNPJ_RE = re.compile(r"(?<![\d./-])\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?![\d./-])")
CEP_RE = re.compile(r"(?<![\d.-])\d{5}-\d{3}(?![\d-])")
REGISTRO_RE = re.compile(
    r"\b(?:CRECI|CRM|OAB|CREA|CRO|CRP|CRC)\b[\s:ºn°.-]*\d{2,7}(?:[-/\s]?[A-Z]{2}\b)?", re.I)
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
SEGREDO_CHAVE_RE = re.compile(
    r"\b(?:senha|password|passwd|pwd|token|api[_ -]?key|secret|segredo)\b\s*[:=]\s*(\S+)", re.I)
SEGREDO_CONHECIDO_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|"
    r"xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35})\b")

#: Vocabulário que costuma indicar vida pessoal. Sinal fraco, de propósito: a
#: palavra "mãe" num roteiro de curso não é dado pessoal. Serve para chamar a
#: atenção da leitura, nunca para decidir.
PALAVRAS_PESSOAIS = [
    "mae", "pai", "filho", "filha", "filhos", "sobrinho", "sobrinha", "esposa", "marido",
    "namorado", "namorada", "irmao", "irma", "avo", "tio", "tia", "primo", "prima",
    "sogro", "sogra", "cunhado", "cunhada", "neto", "neta", "familia",
    "lista de compras", "supermercado", "farmacia", "escola do", "escola da",
    "aniversario", "churrasco", "ferias", "casamento", "igreja",
]
#: Categoria sensível da lei de proteção de dados — pesa mais que o resto.
PALAVRAS_SAUDE = [
    "medico", "medica", "consulta medica", "exame de sangue", "remedio", "remedios",
    "dentista", "hospital", "terapia", "psicologo", "psicologa", "cirurgia",
    "receita medica", "plano de saude",
]
PALAVRAS_PROFISSIONAIS = [
    "cliente", "clientes", "projeto", "reuniao", "proposta", "contrato", "entrega",
    "backlog", "deploy", "prototipo", "mvp", "lead", "leads", "fornecedor", "parceiro",
    "investidor", "pitch", "funcionalidade", "roadmap",
]

CATEGORIAS_TERCEIRO = {"telefone", "email", "cpf", "cnpj", "cep", "registro", "participante"}
CATEGORIAS_SEGREDO = {"segredo"}


def _dv_cpf(d):
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (s * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def _dv_cnpj(d):
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        s = sum(int(d[i]) * pesos[i] for i in range(n))
        r = s % 11
        if (0 if r < 2 else 11 - r) != int(d[n]):
            return False
    return True


def _parece_segredo_pela_forma(linha):
    """Uma linha sozinha, sem espaço, com letra e dígito — a senha colada no dump.

    Heurística, e rotulada como tal. Fica de fora o que tem cara de coisa do
    próprio sistema: identificador com data, slug, hash hexadecimal, nome de
    arquivo, link, e-mail, número puro.
    """
    s = linha.strip()
    if not (8 <= len(s) <= 64) or re.search(r"\s", s):
        return False
    if not (re.search(r"[A-Za-z]", s) and re.search(r"\d", s)):
        return False
    if re.search(r"[|#*\[\]()<>`/\\]", s) or "://" in s or "@" in s:
        return False
    if re.fullmatch(r"[0-9a-fA-F]+", s):                       # hash
        return False
    if re.match(r"\d{2}\.\d{2}\.\d{2}-", s):                   # identificador
        return False
    if re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)+", s):          # slug
        return False
    if re.search(r"\.[A-Za-z]{2,4}$", s):                      # arquivo
        return False
    if re.fullmatch(r"[\d.,:/-]+", s):                          # data, número
        return False
    return True


def detectar(texto):
    """Lista de sinais em `texto`: dicts com categoria, valor, linha e rótulo."""
    sinais = []

    def add(cat, valor, linha, rotulo=None):
        sinais.append({"categoria": cat, "valor": valor, "linha": linha,
                       "rotulo": rotulo or cat})

    for n, linha in enumerate((texto or "").splitlines(), 1):
        ocupado = []

        def livre(m):
            return all(m.end() <= a or m.start() >= b for a, b in ocupado)

        for m in CNPJ_RE.finditer(linha):
            d = _so_digitos(m.group())
            if _dv_cnpj(d) and (len(m.group()) > 14 or re.search(r"cnpj", linha, re.I)):
                add("cnpj", m.group(), n)
                ocupado.append(m.span())
        for m in CPF_RE.finditer(linha):
            d = _so_digitos(m.group())
            if livre(m) and _dv_cpf(d) and (len(m.group()) > 11 or re.search(r"cpf", linha, re.I)):
                add("cpf", m.group(), n)
                ocupado.append(m.span())
        for m in EMAIL_RE.finditer(linha):
            add("email", m.group(), n)
            ocupado.append(m.span())
        for m in URL_RE.finditer(linha):
            add("link", m.group(), n)
            ocupado.append(m.span())
        for m in CEP_RE.finditer(linha):
            if livre(m):
                add("cep", m.group(), n)
                ocupado.append(m.span())
        for m in REGISTRO_RE.finditer(linha):
            add("registro", m.group(), n, "registro profissional")
            ocupado.append(m.span())
        for rx in (TELEFONE_RE, CELULAR_SEM_DDD_RE):
            for m in rx.finditer(linha):
                if livre(m) and 10 <= len(_so_digitos(m.group())) + (2 if rx is CELULAR_SEM_DDD_RE else 0) <= 13:
                    add("telefone", m.group(), n)
                    ocupado.append(m.span())
        for m in SEGREDO_CHAVE_RE.finditer(linha):
            add("segredo", m.group(1), n, "segredo (palavra-chave)")
        for m in SEGREDO_CONHECIDO_RE.finditer(linha):
            add("segredo", m.group(), n, "segredo (formato de chave conhecido)")
        if not ocupado and _parece_segredo_pela_forma(linha):
            add("segredo", linha.strip(), n, "possível segredo (forma)")
    return sinais


def vocabulario(texto, extra_pessoais=(), extra_profissionais=()):
    """Quantas vezes cada grupo de palavras aparece — {grupo: {palavra: n}}."""
    alvo = f" {normalizar(texto)} "
    grupos = {
        "pessoal": list(PALAVRAS_PESSOAIS) + [normalizar(p) for p in extra_pessoais],
        "saude": list(PALAVRAS_SAUDE),
        "profissional": list(PALAVRAS_PROFISSIONAIS) + [normalizar(p) for p in extra_profissionais],
    }
    saida = {}
    for g, palavras in grupos.items():
        achou = {}
        for p in palavras:
            k = alvo.count(f" {p} ")
            if k:
                achou[p] = k
        if achou:
            saida[g] = achou
    return saida


# --------------------------------------------------------------------------
# apelidos de projeto
# --------------------------------------------------------------------------

def apelidos_em(texto, projetos, limiar=0.85):
    """{projeto: {"modo": "exato"|"aproximado", "termo": ...}} para cada projeto citado.

    `projetos` é o `triagem.projetos` da config. Exato compara texto normalizado
    palavra a palavra; aproximado compara sem espaços contra janelas de uma a
    três palavras — é o que acha o nome de projeto que a transcrição quebrou.
    """
    norm = normalizar(texto)
    palavras = norm.split()
    alvo = f" {norm} "
    compacto = norm.replace(" ", "")
    janelas = set()
    for tam in (1, 2, 3, 4):
        for i in range(len(palavras) - tam + 1):
            janelas.add("".join(palavras[i:i + tam]))
    achados = {}
    for nome, dados in (projetos or {}).items():
        termos = [nome] + list((dados or {}).get("apelidos") or [])
        for termo in termos:
            t = normalizar(termo)
            if not t:
                continue
            if f" {t} " in alvo or (len(t.replace(" ", "")) >= 6 and t.replace(" ", "") in compacto):
                achados[nome] = {"modo": "exato", "termo": termo}
                break
        if nome in achados:
            continue
        for termo in termos:
            t = normalizar(termo).replace(" ", "")
            if len(t) < 6:
                continue
            for j in janelas:
                if abs(len(j) - len(t)) > 2:
                    continue
                sm = difflib.SequenceMatcher(None, t, j)
                if sm.real_quick_ratio() >= limiar and sm.quick_ratio() >= limiar and sm.ratio() >= limiar:
                    achados[nome] = {"modo": "aproximado", "termo": termo, "no_texto": j}
                    break
            if nome in achados:
                break
    return achados


# --------------------------------------------------------------------------
# conversa exportada
# --------------------------------------------------------------------------

CONVERSA_RES = [
    # [17/9/26, 5:24:14 PM] Nome: texto
    re.compile(r"^‎?\[\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?\] ([^:]{1,60}): (.*)$"),
    # 17/09/2026 17:24 - Nome: texto
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2} - ([^:]{1,60}): (.*)$"),
    # [17:24] **Nome:** texto
    re.compile(r"^\[\d{1,2}:\d{2}\] \*\*([^*]{1,60}):\*\* ?(.*)$"),
]
APAGADA_RE = re.compile(r"mensagem apagada|esta mensagem foi apagada|this message was deleted|"
                        r"you deleted this message|voc[eê] apagou esta mensagem", re.I)
MIDIA_OMITIDA_RE = re.compile(r"omitid|ocult|media omitted|<m[ií]dia|\[mensagem de voz\]|"
                              r"\[imagem\]|\[v[ií]deo\]|\[figurinha\]", re.I)
VOCE = {"voce", "você", "you", "eu"}


def ler_conversa(texto):
    """Resumo de um export de conversa, ou None se o texto não tem essa forma."""
    por_pessoa = {}
    apagadas = omitidas = total = 0
    for linha in (texto or "").splitlines():
        for rx in CONVERSA_RES:
            m = rx.match(linha.strip())
            if m:
                quem, msg = m.group(1).strip(), m.group(2)
                total += 1
                por_pessoa[quem] = por_pessoa.get(quem, 0) + 1
                if APAGADA_RE.search(msg):
                    apagadas += 1
                elif MIDIA_OMITIDA_RE.search(msg):
                    omitidas += 1
                break
    if total < 2:
        return None
    return {
        "mensagens": total,
        "participantes": {k: v for k, v in por_pessoa.items() if normalizar(k) not in VOCE},
        "suas": sum(v for k, v in por_pessoa.items() if normalizar(k) in VOCE),
        "apagadas": apagadas,
        "midia_omitida": omitidas,
        "com_conteudo": total - apagadas - omitidas,
    }


# --------------------------------------------------------------------------
# máscara
# --------------------------------------------------------------------------

def mascarar(categoria, valor):
    v = str(valor)
    if categoria in ("telefone", "cpf", "cnpj", "cep"):
        total = len(_so_digitos(v))
        vistos = 0
        saida = []
        for c in v:
            if c.isdigit():
                vistos += 1
                saida.append(c if vistos > total - 2 else "•")
            else:
                saida.append(c)
        return "".join(saida)
    if categoria == "email":
        usuario, _, dominio = v.partition("@")
        return f"{usuario[:1]}•••@{dominio}"
    if categoria == "registro":
        return re.sub(r"\d(?=\d{2})", "•", v)
    if categoria == "link":
        m = re.match(r"(https?://[^/?#]+)", v)
        return (m.group(1) + "/…") if m and len(v) > len(m.group(1)) + 1 else v
    if categoria == "participante":
        partes = [p for p in re.split(r"\s+", v) if p]
        if partes and re.fullmatch(r"[\d\s()+.-]+", v):
            return mascarar("telefone", v)
        return " ".join(p[0].upper() + "." for p in partes) or "?"
    if categoria == "segredo":
        return f"••• ({len(v)} caracteres)"
    return v


def mascarar_texto(texto):
    """O mesmo texto com cada sinal de terceiro ou segredo mascarado."""
    saida = texto
    for s in sorted(detectar(texto), key=lambda s: -len(s["valor"])):
        if s["categoria"] in CATEGORIAS_TERCEIRO | CATEGORIAS_SEGREDO:
            saida = saida.replace(s["valor"], mascarar(s["categoria"], s["valor"]))
    return saida


# --------------------------------------------------------------------------
# inventário
# --------------------------------------------------------------------------

def _ffprobe():
    return os.environ.get("TRIAGEM_FFPROBE") or shutil.which("ffprobe")


def sondar_video(caminho):
    """O que o vídeo tem: fala, só imagem, ou imagem parada com som. None sem ffprobe."""
    exe = _ffprobe()
    if not exe:
        return None
    try:
        r = subprocess.run(
            [exe, "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,nb_frames", "-of", "json", str(caminho)],
            capture_output=True, text=True, timeout=60)
        dados = json.loads(r.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    streams = dados.get("streams") or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    quadros = None
    if video:
        try:
            quadros = int(video[0].get("nb_frames"))
        except (TypeError, ValueError):
            quadros = None
    dur = float((dados.get("format") or {}).get("duration") or 0)
    if video and quadros is not None and quadros <= 2:
        caso = "imagem parada" + (" com áudio: ver o quadro; o áudio pode ser só música" if audio else "")
    elif video and audio:
        caso = "com áudio: transcrever e ver alguns quadros"
    elif video:
        caso = "sem áudio: ver quadros"
    else:
        caso = "só áudio: transcrever"
    return {"duracao_s": round(dur, 1), "quadros": quadros, "tem_audio": bool(audio), "caso": caso}


def ler_texto(caminho):
    dados = Path(caminho).read_bytes()[:LIMITE_TEXTO]
    for cod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def midia_de(caminho, texto=None):
    ext = Path(caminho).suffix.lower()
    for midia, exts in MIDIAS.items():
        if ext in exts:
            break
    else:
        return "outro"
    if midia == "texto" and texto is not None:
        cabeca = texto[:1500]
        if ler_conversa(texto):
            return "conversa"
        if re.search(r"^(?:transcricao|motor|duracao_s)\s*:", cabeca, re.M):
            return "transcricao"
        linhas = [l for l in texto.splitlines() if l.strip()]
        if linhas and all(URL_RE.fullmatch(l.strip()) for l in linhas):
            return "link"
    return midia


def _hash(caminho):
    h = hashlib.sha1()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()[:12]


def _expandir(alvos):
    """(arquivo, rótulo) — o rótulo é o caminho relativo ao alvo, porque nome de
    pasta também carrega dado: o export de conversa leva o contato no nome."""
    for alvo in alvos:
        p = Path(alvo)
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                if q.is_file():
                    yield q, q.relative_to(p).as_posix()
        elif p.is_file():
            yield p, p.name


def sugerir(item):
    """A sugestão de destino de um item — rotulada, nunca decisão."""
    cats = {s["categoria"] for s in item["sinais"]}
    voc = item.get("vocabulario") or {}
    esferas = {p.get("esfera") for p in (item.get("projetos") or {}).values()}
    if "segredo" in cats:
        return "alerta: possível segredo — não gravar em lugar versionado; trocar se for real"
    if item["midia"] in ("audio", "video", "imagem", "documento", "pacote", "outro") and not item.get("texto_lido"):
        return "ler antes: precisa de extração"
    if cats & CATEGORIAS_TERCEIRO or item.get("conversa"):
        return "espera: dado de terceiro — reescrever sem ele antes de qualquer captura profissional"
    if "saude" in voc:
        return "provável pessoal (dado sensível de saúde)"
    if "misto" in esferas:
        return "projeto de esfera mista: decidir na leitura"
    pessoal = "pessoal" in voc or "pessoal" in esferas
    profissional = "profissional" in esferas or "profissional" in voc
    if pessoal and profissional:
        return "misto: fatiar em trechos"
    if pessoal:
        return "provável pessoal"
    if "profissional" in esferas:
        return "provável profissional"
    return "decidir na leitura"


def levantar(alvos, config=None):
    config = config or {}
    projetos = config.get("projetos") or {}
    extra_p = config.get("palavras_pessoais") or ()
    extra_t = config.get("palavras_profissionais") or ()
    itens = []
    for caminho, rotulo in _expandir(alvos):
        texto = None
        if caminho.suffix.lower() in MIDIAS["texto"] | {".csv", ".tsv", ".url", ".webloc"}:
            texto = ler_texto(caminho)
        midia = midia_de(caminho, texto)
        sinais = [dict(s, origem="nome") for s in detectar(rotulo)]
        item = {"caminho": str(caminho), "nome": rotulo, "midia": midia,
                "bytes": caminho.stat().st_size, "hash": _hash(caminho),
                "extracao": EXTRACAO.get(midia, EXTRACAO["outro"]), "texto_lido": texto is not None}
        if texto is not None:
            sinais += [dict(s, origem="conteúdo") for s in detectar(texto)]
            item["vocabulario"] = vocabulario(texto, extra_p, extra_t)
            achados = apelidos_em(texto, projetos)
            item["projetos"] = {k: dict(v, esfera=(projetos.get(k) or {}).get("esfera"))
                                for k, v in achados.items()}
            conversa = ler_conversa(texto)
            if conversa:
                item["conversa"] = conversa
                for quem in conversa["participantes"]:
                    sinais.append({"categoria": "participante", "valor": quem, "linha": None,
                                   "rotulo": "participante de conversa", "origem": "conteúdo"})
        if midia == "pacote":
            try:
                with zipfile.ZipFile(caminho) as z:
                    item["conteudo_pacote"] = z.namelist()[:200]
            except zipfile.BadZipFile:
                item["conteudo_pacote"] = []
        if midia in ("video", "audio"):
            item["sonda"] = sondar_video(caminho)
            if item["sonda"]:
                item["extracao"] = item["sonda"]["caso"]
        item["sinais"] = sinais
        item["sugestao"] = sugerir(item)
        itens.append(item)
    por_hash = {}
    for i, it in enumerate(itens):
        por_hash.setdefault(it["hash"], []).append(i)
    duplicatas = [v for v in por_hash.values() if len(v) > 1]
    return {"gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
            "itens": itens, "duplicatas": duplicatas}


# --------------------------------------------------------------------------
# relatório
# --------------------------------------------------------------------------

def _resumo_sinais(item, mostrar):
    grupos = {}
    for s in item["sinais"]:
        v = s["valor"] if mostrar else mascarar(s["categoria"], s["valor"])
        onde = "nome" if s.get("origem") == "nome" else (f"l.{s['linha']}" if s.get("linha") else "")
        grupos.setdefault(s["rotulo"], []).append(f"{v} ({onde})" if onde else v)
    return "; ".join(f"**{k}** ×{len(v)}: " + ", ".join(v[:3]) + (" …" if len(v) > 3 else "")
                     for k, v in grupos.items()) or "—"


def markdown(resultado, lote="", mostrar=False):
    itens = resultado["itens"]
    nome = (lambda it: it["nome"]) if mostrar else (lambda it: mascarar_texto(it["nome"]))
    L = [f"# Levantamento de triagem{' — ' + lote if lote else ''}", "",
         f"> Gerado por `metodo/triagem.py` em {resultado['gerado_em']}. **Sinais, não decisões**: "
         "a esfera de cada item se decide na leitura. "
         + ("Valores **sem máscara** — este arquivo não pode ir para lugar versionado."
            if mostrar else "Valores mascarados."), ""]
    contagem = {}
    for it in itens:
        contagem[it["midia"]] = contagem.get(it["midia"], 0) + 1
    L += ["## Resumo", "", "| Mídia | Itens |", "|---|---|"]
    L += [f"| {m} | {n} |" for m, n in sorted(contagem.items(), key=lambda x: -x[1])]
    segredos = [(it, s) for it in itens for s in it["sinais"] if s["categoria"] == "segredo"]
    if segredos:
        L += ["", "## ⚠ Alertas de segredo", ""]
        for it, s in segredos:
            v = s["valor"] if mostrar else mascarar("segredo", s["valor"])
            L.append(f"- `{nome(it)}` l.{s['linha']}: {s['rotulo']} — {v}")
    L += ["", "## Itens", "", "| # | Item | Mídia | Extração | Sinais | Projetos citados | Sugestão |",
          "|---|---|---|---|---|---|---|"]
    for i, it in enumerate(itens):
        projs = ", ".join(f"{k} ({v['modo']})" for k, v in (it.get("projetos") or {}).items()) or "—"
        L.append(f"| {i} | `{nome(it)}` | {it['midia']} | {it['extracao']} | "
                 f"{_resumo_sinais(it, mostrar)} | {projs} | {it['sugestao']} |")
    conversas = [it for it in itens if it.get("conversa")]
    for it in conversas:
        c = it["conversa"]
        pessoas = ", ".join((k if mostrar else mascarar("participante", k)) + f" ({v})"
                            for k, v in c["participantes"].items()) or "—"
        L += ["", f"### Conversa — `{nome(it)}`", "",
              f"- {c['mensagens']} mensagens: {c['suas']} suas; participantes: {pessoas}",
              f"- apagadas: {c['apagadas']} · mídia omitida: {c['midia_omitida']} · "
              f"com conteúdo legível: {c['com_conteudo']}"]
    if resultado["duplicatas"]:
        L += ["", "## Duplicatas (mesmo conteúdo)", ""]
        for grupo in resultado["duplicatas"]:
            L.append("- " + " = ".join(f"#{i}" for i in grupo))
    L += ["", "## O que este levantamento não faz", "",
          "- não lê imagem nem transcreve áudio — só diz que precisa;",
          "- não reconhece nome de pessoa no meio do texto (só participante de conversa);",
          "- não decide se um item é pessoal ou profissional.", ""]
    return "\n".join(L)


def carregar_config(raiz):
    raiz = Path(raiz)
    for nome in ("estacao.json", "plataforma.json"):
        arq = raiz / nome
        if arq.exists():
            try:
                return json.loads(arq.read_text(encoding="utf-8")).get("triagem") or {}
            except ValueError:
                return {}
    return {}


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Triagem: levanta sinais de uma entrada bruta.")
    p.add_argument("alvos", nargs="+", help="arquivos ou pastas a levantar")
    p.add_argument("--raiz", default=".", help="estação cuja chave `triagem` vale (padrão: pasta atual)")
    p.add_argument("--lote", default="", help="nome do lote, para o título do relatório")
    p.add_argument("--saida", help="grava o relatório neste arquivo (padrão: imprime)")
    p.add_argument("--json", help="grava também o levantamento cru em JSON (sem máscara)")
    p.add_argument("--mostrar", action="store_true",
                   help="não mascara — só para relatório que fica em área privada")
    p.add_argument("--estrito", action="store_true",
                   help="sai com código 1 se houver segredo ou dado de terceiro")
    a = p.parse_args(argv)
    resultado = levantar(a.alvos, carregar_config(a.raiz))
    texto = markdown(resultado, a.lote, a.mostrar)
    if a.saida:
        Path(a.saida).write_text(texto, encoding="utf-8")
        print(f"relatório: {a.saida} ({len(resultado['itens'])} itens)")
    else:
        print(texto)
    if a.json:
        Path(a.json).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.estrito:
        cats = {s["categoria"] for it in resultado["itens"] for s in it["sinais"]}
        if cats & (CATEGORIAS_TERCEIRO | CATEGORIAS_SEGREDO):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
