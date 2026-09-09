# CLAUDE.md — Estação

> **Documento** · v0.7.0 · atualizado em 2026-09-08
>
> **Nome:** este projeto se chamava `PRJ-Explorer` até 2026-09-08. Virou
> **Estação** porque "Explorer" descreve ler, e o app passou a operar (criar
> nota, responder pendência, anotar em backlog, gerar briefing). A pasta é
> `PRJ-Estacao`, sem acento, por causa de escape de caminho no git; "Estação"
> é o nome em tela e em prosa. Registro histórico (LOG, pendências resolvidas,
> relatórios, `propostas-<data>`) mantém o nome antigo de propósito — era o
> nome na época. Razões em `analise-produto-e-onboarding-2026-09-08.md`.

> **Bifurcação — 2026-09-08.** Este repositório é um **fork** de
> `C:\Plataforma\PRJ-Estacao`, feito pelo Trecho 1 de
> `plano-hub-estacao-e-embarque-2026-09-08.md`. Ele é o **produto genérico**:
> uma Estação que opera N plataformas, com raiz configurável, taxonomia neutra
> e módulo de primeiros passos. A Estação do `C:\Plataforma` **continua existindo**
> e servindo o caso aplicado — as duas bases divergem de propósito, e
> `C:\Plataforma` é **somente leitura** neste trabalho. O hub deste fork é
> `C:\.Estacao`; a aplicação mora em `C:\.Estacao\app`.
>
> **Raiz configurável desde o Trecho 3 (2026-09-08).** Nenhum módulo tem mais
> caminho de plataforma escrito dentro dele: tudo sai de `app/config.py`, lido
> **na hora da chamada** (é o que faz o seletor trocar de plataforma sem
> reiniciar). A raiz resolve nesta ordem — `--raiz` → `ESTACAO_PLATAFORMA` →
> plataforma ativa no `estacao.json` do hub → erro em português. O fallback
> `PROJECT_DIR.parent` **foi removido de propósito**: fora do `plataforma de origem` ele
> mascarava erro de configuração como árvore vazia.

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta.

## O que é este projeto

A **Estação** é onde o humano opera o `plataforma de origem` sem abrir uma sessão de IA — e de
onde ele dispara a sessão quando quiser. Começou (v0.1) como navegador local do
corpus: índice, árvore, busca, e um único write (toggle de checkbox de backlog).
Hoje (v0.7) também:

- **captura nota** crua (aba Nota) — vira Captura com ID e linha no LOG;
- **responde pendência** (aba Workflow) — grava a opção no próprio `.md`, e a
  rodada seguinte do `rotina-de-avanco` encaminha; o app nunca fecha a pendência;
- **abre projeto** (pelo Portfólio) — maturidade, backlogs com toggle, e anotação
  que vira linha de checkbox no backlog do projeto;
- **gera briefing pra IA** — texto pronto pra colar no Claude Code / Codex, com
  caminhos reais e os guardrails do método embutidos;
- **mostra o fluxo** (aba Fluxo) — Passo 0/1/2/3 e os 4 critérios de promoção.

É por isso que ela funciona como **sub-harness**: a IA não roda aqui dentro; a
Estação prepara o que entra (contexto + guardrail) e recebe o que sai (decisão,
nota, anotação), sempre no formato que a automação já lê. Planos:
`plano-console-operacional-2026-09-06.md` (v0.5) e
`plano-console-sub-harness-2026-09-08.md` (v0.6–v0.7).

## Como rodar

```
python app/server.py
```

Abre em `http://127.0.0.1:8744`. `app/templates/index.html` é lido fresco do
disco a cada request — não precisa reiniciar o servidor pra mudança de
HTML/CSS/JS, só pra mudança em arquivo `.py`.

## Cuidado: este projeto lê `C:\Plataforma`, mas não é `C:\Plataforma`

