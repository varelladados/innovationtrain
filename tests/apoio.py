"""Apoio dos testes: montar uma plataforma temporária e ativá-la.

Desde o Trecho 3 os módulos não têm mais constantes de caminho — eles leem
`config.atual()` na hora da chamada. Então o teste não monkeypatcha atributo de
módulo: ele **aplica uma configuração**, que é o mesmo caminho que o servidor
usa de verdade. Isso é mais fiel e sobrevive a refatoração de nome de variável.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import config  # noqa: E402


def aplicar(raiz, **taxonomia):
    """Ativa uma plataforma em `raiz`, com as sobrescritas dadas.

    Cria o arquivo marcador se ele ainda não existir, para que `plataforma_ok`
    seja verdadeiro — o teste que quer o modo degradado passa `marcador` para um
    nome que não existe.
    """
    raiz = Path(raiz)
    cfg = config.carregar(raiz, taxonomia or {})
    marcador = raiz / cfg.marcador
    if not marcador.exists() and marcador.parent.exists():
        marcador.write_text("# plataforma de teste\n", encoding="utf-8")
    return config.aplicar(cfg)


def qualquer_pasta_e_projeto():
    """Sobrescrita comum: a raiz inteira é a pasta de projetos e não há prefixo.

    Vale para os testes que criam `<tmp>/<projeto>/` direto, sem a árvore
    numerada dos quatro estágios.
    """
    return {"projetos": {"pasta": "", "prefixo_re": None}}
