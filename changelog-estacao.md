# Changelog — Estação

## 0.8.0 — 2026-09-09

**A Estação vira produto.** Fork de `C:\Plataforma\PRJ-Estacao` para `C:\.Estacao\app`, execução dos nove trechos do `plano-hub-estacao-e-embarque-2026-09-08.md`. A Estação do `plataforma de origem` continua existindo e servindo o caso aplicado; `C:\Plataforma` foi somente leitura o tempo todo e não recebeu nenhum arquivo.

### A raiz deixou de ser adivinhada

- **`app/config.py`** (novo) — taxonomia e resolução da raiz num lugar só. A raiz resolve por `--raiz` → `ESTACAO_PLATAFORMA` → plataforma ativa no `estacao.json` → erro em português. **O fallback `PROJECT_DIR.parent` foi removido**: fora do `plataforma de origem` ele resolvia para uma pasta qualquer e fazia erro de configuração aparecer como "árvore vazia". Há teste cobrando que não voltou.
- **Onze módulos** deixaram de ter caminho escrito dentro deles. Todos leem `config.atual()` **na hora da chamada**, nunca no import — é isso que faz trocar de plataforma sem reiniciar.
- **Boot tolerante**: `reindex()` nunca levanta; `STATE` ganhou `plataforma_ok`; `_cached()` reconstrói dentro de `try/except` (antes um `OSError` com o índice vazio subia até o `do_GET` e virava traceback).
- **Seletor de plataforma** no topo da barra lateral (`GET /api/plataformas`, `POST /api/plataforma/ativar`).
- `projetos.PASTA_RE` (regex de prefixo) virou `_pasta_valida()`, que confere contra as pastas que existem no disco: allow-list de verdade, e sobrevive à taxonomia sem prefixo.

**Paridade medida, não afirmada:** com os dois lados rodando no mesmo instante contra `C:\Plataforma`, os resumos de índice, portfólio, métricas, pendências e workflow são iguais. As únicas diferenças são adições de propósito e **uma correção**: a contagem por tipo do Dashboard procurava o tipo em qualquer lugar da coluna Etapa/Tipo e contava o tipo do **destino** em toda linha que já tinha avançado — uma entrada crua, que não tem tipo, aparecia como `DIG` porque a seta apontava para um `SBI-DIG`. Inflava 8 das 128 linhas. `DIG` 29→23, `ADE` 10→8.

### Identidade própria, e o vocabulário privado saiu da tela

