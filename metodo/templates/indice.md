# <nome da plataforma>

> **A porta de entrada.** Quem chega aqui — pessoa ou sessão de IA — lê este
> arquivo primeiro. Uma plataforma tem um só.

## Em 30 segundos

<o que esta plataforma guarda, de quem é, e o que ela NÃO é. Três frases.>

## Os cinco estágios

Toda ideia entra crua e vai amadurecendo. As pastas numeradas são esse caminho:

| Pasta | O que tem aqui |
|---|---|
| `1-capturas/` | chegou e ninguém tratou |
| `2-notas/` | já foi lido e organizado |
| `3-ideias/` | tem forma e serve de insumo |
| `4-funcionalidades/` | diz o que vai existir quando estiver pronto, e onde entra |
| `5-projetos/` | ganhou corpo próprio: pasta, backlog, git |

Dentro de cada uma, `_historico/` guarda o que já avançou dali.
As regras da passagem estão em `metodo/classificar.md`.

## Onde estão as coisas

| Arquivo | O que é |
|---|---|
| `_registro.md` | a linha do tempo de tudo. Append-only: nunca se apaga |
| `_sem-destino.md` | gerado — o que está no registro e ainda não avançou |
| `plataforma.json` | os nomes: estágios, siglas, tipos de projeto |

## Como trabalhar aqui

1. **Capturar** é a operação mais barata: cole e siga em frente. Organizar é
   depois, e é uma etapa própria.
2. **Nunca monte identificador à mão** —
   `python metodo/plataforma.py novo-id --raiz . --etapa CAP --slug "..."`.
3. **Nada é apagado.** Encerrar é mover para o `_historico/` do estágio.
4. Antes de dar uma rodada por encerrada:
   `python metodo/plataforma.py verificar --raiz .`

## Links

- `metodo/regras.md` — as regras permanentes, e por que cada uma existe
- `metodo/classificar.md` — quando um item passa de estágio
- `metodo/versionamento.md` — salvar, publicar e o que fazer quando der ruim
