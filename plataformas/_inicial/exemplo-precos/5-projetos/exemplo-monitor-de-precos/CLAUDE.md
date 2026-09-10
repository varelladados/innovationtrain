---
id: 26.07.28-PRJ-001-exemplo-monitor-de-precos-1e77
data: 2026-07-28
estagio: 5
origem: 26.07.26-FUN-001-coleta-diaria-de-preco-e-frete-4e63
tipo: dados
status: em andamento
---

# CLAUDE.md — Exemplo: Monitor de preços

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.
>
> **Isto é um exemplo.** A loja, os concorrentes e os domínios são inventados.
> O nome começa com `exemplo-` justamente para você saber que pode apagar.

## O que é este projeto

Uma coleta diária do preço de uma lista curta de produtos dos concorrentes, no
mesmo horário, guardando **preço, frete, data e hora** — e nunca sobrescrevendo
a coleta anterior. O valor não está no preço de hoje: está na série.

Veio de `26.07.26-FUN-001-coleta-diaria-de-preco-e-frete-4e63` — a funcionalidade que o
originou, e a primeira linha do backlog —, que veio de
`26.07.25-IDE-001-historico-de-preco-em-vez-de-print-d5f0`, que veio de
uma nota sobre reclamações concentradas no fim de semana, que veio de um
desabafo depois do terceiro cliente reclamando — a cadeia inteira está no
`_registro.md` desta plataforma.

## Como rodar

```
python coleta/rodar.py --uma-vez
```

*(Este é um projeto de exemplo: o `coleta/` não existe. O que importa aqui é o
formato do `CLAUDE.md`, não o código.)*

## Estrutura

```
exemplo-monitor-de-precos/
├── CLAUDE.md                   este arquivo
├── backlog-monitor.md          o que falta
├── portfolio.json              o que este projeto publica
├── prototipo-serie-de-preco.html  uma tela, dados inventados
└── produtos-observados.md      a lista curta, mantida à mão
```

## Convenções

- **Nada é sobrescrito.** Cada coleta é uma linha nova. Corrigir uma coleta
  errada é acrescentar a correção, nunca editar a linha antiga — mesma regra do
  `_registro.md` da plataforma.
- **Frete junto com o preço, desde a primeira coleta.** A nota
  `26.09.06-NOT-001` mostrou por quê: a peça 20% mais barata sai 4% mais cara no
  total. Um monitor que só olha a vitrine dá conselho errado.
- **Antes de coletar de um site novo, leia os termos de uso dele.** Isto é
  bloqueante, e é a razão de a lista ser curta e mantida à mão.
- **Uma lista curta que eu mantenho** — 20 produtos que importam, não o catálogo
  inteiro. Catálogo inteiro é o caminho mais rápido para dado que ninguém olha.

## Como esta sessão salva o trabalho

**Salvar é automático; publicar é decisão.**

- **Commite sem pedir autorização** ao terminar um artefato e ao encerrar a
  sessão. **Avise** numa linha o que entrou — não pergunte.
- Adicione os arquivos **nominalmente**. Nunca `git add .`, nunca `git add -A`.
- Mudança que não foi você quem fez: liste no aviso e **deixe de fora**.
- **Push só com autorização explícita e separada**, uma por vez.
- Nunca commite segredo (chave, senha, `.env`, token).
- **Nunca encerre a sessão deixando mudança sua sem commit.**

Commit local não publicado se desfaz inteiro com `git reset --soft HEAD~1`, que
mantém tudo no lugar. O custo de um commit a mais é zero; o de um a menos já foi
trabalho perdido.

## Links

- [backlog-monitor.md](backlog-monitor.md)
- [produtos-observados.md](produtos-observados.md)
- `_indice.md` da plataforma — a porta de entrada
