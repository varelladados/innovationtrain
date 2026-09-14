#!/usr/bin/env python3
"""Utilitário da estação — `novo-id`, `gerar-sem-destino`, `verificar`.

Derivado do utilitário do sistema em que a Central nasceu, não escrito do zero: a
lógica de sequência por dia e de hash sem colisão já estava testada em uso real,
e reescrever isso só produziria bugs novos. O que mudou foi o vocabulário (os
estágios saem do `estacao.json`, não são três siglas fixas) e o tamanho —
aqui ficaram os três comandos que qualquer estação precisa.

**A raiz vem por argumento.** Este script não sabe onde ele mora nem assume que
está dentro da estação. `--raiz` vale para todos os comandos; quando omitido,
vale a pasta atual — é assim que a Central o chama, com o `cwd` já na raiz da
estação (e é o que deixa o mesmo código servir para o utilitário legado, que
não conhece esse argumento).

**A taxonomia vem do `estacao.json` da raiz**, e só de lá. Não há padrão
embutido aqui de propósito: um segundo lugar com os nomes dos estágios seria
uma cópia a mais para divergir (o `app/config.py` já é a cópia executável de
`taxonomia.md`). Sem `estacao.json` — nem `plataforma.json`, o nome até a 0.9 —,
este script diz isso e para.

Stdlib puro, sem dependência — mesma regra do resto do produto.
"""
import argparse
import datetime
import json
import re
import secrets
import sys
import unicodedata
from pathlib import Path

MARK_START = "<!-- gerado:{key}:inicio -->"
MARK_END = "<!-- gerado:{key}:fim -->"

#: Uma linha de continuação do mesmo grão usa o próprio identificador + `-N`,
#: nunca repete a string igual — senão vira duplicata. Convenção herdada.
SUFIXO_CONTINUACAO_RE = re.compile(r"^(.*-[a-f0-9]{4,5})-(\d+)$")

TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


# --------------------------------------------------------------------------
# configuração da estação
# --------------------------------------------------------------------------