A Estação **lê** a pasta um nível acima da sua própria (`C:\Plataforma`),
mas o próprio código do app vive em `C:\Plataforma\PRJ-Estacao\` — igual
todo outro projeto-projeto, um nível abaixo da raiz. O indexer nunca
autoindexa a própria pasta `PRJ-Estacao/` (está na lista de exclusão).

## Estrutura

```
PRJ-Estacao/
├── app/
│   ├── server.py       servidor HTTP + roteamento + endpoints de efeito colateral (toggle, launch, nota) + /files
│   ├── indexer.py       varredura do corpus, classificação, índice JSON
│   ├── search.py         busca em memória sobre o índice
│   ├── log_parser.py    parser dedicado das tabelas de 1-capturas/LOG/_log.md
│   ├── export_static.py snapshot estático de arquivo único (dist/), pra compartilhar sem servidor
│   ├── portfolio.py     inventário de 'tudo que roda' por Projeto (aba Portfólio) — curadoria via portfolio.json
│   ├── export_portfolio.py vitrine pública (dist/portfolio-seu-beira.html) — só o que pode ser visto de fora
│   ├── notas.py          (v0.5) POST /api/nota/nova — cria Captura crua (SBC) sem sessão do Claude Code
│   ├── workflow.py       (v0.5) GET /api/workflow — pipeline SBC→SBI→SBZ + pendências, aba Workflow
│   ├── pendencias.py     (v0.6) parser tolerante + POST /api/pendencia/responder (responder no app)
│   ├── avanco.py         (v0.5) GET /api/avanco — última rodada do rotina-de-avanco, lida de historico.md
│   ├── projetos.py       (v0.6) GET /api/projeto + POST /api/projeto/anotar — view por Projeto
│   ├── noar.py           (v0.6) checagem "está no ar?" das URLs públicas (cache 6h, thread pós-reindex)
│   ├── backfill_portfolio.py (v0.6) semeia portfolio.json a partir dos perfis (CLI, --dry-run padrão)
│   ├── briefing.py       (v0.7) GET /api/briefing — texto pronto pra colar numa sessão do Claude Code
│   └── templates/
│       ├── index.html    UI de página única
│       └── vendor/                marked.min.js + mermaid.min.js (10.9.1) — vendorizados (MIT), sem CDN
├── cache/                index.json + backups/, gitignored
└── docs/
```

## Convenção de nomes que este app pressupõe (fonte de verdade: `indexer.py`)

Desde 2026-08-31, todo `plataforma de origem` segue esta convenção — o classificador do
indexer é escrito em cima dela, não invente exceção sem atualizar os dois
juntos:

| Padrão de nome | Tipo | Observação |
|---|---|---|
| `o-*.md` | `orquestra` | Prefixo `o-` sinaliza "isto é um índice de pasta" |
| `_metodo/trilha.md` | `trilha` | **Caso único** — a trilha de leitura; abre na aba Tour (v0.3), não como markdown comum |
| `CLAUDE.md` | `orquestra` | **Exceção sem prefixo** — nome hardcoded pelo Claude Code (auto-carrega como contexto do projeto); nunca renomear |
| `SKILL.md` | `skill` | **Exceção sem prefixo** — nome hardcoded pelo Claude Code (torna a skill descobrível); nunca renomear |
| `backlog-<assunto>.md` | `backlog` | `docs/BACKLOG.md` (maiúsculo) é o único caso legado, também aceito |
| `readme-<assunto>.md` | `readme` | |
| `changelog-<assunto>.md` | `changelog` | |
| `1-capturas/LOG/_log.md` | `log` | Singleton — parser dedicado em `log_parser.py`, não markdown genérico |
| `glossario.md` | `glossary` | |
| `doutrina.md` | `doctrine` | Regras permanentes de reorganização, em `_metodo` |
| `chaves.md` | `linkmap` | Mantido manualmente — UI mostra aviso de que pode divergir |
| `_leia-me.md` | `readme` | Convenção das pastas de ciclo de vida (ver abaixo) e de `memoria-claude/` |

Para `CLAUDE.md`/`SKILL.md` (que não podem levar o prefixo `o-`), o app
extrai e mostra o **título** (primeiro `# heading` do arquivo) em vez do
nome cru — é assim que a UI resolve "não sei do que se trata, só que é um
CLAUDE.md" sem tocar no arquivo.

