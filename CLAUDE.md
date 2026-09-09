# CLAUDE.md — Estação

> **Documento** · v0.8.2 · atualizado em 2026-09-09
>
> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.

## O que é este projeto

A **Estação** é onde uma pessoa opera as próprias ideias sem abrir uma sessão de
IA — e de onde ela dispara a sessão quando quiser. Começou como navegador local
de um corpus de markdown: índice, árvore, busca, e um único write (toggle de
checkbox de backlog). Hoje também:

- **captura nota** crua (aba Nota) — vira item do primeiro estágio, com
  identificador e linha no registro;
- **responde pendência** (aba Workflow) — grava a opção no próprio `.md`, e a
  rodada seguinte da automação encaminha; o app nunca fecha a pendência;
- **abre projeto** (pelo Portfólio) — maturidade, backlogs com toggle, e anotação
  que vira linha de checkbox no backlog do projeto;
- **gera briefing pra IA** — texto pronto pra colar numa sessão de IA, com
  caminhos reais e os guardrails do método embutidos;
- **mostra o fluxo** (aba Fluxo) — as passagens entre estágios e os critérios de
  promoção;
- **cria a primeira plataforma** (aba Embarque) — cinco perguntas, um prompt.

É por isso que ela funciona como **sub-harness**: a IA não roda aqui dentro; a
Estação prepara o que entra (contexto + guardrail) e recebe o que sai (decisão,
nota, anotação), sempre no formato que a automação já lê.

## Como rodar

```
python app/server.py
```

Abre em `http://127.0.0.1:8744`. `app/templates/index.html` é lido fresco do
disco a cada request — não precisa reiniciar o servidor pra mudança de
HTML/CSS/JS, só pra mudança em arquivo `.py`.

## A raiz não é adivinhada — ela é resolvida

A Estação **não assume** que mora dentro da plataforma que lê. A raiz resolve
nesta ordem, em `config.resolver()`:

1. `--raiz <pasta>` na linha de comando;
2. a variável de ambiente `ESTACAO_PLATAFORMA`;
3. a plataforma marcada `ativa` no `estacao.json` do hub;
4. erro em português, dizendo as três saídas acima.

**Não existe fallback para `PROJECT_DIR.parent`**, e a ausência dele é
deliberada: fora da plataforma em que a Estação nasceu ele resolvia para uma
pasta qualquer e fazia erro de configuração aparecer como "árvore vazia". Há um
teste que cobra que ele não voltou (`test_config.py`).

Quando **nada** resolve — o caso de quem acabou de clonar — `config.iniciar()`
não levanta: devolve `sem_plataforma()`, o servidor sobe e a aba Embarque abre
sozinha. É o único caminho que faz sentido oferecer a quem chega.

## Nada de plataforma fica escrito no código

Tudo que é nome de plataforma sai de `config.atual()`, **lido na hora da
chamada**, nunca no import — é isso que faz o seletor trocar de plataforma sem
reiniciar o servidor. Isso vale para três famílias de coisa, e a terceira é a que
se esquece:

| Família | Onde é declarada | Exemplos |
|---|---|---|
| **Taxonomia** | `estagios`, `siglas`, `tipos`, `historico` | pastas, nomes, siglas dos estágios |
| **Caminhos** | as chaves opcionais (`perfis`, `trilha`, `pendencias`, `manifesto`…) | onde cada coisa mora dentro da plataforma |
| **Campos de frontmatter** | `frontmatter.processado` · `.nucleo` · `.origem` | os nomes de campo que o app **lê e escreve** |

A terceira existe porque nome de campo é comportamento, não prosa: o app grava
`<processado>: <id>` no arquivo que cria e procura esse mesmo campo depois. Se
ele estivesse escrito no código, uma plataforma com convenção própria só poderia
ser lida mudando o produto. Chave ausente degrada: sem `nucleo`, a métrica
correspondente simplesmente **sai** do dashboard, em vez de contar zero como se
fosse informação.

O `config.PADROES` é a cópia executável de `metodo/taxonomia.md`. Mudou lá, muda
aqui — e há um teste que compara os dois.

## Estrutura

