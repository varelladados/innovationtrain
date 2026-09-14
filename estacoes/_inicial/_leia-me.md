# _inicial — as estações de exemplo como elas vêm

Cópias intactas de `exemplo/` e `exemplo-precos/`. Elas existem para que
**reiniciar** funcione: `estacao.py reiniciar` deixa a estação idêntica ao
instantâneo daqui, e nada mais.

Três coisas que fazem esta pasta ser segura:

1. Ela mora **fora** das estações. Se estivesse dentro, seria apagada junto
   no primeiro reiniciar — o utilitário recusa esse caso em voz alta.
2. Ela não é uma estação ativa: nada aqui é indexado, porque o app só varre
   a raiz da estação que está aberta.
3. **Só uma estação que declara `estado_inicial` pode ser reiniciada.** Uma
   estação sua não declara, e é por isso que esse comando não tem como
   apagar o seu trabalho.

Mexeu de propósito no exemplo e quer que a mudança vire o novo ponto de partida?
Copie a estação por cima da cópia daqui, num commit próprio.
