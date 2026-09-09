# CLAUDE.md — Exemplo: preços, concorrência e lojas clone

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.

## O que é isto

Uma **plataforma de exemplo** da Estação, sobre acompanhar preço de concorrente
e detectar lojas que copiam a sua. É a irmã de `plataformas/exemplo` (cozinha e
fotografia): mesma estrutura, assunto oposto de propósito.

**Tudo aqui é inventado** — a loja, os concorrentes, os domínios, a advogada, o
estagiário. Nenhum endereço citado existe, e nenhum deve ser visitado.

## Como ela está montada

Cinco cadeias, e a graça está em elas não terem todas o mesmo fim:

| Cadeia | Termina em | Por quê |
|---|---|---|
| cliente reclamou → monitor de preços | **projeto** | |
| cliente comprou numa cópia → radar de clones | **projeto** | |
| planilha do estagiário → dados sujos | **nota** | não vira ideia sem regra de coleta |
| conversa com a advogada → notificar quem | **ideia** | espera decisão em `_pendencias/` |
| margem encolheu → alerta abaixo do custo | **ideia** | depende de custo cadastrado |

Mais três capturas cruas, uma delas de julho — e essa bloqueia a última cadeia.

## Se você for mexer aqui

- **O registro é append-only.** Acrescentar linha, nunca editar nem apagar.
- **`_sem-destino.md` é gerado.** Não edite dentro dos marcadores
  `<!-- gerado:... -->`; rode
  `python ../../metodo/plataforma.py gerar-sem-destino --raiz .`
- **Nunca monte identificador à mão:** `plataforma.py novo-id`.
- **Avançar copia**, e o original vai para o `_historico/` do estágio, com o
  rodapé apontando para onde foi. Os dois lados da linhagem precisam bater.
- Antes de encerrar: `python ../../metodo/plataforma.py verificar --raiz .`

## O que este exemplo não segue

Numa plataforma de verdade cada projeto é um repositório git próprio. Aqui os
dois vivem dentro do repositório da plataforma, para caber num clone só. É a
única regra quebrada, e está dita em voz alta.

## Links

- `_indice.md` — a porta de entrada
- `_trilha.md` — a leitura guiada (aba Tour)
- `../../metodo/taxonomia.md` — os nomes, e a fonte de tudo isto