```
estacao/                  ← a raiz do repositório É o hub
├── app/
│   ├── server.py         servidor HTTP + roteamento + endpoints de efeito colateral + /files
│   ├── config.py         taxonomia + resolução da raiz. TODO módulo lê daqui, na hora da chamada
│   ├── indexer.py        varredura do corpus, classificação, índice JSON
│   ├── search.py         busca em memória sobre o índice
│   ├── log_parser.py     parser dedicado das tabelas do registro central
│   ├── metrics.py        métricas do Dashboard
│   ├── export_static.py  snapshot estático de arquivo único (dist/), pra compartilhar sem servidor
│   ├── portfolio.py      inventário de "tudo que roda" por projeto — curadoria via portfolio.json
│   ├── export_portfolio.py vitrine pública — só o que pode ser visto de fora
│   ├── notas.py          POST /api/nota/nova — cria captura crua sem sessão de IA
│   ├── workflow.py       GET /api/workflow — o trem: pipeline dos estágios + pendências
│   ├── pendencias.py     parser tolerante + POST /api/pendencia/responder
│   ├── avanco.py         GET /api/avanco — última rodada da rotina de avanço
│   ├── projetos.py       GET /api/projeto + POST /api/projeto/anotar
│   ├── noar.py           checagem "está no ar?" das URLs públicas (cache 6h)
│   ├── backfill_portfolio.py semeia portfolio.json a partir dos perfis (CLI, --dry-run padrão)
│   ├── briefing.py       GET /api/briefing — texto pronto pra colar numa sessão de IA
│   ├── embarque.py       POST /api/embarque/prompt — os primeiros passos de quem não tem plataforma
│   ├── versoes.py        GET /api/versoes — leitura do git, allow-list de subcomando, só leitura
│   └── templates/
│       ├── index.html    UI de página única
│       └── vendor/       marked.min.js + mermaid.min.js e as três fontes .woff2 — sem CDN
├── metodo/               regras, taxonomia, templates e plataforma.py (o utilitário)
├── plataformas/
│   ├── exemplo/          cozinha e fotografia — a cadeia 1→2→3→4 navegável
│   └── exemplo-precos/   preços e lojas clone — e três cadeias que empacaram
├── tests/                a suíte, stdlib, sem dependência
├── docs/                 design-system.md e os mockups de aprovação
├── cache/                index.json + backups/, gitignored
├── README.md  LICENSE    a porta de entrada pública e a Apache 2.0
├── estacao.exemplo.json  template — copie como estacao.json (que é gitignored)
└── pendencias/           decisões de quem usa; fora do versionamento
```

**Isto era três repositórios até 2026-09-09** (`app`, `metodo`,
`plataformas/exemplo`, dentro de um hub). Na publicação viraram um só: quem
clona pega o produto inteiro e ele funciona de primeira. O efeito colateral bom
é que os testes de `test_exemplo.py` e o de taxonomia deixaram de pular em
silêncio — antes dependiam de repositórios irmãos que um clone não trazia.

## Convenção de nomes que o indexer pressupõe (fonte de verdade: `indexer.py`)

O classificador é escrito em cima desta convenção — não invente exceção sem
atualizar os dois juntos:

| Padrão de nome | Tipo | Observação |
|---|---|---|
| `<prefixo>*.md` | `orquestra` | o prefixo de índice é declarado pela plataforma (`indice_prefixo`); sinaliza "isto é um índice de pasta" |
| o documento de `trilha` | `trilha` | **caso único** — abre na aba Tour, não como markdown comum |
| `CLAUDE.md` | `orquestra` | **exceção sem prefixo** — nome fixado pelo Claude Code (auto-carrega como contexto do projeto); nunca renomear |
| `SKILL.md` | `skill` | **exceção sem prefixo** — nome fixado pelo Claude Code (torna a skill descobrível); nunca renomear |
| `backlog-<assunto>.md` | `backlog` | `docs/BACKLOG.md` (maiúsculo) também é aceito |
| `readme-<assunto>.md` | `readme` | |
| `changelog-<assunto>.md` | `changelog` | |
| o arquivo de `registro` | `log` | singleton — parser dedicado em `log_parser.py`, não markdown genérico |
| `glossario.md` | `glossary` | |
| `doutrina.md` | `doctrine` | regras permanentes |
| `chaves.md` | `linkmap` | mantido manualmente — a UI avisa que pode divergir |
| `_leia-me.md` | `readme` | convenção das pastas de ciclo de vida |

Para `CLAUDE.md`/`SKILL.md` (que não podem levar o prefixo de índice), o app
extrai e mostra o **título** (primeiro `# heading` do arquivo) em vez do nome
cru — é assim que a UI resolve "não sei do que se trata, só que é um CLAUDE.md"
sem tocar no arquivo.

## Ciclo de vida físico dentro de um estágio