## Ciclo de vida físico dentro de `1-capturas` (convenção desde 2026-08-31)

O conteúdo de `1-capturas` foi dividido em três subpastas que espelham
o **estágio de triagem** (ortogonal à etapa Captura/Ideia/Projeto):
`.entrada/` (zero linha no LOG), `.pendente/` (tem linha no LOG, sem `→`),
`.historico/` (tem linha no LOG, com `→destino`). O indexer expõe isso como
`entry.lifecycle_stage` (`"entrada"`/`"pendente"`/`"historico"`/`null`),
derivado só do caminho (`indexer.py::lifecycle_stage`) — a UI mostra um
badge de cor diferente por estágio. Isso é **conteúdo de `1-capturas`
especificamente**, não um conceito geral do resto do corpus.

## Exclusões do indexer (fonte de verdade: `indexer.py::EXCLUDE_PREFIXES`)

`.git`, `node_modules`, `__pycache__`, `.claude` (config/skills do próprio
Claude Code, não é conteúdo do usuário), `.Biblioteca/Takeout_Google`,
`outro-app-local/build`, `outro-app-local/dist`,
`pasta-de-rascunho/subpasta`, e a própria
`PRJ-Estacao/`. Mudar essa lista aqui também.

## Histórico de revisões pós-reorganização

**v0.2 (2026-08-31, mesmo dia da v0.1):** entre a v0.1 e esta revisão, uma
rodada do `rotina-de-avanco` (rodando fora desta sessão, concorrente com
ela) reorganizou boa parte do `plataforma de origem`: `1-capturas` ganhou as pastas de
ciclo de vida acima, `ideias-embrionarias.md` virou `fragmentos.md`, surgiu
`pendentes.md` (auditoria mecânica do LOG sem `→`), `_metodo` ganhou
`doutrina.md` e `memoria-claude/`, os Ideias em `3-ideias` passaram a
viver em subpastas `<id>/<id>.md`, `Scheduled/` saiu da raiz pra dentro de
`_ferramentas/`, e surgiu um `.claude/` na raiz (config de skill do próprio
Claude Code). O indexer foi revisado e reverificado ponta a ponta contra
esse novo estado (ver `docs/backlog-estacao.md`). **Isso deve
acontecer de novo** — o `plataforma de origem` é ativamente reorganizado por automações
próprias do usuário. Antes de mexer no `indexer.py` achando algo quebrado,
primeiro confira se a árvore real mudou de baixo (comparar `ls` real contra
o que o classificador espera), não assuma que é bug do app.

## Endpoints de escrita — tabela

| endpoint | escreve | módulo | trava de segurança |
|---|---|---|---|
| `POST /api/backlog/toggle` | `- [ ]`/`- [x]` em backlog | `server.py` | tipo `backlog` no índice + `expected_text` (409) + backup |
| `POST /api/nota/nova` | SBC em `.pendente/` + linha no LOG | `notas.py` | ID via `plataforma.py` (subprocess) + lock + append-only + backup |
| `POST /api/pendencia/responder` | opção / "Outra resposta" de pendência | `pendencias.py` | `ref` validado + linha tem que ser opção + `expected_text` (409) + backup |
| `POST /api/projeto/anotar` | `- [ ] …` no backlog do projeto | `projetos.py` | allow-list do índice + `expected_sha1` (409) + backup |

`POST /api/launch` abre executável local (efeito colateral, não escreve arquivo).
Toda escrita nova segue a mesma disciplina — ver a seção abaixo antes de somar a quarta.

## Efeitos colaterais: toggle de backlog (v1), abrir executável (v0.4), nota (v0.5)

**`POST /api/launch` (v0.4, aba Portfólio)** não escreve em arquivo nenhum, mas
tem efeito colateral maior: abre um `.bat`/`.exe`/`server.py` local numa
janela própria. Regras (`server.py::_handle_launch`): só aceita path que
`portfolio.py` já classificou como launcher/binário/servidor (nunca caminho
arbitrário vindo do navegador); cwd na pasta do arquivo; UI pede confirmação;
o snapshot estático responde "somente leitura". **`GET /files/<path>`** serve
qualquer arquivo da raiz só pra leitura (nunca `.git`/`node_modules`, sem sair
da raiz) — é o que faz protótipos HTML abrirem renderizados.

