# Exemplo — preços, concorrência e lojas clone

> **Esta plataforma é um exemplo**, e é feita para ser mexida. A loja, os
> concorrentes, os domínios e as pessoas são inventados; tudo começa com
> `exemplo-` ou fala de preço e de cópia — apague à vontade quando tiver a sua.
>
> Ela existe ao lado de `plataformas/exemplo` (cozinha e fotografia) para
> mostrar a **mesma estrutura em outro assunto**: um assunto de trabalho, com
> dinheiro, prazo e decisão jurídica envolvidos. O método é o mesmo; o conteúdo
> não podia ser mais diferente.

## Em 30 segundos

Alguém que vende um produto de nicho e precisa saber duas coisas: **o que o
concorrente está cobrando** e **quem está se passando pela loja dele**. Cinco
cadeias saíram de coisas soltas: duas viraram projeto, duas empacaram na ideia
esperando decisão, e uma parou na nota porque os dados não sustentavam
conclusão. Três capturas continuam cruas — uma delas desde julho.

**Isso é o estado normal.** Uma plataforma onde tudo avançou não existe.

## Os quatro estágios

| Pasta | O que tem aqui | Agora |
|---|---|---|
| `1-capturas/` | chegou e ninguém tratou | 3 esperando |
| `2-notas/` | já foi lido e organizado | 2 |
| `3-ideias/` | tem forma e serve de insumo | 2 |
| `4-projetos/` | ganhou corpo próprio | 2 |

Dentro de cada uma, `_historico/` guarda o que já avançou dali — o texto
preservado como era naquele estágio.

## Siga um grão do começo ao fim

Esta é a cadeia inteira, e ela existe para ser percorrida clicando:

| # | Item | Onde |
|---|---|---|
| 1 | `26.07.20-CAP-001-cliente-reclamou-do-preco-4c19` | `1-capturas/_historico/` |
| 2 | `26.07.22-NOT-001-o-concorrente-muda-preco-na-sexta-8ab3` | `2-notas/_historico/` |
| 3 | `26.07.25-IDE-001-historico-de-preco-em-vez-de-print-d5f0` | `3-ideias/_historico/` |
| 4 | **`exemplo-monitor-de-precos`** | `4-projetos/` |

Começa com "terceiro cliente essa semana mandando print" e termina num projeto
com backlog. A segunda cadeia (cliente que comprou numa cópia → radar de clones)
faz o mesmo caminho.

## O que empacou, e por quê

É a metade que um exemplo costuma esconder — e é a mais parecida com a vida:

| Item | Onde parou | Por quê |
|---|---|---|
| `26.08.19-NOT-001` os dados estão sujos | **na nota** | organizou o problema, mas não vira ideia enquanto não houver regra de coleta |
| `26.08.30-IDE-001` notificar quem primeiro | **na ideia** | espera a decisão em `_pendencias/` — e está dito no próprio arquivo |
| `26.09.07-IDE-001` alerta abaixo do custo | **na ideia** | depende de um custo cadastrado que ainda não existe |
| `26.07.14-CAP-001` áudio do fornecedor | **na captura, desde julho** | tem número importante e ninguém ouviu de novo |

O áudio de julho é o caso mais honesto do exemplo: ele **bloqueia** o alerta de
margem, e está parado há quase dois meses a três cliques de distância. É para
isso que o `_sem-destino.md` existe.

## Onde estão as coisas

| Arquivo | O que é |
|---|---|
| `_registro.md` | a linha do tempo de tudo. Append-only: nunca se apaga |
| `_sem-destino.md` | gerado — o que está no registro e ainda não avançou |
| `_pendencias/` | as decisões esperando por você (aba Workflow) |
| `_trilha.md` | a leitura guiada desta plataforma (aba Tour) |
| `plataforma.json` | os nomes: estágios, siglas, tipos de projeto |

## Como trabalhar aqui

1. **Capturar é a operação mais barata:** cole e siga em frente. Organizar é
   uma etapa própria, depois.
2. **Nunca monte identificador à mão:**
   `python ../../metodo/plataforma.py novo-id --raiz . --etapa CAP --slug "..."`
3. **Nada é apagado.** Avançar move o original para o `_historico/` do estágio.
4. Antes de encerrar uma rodada:
   `python ../../metodo/plataforma.py verificar --raiz .`

## Duas simplificações deste exemplo

1. Numa plataforma de verdade, **cada projeto é um repositório git próprio**
   (ver `metodo/classificar.md`). Aqui os dois vivem dentro do repositório da
   plataforma, para o exemplo caber num clone só.
2. **Os domínios, os concorrentes e as pessoas são inventados.** Nenhum endereço
   deste exemplo existe, e nenhum deve ser visitado.

## Links

- `metodo/regras.md` — as regras permanentes, e por que cada uma existe
- `metodo/classificar.md` — quando um item passa de estágio
- `metodo/versionamento.md` — salvar, publicar e o que fazer quando der ruim
