# Design system da Estação

> **Documento operacional** · escrito em 2026-09-08 (Trecho 4 do
> `plano-hub-estacao-e-embarque-2026-09-08.md`) · sucede
> [`plano-incorporacao-dashboard-nova-identidade.md`](plano-incorporacao-dashboard-nova-identidade.md)

Este documento existe porque a identidade visual da Estação estava aplicada mas
não estava **escrita**: os tokens viviam num `:root` sem explicação, e 17 valores
de cor tinham escapado para regras soltas — inclusive um azul da paleta anterior,
que ninguém percebeu porque ninguém tinha olhado o modo escuro.

---

## A regra de ouro

**Nenhum valor literal de cor fora do bloco de tokens.** Nem em regra CSS, nem em
atributo `style`, nem em objeto JavaScript.

Não é preferência de estilo: é o que faz o modo escuro funcionar **sem uma
segunda folha de estilo**. Um `#3b6d11` escrito numa regra é uma cor que não
troca quando o tema troca — e o jeito de descobrir é abrir o modo escuro e ver o
que ficou apagado.

A regra é cobrada por [`tests/test_design_tokens.py`](../tests/test_design_tokens.py),
que falha o build se um hex aparecer depois do bloco de tokens. Sem o teste, o
furo volta em duas semanas — foi assim que os 17 apareceram.

**Como escrever cor, então:** use um token existente. Se nenhum servir, crie um
no `:root` **com par claro e escuro**, e só então use.

---

## Os temas

A Estação tem **dois eixos independentes**: o *tema* (a identidade) e o *modo*
(claro ou escuro).

| Eixo | Como se escolhe | Onde fica guardado |
|---|---|---|
| **Tema** — `padrão` ou `areia` | seletor no topo da barra lateral | `localStorage`, chave `estacao.tema.v1` |
| **Modo** — claro ou escuro | preferência do sistema operacional; `data-theme` força | o sistema |

**Tema padrão** é a identidade do produto: verde-petróleo sobre cinza-frio.
**Tema areia** é a identidade alternativa — dourado sobre areia —
preservada como um tema entre outros (Trecho 4, Parada 1).

Isso dá quatro combinações, e as quatro têm bloco próprio no CSS, **nesta
ordem** (a ordem importa: os seletores empatam em especificidade e quem vem
depois vence):

```
:root                                                     tema padrão, claro
@media (prefers-color-scheme: dark) :root:not([data-theme="light"])   padrão, escuro
:root[data-theme="dark"]                                  padrão, escuro forçado
:root[data-tema="areia"]                                  areia, claro
@media (prefers-color-scheme: dark) :root[data-tema="areia"]:not(...) areia, escuro
:root[data-tema="areia"][data-theme="dark"]               areia, escuro forçado
```

**A paleta de tipo de arquivo é compartilhada pelos dois temas** — ela diz o que
o arquivo *é*, não de quem é a plataforma. Só a paleta base e a escala de
maturidade mudam com o tema.

---

## Os tokens

### Superfície e texto

| Token | Padrão claro | Padrão escuro | Quando usar |
|---|---|---|---|
| `--bg` | `#F3F5F7` | `#0F1317` | o fundo da página; também a cor de texto **sobre** `--text` |
| `--surface` | `#FFFFFF` | `#161B21` | cartão, painel, barra lateral — o que "flutua" sobre o fundo |
| `--surface-2` | `#E7ECF1` | `#1F262E` | dentro de um cartão: chip, `code`, cabeçalho de tabela |
| `--border` | `rgba(16,24,40,.13)` | `rgba(230,237,243,.14)` | toda borda e divisória |
| `--text` | `#101828` | `#E6EDF3` | texto normal |
| `--text-2` | `#5A6478` | `#98A6B3` | texto secundário: rótulo, meta, contagem |
| `--stub` | `#9AA4B2` | `#6B7684` | conteúdo vazio ou desabilitado |
| `--shadow` | (duas camadas) | (duas camadas) | elevação de cartão; nunca invente `box-shadow` |