Uma plataforma pode dividir um estágio em subpastas de **triagem**, ortogonais à
etapa: o que entrou e ninguém tocou, o que está pendente, o que já foi
encaminhado. A plataforma declara quais são em `ciclo_vida`; o indexer expõe
isso como `entry.lifecycle_stage`, derivado só do caminho
(`indexer.py::lifecycle_stage`), e a UI mostra um badge de cor por estágio. Na
taxonomia padrão a única subpasta é o `_historico/` de cada estágio.

## Exclusões do indexer

O padrão está em `config.PADROES["excluir"]` (`.git`, `node_modules`,
`__pycache__`, `.claude`, `dist`, `build`) e **cada plataforma acrescenta o que
quiser** no `plataforma.json` dela — acervos externos, pastas de build de
projetos, o que não deve entrar em varredura. Nada disso é escrito no código.

## Endpoints de escrita — tabela

| endpoint | escreve | módulo | trava de segurança |
|---|---|---|---|
| `POST /api/backlog/toggle` | `- [ ]`/`- [x]` em backlog | `server.py` | tipo `backlog` no índice + `expected_text` (409) + backup |
| `POST /api/nota/nova` | item novo no estágio de entrada + linha no registro | `notas.py` | identificador via utilitário (subprocess) + lock + append-only + backup |
| `POST /api/pendencia/responder` | opção / "Outra resposta" de pendência | `pendencias.py` | `ref` validado + linha tem que ser opção + `expected_text` (409) + backup |
| `POST /api/projeto/anotar` | `- [ ] …` no backlog do projeto | `projetos.py` | allow-list do índice + `expected_sha1` (409) + backup |

`POST /api/plataforma/ativar` e `POST /api/embarque/registrar` escrevem **só no
`estacao.json` do hub** — que é config de quem usa, não corpus de plataforma. Por
isso não passam pela disciplina acima; a trava deles é outra: caminho tem que
estar registrado (ou ser acrescentado por eles), e nada é tocado dentro de
plataforma nenhuma.

### Endpoints que **não escrevem em disco** — e é de propósito

| endpoint | o que faz | por que não escreve |
|---|---|---|
| `GET /api/briefing` | texto pra colar numa sessão de IA | a IA é que executa, com o humano olhando |
| `POST /api/embarque/prompt` | texto que **cria a primeira plataforma** | é POST porque a entrada é um objeto de respostas, não porque escreve |
| `GET /api/versoes` | estado do git dos repositórios | allow-list de subcomando, todos de leitura |
| `GET /api/versoes/prompt` | "salvar um ponto", "mandar pra nuvem", "linha nova" | a Estação lê o git e gera o texto; **nunca o executa** |

Sobre o último: automatismo de commit mora onde a IA está, não numa interface
web onde um botão um dia é clicado sem querer. Ver `metodo/versionamento.md`.

`POST /api/launch` abre executável local (efeito colateral, não escreve arquivo).
Toda escrita nova segue a mesma disciplina — ver a seção abaixo antes de somar a
quinta.

## Efeitos colaterais que não são escrita de arquivo

**`POST /api/launch`** (aba Portfólio) não escreve em arquivo nenhum, mas tem
efeito colateral maior: abre um `.bat`/`.exe`/`server.py` local numa janela
própria. Regras (`server.py::_handle_launch`): só aceita path que `portfolio.py`
já classificou como launcher/binário/servidor (nunca caminho arbitrário vindo do
navegador); cwd na pasta do arquivo; a UI pede confirmação; o snapshot estático
responde "somente leitura". **`GET /files/<path>`** serve qualquer arquivo da
raiz só pra leitura (nunca `.git`/`node_modules`, sem sair da raiz) — é o que faz
protótipos HTML abrirem renderizados.

**`POST /api/nota/nova`** cria um item do primeiro estágio a partir de texto
solto, sem sessão de IA. Regras (`app/notas.py`): o utilitário da plataforma é
chamado via `subprocess` (nunca import — `novo-id` faz `sys.exit()` em erro, o
que mataria o servidor); grava o `.md` com gravação atômica (`os.replace`);
acrescenta uma linha na seção do dia do registro central — nunca edita linha
existente (o registro é append-only), lê e escreve sem tradução de fim de linha
pra preservar LF/CRLF do arquivo original; um `threading.Lock()` serializa
criações concorrentes, porque `novo-id` lê a maior sequência do dia no momento da
chamada — duas notas quase simultâneas sem essa trava podiam colidir no mesmo
número. Nunca classifica: o item nasce sempre no primeiro estágio.

### A disciplina que todo endpoint de escrita segue