**`POST /api/nota/nova` (v0.5, aba Nota)** — terceiro endpoint de escrita:
cria uma Captura crua (SBC) a partir de texto solto, sem sessão do Claude
Code. Regras (`app/notas.py`): `plataforma.py novo-id` chamado via `subprocess`
(nunca import — o comando faz `sys.exit()` em erro, o que mataria o servidor
se fosse import direto); grava o `.md` em `.pendente/` com gravação atômica
(`os.replace`); acrescenta uma linha na seção do dia (`## Entradas <data> —
captura via console (Estação)`) do LOG central — nunca edita linha
existente (doutrina: LOG é append-only), lê/escreve sem tradução de fim de
linha pra preservar LF/CRLF do arquivo original (mesmo cuidado do toggle);
`threading.Lock()` serializa criações concorrentes, porque `novo-id` lê o
maior `SEQ` do LOG no momento da chamada — duas notas quase simultâneas sem
essa trava puderam colidir no mesmo SEQ (mesma corrida já documentada em
`encaminhando-trecho`). Nunca classifica (sempre SBC) — mesma
disciplina da skill de chat equivalente. Testado ponta a ponta em 2026-09-06:
2 notas reais, `plataforma.py verificar` sem PROBLEMA novo, diff do LOG conferido
(append puro).

### Único write em v1: toggle de checkbox de backlog

`POST /api/backlog/toggle` é a **única** forma deste app escrever em
qualquer arquivo do corpus. Regras (ver `server.py::_handle_backlog_toggle`):
só aceita arquivos classificados `backlog`; confere concorrência otimista
(a linha precisa bater com o que foi lido antes de gravar, senão 409);
troca só `- [ ] `/`- [x] ` naquela linha específica; faz backup em
`cache/backups/` antes de gravar. Qualquer escrita nova (v2) precisa passar
por essa mesma disciplina primeiro — não adicionar endpoint de escrita sem
esse cuidado.

Como cada projeto-projeto tem git próprio, marcar um checkbox lá aparece
como alteração não commitada naquele repo — revisão/commit é do usuário,
a Estação nunca commita em nome de ninguém.

## Convenções

- Zero build step, zero dependência de terceiros no lado Python (stdlib
  puro). Do lado do frontend, `marked.js` (v0.3, markdown) e `mermaid.min.js`
  (v0.3, diagramas na aba Tour) são as duas exceções — vendorizadas
  (arquivo copiado, não CDN), decisão deliberada priorizando velocidade de
  entrega e cobertura correta de markdown/diagrama sobre a pureza
  "zero terceiro" do `outro-app-local` (que tinha motivo específico:
  empacotamento PyInstaller, que não se aplica aqui).
- Antes de considerar uma mudança pronta: `python -m py_compile app/*.py`;
  `python -m unittest discover tests` (suíte stdlib, sem dependência — desde a
  v0.6.0); se mexer no `<script>` de `index.html`, `node --check` no trecho
  extraído.
- **Salvar é automático; publicar é decisão** — doutrina do `plataforma de origem`, regra 6,
  definida em 2026-09-08 depois de perda real de trabalho. A sessão commita
  local **sem pedir autorização** ao terminar um artefato e ao encerrar a
  sessão; ela **avisa** o que entrou, não pergunta. `git add` **nominal**,
  nunca `git add .` nem `git add -A`. Mudança de outra origem é listada no
  aviso e fica de fora. **Push só com autorização explícita e separada**, uma
  por vez. A regra que estava aqui era o oposto ("só commitar depois que o
  usuário confirmar que testou") e foi ela que custou o trabalho perdido —
  testar antes de commitar continua valendo; esperar autorização para **salvar**
  não.

## Links

- [_indice.md](../_metodo/_indice.md) — pai
- [_indice-projetos.md](../4-projetos/_indice-projetos.md)
- [backlog-estacao.md](backlog-estacao.md)