class Estacao:
    def __init__(self, raiz: Path):
        self.raiz = raiz.resolve()
        arquivo = self.raiz / "estacao.json"
        if not arquivo.exists() and (self.raiz / "plataforma.json").exists():
            arquivo = self.raiz / "plataforma.json"   # o nome até a 0.9
        if not arquivo.exists():
            sys.exit(
                f"ERRO: {arquivo} não existe.\n"
                "\n"
                "Este utilitário lê a taxonomia do estacao.json da raiz — ele não\n"
                "tem nomes de estágio embutidos, de propósito. Se esta pasta é mesmo\n"
                "uma estação, crie o arquivo; se você ainda não tem estação\n"
                "nenhuma, é a aba Embarque da Central que cria a primeira."
            )
        self.arquivo = arquivo
        try:
            self.d = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"ERRO: {arquivo} não é um JSON válido: {e}")

        for chave in ("estagios", "arquivos"):
            if chave not in self.d:
                sys.exit(f"ERRO: {arquivo} não declara '{chave}'.")

    # -- taxonomia --------------------------------------------------------
    @property
    def estagios(self):
        return self.d["estagios"]

    @property
    def siglas(self):
        """As canônicas, uma por estágio. É delas que sai todo identificador novo."""
        return [e["sigla"] for e in self.estagios]

    @property
    def duplicatas_historicas(self):
        """Identificadores que já chegaram repetidos, de antes da convenção `-N`.

        Mesmo espírito de `siglas_legadas`: uma estação com acervo chega com
        as marcas do tempo em que ela ainda não tinha regra. Exigir que o
        passado seja reescrito para o `verificar` ficar verde é o caminho mais
        curto para ninguém mais rodar o `verificar`.

        Declarar aqui **não resolve** a duplicata — rebaixa de PROBLEMA para
        AVISO e a mantém à vista. Só o dono decide se retrofita ou convive.
        """
        return {str(x) for x in (self.d.get("duplicatas_historicas") or [])}

    @property
    def siglas_legadas(self):
        """{sigla antiga: número do estágio} — estação que já tinha acervo.

        Reconhecidas na **leitura** (registro, nome de arquivo, `sem-destino`,
        `verificar`) e nunca na **escrita**: `novo-id` recusa uma sigla daqui,
        porque item novo nasce com o vocabulário de hoje.
        """
        d = self.d.get("siglas_legadas") or {}
        return {str(k): int(v) for k, v in d.items() if str(k) not in self.siglas}

    @property
    def siglas_todas(self):
        # as mais longas primeiro: numa alternância, a curta casaria antes e
        # truncaria a captura
        return sorted(self.siglas + list(self.siglas_legadas),
                      key=lambda s: (-len(s), s))

    def estagio_de_sigla(self, sigla):
        for e in self.estagios:
            if e["sigla"] == sigla:
                return e["n"]
        return self.siglas_legadas.get(sigla)

    @property
    def tipos(self):
        return list(self.d.get("tipos") or [])

    @property
    def historico(self):
        return self.d.get("historico", "_historico")

    @property
    def marcador(self):
        return self.d.get("marcador", "_indice.md")

    def caminho(self, qual):
        rel = self.d["arquivos"].get(qual)
        return self.raiz / rel if rel else None

    def pasta_do_estagio(self, sigla):
        for e in self.estagios:
            if e["sigla"] == sigla:
                return self.raiz / e["pasta"]
        return None

    # -- registro ---------------------------------------------------------
    @property
    def id_re(self):
        siglas = "|".join(re.escape(s) for s in self.siglas_todas)
        tipos = r"(?:-([A-Z]{2,4}))?"
        return re.compile(
            r"\b(\d{2}\.\d{2}\.\d{2})-(" + siglas + r")" + tipos +
            r"-(\d{3})-([a-z0-9-]+)-([a-f0-9]{4,5})\b")

    def ler_registro(self):
        caminho = self.caminho("registro")
        if caminho is None:
            sys.exit(f"ERRO: {self.arquivo.name} não declara arquivos.registro")
        if not caminho.exists():
            sys.exit(f"ERRO: registro não encontrado em {caminho}")
        return caminho.read_text(encoding="utf-8")

    def todos_ids(self, texto):
        out = []
        for m in self.id_re.finditer(texto):
            data, etapa, tipo, seq, slug, h = m.groups()
            out.append({"id": m.group(0), "data": data, "etapa": etapa,
                        "tipo": tipo, "seq": int(seq), "slug": slug, "hash": h})
        return out

    def linhas_do_registro(self, texto):
        """Só as linhas de tabela de verdade: 6 colunas, primeira com identificador."""
        linhas = []
        for line in texto.splitlines():
            m = TABLE_ROW_RE.match(line.strip())
            if not m:
                continue
            cols = [c.strip() for c in m.group(1).split("|")]
            if len(cols) != 6:
                continue
            if cols[0] in ("ID", "---") or set(cols[0]) <= {"-"}:
                continue
            if not self.id_re.search(cols[0]):
                continue
            linhas.append({"id": cols[0], "data": cols[1], "etapa_tipo": cols[2],
                           "local": cols[3], "resumo": cols[4], "link": cols[5]})
        return linhas


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------

def slugify(text, max_words=5, max_len=40):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    palavras = [w for w in re.split(r"[\s-]+", text) if w][:max_words]
    return "-".join(palavras)[:max_len].rstrip("-")


# --------------------------------------------------------------------------
# novo-id
# --------------------------------------------------------------------------

