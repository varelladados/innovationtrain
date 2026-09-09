---
id: <novo-id --etapa PRJ>
data: AAAA-MM-DD
estagio: 4
origem: <identificador da ideia de onde isto veio>
tipo: <um dos tipos declarados no plataforma.json>
status: <rascunho | em andamento | no ar | pausado | encerrado>
---

# CLAUDE.md — <nome do projeto>

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta. É a porta de entrada do projeto: o que estiver aqui vale
> como contexto; o que não estiver, a sessão não sabe.

## O que é este projeto

<uma frase do que é, e uma de para quem.>

## Como rodar

```
<o comando, literal — nada de "instale as dependências e execute">
```

## Estrutura

```
<as pastas que importam, com uma linha de explicação cada. Só o que importa.>
```

## Convenções

- <as decisões que a próxima sessão precisa respeitar para não quebrar nada.>

## Como esta sessão salva o trabalho

**Salvar é automático; publicar é decisão.**

- **Commite sem pedir autorização** ao terminar um artefato e ao encerrar a
  sessão. **Avise** numa linha o que entrou — não pergunte.
- Adicione os arquivos **nominalmente**. Nunca `git add .`, nunca `git add -A`.
- Mudança que não foi você quem fez: liste no aviso e **deixe de fora**.
- **Push só com autorização explícita e separada**, uma por vez.
- Nunca commite segredo (chave, senha, `.env`, token) — sai do arquivo mas fica
  no histórico.
- **Nunca encerre a sessão deixando mudança sua sem commit.**

Isto não é zelo excessivo: a regra oposta ("só commite depois que eu mandar")
já custou trabalho perdido. Commit local não publicado se desfaz inteiro com
`git reset --soft HEAD~1`, que mantém tudo no lugar — o custo de um commit a
mais é zero.

## Links

- [backlog-<assunto>.md](backlog-<assunto>.md) — o que falta
- <o `_indice.md` da plataforma>
