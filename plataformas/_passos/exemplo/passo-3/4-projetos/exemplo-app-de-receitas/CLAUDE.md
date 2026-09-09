---
id: 26.09.02-PRJ-001-exemplo-app-de-receitas-e4a8
data: 2026-09-02
estagio: 4
origem: 26.08.28-IDE-001-receita-pela-despensa-b3a9
tipo: app
status: em andamento
---

# CLAUDE.md — Exemplo: App de receitas

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.
>
> **Isto é um exemplo.** Ele existe para mostrar como uma plataforma fica quando
> está sendo usada de verdade — os objetos estão conectados, não são enfeite.
> O nome começa com `exemplo-` justamente para você saber que pode apagar.

## O que é este projeto

Um app onde você diz o que tem em casa e ele responde o que dá pra fazer com
isso hoje. A busca é invertida em relação aos apps de receita comuns: eles
partem do prato e produzem uma lista de compras; este parte da despensa.

Veio de `26.08.28-IDE-001-receita-pela-despensa-b3a9`, que veio de uma nota, que veio de um braindump no ônibus —
a cadeia inteira está no `_registro.md` desta plataforma.

## Como rodar

```
python app/servidor.py
```

*(Este é um projeto de exemplo: o `servidor.py` não existe. O que importa aqui é
o formato do `CLAUDE.md`, não o código.)*

## Estrutura

```
exemplo-app-de-receitas/
├── CLAUDE.md                    este arquivo
├── backlog-app-de-receitas.md   o que falta
└── portfolio.json               o que este projeto publica
```

## Convenções

- As receitas ficam em arquivo, não em banco. A decisão sobre onde os dados vão
  morar está **adiada de propósito** até existirem 50 receitas de verdade — foi
  travar nisso que parou o projeto por duas semanas.
- Uma tela primeiro. Só depois a segunda.

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

- [backlog-app-de-receitas.md](backlog-app-de-receitas.md)
- `_indice.md` da plataforma — a porta de entrada
