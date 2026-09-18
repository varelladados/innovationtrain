# Roteiros para apresentar o método

Três formatos, para três públicos. Os três seguem o [princípio 7](../metodo/principios.md):
o que só quem apresenta sabe — mercado, números, modelo de negócio, time — fica
marcado **[PREENCHER]** e é preenchido com dado real na hora de apresentar,
nunca estimado aqui.

---

## 1. Executivo — uma página

Para quem decide em três minutos se quer uma segunda conversa. Sem slide, sem
animação: um documento que se lê de cima a baixo.

1. **O que é** (duas frases) — um método para levar ideia bruta até projeto com
   corpo próprio, em cinco estágios, com um app local que opera tudo sem abrir
   sessão de IA e um motor que aprende com cada estação.
2. **O problema** (um parágrafo) — ideias morrem por falta de processo (viram
   fragmento esquecido) ou por processo demais (a burocracia mata a
   velocidade). O método resolve os dois lados: cinco estágios, rastro
   obrigatório, uma triagem antes de qualquer coisa entrar, e o "matar" como
   desfecho legítimo.
3. **A prova** (um caso real, com números) — a estação de quem apresenta:
   **[PREENCHER]** projetos ativos, itens no registro, padrões promovidos para o
   método.
4. **O que diferencia** (três pontos) — mede o disco, não a intenção; a decisão
   fica escrita e esperando o dono, em vez de acontecer em silêncio; nasce como
   código versionado e testado, não como slide de metodologia.
5. **O pedido** (uma frase) — **[PREENCHER]**: uma reunião, um piloto, um
   investimento.

---

## 2. Pitch — de 10 a 12 slides

1. **Título** — nome e uma linha de posicionamento.
2. **Propósito** — uma frase: por que isto existe.
3. **Problema** — ideias morrem em dois pontos previsíveis: sem processo, ou
   com processo demais; e times reinventam a mesma solução em paralelo por não
   terem um lugar para os padrões que já se provaram.
4. **Por que agora** — a IA tornou barato manter rastro e estrutura em cada
   ideia; antes, era trabalho manual demais para valer a pena.
5. **Solução** — os cinco estágios, as quatro passagens, a triagem na entrada e
   a promoção de padrões entre estação e método. Um diagrama vale mais que o
   texto aqui.
6. **Tamanho de mercado** — **[PREENCHER]** com dado real.
7. **Produto** — o app ao vivo: uma nota passando pela triagem, uma pendência
   respondida, o portfólio lido do disco.
8. **Modelo de negócio** — **[PREENCHER]**; é decisão do dono, não se infere.
9. **Concorrência** — o que o método conscientemente não é: *stage-gate* (mais
   pesado, com aprovação formal a cada estágio), sistemas de arquivamento de
   notas (arquivam, não amadurecem), estúdios tradicionais (funil sem software
   por trás).
10. **Time** — **[PREENCHER]**.
11. **Tração** — **[PREENCHER]** com os números reais da estação em uso, nunca
    com projeção.
12. **Pedido** — o que se pede nesta rodada.

---

## 3. Técnico — requisito, desenho, verificação

Uma revisão de desenho enxuta, para apresentar a arquitetura a quem vai
construir junto.

1. **Objetivo** — o problema de engenharia: estruturar conhecimento
   reaproveitável entre estações sem que elas se afastem do método sem ninguém
   ver.
2. **Restrições** — sem servidor central (arquivos em disco, versionados em
   git); sem depender de uma única ferramenta de IA; nenhuma decisão de
   promoção ou de classificação automática; o app nunca executa git.
3. **Requisitos, com rastreabilidade:**

   | Requisito | De onde vem | Implementado por |
   |---|---|---|
   | Todo item tem proveniência | princípio 2 | identificador pelo utilitário e registro append-only |
   | Nenhuma promoção automática | princípio 6 | os três critérios de [`promocao.md`](../metodo/promocao.md), decisão sempre humana |
   | A voz de uma estação não vaza para o genérico | princípio 5 | nomes declarados no `estacao.json`, nunca no código; guarda-corpo de publicação |
   | Toda etapa pode terminar em "matar" | princípio 4 | histórico em cada estágio; apagar é sempre lógico |
   | Nada entra sem triagem | regra 9 | o portão da aba Nota e a espera na estação privada |

4. **Arquitetura** — estações (pastas com a própria configuração) ↔ a Central
   (lê na hora da chamada, escreve só com trava, backup e concorrência
   otimista) ↔ o método (`metodo/`). Nenhum acoplamento em tempo de execução
   entre estação e método: a ponte é o changelog e uma checagem periódica do
   lado da estação.
5. **Decisões e alternativas descartadas** — por que o nome da estação vem da
   configuração e não de constante; por que o app gera o texto do commit mas
   não o executa; por que a trilha de exemplo restaura instantâneos em vez de
   promover itens.
6. **Estrutura** — a árvore do repositório ([`../CENTRAL.md`](../CENTRAL.md),
   seção Estrutura) e a de uma estação ([`../metodo/taxonomia.md`](../metodo/taxonomia.md)).
7. **Verificação** — a suíte de testes, o CI em Linux e Windows, o guarda-corpo
   de publicação e o `estacao.py verificar` de cada estação.
8. **Roteiro técnico** — **[PREENCHER]** conforme a prioridade do dono.
