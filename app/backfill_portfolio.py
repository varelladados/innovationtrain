"""Semeia `portfolio.json` nas Projetos que ainda não têm, a partir dos perfis da
rodada de portfólio (`_metodo/portfolio/perfis/<projeto>.json`, 2026-09-05).

Fecha a Frente 4 do plano de 2026-09-06 ("Produção = link"): a aba Portfólio já
lê curadoria de `portfolio.json`, mas só 2 dos 16 projetos tinham o arquivo — o
resto caía inteiro na heurística. O dado pra preencher já existia; faltava passar
de um lugar pro outro.

Conservador de propósito:
- **nunca sobrescreve** um `portfolio.json` existente (a curadoria manual manda);
- escreve só `tags`, `nota` e `repo_publico: false` — nada de `estavel`/`destaque`,
  que dependem de julgamento de qual artefato é a peça boa;
- `--dry-run` é o padrão; `--write` é explícito;
- **não commita** — cada Projeto tem repo próprio, revisão é do usuário.

    python app/backfill_portfolio.py            # mostra o que faria
    python app/backfill_portfolio.py --write    # grava
"""
import argparse
import json
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent.parent
PERFIS_DIR = ROOT / "_metodo" / "portfolio" / "perfis"
PASTA_RE = re.compile(r"^(PJ|PR)[A-Z]-")
MAX_NOTA = 200


def candidatos():
    """(pasta, perfil, destino) de cada Projeto sem portfolio.json."""
    if not PERFIS_DIR.exists():
        return []
    achados = []
    for perfil_path in sorted(PERFIS_DIR.glob("*.json")):
        nome = perfil_path.stem
        if not PASTA_RE.match(nome):
            continue  # perfis de coisas que não são pasta de Projeto (ex.: _metodo)
        pasta = ROOT / nome
        if not pasta.is_dir():
            continue
        destino = pasta / "portfolio.json"
        if destino.exists():
            continue
        try:
            perfil = json.loads(perfil_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"  ! {nome}: perfil ilegível ({e})")
            continue
        achados.append((nome, perfil, destino))
    return achados


def semear(perfil):
    nota = (perfil.get("proposta_de_valor") or "").strip()
    if len(nota) > MAX_NOTA:
        corte = nota.rfind(" ", 0, MAX_NOTA)
        nota = nota[:corte if corte > 0 else MAX_NOTA].rstrip() + "…"
    dados = {"tags": perfil.get("dominios", []), "repo_publico": False}
    if nota:
        dados["nota"] = nota
    return dados


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="grava de verdade (o padrão é só mostrar)")
    args = ap.parse_args()

    achados = candidatos()
    if not achados:
        print("Nada a fazer: toda Projeto com perfil já tem portfolio.json.")
        return 0

    print(f"{len(achados)} projeto(s) sem portfolio.json:\n")
    for pasta, perfil, destino in achados:
        dados = semear(perfil)
        print(f"  {pasta}")
        print(f"    tags: {dados['tags']}")
        if dados.get("nota"):
            print(f"    nota: {dados['nota'][:90]}…")
        if args.write:
            destino.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"    -> escrito em {destino.relative_to(ROOT)}")
    if not args.write:
        print("\n[dry-run] nada foi escrito. Rode com --write pra gravar.")
    else:
        print("\nEscrito. Revise e commite em cada repo — este script nunca commita.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
