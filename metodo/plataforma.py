"""O nome que o utilitário teve até a 0.9 — hoje ele é `estacao.py`.

Continua existindo porque há estações de fora deste repositório que o chamam
por este caminho, declarado na chave `utilitario` da config delas. Não
acrescente nada aqui: tudo mora em `estacao.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estacao import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