def cmd_novo_id(args):
    p = Estacao(Path(args.raiz))
    etapa = args.etapa.upper()
    if etapa in p.siglas_legadas:
        sys.exit(
            f"ERRO: '{etapa}' é uma sigla legada desta estação — ela é lida, "
            f"nunca emitida.\nItem novo nasce com o vocabulário de hoje: "
            f"{p.siglas}")
    if etapa not in p.siglas:
        sys.exit(f"ERRO: --etapa precisa ser uma de {p.siglas}")

    tipo = args.tipo.upper() if args.tipo else None
    if tipo and p.tipos and tipo not in [t.upper() for t in p.tipos]:
        sys.exit(f"ERRO: --tipo {tipo} não está declarado no {p.arquivo.name} "
                 f"(tipos: {p.tipos})")

    data_str = args.data or datetime.date.today().strftime("%y.%m.%d")
    texto = p.ler_registro()
    existentes = p.todos_ids(texto)

    # a sequência é por dia + estágio + tipo, como no original: dois itens do
    # mesmo dia e estágio nunca compartilham SEQ.
    do_dia = [e for e in existentes
              if e["data"] == data_str and e["etapa"] == etapa and e["tipo"] == tipo]
    proximo = max((e["seq"] for e in do_dia), default=0) + 1

    slug = slugify(args.slug)
    if not slug:
        sys.exit("ERRO: --slug vazio depois de normalizar — dê pelo menos uma palavra")

    usados = {e["hash"] for e in existentes}
    for _ in range(50):
        h = secrets.token_hex(2)
        if h not in usados:
            break
    else:
        sys.exit("ERRO: não consegui gerar hash sem colisão em 50 tentativas")

    partes = [data_str, etapa] + ([tipo] if tipo else []) + [f"{proximo:03d}", slug, h]
    novo = "-".join(partes)
    print(novo)
    if args.verbose:
        print(f"  (SEQ {proximo:03d} — havia {len(do_dia)} entrada(s) {etapa}"
              f"{'-' + tipo if tipo else ''} em {data_str})", file=sys.stderr)
    return novo


# --------------------------------------------------------------------------
# gerar-sem-destino
# --------------------------------------------------------------------------

def cmd_gerar_sem_destino(args):
    """Regenera a lista do que está no registro e ainda não avançou.

    "Sem destino" é a linha sem o marcador de linhagem `→`. O arquivo é
    **gerado**: só os blocos entre os marcadores são reescritos, o resto do
    texto é do usuário e não se toca.
    """
    p = Estacao(Path(args.raiz))
    destino = p.caminho("sem_destino")
    if destino is None:
        sys.exit(f"ERRO: {p.arquivo.name} não declara arquivos.sem_destino")

    linhas = p.linhas_do_registro(p.ler_registro())
    sem_destino, vistos = [], set()
    for l in linhas:
        if "→" in l["etapa_tipo"] or l["id"] in vistos:
            continue
        vistos.add(l["id"])
        sem_destino.append(l)

    def bloco(chave, itens):
        cab = ["| ID | Data | Etapa/Tipo | Local | Resumo | Link |",
               "|---|---|---|---|---|---|"]
        corpo = "\n".join(cab + [
            f"| {i['id']} | {i['data']} | {i['etapa_tipo']} | {i['local']} | {i['resumo']} | {i['link']} |"
            for i in itens]) if itens else "*(nada nesta etapa no momento)*"
        return f"{MARK_START.format(key=chave)}\n{corpo}\n{MARK_END.format(key=chave)}"

    if not destino.exists():
        sys.exit(f"ERRO: {destino} não existe — crie o arquivo com um par de marcadores "
                 f"{MARK_START.format(key=p.siglas[0].lower())} … "
                 f"{MARK_END.format(key=p.siglas[0].lower())} por estágio.")

    def sigla_da_linha(l):
        """A sigla no início da coluna Etapa/Tipo — a mais longa que casar.

        A coluna começa com a sigla e pode trazer tipo e seta depois
        (`SBZ-DIG →PJD-x`). Casar pela mais longa evita que uma sigla curta
        engula uma longa que começa igual.
        """
        campo = l["etapa_tipo"].lstrip("→ ")
        for s in p.siglas_todas:
            if campo.startswith(s):
                return s
        return None

    texto = original = destino.read_text(encoding="utf-8")
    contagens = {}
    for sigla in p.siglas:
        chave = sigla.lower()
        n = p.estagio_de_sigla(sigla)
        # por ESTÁGIO, não por string: numa estação que já tinha acervo, a
        # linha antiga traz a sigla antiga e precisa cair no bloco do estágio a
        # que ela corresponde hoje — senão o gerado nasce vazio e mente.
        itens = [l for l in sem_destino
                 if p.estagio_de_sigla(sigla_da_linha(l) or "") == n]
        contagens[sigla] = len(itens)
        padrao = re.compile(
            re.escape(MARK_START.format(key=chave)) + r".*?" + re.escape(MARK_END.format(key=chave)),
            re.DOTALL)
        if not padrao.search(texto):
            sys.exit(f"ERRO: marcador '{chave}' não encontrado em {destino}")
        texto = padrao.sub(lambda _m, b=bloco(chave, itens): b, texto)

    resumo = ", ".join(f"{n} {s}" for s, n in contagens.items())
    if args.dry_run:
        print(f"[dry-run] {len(sem_destino)} sem destino ({resumo}).")
        print("[dry-run] mudaria o arquivo." if texto != original
              else "[dry-run] já está sincronizado.")
        return
    if texto != original:
        destino.write_text(texto, encoding="utf-8")
        print(f"{destino.name} regenerado: {len(sem_destino)} sem destino ({resumo}).")
    else:
        print(f"{destino.name} já estava sincronizado com o registro — nada mudou.")


