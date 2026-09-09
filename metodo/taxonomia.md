# Taxonomia de uma plataforma

> **Este documento é a fonte única dos nomes.** Todo nome de estágio, sigla,
> arquivo de sistema e tipo de projeto sai daqui. O código não repete essas
> strings: ele lê do `plataforma.json` de cada plataforma, e os padrões de
> `app/config.py` são uma cópia deste documento, não uma segunda opinião.
>
> Decidido em 2026-09-08 (Trecho 2 do `plano-hub-estacao-e-embarque-2026-09-08.md`),
> em cinco paradas respondidas pelo usuário. Se algum nome mudar, três coisas
> mudam **juntas**: este arquivo, o `plataforma.json` de cada plataforma e os
> padrões do `app/config.py`.

---

## Os quatro estágios

Uma ideia não nasce pronta. Ela chega, é organizada, ganha forma e — às vezes —
vira trabalho de verdade. Os quatro estágios são esses quatro momentos, e a
numeração das pastas carrega a sequência.

| # | Pasta | Nome | Sigla | O que é |
|---|---|---|---|---|
| 1 | `1-capturas/` | **Captura** | `CAP` | chegou e ninguém tratou — colado, transcrito, importado, fotografado |
| 2 | `2-notas/` | **Nota** | `NOT` | foi lida e organizada; já dá para entender sem esforço |
| 3 | `3-ideias/` | **Ideia** | `IDE` | tem forma própria e serve de insumo para outra coisa sem reprocessar |
| 4 | `4-projetos/` | **Projeto** | `PRJ` | ganhou corpo próprio: pasta, backlog, git |

A separação entre **1** e **2** é a novidade em relação ao `plataforma de origem`, onde
organizar a nota crua acontecia invisivelmente dentro do mesmo estágio. Ela
existe porque "colei um texto" e "esse texto está legível" são dois estados
diferentes, e confundi-los faz a caixa de entrada parecer resolvida quando não
está.

**Nenhum item pula estágio.** Uma ideia que já nasce madura passa pelos quatro
mesmo assim — as quatro passagens podem acontecer na mesma sessão, minutos uma
depois da outra, mas cada uma ganha identificador próprio e linha própria no
registro. Passagem rápida não é passagem sem registro.

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
│   └── _historico/     ideias que já viraram projeto
└── 4-projetos/
    ├── _historico/     projetos encerrados
    └── <nome-do-projeto>/
        ├── CLAUDE.md
        └── backlog-<assunto>.md