### Acento e estados

| Token | Padrão claro | Padrão escuro | Quando usar |
|---|---|---|---|
| `--accent` | `#1F6F6B` | `#5FB8B0` | a cor da marca: link, botão primário, ênfase |
| `--accent-bg` | `#D8EAE8` | `#15302E` | fundo suave de acento (botão de navegação, badge) |
| `--on-accent` | `#FFFFFF` | `#0F1317` | **texto sobre `--accent`.** Nunca escreva `#fff`: no escuro o acento é claro |
| `--danger` / `--danger-bg` | `#8C2F3A` / `#F5DEE1` | `#D98A96` / `#322226` | erro, item essencial, aviso duro |
| `--success` / `--success-bg` | `#2F6B45` / `#DDEDE3` | `#8FC5A3` / `#1B2A21` | pendência respondida, confirmação |
| `--warn` / `--warn-bg` | `#7A5A1F` / `#F2E8D2` | `#E0BE7E` / `#2C2519` | adiado, atenção, plataforma não encontrada |

### Maturidade — `--estagio-1` a `--estagio-4`

Um matiz só, do apagado ao saturado: a cor **diz o quanto o grão avançou**
(Trecho 4, Parada 3).

| Token | Padrão claro | Padrão escuro | Areia claro | Areia escuro |
|---|---|---|---|---|
| `--estagio-1` | `#A3B0B2` | `#55686B` | `#B0A896` | `#6E6555` |
| `--estagio-2` | `#7FA6A2` | `#6E918D` | `#C0A87A` | `#9A8862` |
| `--estagio-3` | `#4C8F89` | `#46A197` | `#B08F4B` | `#BE9A55` |
| `--estagio-4` | `#1F6F6B` | `#6ECFC6` | `#9C7A3C` | `#CBA25A` |

**Como usar:** ponha a classe `est-1`…`est-4` no elemento; ela define a variável
local `--est`, que a regra consome com fallback:

```css
.wf-card{border-left:3px solid var(--est,var(--border))}
.wf-card .et{color:var(--est,var(--accent))}
```

O número do estágio vem do servidor (`workflow.py::_estagio_de`), derivado da
sigla no identificador — nunca deduzido no cliente.

### Tipo de arquivo — `--tipo-*`

Diz **o que o arquivo é**, e é ortogonal à maturidade: um `backlog-app.md` é do
tipo *backlog* e está no estágio *projetos* ao mesmo tempo. São 14 tokens
(`--tipo-orquestra`, `--tipo-backlog`, `--tipo-log`, `--tipo-changelog`,
`--tipo-readme`, `--tipo-skill`, `--tipo-glossary`, `--tipo-doctrine`,
`--tipo-linkmap`, `--tipo-script`, `--tipo-trilha`, `--tipo-dashboard-html`,
`--tipo-other-markdown`, `--tipo-other-pertinent`) mais `--tipo-outro` de
fallback, todos com par claro/escuro.

**Como usar:** a bolinha da árvore recebe a classe do tipo, e o CSS resolve.
O JavaScript **não** conhece cor nenhuma:

```js
const dot = `<span class="type-dot t-${e.type}"></span>`;
```

### Espaço, raio e tipografia

Escala **pequena e fechada** de propósito (Trecho 4, Parada 4): antes eram 42
valores de `padding` e 18 tamanhos de letra distintos, e o resultado era uma
interface quase-alinhada. Poucos valores é o que faz uma escala servir.

| Espaço | Raio | Tipografia |
|---|---|---|
| `--sp-1` 4px · `--sp-2` 8px · `--sp-3` 12px · `--sp-4` 16px | `--r-1` 4px | `--fs-1` 12px — meta, chip, badge |
| `--sp-6` 24px · `--sp-8` 32px · `--sp-10` 40px | `--r-2` 8px | `--fs-2` 13px — texto de interface |
| | `--r-pill` 999px | `--fs-3` 14px — texto corrido |
| | (`50%` para círculo) | `--fs-4` 17px — título de seção |
| | | `--fs-lg` 20px · `--fs-num` 28px — números do dashboard |

