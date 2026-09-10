# Classificar — quando um item passa de estágio

> **Quatro passagens, quatro conjuntos de critérios.** Derivado do checklist do
> origem, que só cobria uma passagem porque lá os estágios eram três e a
> etapa de organizar acontecia invisivelmente. Com cinco estágios
> ([`taxonomia.md`](taxonomia.md)), cada passagem tem a sua pergunta.

**Antes de tudo:** nenhum item pula estágio ([regra 4](regras.md#4-nenhum-item-pula-estágio)).
Um item que já chega maduro percorre os cinco assim mesmo — as passagens podem
acontecer na mesma sessão, mas cada uma ganha identificador próprio e linha
própria no registro.

**Nunca force uma classificação.** Ficar parado num estágio por tempo
indefinido é um estado normal, não um problema. O que não pode é ficar parado
**invisível** — para isso existe o `_sem-destino.md`, que lista tudo que ainda
não avançou.

---

## O que acontece em toda passagem

Sempre estas quatro coisas, nesta ordem:

1. **Identificador novo**, pelo utilitário, com a sigla do estágio de destino:
   `python metodo/plataforma.py novo-id --raiz <plataforma> --etapa <SIGLA> --slug "..."`
2. **Cópia no estágio de destino**, com o campo `origem:` apontando para o
   identificador de onde veio.
3. **O original vai para o `_historico/`** do estágio de onde saiu — não fica
   no lugar (a pasta ativa mentiria sobre o que falta tratar) e não some.
4. **Linha nova no registro** para o item novo, e o marcador `→<novo-id>`
   acrescentado à linha antiga. A linha antiga **nunca** é editada nem apagada.

---

## Passagem 1 — Captura → Nota

**A pergunta:** isto já foi lido e organizado por um humano?

Uma captura é o que chegou: um texto colado, uma transcrição, um export, um
print. Uma nota é a mesma coisa **depois que alguém passou os olhos e deu
forma** — não precisa estar bonita, precisa estar legível.

Responda sim ou não a cada um. **Dois ou mais "sim" promovem:**

- [ ] Alguém leu isto inteiro (não é mais um "vou ver depois")
- [ ] Tem título e alguma estrutura — parágrafos, tópicos, seções
- [ ] Dá para entender do que se trata sem reler três vezes
- [ ] O que era ruído (assinatura de e-mail, timestamp, repetição) saiu

**Menos de dois:** o item continua em `1-capturas/`. Nada de errado nisso — a
caixa de entrada existe para acumular.

## Passagem 2 — Nota → Ideia

**A pergunta:** isto serve de insumo para outra coisa, sem precisar
reprocessar?

Uma nota é organizada. Uma ideia tem **forma própria**: é uma decisão, uma
primeira versão, um resumo com próximos passos — algo que outra pessoa (ou
outra sessão) consegue pegar e usar.

Responda sim ou não. **Dois ou mais "sim" promovem:**

- [ ] Tem forma definida — é um documento, não um fragmento
- [ ] Poderia ser usado como entrada de outro trabalho sem reprocessamento
- [ ] Representa uma decisão, uma v1, ou um resumo com próximos passos
- [ ] Deixou de ser ambíguo sobre o que é e para que serve

**Menos de dois:** continua em `2-notas/`, esperando ganhar forma.

## Passagem 3 — Ideia → Funcionalidade

**A pergunta:** isto já diz o que vai existir quando estiver pronto, e onde?

Uma ideia responde *o que* e *por quê*. Uma funcionalidade responde **o que
exatamente vai existir quando estiver feito, para quem, como se sabe que ficou
pronto, e em que projeto isso entra** — um que já existe, ou um novo. É a
unidade de trabalho: uma entrega só.

Responda sim ou não. **Dois ou mais "sim" promovem:**

- [ ] Descreve um comportamento ou entregável concreto — o que faz, não só o
      que resolve
- [ ] Tem **destino declarado**: o nome de um projeto que já existe, ou
      "projeto novo"
- [ ] Tem **critério de pronto**: dá para responder sim ou não se está feito
- [ ] Cabe numa entrega só — se precisa de várias, são várias funcionalidades
      (desmembre a ideia), ou é um projeto

**Menos de dois:** continua em `3-ideias/`. Uma ideia boa que ainda não sabe
onde entra é uma ideia, não uma funcionalidade mal escrita.

**Por que este estágio existe:** a maioria das ideias com forma não é projeto
novo — é peça de um projeto que já está de pé. Sem este estágio ela ficava
parada em ideia para sempre, ou virava pasta vazia em projetos. Aqui ela tem
para onde ir.

## Passagem 4 — Funcionalidade → Projeto

**A pergunta:** para onde ela vai — e, se é um projeto novo, ele tem corpo
próprio?

Esta passagem tem **dois desfechos**, decididos pelo campo `projeto:` da
funcionalidade:

### 4a — o destino é um projeto que já existe: **acoplar**

Não há promoção. A funcionalidade não vira projeto: ela **chega** ao projeto.
O que acontece (e só isto):

1. a cópia vai para `5-projetos/<projeto>/funcionalidades/`, com o **mesmo
   identificador** — não mudou de estágio;
2. o `backlog-*.md` do projeto ganha uma linha `- [ ] <título> (<identificador>)`;
3. o original vai para `4-funcionalidades/_historico/`;
4. a linha dela no registro ganha o marcador `→` com a **pasta do projeto**.

Critério único: o projeto existe e tem `CLAUDE.md`. Se não tem, ele não é
projeto, e o desfecho é o 4b.

### 4b — o destino é "projeto novo": **corpo próprio**

Corpo próprio não é "está pronto". É ter contorno de projeto: um lugar para
morar, uma lista do que falta, e histórico próprio. A funcionalidade vira a
**primeira linha do backlog** do projeto que nasce.

Aqui os critérios **não são de maioria — são os quatro, juntos:**

- [ ] Tem **pasta própria** dentro de `5-projetos/`
- [ ] Tem **`CLAUDE.md`** dizendo o que é, para quem, e em que estado está
- [ ] Tem **`backlog-<assunto>.md`** com pelo menos um item aberto de verdade —
      e o primeiro é a funcionalidade que o originou
- [ ] É um **repositório git próprio** — porque a partir daqui o trabalho
      acontece dentro dele, e cada mudança precisa de ponto salvo próprio

**Por que aqui a régua é mais alta:** promover cedo demais cria uma pasta vazia
que dá a impressão de que existe um projeto. Uma funcionalidade parada em
`4-funcionalidades/` é honesta; um projeto vazio em `5-projetos/` mente para
você toda vez que você abre o Portfólio.

---

## Quando você não consegue decidir

Não decida. Uma dúvida genuína vira **pendência** — uma pergunta objetiva, com
opções e o motivo de cada uma, que espera por você em vez de ser resolvida no
chute. O formato está em [`templates/pendencia.md`](templates/pendencia.md).

Isso vale para qualquer uma das quatro passagens, e **não desfaz** promoção já
feita: a pendência pausa a próxima, não volta a anterior.

---

## Links

- [`regras.md`](regras.md) — as regras permanentes
- [`taxonomia.md`](taxonomia.md) — os nomes e o que cada estágio é
- [`templates/`](templates/) — os modelos de cada estágio
