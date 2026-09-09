# Licenças das fontes vendorizadas

As três fontes da Estação são servidas **do próprio repositório**, não de CDN —
mesma decisão já tomada para `marked.js` e `mermaid.js`. Um app que se vende
como local, stdlib puro e sem dependência não deveria pedir a internet para
abrir com a cara certa (Trecho 4, Parada 2, decidido em 2026-09-08).

Todas as três estão sob a **SIL Open Font License, Version 1.1** — o que permite
redistribuir os arquivos junto com o software, desde que a licença viaje junto.
É o que este arquivo faz.

**Verificado em 2026-09-08 lendo o arquivo de licença de cada projeto de
origem**, não de memória:

| Fonte | Onde é usada | Licença | Verificado em |
|---|---|---|---|
| **Fraunces** | títulos, botões da barra lateral, números grandes | OFL 1.1 — *Copyright 2018 The Fraunces Project Authors* | `undercasetype/Fraunces` · `OFL.txt` |
| **Public Sans** | texto corrido | OFL 1.1 — *Copyright 2015 The Public Sans Project Authors* | `uswds/public-sans` · `LICENSE.md` |
| **IBM Plex Mono** | código, identificadores, caminhos | OFL 1.1 — *Copyright © 2017 IBM Corp., Reserved Font Name "Plex"* | `IBM/plex` · `LICENSE.txt` |

**Nota sobre a Public Sans:** ela é uma versão modificada da Libre Franklin. As
modificações do GSA (governo dos EUA) são CC0, mas a obra original continua sob
OFL 1.1 — e o próprio arquivo de licença do projeto diz, em negrito, que na
prática o uso deve seguir a OFL 1.1, porque num trabalho combinado vale o termo
mais restritivo. É o que fazemos aqui.

## O que está nesta pasta

Baixado de `fonts.gstatic.com` em 2026-09-08, apenas os subsets **latin** e
**latin-ext** — cirílico, grego e vietnamita não servem a este app e
triplicariam o peso. Total: **223 KB**.

| Arquivo | Peso | Subset |
|---|---|---|
| `fraunces-400-700-latin.woff2` | 400–700 (variável) | latin |
| `fraunces-400-700-latin-ext.woff2` | 400–700 (variável) | latin-ext |
| `public-sans-400-700-latin.woff2` | 400–700 (variável) | latin |
| `public-sans-400-700-latin-ext.woff2` | 400–700 (variável) | latin-ext |
| `ibm-plex-mono-400-latin.woff2` | 400 | latin |
| `ibm-plex-mono-400-latin-ext.woff2` | 400 | latin-ext |
| `ibm-plex-mono-500-latin.woff2` | 500 | latin |
| `ibm-plex-mono-500-latin-ext.woff2` | 500 | latin-ext |

As regras `@font-face` correspondentes vivem no `<style>` do
`app/templates/index.html`, junto do resto do CSS — o app não tem build step e
não serve folha de estilo separada.

## Para atualizar

Baixe de novo pelo `css2` do Google Fonts com um user-agent de navegador
moderno (senão ele devolve TTF em vez de WOFF2), fique só com os blocos
`/* latin */` e `/* latin-ext */`, e **confira o arquivo de licença do projeto
de origem outra vez** — a licença de uma fonte pode mudar entre versões, e
memória não é verificação.