---

## As fontes

Três, **servidas do próprio repositório** — nenhuma requisição externa
(Trecho 4, Parada 2). Verificado: com o app aberto, todas as requisições vão
para `127.0.0.1`.

| Família | Onde | Peso |
|---|---|---|
| **Fraunces** | títulos, botões de navegação, números grandes | variável 400–700 |
| **Public Sans** | texto corrido, interface | variável 400–700 |
| **IBM Plex Mono** | código, identificadores, caminhos, árvore | 400 e 500 |

Arquivos e licenças (as três são OFL 1.1) em
[`app/templates/vendor/fonts/LICENCAS.md`](../app/templates/vendor/fonts/LICENCAS.md).
São 223 KB, subsets `latin` e `latin-ext` apenas. As regras `@font-face` estão no
topo do `<style>` do `index.html`, e o `server.py` serve os arquivos por uma rota
com allow-list de nome (nunca caminho arbitrário).

**Sempre declare a pilha de fallback** — `"Fraunces",serif`,
`"Public Sans",-apple-system,Segoe UI,Roboto,sans-serif`,
`"IBM Plex Mono",ui-monospace,monospace`. Vendorizar não dispensa o fallback:
o arquivo pode faltar num fork mal copiado.

---

## Criar uma aba nova: são três pontos, e esquecer um é silencioso

Este era um fato solto que só existia na cabeça de quem já tinha feito. Está
aqui porque **esquecer o ponto 2 deixa o botão sem estilo nenhum**, e nada
avisa.

1. **O botão**, na barra lateral do `index.html`, junto dos outros:
   ```html
   <button id="minha-nav-btn" title="uma frase do que a aba faz">🧭 Minha aba</button>
   ```
2. **O id nas duas regras compartilhadas do CSS** — a de estilo e a de `:hover`.
   Hoje são as linhas **194 e 195** do `index.html`. As duas, sempre; são
   listas de seletores separadas por vírgula e o id precisa entrar nas duas.
3. **O wiring**, no bloco final de `addEventListener` (perto da linha 2214):
   ```js
   document.getElementById("minha-nav-btn").addEventListener("click", openMinhaView);
   ```

---

## Os mockups aprovados

As quatro decisões deste trecho foram aprovadas **olhando**, não lendo. Os
artefatos estão vivos em [`docs/mockups/`](mockups/) — cada painel é um
documento completo com o CSS real do app dentro de um `iframe`, então eles não
envelhecem para "um desenho antigo": mostram o que o CSS daquele momento fazia.

| Arquivo | Decidiu |
|---|---|
| [`parada-1-identidade.html`](mockups/parada-1-identidade.html) | identidade própria do produto; areia vira tema |
| [`parada-2-fontes.html`](mockups/parada-2-fontes.html) | vendorizar (a linha do meio mostra o app sem internet) |
| [`parada-3-cor.html`](mockups/parada-3-cor.html) | tipo na árvore **e** escala de maturidade |
| [`parada-4-escala.html`](mockups/parada-4-escala.html) | escala pequena e fechada |

*(O itinerário pedia "um print do mockup aprovado". Guardar os mockups vivos é
melhor que um PNG: dá para reabrir, comparar os dois modos e ler os valores
computados. Um print seria uma cópia pior de algo que já está aqui.)*

---

## Links

- [`CLAUDE.md`](../CLAUDE.md) — como o app funciona
- [`plano-incorporacao-dashboard-nova-identidade.md`](plano-incorporacao-dashboard-nova-identidade.md) — de onde a identidade veio
- [`metodo/taxonomia.md`](../../metodo/taxonomia.md) — os nomes dos estágios que a escala de maturidade colore
