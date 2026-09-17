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
            valor = m.group(1).strip("`'\".,;:*_")
            resto = linha[m.end():].strip()
            # "senha: registrar como falso positivo" é prosa, não senha: valor só de
            # letras seguido de mais palavras não conta. Pego pela primeira vez
            # rodando a triagem sobre os próprios documentos dela.
            if len(valor) < 4 or (valor.isalpha() and re.match(r"\w", resto)):
                continue
            add("segredo", valor, n, "segredo (palavra-chave)")
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


# --------------------------------------------------------------------------
# decidir — os dois relatórios saem do decisoes.json
# --------------------------------------------------------------------------
#
# O `decisoes.json` mora no lote (privado) e é a saída da leitura: o que chegou,
# cada trecho com esfera, terceiro, segredo e motivo, os alertas, as perguntas —
# cada opção com os **efeitos** que a resposta tem sobre os trechos — e o que já
# seguiu. O relatório deixa de ser escrito à mão: sai dele, duas vezes.
#
# Efeito de uma opção: {"trecho": "B", "saidas": [{"destino": "profissional",
# "texto": "rascunhos/mercado-{P3}.md"}]}. `{P3}` vira a letra respondida na P3,
# em minúscula — é assim que uma pergunta escolhe a variante da outra.

ESFERAS = ("profissional", "pessoal", "administrativo", "duvida", "encerrado")
DESTINOS = ("profissional", "pessoal", "administrativo", "encerrar")


class TriagemErro(Exception):
    pass


def ler_decisoes(lote):
    arq = Path(lote) / "decisoes.json"
    if not arq.exists():
        raise TriagemErro(f"{arq} não existe — a leitura do lote grava as decisões nele")
    d = json.loads(arq.read_text(encoding="utf-8"))
    for chave in ("lote", "trechos", "perguntas"):
        if chave not in d:
            raise TriagemErro(f"decisoes.json sem a chave '{chave}'")
    d.setdefault("versao", 1)
    d.setdefault("seguiu", [])
    return d


def _tabela(cab, linhas):
    L = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    L += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return L


def render_relatorio(d, mascarado, aplicar_mascara=True):
    """Markdown do relatório. Mascarado: sem seções privadas e com `mascarar_texto`
    passado em tudo — a rede de segurança, não o método (o texto já deveria vir limpo:
    `cmd_decidir` recusa antes de mascarar se não vier)."""
    L = [f"# Relatório de triagem — {d.get('titulo') or d['lote']} · v{d['versao']}", ""]
    if d.get("cabecalho"):
        L += [d["cabecalho"], ""]
    L += [f"**Lote:** `{d.get('espera_rel', '_triagem')}/{d['lote']}/` (privado)",
          f"**Chegou em:** {d.get('chegou_em', '?')} · **Origem:** {d.get('origem', '?')}",
          f"**Versão:** v{d['versao']} — {d.get('nota_versao', '')}",
          "**Este arquivo é:** " + ("mascarado — sem nome, telefone, identificador de pessoa nem segredo; "
                                    "a cópia completa fica no lote." if mascarado
                                    else "a cópia **completa**; não sai da área privada."), ""]
    if d.get("em_uma_frase"):
        L += ["## Em uma frase", "", d["em_uma_frase"], ""]
    if d.get("chegou"):
        L += ["## O que chegou", ""]
        L += _tabela(["Grupo", "Itens", "Mídia", "Extração feita", "Achado"],
                     [[c.get("grupo", ""), c.get("itens", ""), c.get("midia", ""),
                       c.get("extracao", ""), c.get("achado", "")] for c in d["chegou"]])
        L.append("")
    L += ["## Decisões por trecho", ""]
    L += _tabela(["Trecho", "Esfera", "Terceiro", "Segredo", "Destino", "Por quê"],
                 [[f"{t['id']}. {t.get('descricao', '')}", t.get("esfera", "duvida"),
                   ", ".join(t.get("terceiro") or []) or "—", "sim" if t.get("segredo") else "não",
                   _destino_legivel(t, d), t.get("motivo", "")] for t in d["trechos"]])
    L.append("")
    for s in d.get("secoes") or []:
        if mascarado and s.get("privado"):
            continue
        L += [f"## {s['titulo']}", "", s["texto"].rstrip(), ""]
    if d.get("alertas"):
        L += ["## Alertas", ""] + [f"- {a}" for a in d["alertas"]] + [""]
    abertas = [p for p in d["perguntas"] if not p.get("resposta")]
    respondidas = [p for p in d["perguntas"] if p.get("resposta")]
    if abertas:
        L += ["## Perguntas", ""]
        for p in abertas:
            L += [f"### {p['id']} — {p['titulo']}", ""]
            L += [f"- [ ] **{o['id']}** — {o['texto']}" for o in p["opcoes"]]
            L += ["- [ ] Outra resposta: _______________", "- [ ] Deixar para depois", ""]
    if respondidas:
        L += ["## Respondidas", ""]
        for p in respondidas:
            o = next((o for o in p["opcoes"] if o["id"] == p["resposta"]), None)
            L.append(f"- **{p['id']}** — {p['titulo']}: **{p['resposta']}**"
                     + (f" — {o['texto']}" if o else ""))
        L.append("")
    L += ["## O que já seguiu", ""]
    L += _tabela(["Trecho", "Virou", "Onde"],
                 [[s["trecho"], s["virou"], s["onde"]] for s in d["seguiu"]] or [["—", "nada ainda", "—"]])
    L.append("")
    texto = "\n".join(L)
    return mascarar_texto(texto) if (mascarado and aplicar_mascara) else texto