# --------------------------------------------------------------------------
# verificar
# --------------------------------------------------------------------------

def cmd_verificar(args):
    p = Estacao(Path(args.raiz))
    problemas, avisos = [], []

    # 1. a raiz é mesmo uma estação
    if not (p.raiz / p.marcador).exists():
        problemas.append(f"{p.marcador} não existe — sem porta de entrada, "
                         "a Central não abre esta pasta")

    # 2. as pastas dos estágios existem
    for e in p.estagios:
        if not (p.raiz / e["pasta"]).is_dir():
            avisos.append(f"pasta do estágio {e['n']} não existe: {e['pasta']}/")

    texto = p.ler_registro()
    linhas = p.linhas_do_registro(texto)

    # 3. identificador repetido (linha canônica duplicada) e continuação órfã
    por_id = {}
    for l in linhas:
        por_id.setdefault(l["id"], []).append(l["data"])
    bases = {l["id"] for l in linhas if not SUFIXO_CONTINUACAO_RE.match(l["id"])}
    historicas = p.duplicatas_historicas
    for id_, datas in por_id.items():
        if len(datas) <= 1:
            continue
        if id_ in historicas:
            avisos.append(f"identificador repetido ({len(datas)}x), declarado como "
                          f"histórico no {p.arquivo.name}: {id_} — anterior à "
                          "convenção do sufixo -N; decidir retrofit ou convivência")
        else:
            problemas.append(f"identificador repetido no registro ({len(datas)}x): {id_} "
                             "— continuação usa o mesmo id + sufixo -N, nunca a string igual")
    for id_ in por_id:
        m = SUFIXO_CONTINUACAO_RE.match(id_)
        if m and m.group(1) not in bases:
            problemas.append(f"continuação '-{m.group(2)}' sem linha-base no registro: {id_}")

    # 4. arquivo com identificador no nome que não tem linha no registro
    ids_no_registro = {l["id"] for l in linhas}
    ids_mencionados = {i["id"] for i in p.todos_ids(texto)}
    for e in p.estagios:
        pasta = p.raiz / e["pasta"]
        if not pasta.is_dir():
            continue
        for arq in pasta.rglob("*.md"):
            m = p.id_re.match(arq.stem)
            if not m:
                continue
            if m.group(0) not in ids_no_registro and m.group(0) not in ids_mencionados:
                problemas.append(f"arquivo sem linha no registro: "
                                 f"{arq.relative_to(p.raiz).as_posix()}")

    # 5. linha no registro cujo estágio não existe na taxonomia (nem como legado)
    for l in linhas:
        sigla = l["etapa_tipo"].split("-")[0].split(" ")[0].strip("→ ")
        if sigla and p.estagio_de_sigla(sigla) is None:
            avisos.append(f"linha com estágio desconhecido '{sigla}': {l['id']}")

    # 6. o gerado está sincronizado?
    destino = p.caminho("sem_destino")
    if destino is not None and destino.exists():
        import io
        antes = destino.read_text(encoding="utf-8")
        buf, real = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            cmd_gerar_sem_destino(argparse.Namespace(raiz=str(p.raiz), dry_run=True))
        finally:
            sys.stdout = real
        if "mudaria o arquivo" in buf.getvalue():
            avisos.append(f"{destino.name} está desatualizado — rode: "
                          f"python estacao.py gerar-sem-destino --raiz {p.raiz}")
        assert destino.read_text(encoding="utf-8") == antes  # dry-run não escreve

    # -- relatório --------------------------------------------------------
    print(f"Estação: {p.d.get('nome') or p.raiz.name}  ({p.raiz})")
    print(f"Estágios: {' → '.join(p.siglas)}   ·   linhas no registro: {len(linhas)}")
    for a in avisos:
        print(f"  AVISO:    {a}")
    for pr in problemas:
        print(f"  PROBLEMA: {pr}")
    if not problemas and not avisos:
        print("  tudo certo.")
    elif not problemas:
        print(f"  {len(avisos)} aviso(s), nenhum problema.")
    return 1 if problemas else 0