- **Tema padrão novo** (verde-petróleo sobre cinza-frio) e a paleta dourado/areia do `plataforma de origem` preservada como o tema nomeado `areia`. Dois eixos independentes: tema × modo claro/escuro, quatro blocos de token.
- **17 valores de cor** que viviam fora do `:root` (incluindo `#185fa5`, o azul da paleta anterior à migração de agosto) viraram **zero** — e isso virou `tests/test_design_tokens.py`.
- **Duas escalas de cor**: tipo de arquivo na árvore (tokenizado, com par claro/escuro) e `--estagio-1..4`, uma escala de maturidade do apagado ao saturado, no trem e no Portfólio. O itinerário tratava as duas como a mesma coisa; não são — um `backlog-app.md` é do tipo *backlog* **e** está no estágio *projetos*.
- **Escala fechada** de espaço, raio e tipografia. Eram 42 valores de `padding` e 18 tamanhos de letra distintos.
- **As três fontes vendorizadas** (223 KB, subsets latin e latin-ext, licenças OFL 1.1 conferidas nos repositórios de origem). Com o app aberto, **todas** as requisições vão para `127.0.0.1`.
- "Dashboard Método", "2 PROJETOS", "pipeline Captura→Ideia→Projeto" e `C:\Plataforma\` no breadcrumb: tudo sai da plataforma ativa agora. A aba **Fluxo** foi reescrita — eram os Passos 0-3 do checklist do `plataforma de origem`, agora são N-1 passagens montadas do config.
- **`docs/design-system.md`** e os quatro mockups de aprovação em `docs/mockups/`.

### Duas abas novas

- **🚂 Embarque** (`app/embarque.py`, `POST /api/embarque/prompt`) — cinco paradas, e a pessoa sai com o texto que cria a primeira plataforma. Módulo próprio, com guardrails próprios (não apague nada, se a pasta tiver conteúdo pare e mostre, não commite, caminhos absolutos). **Não escreve em disco.** Abre sozinha quando não há plataforma. Testado executando o prompt gerado, não lendo.
- **📦 Versões** (`app/versoes.py`, `GET /api/versoes`) — painel de respostas a quatro perguntas nos três repositórios, não um cliente de git. **Allow-list de subcomando**, todos de leitura; degrada em português quando falta git, remoto ou upstream. A **rede de proteção** ficou visível com as três camadas nomeadas. Os botões geram prompt com o `git status` real embutido; a Estação nunca executa git.

### Versionamento

- O guardrail dos briefings dizia **"Nunca commite automaticamente"** — o oposto da regra 6 da doutrina, escrita depois de perda real de trabalho. Corrigido, e o teste cobra as duas metades.
- O `CLAUDE.md` que o Embarque gera **já nasce com a regra dentro**: é isso que faz a IA do usuário salvar sozinha desde o dia um.
- `metodo/versionamento.md` e `metodo/salvar-tudo.md` (a rotina de fechamento) no hub.

### Launcher e testes

- **A porta tem uma fonte só** (`config.PORTA`). O `.bat` pergunta ao Python; o `launch.json` é o único lugar que repete o número, e um teste cobra que concordem.
- `iniciar-estacao.bat`: confere o Python **antes** (com `pause` se faltar), avisa se a porta está ocupada, e o navegador abre pelo **próprio servidor**, depois de o socket estar escutando.
- **47 → 137 testes.** Novos: `test_config.py`, `test_embarque.py`, `test_versoes.py`, `test_design_tokens.py`, `test_exemplo.py` (o indexer contra plataforma de exemplo, incluindo a cadeia 1→2→3→4 inteira). Os testes deixaram de monkeypatchar constante de módulo e passaram a **aplicar uma configuração** — o mesmo caminho do servidor.

## 0.7.0 — 2026-09-08

Sub-harness: o app deixa de ser só onde se olha o método e passa a ser de onde se dispara a sessão de IA. Terceira fase do `plano-console-sub-harness-2026-09-08.md`.

- **Briefing pra IA** (`app/briefing.py`, `GET /api/briefing?tipo=`, modal com "copiar"). A IA não mora no app — o app prepara o texto e o humano cola na sessão do Claude Code / Codex. Três tipos, todos derivados do estado real do disco:
  - `pendencias` — as que foram respondidas na interface e esperam encaminhamento, com caminho, título, `Fonte` (marcada como chave de junção que não se altera) e a opção escolhida por extenso; lista à parte as marcadas como "Deixar para depois", que devem incrementar `**Adiada:**` em vez de fechar.
  - `classificar` — uma Captura crua contra o Passo 1 do `checklist-classificacao.md`, com o trecho do conteúdo (sem frontmatter) e a regra dos 2 critérios.
  - `avancar` — um projeto, com os backlogs indexados e os itens `[ESSENCIAL]` abertos extraídos.
  - Todo briefing carrega um bloco de **guardrails hardcoded** (apagar é lógico, LOG append-only, não pula etapa, IDs via `plataforma.py`, não fecha pendência por inferência, não commita sozinho, artefato vive no repo, `.Biblioteca` fora). Hardcoded de propósito: parsear `doutrina.md` faria o gerador quebrar em silêncio a cada edição de prosa. Botões no Workflow (habilita quando há respondida), na view de Projeto e na tela de Fluxo.
- **Aba Fluxo** (🧩): o método na tela — Passo 0/1/2/3 do `fluxo.v2`, com os **4 critérios de promoção como checklist ao vivo** ("2 de 4 → promove a Ideia"). Não grava veredito: classificar continua sendo trabalho da skill, e daqui sai o briefing pra ela. Links pro checklist, fluxo e doutrina.
- **Workflow reordenado**: as pendências (parte acionável) vêm antes do kanban (panorama), que ficou limitado a 12 cards por coluna. Com 109 itens em `.pendente`, o quadro empurrava a decisão pra fora da primeira tela.
- `tests/test_briefing.py` (14 testes) — a garantia principal é que **nenhum briefing sai sem o bloco de guardrails**.

## 0.6.2 — 2026-09-08

Projetos e "produção = link" — segunda fase do `plano-console-sub-harness-2026-09-08.md`.

- **View de projeto** (`app/projetos.py`, `GET /api/projeto?pasta=`, botão "abrir projeto →" no card do Portfólio): junta numa tela o que estava em quatro lugares — status/resumo/git/links do portfólio, **maturidade 0-5 × 6 dimensões** do perfil da rodada de 2026-09-05, os `backlog-*.md` do projeto renderizados com os toggles que já existiam, lacunas, ligações com outros projetos e documentos-chave clicáveis.
- **`POST /api/projeto/anotar` — quinto endpoint de escrita.** Acrescenta `- [ ] <texto> _(via console, AAAA-MM-DD)_` no backlog do projeto, antes do rodapé `## Links`. Formato escolhido de propósito: é o que `plataforma.py` e o snapshot do avanço já leem, então a anotação feita aqui volta pra IA na rodada seguinte sem formato novo. Sem `**[ESSENCIAL]**` — anotação não é bloqueio de entrega. Allow-list vinda do índice (só backlogs daquela pasta), trava por sha1 do arquivo inteiro (409), backup, LF/CRLF preservados.
- **Badge "no ar"** (`app/noar.py`): item de backlog aberto desde a v0.4. HEAD com timeout de 4s (cai pra GET se o servidor recusar HEAD), cache de 6h, thread daemon disparada depois do reindex — nunca no caminho do request, nunca no export estático. Sem checagem, o link não ganha selo (não inventa "no ar").
- **`app/backfill_portfolio.py`**: semeia `portfolio.json` a partir dos perfis (`tags`, `nota`, `repo_publico: false`), `--dry-run` por padrão, nunca sobrescreve arquivo existente, nunca commita. Rodado: **14 projetos** ganharam `portfolio.json` (eram 2 de 16 com curadoria; agora 16 de 16).
- **Export estático consertado**: `/api/workflow` e `/api/avanco` agora viajam no snapshot (leitura), e os endpoints de escrita respondem "somente leitura" em vez de 404 — sem isso as abas novas quebrariam em silêncio no snapshot compartilhado por Remote Control.
- `tests/test_projetos.py` (12 testes): posição da linha, CRLF, 409, allow-list, texto inválido, backup, e a garantia de que a anotação não vira `[ESSENCIAL]`.
- **Bug pego no teste ao vivo** (não pelos unitários): o `text_cache` do indexer lê com universal newlines (CRLF→LF) e a escrita lê cru, então o sha1 divergia e todo backlog CRLF dava 409 eterno. `projetos.sha1()` normaliza os dois lados; o teste foi corrigido pra reproduzir o caminho real.