`POST /api/backlog/toggle` foi o primeiro e definiu o padrão: só aceita arquivos
classificados `backlog`; confere concorrência otimista (a linha precisa bater com
o que foi lido antes de gravar, senão 409); troca só `- [ ] `/`- [x] ` naquela
linha específica; faz backup em `cache/backups/` antes de gravar. Qualquer
escrita nova precisa passar por esse mesmo cuidado primeiro.

Como cada projeto pode ter git próprio, marcar um checkbox lá aparece como
alteração não commitada naquele repositório — revisão e commit são de quem usa; a
Estação nunca commita em nome de ninguém.

## Convenções

- Zero build step, zero dependência de terceiros no lado Python (stdlib puro). Do
  lado do frontend, `marked.js` (markdown) e `mermaid.min.js` (diagramas) são as
  duas exceções — vendorizadas (arquivo copiado, não CDN), decisão deliberada
  priorizando cobertura correta de markdown e diagrama sobre a pureza
  "zero terceiro".
- Antes de considerar uma mudança pronta: `python -m py_compile app/*.py`;
  `python -m unittest discover tests`; se mexer no `<script>` de `index.html`,
  `node --check` no trecho extraído.
- **Nenhum valor literal de cor fora do bloco de tokens** do `index.html`. É
  cobrado por `tests/test_design_tokens.py` e explicado em
  `docs/design-system.md`. Cor escrita numa regra não troca no modo escuro.
- **A porta tem uma fonte só:** `config.PORTA`. O `.bat` pergunta ao Python; o
  `.claude/launch.json` é o único lugar que repete o número, porque é JSON lido
  pelo harness — e um teste cobra que os dois concordem.
- **Este repositório é público, e nenhum nome de plataforma de ninguém entra
  nele.** São **quatro camadas**, e a ordem importa — cada uma pega o que a
  anterior deixou passar:

  | # | Camada | Onde | Pega o quê |
  |---|---|---|---|
  | 1 | **Não está na pasta** | `estacao.json` e `pendencias/` fora do versionamento | o que nunca entra não vaza |
  | 2 | **`.gitignore`** | os padrões de papel de trabalho | o `git add` distraído |
  | 3 | **`.githooks/pre-commit`** | roda o guarda-corpo contra o índice | barra **antes de o commit existir** |
  | 4 | **`tests/test_publicacao.py` + CI** | Linux e Windows a cada push | o hook não instalado, e a história inteira |

  O guarda-corpo cobra a **forma**, nunca uma lista de nomes — um teste que
  listasse o que é privado publicaria exatamente o que deveria proteger. Por isso
  o vocabulário proibido está lá em **hash**, e as mensagens de falha devolvem
  hash, não palavra. Os testes de histórico existem porque um `git revert`
  traria de volta o commit que o teste do topo deveria ter barrado.

  **Reescrever história não é camada** — é o conserto de emergência de quando as
  quatro falharam, e ele não desfaz o que já foi publicado: `push --force` só
  desreferencia o objeto no GitHub. Para remover de verdade, apagar e recriar o
  repositório.
- **Aba nova exige três pontos**, e esquecer o segundo é silencioso: o botão no
  `<aside>`, o id nas **duas** regras compartilhadas do CSS (a de estilo e a de
  `:hover`), e o wiring no bloco final de `addEventListener`. Ver
  `docs/design-system.md`.
- **Salvar é automático; publicar é decisão** — `metodo/regras.md`, regra 6,
  definida depois de perda real de trabalho. A sessão commita local **sem pedir
  autorização** ao terminar um artefato e ao encerrar a sessão; ela **avisa** o
  que entrou, não pergunta. `git add` **nominal**, nunca `git add .` nem
  `git add -A`. Mudança de outra origem é listada no aviso e fica de fora.
  **Push só com autorização explícita e separada**, uma por vez. A regra que
  vigorava antes era o oposto ("só commitar depois que o usuário confirmar que
  testou") e foi ela que custou o trabalho perdido — testar antes de commitar
  continua valendo; esperar autorização para **salvar** não.

## Links

- [`README.md`](README.md) — a porta de entrada
- [`metodo/taxonomia.md`](metodo/taxonomia.md) — os nomes, e a fonte de `config.PADROES`
- [`metodo/regras.md`](metodo/regras.md) — as regras permanentes, cada uma com o porquê
- [`metodo/versionamento.md`](metodo/versionamento.md) — salvar, publicar, e o que fazer quando der ruim
- [`docs/design-system.md`](docs/design-system.md) — tokens, temas, fontes e a regra de ouro do CSS