# --------------------------------------------------------------------------

# ---------------------------------------------------------------- reiniciar

#: Nunca removidos ao reiniciar: metadados de ferramenta, não conteúdo da
#: estação. `cache/` e `dist/` são derivados e voltam sozinhos.
PRESERVAR = {".git", ".hg", ".svn", "cache", "dist", "node_modules", "__pycache__"}


def cmd_reiniciar(args):
    """Devolve a estação ao estado declarado em `estado_inicial`.

    A semântica é simples de explicar e de conferir: **deixa a pasta idêntica ao
    instantâneo**. Some o que foi criado depois, volta o que foi apagado, e o que
    foi editado volta ao texto original.

    Três portões, nesta ordem, e o primeiro é o que importa:

    1. **A estação tem que declarar `estado_inicial`.** Uma estação de
       verdade não declara, e por isso este comando não tem como apagar o
       trabalho de ninguém — ele recusa antes de olhar o disco.
    2. O instantâneo tem que existir e ser mesmo uma estação (`estacao.json`).
    3. O instantâneo tem que estar **fora** da raiz, senão ele se apagaria.

    Sem `--confirmar` só mostra o que faria.
    """
    import shutil

    p = Estacao(Path(args.raiz))
    rel = p.d.get("estado_inicial")
    if not rel:
        print(f"Esta estação não declara `estado_inicial` no {p.arquivo.name}.")
        print("")
        print("Reiniciar só existe para as estações de exemplo, que vêm com uma")
        print("cópia intacta de si mesmas. Uma estação sua não tem essa cópia —")
        print("e é por isso que este comando não consegue apagar o seu trabalho.")
        return 2

    # `--de` escolhe QUAL instantaneo restaurar (a trilha usa isso para andar de
    # passo em passo). O portao continua sendo `estado_inicial`: sem ele, nem
    # `--de` faz este comando tocar em nada.
    rel = getattr(args, "de", None) or rel
    origem = (p.raiz / str(rel).replace("\\", "/")).resolve()
    if not any((origem / n).is_file() for n in ("estacao.json", "plataforma.json")):
        print(f"ERRO: `estado_inicial` aponta para {origem}, que não é uma estação.")
        return 2
    if origem == p.raiz or p.raiz in origem.parents:
        print(f"ERRO: o estado inicial ({origem}) está dentro da própria estação.")
        print("Ele seria apagado junto. Mova-o para fora antes.")
        return 2

    atual = {q.name for q in p.raiz.iterdir()} - PRESERVAR
    novo = {q.name for q in origem.iterdir()}
    remover = sorted(atual)
    print(f"Estação: {p.d.get('nome') or p.raiz.name}  ({p.raiz})")
    print(f"Estado inicial: {origem}")
    print("")
    print(f"  remove da raiz:  {len(remover)} item(ns)  {', '.join(remover[:8])}"
          + (" …" if len(remover) > 8 else ""))
    print(f"  restaura:        {len(novo)} item(ns)")
    preservados = sorted({q.name for q in p.raiz.iterdir()} & PRESERVAR)
    if preservados:
        print(f"  preserva:        {', '.join(preservados)}")

    if not args.confirmar:
        print("")
        print("Nada foi tocado. Rode de novo com --confirmar para valer.")
        return 0

    for nome in remover:
        alvo = p.raiz / nome
        if alvo.is_dir():
            shutil.rmtree(alvo)
        else:
            alvo.unlink()
    for q in sorted(origem.iterdir()):
        destino = p.raiz / q.name
        if q.is_dir():
            shutil.copytree(q, destino)
        else:
            shutil.copy2(q, destino)

    print("")
    print("  a estação voltou ao estado inicial.")
    return 0