def _destino_legivel(t, d):
    feitos = [s for s in d["seguiu"] if s["trecho"] == t["id"]]
    if feitos:
        return "; ".join(f"{s['onde']}" for s in feitos)
    if t.get("esfera") == "encerrado":
        return "encerrado"
    return "espera" + (f" ({', '.join(t['depende_de'])})" if t.get("depende_de") else "")


def sinais_que_vazam(texto):
    return [s for s in detectar(texto) if s["categoria"] in CATEGORIAS_TERCEIRO | CATEGORIAS_SEGREDO]


def cmd_decidir(lote, saida_mascarado=None, saida_completo=None):
    d = ler_decisoes(lote)
    lote = Path(lote)
    completo = Path(saida_completo) if saida_completo else lote / f"relatorio-v{d['versao']}.md"
    completo.write_text(render_relatorio(d, mascarado=False), encoding="utf-8")
    print(f"completo: {completo}")
    if saida_mascarado:
        # confere o texto como ele foi escrito, antes da máscara: mascarar e
        # depois conferir esconderia justamente o que devia ser recusado
        vazam = sinais_que_vazam(render_relatorio(d, mascarado=True, aplicar_mascara=False))
        texto = render_relatorio(d, mascarado=True)
        if vazam:
            for s in vazam:
                print(f"  RECUSADO: {s['rotulo']} na linha {s['linha']} do relatório mascarado",
                      file=sys.stderr)
            raise TriagemErro("o relatório mascarado ainda tem dado de terceiro ou segredo — "
                              "limpe o decisoes.json; nada foi gravado")
        Path(saida_mascarado).write_text(texto, encoding="utf-8")
        print(f"mascarado: {saida_mascarado}")
    return 0


# --------------------------------------------------------------------------
# aplicar — as respostas levam cada trecho ao destino
# --------------------------------------------------------------------------

def _json_estacao(raiz):
    raiz = Path(raiz)
    for nome in ("estacao.json", "plataforma.json"):
        if (raiz / nome).exists():
            return json.loads((raiz / nome).read_text(encoding="utf-8"))
    raise TriagemErro(f"{raiz} não é uma estação (sem estacao.json nem plataforma.json)")


def _raiz_destino(raiz, destino, cfg_triagem):
    if destino == "profissional":
        return Path(raiz)
    chave = {"pessoal": "pessoal", "administrativo": "administrativo"}[destino]
    rel = cfg_triagem.get(chave)
    if not rel:
        raise TriagemErro(f"a estação não declara triagem.{chave} — pergunte para onde vai")
    return (Path(raiz) / rel).resolve()


def _resumo(texto, limite=160):
    plano = " ".join(texto.split())
    return plano if len(plano) <= limite else plano[:limite].rsplit(" ", 1)[0] + "…"


