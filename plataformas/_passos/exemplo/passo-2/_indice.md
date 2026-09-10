# Exemplo — cozinha e fotografia

> **Esta plataforma é um exemplo, e ela começa vazia de propósito.** Só há
> capturas: nove textos crus, do jeito que chegaram. Nenhuma nota, nenhuma
> ideia, nenhum projeto — **você** faz o trem andar, e vê os objetos nascerem.
>
> Quando quiser recomeçar, é um clique: **reiniciar** devolve tudo ao estado de
> agora. Nada que você fizer aqui é irreversível, então mexa sem medo.

## Em 30 segundos

Alguém que cozinha e fotografa, jogando coisa aqui dentro há duas semanas sem
tratar nada. Um braindump no ônibus, um áudio do feirante transcrito, um print
do grupo de fotografia, e uma queixa recorrente sobre comprar coentro de novo.

**É assim que uma plataforma de verdade começa:** cheia de matéria-prima e sem
nada organizado. A parte difícil não é capturar — é a primeira passagem.

## Os cinco estágios

| Pasta | O que tem aqui | Agora |
|---|---|---|
| `1-capturas/` | chegou e ninguém tratou | **9** |
| `2-notas/` | já foi lido e organizado | vazio |
| `3-ideias/` | tem forma e serve de insumo | vazio |
| `4-funcionalidades/` | diz o que vai existir quando estiver pronto, e onde | vazio |
| `5-projetos/` | ganhou corpo próprio | vazio |

Dentro de cada uma, `_historico/` guarda o que já avançou dali. Estão todos
vazios — ainda não avançou nada.

## A trilha — sete passos, no painel da barra lateral

Esta plataforma vem com uma **trilha**: sete estados sucessivos dela mesma,
seguindo dois grãos do começo ao fim. Clique em **▶** e a plataforma inteira
passa para o estado seguinte.

| Passo | O que acontece |
|---|---|
| 0 | como ela vem: nove capturas, nada mais |
| 1 | `ideia-no-onibus` vira a nota **app de receitas pela despensa** |
| 2 | a nota vira a ideia **receita pela despensa** |
| 3 | a ideia vira a funcionalidade **busca pelo que tem em casa** — o que vai existir, com critério de pronto, e onde: projeto novo |
| 4 | a funcionalidade vira o projeto **`exemplo-app-de-receitas`**, com backlog — e ela é a primeira linha dele |
| 5 | um segundo grão anda: `conversa-sobre-curso` vira nota e depois ideia |
| 6 | o curso vira a funcionalidade **semana 1: luz, com devolutiva** |
| 7 | o curso vira projeto — e com **dois** na mesa, nasce a primeira decisão |

Em cada passo, repare em três coisas: o item some da pasta ativa e reaparece no
`_historico/` com um rodapé apontando para frente; a linha dele no `_registro.md`
ganha o marcador `→`; e o `_sem-destino.md` para de cobrá-lo.

O passo 7 mostra a coisa mais parecida com a vida real que este exemplo tem:
dois projetos nasceram em três dias, são da mesma pessoa e disputam as mesmas
noites — e isso vira uma **pendência** em `_pendencias/`, que aparece como carta
na aba **🔀 Workflow**. Decisão não se resolve sozinha, e ninguém a fecha por
inferência.

**Não há mágica nem inteligência aqui.** Cada passo é uma pasta com a plataforma
inteira já naquele estado, e o botão só a restaura. Numa plataforma sua a
passagem é decisão (os critérios da aba **🧩 Fluxo**) e escrita (o texto do
estágio novo) — as duas coisas que um botão não faz. A trilha mostra **como
fica**, não como se automatiza.

**↺ voltar ao início** desfaz tudo, a qualquer momento.

## Depois da trilha, dirija você

Sobram sete capturas que a trilha não toca. Os fios estão todos aqui dentro:

| Comece por | Onde isso costuma dar |
|---|---|
| `geladeira-cheia-e-nada-pra-comer` | o desperdício tem padrão → comprar pelo cardápio |
| `recado-da-feira` | o que o feirante sabe que uma lista escrita em casa não sabe |
| `print-do-grupo-de-fotografia` + `anotacoes-da-aula-de-luz` | qual lente primeiro; e o que dá pra fazer só com luz de janela |
| `braindump-do-onibus` | é o caso real: três assuntos misturados num texto só. Separar é o trabalho |
| `export-do-caderno-de-receitas` | texto exportado com a formatação da ferramenta ainda grudada |

Para essas, o caminho é o de sempre: leia os critérios em **🧩 Fluxo**, e peça o
roteiro à aba **📋** — ela gera o briefing pronto para colar numa sessão de IA,
com os guardrails do método embutidos.

**Para ver como fica uma plataforma depois de meses de uso**, abra
`plataformas/exemplo-precos` pelo seletor: lá tudo já aconteceu — duas cadeias
inteiras, três que empacaram no meio e uma decisão em aberto.

## Onde estão as coisas

| Arquivo | O que é |
|---|---|
| `_registro.md` | a linha do tempo de tudo. Append-only: nunca se apaga |
| `_sem-destino.md` | gerado — o que está no registro e ainda não avançou (hoje: tudo) |
| `_pendencias/` | as decisões esperando por você. Vazia até você criar a primeira |
| `_trilha.md` | a leitura guiada desta plataforma (aba Tour) |
| `plataforma.json` | os nomes: estágios, siglas, tipos de projeto |

## Como trabalhar aqui

1. **Capturar é a operação mais barata:** cole e siga em frente. Organizar é
   uma etapa própria, depois.
2. **Nunca monte identificador à mão** — a ação avançar chama o utilitário, e
   fora dela é
   `python ../../metodo/plataforma.py novo-id --raiz . --etapa CAP --slug "..."`
3. **Nada é apagado.** Avançar move o original para o `_historico/` do estágio.
4. Antes de encerrar uma rodada:
   `python ../../metodo/plataforma.py verificar --raiz .`
5. Para voltar ao começo, fora do app:
   `python ../../metodo/plataforma.py reiniciar --raiz . --confirmar`

## Duas coisas que este exemplo simplifica

1. Numa plataforma de verdade, **cada projeto é um repositório git próprio**
   (ver `metodo/classificar.md`). Aqui os projetos que você criar vão viver
   dentro do repositório da plataforma, para o exemplo caber num clone só.
2. **A trilha e o reiniciar só existem aqui.** É a chave `estado_inicial` do
   `plataforma.json` que os permite, e uma plataforma sua não a declara — é por
   isso que esses comandos não têm como apagar o seu trabalho.

## Links

- `metodo/regras.md` — as regras permanentes, e por que cada uma existe
- `metodo/classificar.md` — quando um item passa de estágio
- `metodo/versionamento.md` — salvar, publicar e o que fazer quando der ruim