## 0.6.0 — 2026-09-08

Responder pendência dentro do app — primeira fase do `plano-console-sub-harness-2026-09-08.md` (decisão do usuário: "consultar a lista de pendências, e ter um campo para eu responder lá 'tipo offline' do avança, mas quando ele ver minha resposta já encaminhar").

- **`app/pendencias.py` reescrito: parser próprio, tolerante.** Deixou de delegar a `gerar_trem_pendencias.coletar_cards()`, que busca literalmente o heading `## Resposta (marque uma opção)` e **descarta** o card quando não acha opções — o que escondia da tela as pendências multi-pergunta. Agora entende `## Resposta` com ou sem parêntese, `## Pergunta N — …`, `### 1. …`, e checkbox órfão; o que não parseia vira **card cru** em vez de sumir. Efeito medido: a aba passou de 22 para **29 cards** (todas as ativas), incluindo `framework-3-decisoes-auto-avaliacao` e `um-projeto-o-que-fazer-com-achado`.
- Cada opção sai com `line_number`, `label`, `reason`, `marcado` e `kind` (`opcao`/`outra`/`adiar`); o card sai com `estado` derivado do arquivo — `aberta`, `respondida`, `adiada-marcada`, `nao-parseavel` — mais `fonte`, `essencial`, `revisar_quando`, `adiada`.
- **`POST /api/pendencia/responder` — quarto endpoint de escrita.** Marca/desmarca uma opção ou preenche a linha "Outra resposta". Só isso: renomear pra `pendencia-resolvida-*`, escrever `## Resolvida em` e mexer em `**Adiada:**`/`**Fonte:**` continua sendo da skill `rotina-de-avanco`, por contrato ("nunca fecha uma pendência por inferência"). Mesma disciplina do toggle de backlog: arquivo resolvido no servidor a partir do `ref` (nunca path do navegador), linha tem que ser opção de bloco de resposta, concorrência otimista (409 se o arquivo mudou por fora — a rodada agendada roda concorrente), backup antes de gravar, LF/CRLF preservados, lock no módulo.
- **Aba Workflow interativa**: checkboxes reais, badges de categoria/essencial/adiada/estado, "Outra resposta" com campo de texto, `Revisar quando` e `Fonte` visíveis, filtro todas/abertas/respondidas, contador "N aguardando o avanço". Desmarcar existe pra voltar atrás antes da rodada passar.
- **`tests/` — primeira suíte automatizada do projeto** (21 testes, `unittest` stdlib, sem dependência): variantes de formato, CRLF, e todas as regras de escrita (uma linha só muda, 409, path traversal, texto multilinha, backup, `Fonte`/`Adiada` intocados). Rodar com `python -m unittest discover tests`. Já achou um bug real na primeira execução (`relative_to` estourava fora da raiz).

