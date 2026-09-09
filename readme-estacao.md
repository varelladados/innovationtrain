# Estação

Navegador local pra todo o corpus de `C:\Plataforma` — orquestras, backlogs, LOG
central e demais arquivos pertinentes — pensado pra crescer e operar sobre
esses arquivos como um portfólio.

## Rodar

```
python app/server.py
```

Abre em `http://127.0.0.1:8744`.

## Estrutura

Ver [CLAUDE.md](CLAUDE.md) para a estrutura completa, a convenção de nomes
que o indexer pressupõe, e as regras do único endpoint de escrita.

## Stack

Python stdlib puro no servidor (zero dependência de terceiros, zero build
step). Frontend HTML/CSS/JS de página única, com `marked.js` (markdown) e
`mermaid.min.js` (diagramas na aba Tour) vendorizados — arquivo local, não
CDN.

## Versão

Ver [VERSION](VERSION) e [changelog-estacao.md](changelog-estacao.md).