```

Projetos moram **dentro** de `4-projetos/`, sem prefixo no nome — o que está
ali é projeto, e o tipo é um campo no `CLAUDE.md`, não três letras no nome da
pasta.

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
| 2 — sigla no identificador | `CAP` / `NOT` / `IDE` / `PRJ` | três letras se lêem de relance no meio do nome do arquivo e o formato do identificador não muda, o que deixa o utilitário ser derivado do `plataforma.py` existente em vez de reescrito |
| 3 — avançar move ou copia | **copia**, e o original vai para `_historico/` do estágio | preserva o texto de cada estágio sem depender do git para relê-lo, e ainda assim deixa a parte ativa da pasta esvaziar — que é o que a faz responder "tem coisa por tratar?" de relance |
| 4 — tipos de projeto | livres, declarados no `plataforma.json` | cada pessoa classifica o próprio trabalho, e o filtro do Portfólio sai do config em vez de uma lista fixa que envelhece |
| 5 — nomes de sistema | `_indice.md` · `_registro.md` · `_sem-destino.md` · `_historico/` · `plataforma.json` | o `_` marca "isto é maquinário, não conteúdo seu" e agrupa no topo da listagem; o `plataforma de origem` usava ponto, que *esconde* a pasta em boa parte das ferramentas. `plataforma.json` fica sem `_` porque a extensão já o separa |

---

## De-para: `C:\Plataforma` → plataforma genérica

O `C:\Plataforma` continua funcionando como está — ele entra no `estacao.json` do hub
como plataforma legada, com a taxonomia antiga declarada lá, e **não recebe
arquivo novo**. Esta tabela existe para ler um ao lado do outro, não para migrar.

| `C:\Plataforma` (caso aplicado) | Plataforma genérica | Observação |
|---|---|---|
| Captura crua (`SBC`) | **Captura** (`CAP`) **e** Nota (`NOT`) | o estágio antigo se divide em dois: o que chegou e o que foi organizado |
| Ideia (`SBI`) | **Ideia** (`IDE`) | |
| Projeto (`SBZ`) | **Projeto** (`PRJ`) | |
| `1-capturas/` | `1-capturas/` + `2-notas/` | |
| `3-ideias/<id>/<id>.md` | `3-ideias/` | |
| `4-projetos/` (só índice) + pastas soltas na raiz | `4-projetos/<nome>/` | os projetos passam a morar dentro da pasta que os anuncia |
| `.entrada/` (sem linha no LOG) | — | deixa de existir: tudo que entra ganha linha no registro na hora |
| `.pendente/` (linha sem `→`) | a própria pasta do estágio | |
| `.historico/` (linha com `→`) | `_historico/` de cada estágio | agora existe nos quatro estágios, não só no primeiro |
| `_indice.md` e `_indice.md` | `_indice.md` | dois pontos de entrada disputando viram um |
| `1-capturas/LOG/_log.md` | `_registro.md` | mesmo contrato: append-only |
| `1-capturas/pendentes.md` | `_sem-destino.md` | gerado, não editado à mão |
| prefixos `PJC` `PJD` `PJI` `PJP` `PRA` `PRD` `PRJ` | eliminados | sem significado documentado; o tipo vira campo no `CLAUDE.md` |
| tipos `DIG` (digital) `DAD` (dados) `CON` (consultoria) `ADE` (adestramento) | `tipos` no `plataforma.json` | |
| `o-*.md` ("orquestra") | `_indice.md` da pasta | |
| "índice" | `_indice.md` da plataforma | |
| `_metodo/doutrina.md` | `metodo/regras.md` | sai da plataforma, vai para o hub |
| `_metodo/templates/checklist-classificacao.md` | `metodo/classificar.md` | |
| `_metodo/templates/` | `metodo/templates/` | |
| `_metodo/` | `metodo/` | método é genérico; não mora dentro de um caso aplicado |
| `_ferramentas/` | hub | ferramenta que serve toda plataforma não mora dentro de uma |
| `_ferramentas/scripts/plataforma.py` | `metodo/plataforma.py` | derivado, não reescrito |
| `PRJ-Estacao/` | `app/` no hub | a aplicação não é conteúdo de plataforma |
| `.Biblioteca/` | — | acervo externo; a doutrina já a mantinha fora das regras de linhagem |
| campo `parte_do_nucleo:` | — | distinguia sistema de conteúdo; no hub a separação é física |
| Captura / Ideia / Projeto / Método | — | vocabulário privado do caso aplicado; não viaja para o produto |

**Metáfora ferroviária — os únicos termos:** *Estação* (a aplicação),
*plataforma* (um espaço de trabalho), *projeto* (um trabalho dentro dela),
*trem* (a fila de pendências passando uma por vez) e *embarque* (os primeiros
passos). Não invente outros: chamar prompt de "bilhete" ou projeto de "vagão"
recria exatamente o vocabulário privado que este trabalho desfaz.

---

## O que este documento ainda não decide

- **Os critérios de promoção** entre os estágios — são três conjuntos
  (captura→nota, nota→ideia, ideia→projeto) e vivem em
  [`classificar.md`](classificar.md).
- **As cores de cada estágio** — decisão do design system, no Trecho 4.
- **O `plataforma.json` do `plataforma de origem`** — ele não recebe arquivo nenhum; a
  taxonomia antiga é declarada inline no `estacao.json` do hub (Trecho 3).