## 0.5.0 — 2026-09-06

Primeiro passo do "explorer pro console operacional" (`plano-console-operacional-2026-09-06.md`) — 3 das 4 frentes propostas, as que não dependiam de nenhuma decisão do usuário além do escopo mais conservador:

- **Aba Workflow** (botão 🔀 na sidebar, `app/workflow.py`): kanban de 3 colunas (`.entrada`/`.pendente`/`.historico`) sobre o índice já existente, lista de pendências ativas (`app/pendencias.py`, reaproveita o parser de `gerar_trem_pendencias.py` em vez de duplicar regex) e um card com a última rodada do `rotina-de-avanco` (`app/avanco.py`, lê `historico.md`). v1 só leitura — decidir uma pendência continua sendo uma sessão do Claude Code (decisão em aberto sobre mudar isso — ver pendência `console-workflow-leitura-ou-escrita`).
- **Nota** (botão 📝 na sidebar, `app/notas.py`) — **terceiro endpoint de escrita**: `POST /api/nota/nova` cria uma Captura crua (SBC) a partir de texto solto sem precisar de sessão do Claude Code — gera ID via `plataforma.py novo-id` (subprocess, nunca import direto — o comando faz `sys.exit()` em erro), grava o arquivo em `.pendente/`, acrescenta linha na seção do dia no LOG central (append-only, lê/escreve sem tradução de fim de linha pra preservar LF/CRLF do arquivo original — mesmo cuidado do toggle de backlog) e ressincroniza `pendentes.md`. Lock serializa criações concorrentes (mesma corrida documentada em `encaminhando-trecho`: dois `novo-id` antes de gravar o LOG geram o mesmo SEQ). Nunca classifica — mesma disciplina da skill de chat equivalente.
- `GET /api/workflow`, `GET /api/avanco`: dois endpoints de leitura novos.
- Testado ponta a ponta no navegador: 2 notas reais criadas pela UI, `plataforma.py verificar` sem PROBLEMA novo, diff do LOG conferido linha a linha (append puro, nenhuma linha existente tocada).
- **Fora desta versão** (decisões do usuário, pendências `console-*` de 2026-09-06): profundidade da captura (com/sem sugestão por IA), decisão inline no Workflow, ordem de ataque das frentes restantes. Frente 4 (Produção = link — completar `portfolio.json` nos 14 projetos que ainda não têm) não implementada nesta rodada.

## 0.4.2 — 2026-09-04

Revisão de manutenção, sem módulo novo (commit `c4ed79f`):

- `app/server.py`: import de `plataforma.py` movido pra dentro do endpoint que usa (import tardio) — o servidor sobe mesmo se `plataforma.py` estiver quebrado, em vez de falhar no boot inteiro.
- `app/server.py`: toggle de checkbox do backlog agora preserva o final de linha original do arquivo (LF ou CRLF) em vez de normalizar pra um só.
- `app/indexer.py`: `.claude/` passou a ser excluído em qualquer profundidade da árvore, não só na raiz.
- `app/indexer.py`: título de arquivo `.py` sem docstring/comentário de título cai pro nome do arquivo, em vez de ficar genérico.
- `app/server.py`: `_LOG_CACHE` é limpo a cada build/reindexação, evitando LOG desatualizado servido do cache.
- `app/metrics.py`: métricas agora cacheadas no `STATE` em vez de recalculadas a cada request.
- `app/metrics.py`: status `'v'` (versão) passou a refletir só a versão, sem misturar outro sinal.
- `app/export_portfolio.py` + `app/portfolio.py`: `repo_publico` e `tags` do portfólio público passaram a vir de `portfolio.py` (fonte única), em vez de duplicados no export.

## 0.4.1 — 2026-09-03

- **Portfólio público** (`python app/export_portfolio.py`): gera `dist/portfolio-seu-beira.html`, a vitrine externa derivada do mesmo inventário da aba Portfólio — só o que faz sentido alguém de fora ver: nome, tipo, status, resumo canônico de `_indice-projetos.md`, link "abrir no ar" quando existe URL pública e "código no GitHub" só se `portfolio.json` marcar `"repo_publico": true` (hoje nenhum). Seções "No ar" e "Em construção", rail com tese do manifesto, contadores e índice. Publicado como Artifact privado. Origem: Captura `26.09.03-SBC-001`; decisões de repos públicos/contato/hospedagem respondidas em 2026-09-03 e já aplicadas nesta versão — ver `_ferramentas/skills/rotina-de-avanco/execucao/pendencia-resolvida-2026-09-03-portfolio-publico-landing.md`.
- `portfolio.json` ganha a chave opcional `repo_publico` (bool).

