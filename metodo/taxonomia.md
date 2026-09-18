# Taxonomia de uma estação

> **Este documento é a fonte única dos nomes.** Todo nome de estágio, sigla,
> arquivo de sistema e tipo de projeto sai daqui. O código não repete essas
> strings: ele lê do `estacao.json` de cada estação, e os padrões de
> `app/config.py` são uma cópia deste documento, não uma segunda opinião.
>
> Decidido em 2026-09-08 (Trecho 2 do plano do hub e do Embarque, papel de
> trabalho que não é versionado), em cinco paradas respondidas pelo usuário. O estágio 4, **Funcionalidade**,
> entrou em 2026-09-10 (sexta parada, abaixo). Se algum nome mudar, três coisas
> mudam **juntas**: este arquivo, o `estacao.json` de cada estação e os
> padrões do `app/config.py`.

---

## As estações de uma Central

Uma **Central** opera várias estações, e toda Central começa com três. As três
são trens — o que muda é o tamanho do trem e para que ele serve.

| Estação | Pasta | Estágios | Privada | Para quê |
|---|---|---|---|---|
| **Plataforma** | `plataforma/` | os cinco | não | O trem de inovação: ideias que podem virar funcionalidade, projeto e solução para outras pessoas. |
| **Admin_empresa** | `admin_empresa/` | captura, nota, ideia | não | A burocracia da empresa: RH, impostos, jurídico, contábil e tributário, financeiro. |
| **Vida_Pessoal** | `vida_pessoal/` | captura, nota, ideia | **sim** | A vida fora do trabalho: deveres civis, família, tarefas, rotinas, lazer, amigos, a festa aqui em casa. |

A Admin_empresa é, por enquanto, o mesmo trem da Vida_Pessoal com outro
propósito. Uma estação de três estágios usa os três primeiros da seção abaixo —
os mesmos nomes, pastas e siglas.

Cada estação diz qual modelo segue na chave `modelo` do `estacao.json`. Sem a
chave vale `plataforma`, que é o que toda estação era antes de existirem as
outras duas. A estação sem estágio de projetos declara `"projetos": null` — e é
isso que tira dela o Portfólio. Não confundir com `"pasta": ""`, que diz outra
coisa: os projetos moram na raiz.

O Embarque cria as três lado a lado, numa pasta que você escolhe. A sugestão é
`estacoes/` dentro da própria Central, que o `.gitignore` deixa de fora: o que
está ali é conteúdo seu, não do produto. Quem já tem uma delas informa o
caminho, e ela é só registrada.

### A Vida_Pessoal é privada

**Nunca versionada, nunca compartilhada.** Sem `git init`, sem commit, sem
remoto. O snapshot estático e a vitrine recusam exportá-la, e a aba Versões diz
"não versionada, de propósito" em vez de oferecer criar repositório. O backup
dela é cópia de pasta.

É individual: cada pessoa tem a sua. A Central não precisa saber quem é quem
para isso valer — basta que nada dali saia.

### Passagem entre estações

Uma ideia da Vida_Pessoal ou da Admin_empresa pode ser solução para outras
pessoas. Quando é, ela alimenta uma **captura nova na Plataforma**. Não é um
estágio a mais nem um botão: é o que acontece em toda passagem — decisão e
escrita.

- a captura na Plataforma é **reescrita** para quem é de fora: nada da estação
  de origem vai literal;
- ela nasce com identificador e linha próprios no registro da Plataforma;
- a linhagem cita a estação e o identificador de origem — e, se o identificador
  disser demais sobre alguém, cita só a estação;
- a ideia de origem **fica onde está**: ela não mudou de estágio.

O critério de quando uma ideia serve a outras pessoas está em
[`classificar.md`](classificar.md).

### Triagem — a passagem no sentido contrário

A passagem acima leva uma ideia pessoal para o trabalho, reescrita. A
**triagem** impede o caminho inverso sem querer: toda entrada bruta espera em
`_triagem/`, **dentro da Vida_Pessoal**, até responder se é trabalho ou vida
pessoal e se carrega dado de outra pessoa ou segredo. Só então ganha
identificador — na estação certa. Não é estágio: não tem sigla, identificador
nem linha no registro.

Cada estação declara na chave `triagem` do `estacao.json` onde fica a espera e
o **de-para** dos seus projetos (esfera e apelidos); as que o Embarque cria já
nascem com a espera declarada. O método inteiro está em
[`triagem.md`](triagem.md).

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

## Estrutura de uma estação

