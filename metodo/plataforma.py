#!/usr/bin/env python3
"""Utilitário da plataforma — `novo-id`, `gerar-sem-destino`, `verificar`.

Derivado do utilitário do sistema em que a Estação nasceu, não escrito do zero: a
lógica de sequência por dia e de hash sem colisão já estava testada em uso real,
e reescrever isso só produziria bugs novos. O que mudou foi o vocabulário (os
estágios saem do `plataforma.json`, não são três siglas fixas) e o tamanho —
aqui ficaram os três comandos que qualquer plataforma precisa.

**A raiz vem por argumento.** Este script não sabe onde ele mora nem assume que
está dentro da plataforma. `--raiz` vale para todos os comandos; quando omitido,
vale a pasta atual — é assim que a Estação o chama, com o `cwd` já na raiz da
plataforma (e é o que deixa o mesmo código servir para o utilitário legado, que
não conhece esse argumento).

**A taxonomia vem do `plataforma.json` da raiz**, e só de lá. Não há padrão
embutido aqui de propósito: um segundo lugar com os nomes dos estágios seria
uma cópia a mais para divergir (o `app/config.py` já é a cópia executável de
`taxonomia.md`). Sem `plataforma.json`, este script diz isso e para.

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
# configuração da plataforma
# --------------------------------------------------------------------------

class Plataforma:
    def __init__(self, raiz: Path):
        self.raiz = raiz.resolve()
        arquivo = self.raiz / "plataforma.json"
        if not arquivo.exists():
            sys.exit(
                f"ERRO: {arquivo} não existe.\n"
                "\n"
                "Este utilitário lê a taxonomia do plataforma.json da raiz — ele não\n"
                "tem nomes de estágio embutidos, de propósito. Se esta pasta é mesmo\n"
                "uma plataforma, crie o arquivo; se você ainda não tem plataforma\n"
                "nenhuma, é a aba Embarque da Estação que cria a primeira."
            )
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
        return [e["sigla"] for e in self.estagios]

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
        siglas = "|".join(re.escape(s) for s in self.siglas)
        tipos = r"(?:-([A-Z]{2,4}))?"
        return re.compile(
            r"\b(\d{2}\.\d{2}\.\d{2})-(" + siglas + r")" + tipos +
            r"-(\d{3})-([a-z0-9-]+)-([a-f0-9]{4,5})\b")

    def ler_registro(self):
        caminho = self.caminho("registro")
        if caminho is None:
            sys.exit("ERRO: plataforma.json não declara arquivos.registro")
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
    p = Plataforma(Path(args.raiz))
    etapa = args.etapa.upper()
    if etapa not in p.siglas:
        sys.exit(f"ERRO: --etapa precisa ser uma de {p.siglas}")

    tipo = args.tipo.upper() if args.tipo else None
    if tipo and p.tipos and tipo not in [t.upper() for t in p.tipos]:
        sys.exit(f"ERRO: --tipo {tipo} não está declarado no plataforma.json "
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
    p = Plataforma(Path(args.raiz))
    destino = p.caminho("sem_destino")
    if destino is None:
        sys.exit("ERRO: plataforma.json não declara arquivos.sem_destino")

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

    texto = original = destino.read_text(encoding="utf-8")
    contagens = {}
    for sigla in p.siglas:
        chave = sigla.lower()
        itens = [l for l in sem_destino if l["etapa_tipo"].startswith(sigla)]
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
    p = Plataforma(Path(args.raiz))
    problemas, avisos = [], []

    # 1. a raiz é mesmo uma plataforma
    if not (p.raiz / p.marcador).exists():
        problemas.append(f"{p.marcador} não existe — sem porta de entrada, "
                         "a Estação não abre esta pasta")

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
    for id_, datas in por_id.items():
        if len(datas) > 1:
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

    # 5. linha no registro cujo estágio não existe na taxonomia
    for l in linhas:
        sigla = l["etapa_tipo"].split("-")[0].split(" ")[0].strip("→ ")
        if sigla and sigla not in p.siglas:
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
                          f"python plataforma.py gerar-sem-destino --raiz {p.raiz}")
        assert destino.read_text(encoding="utf-8") == antes  # dry-run não escreve

    # -- relatório --------------------------------------------------------
    print(f"Plataforma: {p.d.get('nome') or p.raiz.name}  ({p.raiz})")
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

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Utilitário de uma plataforma da Estação.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def com_raiz(p):
        p.add_argument("--raiz", default=".",
                       help="pasta da plataforma (padrão: a pasta atual)")
        return p

    p_id = com_raiz(sub.add_parser("novo-id", help="gera o próximo identificador"))
    p_id.add_argument("--etapa", required=True, help="a sigla do estágio")
    p_id.add_argument("--slug", required=True, help="duas ou três palavras do assunto")
    p_id.add_argument("--tipo", help="tipo do projeto, quanda plataforma de origem usa tipos")
    p_id.add_argument("--data", help="AA.MM.DD (padrão: hoje)")
    p_id.add_argument("--verbose", action="store_true")
    p_id.set_defaults(func=cmd_novo_id)

    p_sd = com_raiz(sub.add_parser("gerar-sem-destino",
                                   help="regenera a lista do que ainda não avançou"))
    p_sd.add_argument("--dry-run", action="store_true")
    p_sd.set_defaults(func=cmd_gerar_sem_destino)

    p_v = com_raiz(sub.add_parser("verificar", help="checa as invariantes da plataforma"))
    p_v.set_defaults(func=cmd_verificar)

    args = parser.parse_args(argv)
    rc = args.func(args)
    # novo-id devolve o identificador (util em teste); so' `verificar` devolve
    # codigo de saida. Sem esta guarda, sys.exit() receberia a string e o
    # comando que deu certo sairia com codigo 1.
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main())