## 0.4.0 — 2026-09-03

- **Aba Portfólio** (botão 🗂 na sidebar): o hub de tudo que "roda" no `plataforma de origem`, um card por Projeto — link no ar e repositório, launchers (`.bat`/`.exe`/`server.py`) que abrem daqui mesmo, protótipos HTML que abrem renderizados em nova aba, docs e design systems. KPIs no topo, filtros por natureza (no ar / roda local / tem protótipo / tem docs / sem nada), por tipo (DIG/DAD/CON/ADE) e por status, busca livre, e "mostrar rascunhos" pra ver cópias/versões antigas. Pedido do usuário: "um lugar onde vejo todos os executáveis no sentido amplo… o portfólio do Bruno".
- `app/portfolio.py`: inventário por heurística (extensão/nome/pasta) + curadoria opcional em `portfolio.json` na raiz de cada projeto (`estavel`, `estavel_local`, `destaque`, `ocultar`, `tags`, `nota`). Status/resumo vêm de `_indice-projetos.md`; tipo do `CLAUDE.md` ou, faltando, do LOG central; git (remote, último commit, nº de commits) por `subprocess`.
- `GET /files/<path>`: serve qualquer arquivo da raiz (só leitura, nunca `.git`/`node_modules`, sem sair da raiz) — protótipos HTML abrem de verdade, com seus assets relativos. A view de arquivo `.html` passou a usar isso no link "abrir renderizado" (antes era um `file:///` que não funcionava).
- `POST /api/launch`: segundo endpoint com efeito colateral (o primeiro é o toggle de backlog). Só aceita path já classificado como launcher/binário/servidor pelo `portfolio.py`; abre numa janela própria com `start`, cwd na pasta do arquivo; pede confirmação na UI. Snapshot estático responde "somente leitura".
- Export estático inclui o portfólio; classe `static` no `body` desliga links locais e mostra a nota.

## 0.3.0 — 2026-09-02

- **Aba Tour** (botão 🧭 na sidebar): renderiza `_metodo/trilha.md` uma parada por vez (fatiada por `## `), com navegação anterior/próxima, chips de parada, progresso persistido em `localStorage` e links relativos abrindo dentro do próprio app (mesma resolução de `../` que qualquer arquivo). Blocos ` ```mermaid ` são renderizados pelo `mermaid.min.js` **vendorizado** (`app/templates/vendor/`, 10.9.1, MIT, sem CDN — download aprovado pelo usuário na mesma rodada); erro de sintaxe ou lib ausente caem em modo fonte. Origem: Fase 3 do `_metodo/plano-trilha.md`, decisão do usuário "aba Tour na Estação" em vez de HTML standalone.
- **Export estático** (`python app/export_static.py`): gera `dist/estacao-static.html`, um arquivo só com o snapshot do corpus embutido (índice + texto; `.html` truncados em 3000 chars como a UI já mostra) e um `fetch` falso no lugar dos `/api/*` — árvore, busca, LOG, dashboard e Tour funcionam sem servidor; toggle de backlog e reindexar respondem "somente leitura". `--full` gera a variante com `<html>/<head>/<body>` pra abrir direto no navegador. Motivo: o usuário acessa por remote control e `localhost` não chega lá; o snapshot foi publicado como Artifact privado no claude.ai. `marked` e `mermaid` vêm do cdnjs nessa variante. `dist/` gitignored.
- Indexer: tipo novo `trilha` (só `_metodo/trilha.md`), com cor e chip próprios; abrir a trilha pela árvore cai na view de Tour.

## 0.2.0 — 2026-08-31

- Revisão pós-reorganização: uma rodada concorrente do `rotina-de-avanco` mudou boa parte da árvore do `plataforma de origem` (ver CLAUDE.md, seção "Histórico de revisões"). Indexer atualizado: exclui `.claude/`, classifica `doutrina.md` (tipo novo `doctrine`) e `_leia-me.md` (tipo `readme`), expõe `lifecycle_stage` (`.entrada`/`.pendente`/`.historico` de `1-capturas`) com badge próprio na UI.
- Reverificado ponta a ponta no navegador contra o novo estado: árvore com pastas aninhadas (Ideias agora em `<id>/<id>.md`), LOG estruturado, busca, badges.

## 0.1.0 — 2026-08-31

- Primeira versão: indexer, servidor, busca, UI de navegação (árvore + tipo + busca), LOG central estruturado, toggle de checkbox de backlog.
