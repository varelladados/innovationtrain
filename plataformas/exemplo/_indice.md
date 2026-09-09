# Exemplo — cozinha e fotografia

> **Esta plataforma é um exemplo**, e é feita para ser mexida. Tudo aqui começa
> com `exemplo-` ou fala de comida e de foto — apague à vontade quando tiver a
> sua. Ela existe porque um sistema vazio não ensina nada: dá para ver como fica
> quando **está funcionando**.

## Em 30 segundos

Alguém que cozinha e fotografa usando a Estação para não perder ideia. Duas
ideias já viraram projeto, duas estão em forma esperando, duas notas ainda não
fecharam, e duas capturas chegaram hoje e ninguém tratou. Isso é o estado normal.

## Os quatro estágios

| Pasta | O que tem aqui | Agora |
|---|---|---|
| `1-capturas/` | chegou e ninguém tratou | 2 esperando |
| `2-notas/` | já foi lido e organizado | 2 |
| `3-ideias/` | tem forma e serve de insumo | 2 |
| `4-projetos/` | ganhou corpo próprio | 2 |

Dentro de cada uma, `_historico/` guarda o que já avançou dali — o texto
preservado como era naquele estágio.

## Siga um grão do começo ao fim

Esta é a cadeia inteira, e ela existe para ser percorrida clicando:

| # | Item | Onde |
|---|---|---|
| 1 | `26.08.24-CAP-001-ideia-no-onibus-4f21` | `1-capturas/_historico/` |
| 2 | `26.08.25-NOT-001-app-de-receitas-pela-despensa-8c07` | `2-notas/_historico/` |
| 3 | `26.08.28-IDE-001-receita-pela-despensa-b3a9` | `3-ideias/_historico/` |
| 4 | **`exemplo-app-de-receitas`** | `4-projetos/` |

Começa com "comprei coentro de novo" rabiscado no ônibus e termina num projeto
com backlog. A segunda cadeia (conversa sobre curso → curso de fotografia) faz
o mesmo caminho.

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

## Uma simplificação deste exemplo

Numa plataforma de verdade, **cada projeto é um repositório git próprio**
(ver `metodo/classificar.md`). Aqui os dois projetos vivem dentro do repositório
da plataforma, para o exemplo caber num clone só. É a única regra que este
exemplo não segue, e está dito em voz alta de propósito.

## Links

- `metodo/regras.md` — as regras permanentes, e por que cada uma existe
- `metodo/classificar.md` — quando um item passa de estágio
- `metodo/versionamento.md` — salvar, publicar e o que fazer quando der ruim