```
<estação>/
├── _indice.md          porta de entrada única — o que é esta estação
├── _registro.md        o registro, append-only: uma linha por item
├── _sem-destino.md     gerado: o que está no registro e ainda não avançou
├── estacao.json        nome + taxonomia desta estação
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
([`estacao.py`](estacao.py) `novo-id`), nunca à mão — é ele que sabe qual
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

## Quando a estação já tinha acervo — `siglas_legadas`

Uma estação que adota a Central depois de anos de uso chega com
identificadores já emitidos, numa taxonomia própria, num registro que é
append-only e com a sigla embutida em nome de pasta. Reescrever tudo custaria
caro e mentiria sobre o histórico; ignorar as siglas antigas faria cada linha
antiga virar "estágio desconhecido".

A chave `siglas_legadas` mapeia cada sigla antiga para o **número** do estágio a
que ela corresponde hoje:

```json
"siglas_legadas": {"SBC": 2, "SBI": 3, "SBZ": 5}
```

Mapeia para o número, e não para a posição, porque os dois vocabulários podem
ter tamanhos diferentes — no exemplo acima a taxonomia antiga tinha três
estágios e o último dela salta para o quinto de hoje, porque o de funcionalidade
não existia lá.

**A fronteira é entre ler e escrever**, e ela é o ponto todo:

| | Sigla legada |
|---|---|
| registro, nome de arquivo, `_sem-destino.md`, `verificar`, métricas, cores | **é lida** — cai no estágio de hoje |
| identificador novo (`novo-id`) | **é recusada** — item novo nasce com o vocabulário de hoje |

Sem a segunda metade, a taxonomia antiga nunca terminaria de sair: um item novo
nasceria com a sigla que a migração veio aposentar. O histórico fica bilíngue de
propósito; o futuro, não.

### O acervo também chega com as marcas do tempo sem regra

Mesma ideia, outra chave: `duplicatas_historicas` lista identificadores que já
chegaram repetidos, de antes de a estação ter a convenção do sufixo `-N`.

```json
"duplicatas_historicas": ["26.08.31-XXX-062-assunto-d1ea"]
```

Declarar **não resolve** a duplicata: rebaixa de PROBLEMA para AVISO e a mantém
à vista, nominalmente. A tolerância vale para o identificador declarado, nunca
para a prática — repetir um identificador novo continua sendo problema.

Por que existe: exigir que o passado seja reescrito para o `verificar` ficar
verde é o caminho mais curto para ninguém mais rodar o `verificar`. Um alarme
que sempre toca deixa de ser alarme.

## Tipos de projeto

Cada estação declara os seus, na chave `tipos` do `estacao.json`. Não há
lista fixa no produto. A sugestão inicial, para quem não quer decidir agora:

```json
"tipos": ["app", "dados", "serviço", "curso"]
```

O filtro de tipo do Portfólio é montado a partir dessa lista — então ele nunca
oferece um tipo que ninguém usa nem esconde um que todo mundo usa.

---

## As sete decisões, e por quê

| Parada | Decidido | Por quê |
|---|---|---|
| 1 — nomes dos estágios | Capturas · Notas · Ideias · Projetos | palavra única em vez de "notas cruas / notas estruturadas": a progressão se lê sozinha (chegou → organizei → tomou forma → está sendo feito) e "Captura" cobre o que vem de fora — export, transcrição, print — que "rascunho" não cobre |
| 2 — sigla no identificador | `CAP` / `NOT` / `IDE` / `PRJ` | três letras se lêem de relance no meio do nome do arquivo e o formato do identificador não muda, o que deixa o utilitário ser derivado do que já existia em vez de reescrito |
| 3 — avançar move ou copia | **copia**, e o original vai para `_historico/` do estágio | preserva o texto de cada estágio sem depender do git para relê-lo, e ainda assim deixa a parte ativa da pasta esvaziar — que é o que a faz responder "tem coisa por tratar?" de relance |
| 4 — tipos de projeto | livres, declarados no `estacao.json` | cada pessoa classifica o próprio trabalho, e o filtro do Portfólio sai do config em vez de uma lista fixa que envelhece |
| 5 — nomes de sistema | `_indice.md` · `_registro.md` · `_sem-destino.md` · `_historico/` · `estacao.json` | o `_` marca "isto é maquinário, não conteúdo seu" e agrupa no topo da listagem; um prefixo com ponto *esconde* a pasta em boa parte das ferramentas. `estacao.json` fica sem `_` porque a extensão já o separa |
| 6 — o estágio entre ideia e projeto (2026-09-10) | **Funcionalidade** · `FUN` · `4-funcionalidades/`; projetos passam a `5-projetos/` | a estação de origem mediu, em uso real, que a maioria das ideias com forma era peça de projeto existente, não projeto novo — e não tinha para onde ir. O nome vem do fluxo literal escolhido lá (captura › anotação › ideia › funcionalidade › projeto); a sigla segue a regra das outras quatro (três primeiras letras). A pasta de projetos foi renumerada porque a numeração carrega a sequência — manter `4-projetos/` ao lado de `4-funcionalidades/` diria que os dois são o mesmo momento |
| 7 — os nomes dos níveis (2026-09-14) | **Central** (o app e a pasta; o arquivo da raiz é `CENTRAL.md`) › **estação** (o espaço de trabalho) | a Central passa a operar espaços de propósitos diferentes — o trem de inovação, a vida pessoal, a administração da empresa — e "plataforma" virou o nome de um deles. Os outros arquivos de orquestra continuam `CLAUDE.md`, que é nome fixo do harness; o da raiz ganha nome próprio, e um `CLAUDE.md` de uma linha aponta para ele |

---

**Metáfora ferroviária — os únicos termos:** *Central* (a aplicação),
*estação* (um espaço de trabalho), *projeto* (um trabalho dentro dela),
*trem* (a fila de pendências passando uma por vez) e *embarque* (os primeiros
passos). Não invente outros: chamar prompt de "bilhete" ou projeto de "vagão"
recria exatamente o vocabulário privado que este trabalho desfaz.

---

## O que este documento ainda não decide

- **Os critérios de promoção** entre os estágios — são quatro conjuntos
  (captura→nota, nota→ideia, ideia→funcionalidade, funcionalidade→projeto) e
  vivem em [`classificar.md`](classificar.md).
- **As cores de cada estágio** — decididas no design system, no Trecho 4: a
  escala `--estagio-1` a `--estagio-5` de [`docs/design-system.md`](../docs/design-system.md).
- **O `estacao.json` de uma estação que não pode receber arquivo novo**
  — uma pasta lida em modo somente-leitura, por exemplo. A taxonomia dela é
  declarada inline no `central.json` do hub (Trecho 3), e nada é escrito lá
  dentro.