def capturar(raiz_estacao, texto, slug, lote, trecho, removido=()):
    """Captura crua a partir de um trecho triado: id pelo utilitário, arquivo no
    estágio de entrada, linha no registro (append-only), sem-destino regenerado.
    Mesma mecânica da captura da interface, com a origem e a linhagem da triagem."""
    raiz = Path(raiz_estacao)
    est = _json_estacao(raiz)
    sigla = est["estagios"][0]["sigla"]
    util = Path(__file__).resolve().parent / "estacao.py"
    r = subprocess.run([sys.executable, str(util), "novo-id", "--raiz", str(raiz), "--etapa", sigla,
                        "--slug", slug], capture_output=True, text=True, encoding="utf-8", timeout=60)
    novo = (r.stdout or "").strip().splitlines()[0] if (r.stdout or "").strip() else ""
    if r.returncode != 0 or not novo:
        raise TriagemErro(f"novo-id falhou em {raiz}: {(r.stderr or r.stdout).strip()}")
    entrada = raiz / est.get("entrada", est["estagios"][0]["pasta"])
    entrada.mkdir(parents=True, exist_ok=True)
    fm = est.get("frontmatter") or {}
    marcas = ""
    if fm.get("nucleo"):
        marcas += f"{fm['nucleo']}: false\n"
    marcas += f"{fm.get('processado') or 'registro-id'}: {novo}\n"
    hoje = datetime.date.today().isoformat()
    arquivo = entrada / f"{novo}.md"
    arquivo.write_text(
        f"---\nid: {novo}\ndata: {hoje}\norigem: triagem — lote {lote}, trecho {trecho}\n"
        f"tags: []\nstatus: vaga\nlinks: []\ntriagem:\n  lote: {lote}\n  trecho: {trecho}\n"
        f"  removido: [{', '.join(removido)}]\n{marcas}---\n\n## Conteúdo bruto\n\n{texto.strip()}\n",
        encoding="utf-8")
    registro = raiz / est["arquivos"]["registro"]
    original = registro.read_text(encoding="utf-8") if registro.exists() else ""
    eol = "\r\n" if "\r\n" in original else "\n"
    rel = os.path.relpath(entrada, registro.parent).replace("\\", "/")
    linha = f"| {novo} | {hoje} | {sigla} | `{rel}/` | {_resumo(texto)} | [arquivo](<{rel}/{novo}.md>) |"
    titulo = f"## Entradas {hoje} — triagem"
    if titulo in original:
        ini = original.index(titulo)
        prox = re.search(r"\r?\n## ", original[ini + len(titulo):])
        fim = (ini + len(titulo) + prox.start()) if prox else len(original)
        secao = original[ini:fim].rstrip("\r\n")
        resto = original[fim:].lstrip("\r\n")
        novo_texto = original[:ini] + secao + eol + linha + (eol * 2 + resto if resto else eol)
    else:
        bloco = eol.join([titulo, "", "| ID | Data | Etapa/Tipo | Local | Resumo | Link |",
                          "|---|---|---|---|---|---|", linha])
        pos = original.rfind(eol + "## Pendente")
        if pos == -1:
            novo_texto = original.rstrip("\r\n") + (eol * 2 if original.strip() else "") + bloco + eol
        else:
            novo_texto = original[:pos].rstrip("\r\n") + eol * 2 + bloco + eol * 2 + original[pos:].lstrip("\r\n")
    with registro.open("w", encoding="utf-8", newline="") as f:
        f.write(novo_texto)
    if est.get("arquivos", {}).get("sem_destino") and (raiz / est["arquivos"]["sem_destino"]).exists():
        subprocess.run([sys.executable, str(util), "gerar-sem-destino", "--raiz", str(raiz)],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return novo, str(arquivo)


def planejar(d, respostas):
    """O que as respostas fazem: aplica os efeitos e lista as saídas prontas."""
    perguntas = {p["id"]: p for p in d["perguntas"]}
    for pid, op in respostas.items():
        if pid not in perguntas:
            raise TriagemErro(f"pergunta {pid} não existe neste lote")
        if op not in {o["id"] for o in perguntas[pid]["opcoes"]}:
            raise TriagemErro(f"{pid} não tem a opção {op}")
        perguntas[pid]["resposta"] = op
    letras = {p["id"]: p["resposta"].lower() for p in d["perguntas"] if p.get("resposta")}
    trechos = {t["id"]: t for t in d["trechos"]}
    for p in d["perguntas"]:
        if not p.get("resposta"):
            continue
        op = next(o for o in p["opcoes"] if o["id"] == p["resposta"])
        for ef in op.get("efeitos") or []:
            t = trechos.get(ef["trecho"])
            if t is None:
                raise TriagemErro(f"{p['id']}{op['id']} aponta para o trecho {ef['trecho']}, que não existe")
            for k, v in ef.items():
                if k != "trecho":
                    t[k] = v
    ja = {(s["trecho"], s.get("destino")) for s in d["seguiu"]}
    prontas = []
    for t in d["trechos"]:
        if any(p not in letras for p in t.get("depende_de") or []):
            continue
        for s in t.get("saidas") or []:
            if s["destino"] not in DESTINOS:
                raise TriagemErro(f"trecho {t['id']}: destino '{s['destino']}' desconhecido")
            if (t["id"], s["destino"]) in ja:
                continue
            # a dependência também pode ser da saída: numa resposta em que a
            # outra pergunta não importa, ela não trava o trecho inteiro
            if any(p not in letras for p in s.get("depende_de") or []):
                continue
            texto = s.get("texto")
            for pid, letra in letras.items():
                texto = texto.replace("{" + pid + "}", letra) if texto else texto
            prontas.append({"trecho": t, "destino": s["destino"], "texto": texto,
                            "slug": s.get("slug") or t.get("slug") or t["id"]})
    return prontas


def cmd_aplicar(lote, raiz, respostas, confirmar=False):
    lote = Path(lote)
    d = ler_decisoes(lote)
    cfg = carregar_config(raiz)
    prontas = planejar(d, respostas)
    if not prontas:
        print("nada pronto para seguir: faltam respostas ou efeitos nas opções respondidas.")
    erros = []
    for p in prontas:
        if p["destino"] == "encerrar":
            print(f"  trecho {p['trecho']['id']}: encerrar (sem captura)")
            continue
        arq = lote / p["texto"] if p["texto"] else None
        if not arq or not arq.exists():
            erros.append(f"trecho {p['trecho']['id']}: texto {p['texto']} não existe no lote")
            continue
        texto = ler_texto(arq)
        if p["destino"] != "pessoal":
            vazam = sinais_que_vazam(texto)
            if vazam:
                erros.append(f"trecho {p['trecho']['id']} → {p['destino']}: o texto ainda tem "
                             + ", ".join(sorted({s['rotulo'] for s in vazam})) + " — recusado")
                continue
        destino_raiz = _raiz_destino(raiz, p["destino"], cfg)
        print(f"  trecho {p['trecho']['id']}: {p['destino']} → captura em {destino_raiz} "
              f"({len(texto)} caracteres de {p['texto']})")
        p["pronto"] = (destino_raiz, texto)
    for e in erros:
        print(f"  ERRO: {e}", file=sys.stderr)
    if not confirmar:
        print("simulação: nada foi gravado. Rode de novo com --confirmar.")
        return 1 if erros else 0
    mudou = bool(respostas)
    for p in prontas:
        t = p["trecho"]
        if p["destino"] == "encerrar":
            t["esfera"] = "encerrado"
            d["seguiu"].append({"trecho": t["id"], "destino": "encerrar", "virou": "encerrado", "onde": "—"})
            mudou = True
        elif "pronto" in p:
            destino_raiz, texto = p["pronto"]
            novo, caminho = capturar(destino_raiz, texto, p["slug"], d["lote"], t["id"], t.get("removido") or ())
            onde = "estação pessoal" if p["destino"] == "pessoal" else f"{Path(caminho).parent.name}/"
            d["seguiu"].append({"trecho": t["id"], "destino": p["destino"],
                                "virou": novo if p["destino"] != "pessoal" else "captura privada",
                                "onde": onde})
            print(f"  ✓ {t['id']} → {novo}")
            mudou = True
    if mudou:
        d["versao"] += 1
        hoje = datetime.date.today().isoformat()
        d["nota_versao"] = f"respostas de {hoje}: " + ", ".join(f"{k}={v}" for k, v in respostas.items())
        (lote / "decisoes.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if d.get("saida_mascarado"):
            mascarado = Path(d["saida_mascarado"])
            if not mascarado.is_absolute():
                mascarado = Path(raiz) / mascarado
            cmd_decidir(lote, mascarado)
        else:
            cmd_decidir(lote)
    return 1 if erros else 0


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
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("decidir", "aplicar"):
        return _main_decisoes(argv)
    p = argparse.ArgumentParser(description="Triagem: levanta sinais de uma entrada bruta. "
                                            "Subcomandos: decidir, aplicar (ver triagem.md).")
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


def _main_decisoes(argv):
    p = argparse.ArgumentParser(prog="triagem.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decidir", help="gera os relatórios a partir do decisoes.json do lote")
    d.add_argument("lote")
    d.add_argument("--mascarado", help="onde gravar o relatório mascarado (versionável)")
    d.add_argument("--completo", help="onde gravar o completo (padrão: <lote>/relatorio-v<N>.md)")
    a = sub.add_parser("aplicar", help="registra respostas e leva cada trecho pronto ao destino")
    a.add_argument("lote")
    a.add_argument("--raiz", required=True, help="a estação profissional (a que declara `triagem`)")
    a.add_argument("--responder", action="append", default=[], metavar="P1=A",
                   help="resposta a uma pergunta; repita para várias")
    a.add_argument("--confirmar", action="store_true", help="sem isto, só simula")
    args = p.parse_args(argv)
    try:
        if args.cmd == "decidir":
            return cmd_decidir(args.lote, args.mascarado, args.completo)
        respostas = {}
        for r in args.responder:
            if "=" not in r:
                raise TriagemErro(f"--responder espera P1=A, veio '{r}'")
            k, v = r.split("=", 1)
            respostas[k.strip().upper()] = v.strip().upper()
        return cmd_aplicar(args.lote, args.raiz, respostas, args.confirmar)
    except TriagemErro as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
