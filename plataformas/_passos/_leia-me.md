# _passos — a trilha das plataformas de exemplo

Cada pasta aqui é **a plataforma inteira num estado adiante**. "Avançar a
trilha", no app, não promove nada: ele restaura o próximo instantâneo daqui.

É de propósito que não haja motor de promoção. Numa plataforma de verdade a
passagem entre estágios é decisão (os critérios de `metodo/classificar.md`) e
escrita (o texto do estágio novo) — as duas coisas que um botão não faz. O que a
trilha mostra é **como fica**, não como se automatiza.

O passo atual não é guardado em lugar nenhum: `app/trilha.py` o deduz comparando
o `_registro.md` da plataforma com o de cada instantâneo. Mexeu à mão? A trilha
diz "fora dos passos", que é a resposta honesta.

Só uma plataforma que declara `estado_inicial` pode ser restaurada — e uma
plataforma sua não declara.
