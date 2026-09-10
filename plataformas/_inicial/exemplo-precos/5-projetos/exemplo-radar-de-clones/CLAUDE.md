---
id: 26.08.12-PRJ-001-exemplo-radar-de-clones-72f5
data: 2026-08-12
estagio: 5
origem: 26.08.11-FUN-001-varredura-semanal-de-dominios-a8d2
tipo: servico
status: em andamento
---

# CLAUDE.md — Exemplo: Radar de clones

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.
>
> **Isto é um exemplo.** A loja, os domínios e os casos são inventados. O nome
> começa com `exemplo-` justamente para você saber que pode apagar.

## O que é este projeto

Uma varredura semanal que procura lojas usando o nome, as fotos e o texto da
minha loja — para eu saber **quantas são** antes de decidir o que fazer.

Veio de `26.08.11-FUN-001-varredura-semanal-de-dominios-a8d2` — a funcionalidade que o
originou, e a primeira linha do backlog —, que veio de
`26.08.10-IDE-001-radar-de-dominios-parecidos-3ce8`, que veio de uma nota
com os cinco sinais de loja clone, que veio de uma cliente que comprou numa cópia
e não recebeu.

## O escopo, e o que está fora dele

**Isto é detecção. Não é remoção.** O projeto produz uma ficha por achado, com
data verificável. O que fazer com a ficha — notificar quem, com qual texto, em
que ordem — é a ideia `26.08.30-IDE-001`, que está **parada de propósito** em
`3-ideias/` esperando uma decisão em `_pendencias/`.

Manter a fronteira é a decisão de projeto mais importante aqui: detecção que já
sai notificando erra o canal com pressa, e errar o canal queima a primeira
tentativa.

## Como rodar

```
python radar/semanal.py
```

*(Este é um projeto de exemplo: o `radar/` não existe. O que importa aqui é o
formato do `CLAUDE.md`, não o código.)*

## Estrutura

```
exemplo-radar-de-clones/
├── CLAUDE.md              este arquivo
├── backlog-radar.md       o que falta
├── portfolio.json         o que este projeto publica
└── sinais.md              o que conta como sinal, e o peso de cada um
```

## Convenções

- **Achado não é acusação.** Cada ficha registra o que bateu e o que não bateu.
  Revendedor legítimo que copiou a descrição existe, e tratá-lo como golpe custa
  caro.
- **Prova com data verificável, nunca print solto.** Foi o ponto que a advogada
  cobrou (`26.08.28-NOT-001`), e é o que separa uma ficha útil de uma inútil.
- **Nada é apagado.** Um domínio que saiu do ar continua na lista, marcado —
  reaparecer é informação.

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

- [backlog-radar.md](backlog-radar.md)
- [sinais.md](sinais.md)
- `_indice.md` da plataforma — a porta de entrada
