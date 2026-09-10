# Taxonomia de uma plataforma

> **Este documento é a fonte única dos nomes.** Todo nome de estágio, sigla,
> arquivo de sistema e tipo de projeto sai daqui. O código não repete essas
> strings: ele lê do `plataforma.json` de cada plataforma, e os padrões de
> `app/config.py` são uma cópia deste documento, não uma segunda opinião.
>
> Decidido em 2026-09-08 (Trecho 2 do `plano-hub-estacao-e-embarque-2026-09-08.md`),
> em cinco paradas respondidas pelo usuário. O estágio 4, **Funcionalidade**,
> entrou em 2026-09-10 (sexta parada, abaixo). Se algum nome mudar, três coisas
> mudam **juntas**: este arquivo, o `plataforma.json` de cada plataforma e os
> padrões do `app/config.py`.

---

## Os cinco estágios

Uma ideia não nasce pronta. Ela chega, é organizada, ganha forma, diz o que vai
existir quando estiver pronta e — às vezes — vira trabalho de verdade. Os cinco
estágios são esses cinco momentos, e a numeração das pastas carrega a
sequência.

| # | Pasta | Nome | Sigla | O que é |
|---|---|---|---|---|
| 1 | `1-capturas/` | **Captura** | `CAP` | chegou e ninguém tratou — colado, transcrito, importado, fotografado |
| 2 | `2-notas/` | **Nota** | `NOT` | foi lida e organizada; já dá para entender sem esforço |
| 3 | `3-ideias/` | **Ideia** | `IDE` | tem forma própria e serve de insumo para outra coisa sem reprocessar |
| 4 | `4-funcionalidades/` | **Funcionalidade** | `FUN` | diz o que vai existir quando estiver pronta, para quem, como se sabe que ficou pronta — e **onde entra**: num projeto que já existe, ou num projeto novo |
| 5 | `5-projetos/` | **Projeto** | `PRJ` | ganhou corpo próprio: pasta, backlog, git |

A separação entre **1** e **2** é o ponto em que esta taxonomia se distingue
das que juntam as duas coisas num estágio só. Ela existe porque "colei um
texto" e "esse texto está legível" são dois estados diferentes, e confundi-los
faz a caixa de entrada parecer resolvida quando não está.

A separação entre **3** e **5** é o outro ponto, e ela existe por um motivo
parecido: a maior parte das ideias que têm forma **não é um projeto novo** — é
uma peça de um projeto que já existe. Sem um estágio entre os dois, essa ideia
ou ficava parada em `3-ideias/` para sempre, ou virava uma pasta vazia em
projetos que mentia sobre o que existe. A **funcionalidade** é a unidade de
trabalho: uma entrega só, com critério de pronto, que ou se **acopla** a um
projeto existente ou é a **semente** de um projeto novo — a primeira
funcionalidade dele.

**Nenhum item pula estágio.** Uma ideia que já nasce madura passa pelos cinco
mesmo assim — as passagens podem acontecer na mesma sessão, minutos uma depois
da outra, mas cada uma ganha identificador próprio e linha própria no registro.
Passagem rápida não é passagem sem registro.

Os critérios de cada passagem estão em [`classificar.md`](classificar.md).

---

## Estrutura de uma plataforma

```
<plataforma>/
├── _indice.md          porta de entrada única — o que é esta plataforma
├── _registro.md        o registro, append-only: uma linha por item
├── _sem-destino.md     gerado: o que está no registro e ainda não avançou
├── plataforma.json     nome + taxonomia desta plataforma
├── 1-capturas/
│   └── _historico/     capturas que já viraram nota
├── 2-notas/
│   └── _historico/     notas que já viraram ideia
├── 3-ideias/
│   └── _historico/     ideias que já viraram funcionalidade
├── 4-funcionalidades/
│   └── _historico/     funcionalidades que já viraram projeto, ou já entraram num
└── 5-projetos/
    ├── _historico/     projetos encerrados
    └── <nome-do-projeto>/
        ├── CLAUDE.md
        ├── backlog-<assunto>.md
        └── funcionalidades/   as que foram acopladas a este projeto (ver abaixo)
```

Projetos moram **dentro** de `5-projetos/`, sem prefixo no nome — o que está
ali é projeto, e o tipo é um campo no `CLAUDE.md`, não três letras no nome da
pasta.

Uma funcionalidade **acoplada** a um projeto que já existe mora dentro dele, em
`funcionalidades/`, com o **mesmo identificador** que tinha em
`4-funcionalidades/` — ela não mudou de estágio, chegou ao destino. A pasta é
opcional: um projeto que nunca recebeu funcionalidade não a tem.

`CLAUDE.md` e `backlog-*.md` **não mudam** dentro dos projetos: o primeiro é
nome fixo do harness, o segundo já é claro.

---

## O identificador

```
26.09.08-CAP-001-braindump-do-onibus-a3f2
│        │   │   │                    └── hash curto, evita colisão
│        │   │   └── slug legível
│        │   └── sequência dentro do dia
│        └── sigla do estágio
└── data (AA.MM.DD)
```