def main(argv=None):
    # A saída é sempre UTF-8, que é como quem chama lê. Num pipe do Windows o
    # padrão é a página de código local (cp1252), que não tem "→": o print
    # levantava UnicodeEncodeError no meio do relatório e o comando saía com 1.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Utilitário de uma estação da Central.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def com_raiz(p):
        p.add_argument("--raiz", default=".",
                       help="pasta da estação (padrão: a pasta atual)")
        return p

    p_id = com_raiz(sub.add_parser("novo-id", help="gera o próximo identificador"))
    p_id.add_argument("--etapa", required=True, help="a sigla do estágio")
    p_id.add_argument("--slug", required=True, help="duas ou três palavras do assunto")
    p_id.add_argument("--tipo", help="tipo do projeto, quando a estação usa tipos")
    p_id.add_argument("--data", help="AA.MM.DD (padrão: hoje)")
    p_id.add_argument("--verbose", action="store_true")
    p_id.set_defaults(func=cmd_novo_id)

    p_sd = com_raiz(sub.add_parser("gerar-sem-destino",
                                   help="regenera a lista do que ainda não avançou"))
    p_sd.add_argument("--dry-run", action="store_true")
    p_sd.set_defaults(func=cmd_gerar_sem_destino)

    p_v = com_raiz(sub.add_parser("verificar", help="checa as invariantes da estação"))
    p_v.set_defaults(func=cmd_verificar)

    p_r = com_raiz(sub.add_parser(
        "reiniciar",
        help="devolve uma estação de EXEMPLO ao estado de origem"))
    p_r.add_argument("--de", help="pasta do instantâneo a restaurar "
                                  "(padrão: o `estado_inicial` da estação)")
    p_r.add_argument("--confirmar", action="store_true",
                     help="sem isto, só mostra o que faria")
    p_r.set_defaults(func=cmd_reiniciar)

    args = parser.parse_args(argv)
    rc = args.func(args)
    # novo-id devolve o identificador (util em teste); so' `verificar` devolve
    # codigo de saida. Sem esta guarda, sys.exit() receberia a string e o
    # comando que deu certo sairia com codigo 1.
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main())