Identificador só se gera pelo utilitário
([`plataforma.py`](plataforma.py) `novo-id`), nunca à mão — é ele que sabe qual
é a próxima sequência do dia e garante que o hash não repete.

---

## Como um item avança

Quando um item passa de estágio, três coisas acontecem, nesta ordem:

1. **Uma cópia** dele é criada no estágio seguinte, com **identificador novo**
   (sigla nova, sequência do dia novo).
2. **O original vai para o `_historico/`** do estágio de onde saiu. Ele não fica
   no lugar (a pasta ativa mentiria sobre o que ainda falta tratar) e não some
   (o texto de cada estágio se preserva exatamente como estava).
3. **O registro ganha uma linha nova** para o item novo, com o marcador de
   linhagem apontando para a origem. A linha antiga **nunca** é editada nem
   apagada — o registro é append-only.

**A exceção é a funcionalidade que entra num projeto que já existe.** Ela não
muda de estágio, então não ganha identificador novo nem linha nova: a cópia vai
para `5-projetos/<projeto>/funcionalidades/` com o mesmo identificador, o
backlog do projeto ganha uma linha `- [ ]` apontando para ela, o original vai
para `4-funcionalidades/_historico/`, e a linha dela no registro ganha o
marcador `→` com a **pasta do projeto** como destino. É a mesma mecânica de
"chegou ao destino" — só que o destino já estava de pé.

Consequência que vale saber de antemão: a parte ativa de `1-capturas/` fica
vazia quando tudo foi tratado. Isso é o sinal de que a caixa de entrada está
zerada, não um problema.

---

## Tipos de projeto

Cada plataforma declara os seus, na chave `tipos` do `plataforma.json`. Não há
lista fixa no produto. A sugestão inicial, para quem não quer decidir agora:

```json
"tipos": ["app", "dados", "serviço", "curso"]
```

O filtro de tipo do Portfólio é montado a partir dessa lista — então ele nunca
oferece um tipo que ninguém usa nem esconde um que todo mundo usa.

---

## As cinco decisões, e por quê

| Parada | Decidido | Por quê |
|---|---|---|
| 1 — nomes dos estágios | Capturas · Notas · Ideias · Projetos | palavra única em vez de "notas cruas / notas estruturadas": a progressão se lê sozinha (chegou → organizei → tomou forma → está sendo feito) e "Captura" cobre o que vem de fora — export, transcrição, print — que "rascunho" não cobre |
| 2 — sigla no identificador | `CAP` / `NOT` / `IDE` / `PRJ` | três letras se lêem de relance no meio do nome do arquivo e o formato do identificador não muda, o que deixa o utilitário ser derivado do que já existia em vez de reescrito |
| 3 — avançar move ou copia | **copia**, e o original vai para `_historico/` do estágio | preserva o texto de cada estágio sem depender do git para relê-lo, e ainda assim deixa a parte ativa da pasta esvaziar — que é o que a faz responder "tem coisa por tratar?" de relance |
| 4 — tipos de projeto | livres, declarados no `plataforma.json` | cada pessoa classifica o próprio trabalho, e o filtro do Portfólio sai do config em vez de uma lista fixa que envelhece |
| 5 — nomes de sistema | `_indice.md` · `_registro.md` · `_sem-destino.md` · `_historico/` · `plataforma.json` | o `_` marca "isto é maquinário, não conteúdo seu" e agrupa no topo da listagem; um prefixo com ponto *esconde* a pasta em boa parte das ferramentas. `plataforma.json` fica sem `_` porque a extensão já o separa |
| 6 — o estágio entre ideia e projeto (2026-09-10) | **Funcionalidade** · `FUN` · `4-funcionalidades/`; projetos passam a `5-projetos/` | a plataforma de origem mediu, em uso real, que a maioria das ideias com forma era peça de projeto existente, não projeto novo — e não tinha para onde ir. O nome vem do fluxo literal escolhido lá (captura › anotação › ideia › funcionalidade › projeto); a sigla segue a regra das outras quatro (três primeiras letras). A pasta de projetos foi renumerada porque a numeração carrega a sequência — manter `4-projetos/` ao lado de `4-funcionalidades/` diria que os dois são o mesmo momento |

---

**Metáfora ferroviária — os únicos termos:** *Estação* (a aplicação),
*plataforma* (um espaço de trabalho), *projeto* (um trabalho dentro dela),
*trem* (a fila de pendências passando uma por vez) e *embarque* (os primeiros
passos). Não invente outros: chamar prompt de "bilhete" ou projeto de "vagão"
recria exatamente o vocabulário privado que este trabalho desfaz.

---

## O que este documento ainda não decide

- **Os critérios de promoção** entre os estágios — são quatro conjuntos
  (captura→nota, nota→ideia, ideia→funcionalidade, funcionalidade→projeto) e
  vivem em [`classificar.md`](classificar.md).
- **As cores de cada estágio** — decisão do design system, no Trecho 4.
- **O `plataforma.json` de uma plataforma que não pode receber arquivo novo**
  — uma pasta lida em modo somente-leitura, por exemplo. A taxonomia dela é
  declarada inline no `estacao.json` do hub (Trecho 3), e nada é escrito lá
  dentro.
