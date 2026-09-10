# Changelog — Estação

## 0.9.0 — 2026-09-10

**Um estágio novo entre ideia e projeto: a funcionalidade.** A taxonomia padrão
passa de quatro para **cinco** estágios — capturas → notas → ideias →
**funcionalidades** → projetos —, e a pasta de projetos vai de `4-projetos/` para
`5-projetos/`, porque a numeração carrega a sequência.

**Por quê.** A plataforma em que a Estação nasceu mediu, em uso real, que a
maioria das ideias com forma **não é projeto novo** — é peça de um projeto que
já existe. Sem um estágio entre os dois, essa ideia ou ficava parada em ideias
para sempre, ou virava uma pasta vazia em projetos que mentia no Portfólio. A
funcionalidade é a unidade de trabalho: diz **o que vai existir quando estiver
pronto, para quem, como se sabe que ficou pronto, e onde entra**. Ela ou se
**acopla** a um projeto de pé ou é a **semente** de um novo — a primeira linha
do backlog dele. Decisão registrada em `metodo/taxonomia.md`, parada 6.

- **`metodo/taxonomia.md`** — a tabela dos cinco estágios, a árvore com
  `4-funcionalidades/` e `<projeto>/funcionalidades/`, a exceção ao "copiar com
  identificador novo" (acoplar não muda de estágio, então não ganha identificador
  nem linha nova — só o marcador `→` com a pasta do projeto).
- **`metodo/classificar.md`** — quatro passagens. A 3 (ideia → funcionalidade)
  promove com 2 de 4: comportamento concreto · destino declarado · critério de
  pronto · cabe numa entrega. A 4 tem **dois desfechos**: 4a acoplar a projeto
  existente, 4b corpo próprio (os quatro critérios, juntos).
- **`metodo/templates/funcionalidade.md`** (novo) — com o campo `projeto:` no
  frontmatter e as seções "Pronto quando" e "Onde entra". `ideia.md` ganhou a
  pergunta "onde isso entraria"; `projeto-CLAUDE.md` passa a nascer de uma
  funcionalidade.
- **`app/config.py`** — `PADROES` com o quinto estágio (`FUN`) e
  `projetos.pasta = 5-projetos`. Nada mais no código sabe o nome: a aba Fluxo,
  o Workflow, o Dashboard e o briefing já liam a lista.
- **Embarque** — "Tocar projetos" acrescenta **dois** estágios, não um; sem ele
  a plataforma continua com três.
- **Aba Fluxo** — o conjunto de critérios de cada passagem é escolhido pela
  **sigla de destino**, não pela posição. Uma plataforma lida com taxonomia
  própria (sem `FUN`) cai no alinhamento pelo fim, sem o conjunto de
  funcionalidade — o comportamento de antes.
- **Escala de maturidade** — cinco degraus (`--estagio-5`, classe `est-5`). O
  último continua sendo a cor da marca; o meio foi reespaçado. Documentado em
  `docs/design-system.md`.
- **As duas plataformas de exemplo** passam a cumprir a regra "nenhum item pula
  estágio" também aqui: as quatro cadeias que iam direto de ideia a projeto
  ganharam a funcionalidade no meio (no `_historico/`, com a linha no registro),
  e cada projeto de exemplo tem a funcionalidade que o originou como **primeira
  linha do backlog**. `exemplo-precos` ganhou ainda uma funcionalidade **ativa e
  acoplável** — `alerta de queda acima de 10%`, com `projeto:
  exemplo-monitor-de-precos` —, desmembrada da mesma ideia que originou o
  monitor (a linha `…-d5f0-1` do registro mostra a continuação com sufixo).
- **A trilha da cozinha vai a sete passos**: 3 (a ideia vira funcionalidade) e
  6 (o curso vira funcionalidade) são novos; os demais foram renumerados.
- **Testes** — 175, contra 137: os que fixavam quatro estágios passaram a cobrar
  cinco, a cadeia inteira do exemplo exige `CAP → NOT → IDE → FUN`, e há um
  teste novo que cobra que o exemplo tenha uma funcionalidade ativa apontando
  para um projeto que existe (senão ninguém descobre que o desfecho 4a existe).

**O que este release não faz:** não migra plataforma nenhuma. Uma plataforma
criada antes continua com quatro estágios e abre normalmente — a taxonomia é
dela, no `plataforma.json`. Adotar o quinto é decisão de quem a opera.

## 0.8.5 — 2026-09-09

**A trilha do exemplo vai a cinco passos**, e o quinto é o que ela não tinha:
uma decisão.

Os passos 4 e 5 fazem um **segundo grão** andar — a `conversa-sobre-curso` vira
nota, depois ideia, depois o projeto `exemplo-curso-de-fotografia`. E aí, com
dois projetos na mesa disputando as mesmas noites da mesma pessoa, nasce a
primeira **pendência**: qual dos dois recebe as próximas duas semanas? Uma
plataforma com um projeto só não tem decisão para tomar, e era isso que faltava
para a trilha mostrar o ciclo inteiro.

**Arquivo de sistema deixou de virar carta no trem.** Os `_leia-me.md`
acrescentados na 0.8.4 — para os `_historico/` sobreviverem a um clone — passaram
a ser contados como itens, e a primeira coluna dizia 10 onde havia 9.
`workflow.py` passa a pular nome começado com `_`, que é o que o prefixo já
significa na taxonomia ("maquinário, não conteúdo seu"). Contagem errada num
painel é pior que painel nenhum, e agora há teste.

## 0.8.4 — 2026-09-09

**As duas plataformas de exemplo viram duas trilhas**, e elas passam a se
completar em vez de repetir a mesma coisa.

- **`plataformas/exemplo` (cozinha) começa vazia**: só as nove capturas, nenhuma
  nota, ideia ou projeto. Ela é a que se **dirige**.
- **`plataformas/exemplo-precos` continua povoada.** É a que se **lê**.

**A trilha, e o que ela deliberadamente não é.** A plataforma de cozinha declara
três passos; um clique põe a plataforma inteira no estado seguinte, até a captura
`ideia-no-onibus` virar o projeto `exemplo-app-de-receitas` com backlog. **↺
voltar ao início** desfaz.

Não há motor de promoção, e a ausência dele é a decisão de projeto aqui. Cada
passo é uma pasta em `plataformas/_passos/` com a plataforma inteira já naquele
estado; avançar copia por cima. Numa plataforma de verdade a passagem é
**decisão** (os critérios de `metodo/classificar.md`) e **escrita** (o texto do
estágio novo) — nenhuma das duas cabe num botão, e automatizar a mecânica sem
elas produziria notas que são cópia da captura, ruído com identificador.

- **`metodo/plataforma.py reiniciar [--de <pasta>]`** (novo) — apaga e restaura.
  A lógica destrutiva mora num lugar só, chamável da linha de comando, e o
  **portão** é a chave `estado_inicial` do `plataforma.json`: uma plataforma sua
  não a declara, e o comando recusa antes de olhar o disco.
- **`app/trilha.py`** (novo) — quais são os passos e em qual estamos. O passo
  atual **não é guardado**: é deduzido comparando o `_registro.md` com o de cada
  instantâneo. Sem arquivo de controle para dessincronizar; quem editar o exemplo
  à mão vê "fora dos passos" em vez de um número mentiroso.
- **`tests/test_trilha.py`** (novo) — percorre a trilha inteira numa cópia e
  cobra que voltar ao início devolva o estado **byte a byte**; que as setas do
  registro cresçam passo a passo; que os arquivos constantes não derivem entre os
  instantâneos; e que uma config sem `estado_inicial` recuse restaurar.

**Um falso positivo do guarda-corpo, achado exercitando isto:**
`tests/test_publicacao.py` tratava `26.09.09-PRJ-APP-001-assunto-87eb` como nome
de pasta de projeto de terceiro. Um identificador com tipo declarado tem essa
forma, e o build quebrava. A regex ganhou um lookbehind que separa identificador
(precedido de data) de nome de pasta — e o comentário que documenta isso precisa
trazer o exemplo **com** a data, senão ele próprio derruba o teste.

`tests/test_exemplo.py` passou a separar o que vale para as duas plataformas do
que só vale para uma povoada, com um bloco novo para a que começa vazia: nada
avançou, o registro não tem seta, e há material de sobra no primeiro estágio.

## 0.8.3 — 2026-09-09

**Uma segunda plataforma de exemplo**, e o teste que impede as duas de
apodrecerem.

`plataformas/exemplo-precos` — preços, concorrência e lojas clone. Mesma
estrutura da primeira, assunto oposto de propósito: a de cozinha é doméstica e
sem prazo, esta tem dinheiro, prazo e decisão jurídica. Tudo nela é inventado; os
domínios usam os sufixos reservados pela RFC 2606 (`.example`, `.invalid`,
`.test`), que não resolvem para lugar nenhum.

**O que ela mostra e a primeira não mostrava: o que não avança.** São cinco
cadeias, e só duas chegam a projeto —

| Cadeia | Para onde foi |
|---|---|
| cliente reclamou de preço | **projeto** `exemplo-monitor-de-precos` |
| cliente comprou numa cópia | **projeto** `exemplo-radar-de-clones` |
| planilha de coleta manual | parou **na nota**: dado sujo não vira ideia |
| conversa com a advogada | parou **na ideia**: espera uma decisão em `_pendencias/` |
| a margem do mês encolheu | parou **na ideia**: depende de custo cadastrado |

Mais três capturas cruas — uma delas de **julho**, com os números do reajuste do
fornecedor, que é justamente o que bloqueia a última cadeia. Uma captura não
tratada travando um projeto, visível sem ninguém escrever lembrete: é para isso
que o `_sem-destino.md` existe, e o exemplo antigo não tinha como mostrar.

**`tests/test_exemplo.py` virou bateria parametrizada.** A classe virou mixin e
cada plataforma é uma subclasse de três linhas — 11 testes viraram 22, e um
exemplo novo entra ganhando a bateria inteira. Nenhum teste presume mais nome de
estágio: tudo sai de `config.atual()`. O motivo é direto: exemplo sem teste
apodrece em silêncio, porque ninguém *roda* um exemplo.

`estacao.exemplo.json` passa a registrar as duas, com a de cozinha ativa. Trocar
é pelo seletor, sem reiniciar.

## 0.8.2 — 2026-09-09

**Nenhum nome de plataforma de ninguém dentro do produto.** A publicação tinha
deixado passar uma camada: o vocabulário da plataforma em que a Estação nasceu
ainda estava em comentário, docstring, documentação — e, em alguns lugares, em
*código vivo*.

A correção não foi trocar palavra. O que o app **lê e escreve** virou
configuração, que é o mesmo remédio que o Trecho 3 aplicou à raiz:

- **`config.PADROES["frontmatter"]`** (novo) — `processado`, `nucleo` e `origem`.
  São nomes de campo que o produto grava e procura; estavam literais em
  `indexer.py`, `notas.py`, `metrics.py` e `portfolio.py`. Uma plataforma com
  convenção própria declara a dela e continua sendo lida, sem receber arquivo
  nenhum e sem mudar o produto.
- **`manifesto` e `manifesto_marca`** (novos) — a vitrine lia a frase-tese de um
  caminho fixo. Sem os dois declarados, ela sai sem tese em vez de sair com uma
  frase inventada dentro do código.
- **`export_static.py`** lia o registro por caminho literal; passou a usar
  `config.arquivo_rel("registro")`.
- **O breadcrumb da aba Nota** mostrava um caminho fixo em vez do nome da
  plataforma ativa — o único lugar da interface onde isso ainda aparecia. Agora
  usa `plPrefixo()`, como todas as outras abas.
- **O KPI de núcleo** do Dashboard tinha o nome do campo escrito na interface.
  Agora o rótulo é o nome que a plataforma dá ao campo, e o KPI **some** quando
  ela não declara nenhum — em vez de contar zero como se fosse informação.

Junto: a tabela de-para saiu de `metodo/taxonomia.md`, o `CLAUDE.md` foi
reescrito como o do produto, o changelog foi truncado em 0.8.0 e um papel de
trabalho pré-fork saiu de `docs/`. **A história foi reescrita de novo** — os 15
commits anteriores ao fork descreviam aquele caso aplicado desde a primeira
mensagem e não eram neutralizáveis; a história pública começa na bifurcação.

`tests/test_publicacao.py` ganhou o teste que faltava: ele agora falha o build se
vocabulário de plataforma privada voltar, em arquivo rastreado ou em commit
nenhum. Era a única das quatro proteções que não existia — e a que teria
impedido isto.

## 0.8.1 — 2026-09-09

**A Estação vira pública.** Os três repositórios do hub (`app`, `metodo`,
`plataformas/exemplo`) viraram **um só**, e ele foi publicado sob Apache 2.0.

- **Um repositório.** Quem clona pega o produto inteiro e ele roda de primeira.
  Antes, `app` sozinho gerava um Embarque que apontava para um
  `metodo/plataforma.py` inexistente, e 12 testes pulavam em silêncio. Os
  históricos dos três foram preservados: os commits de `metodo` e de
  `plataformas/exemplo` entraram com as mensagens originais.
- **A raiz do repositório é o hub.** `config.HUB_DIR` deixou de ser
  `PROJECT_DIR.parent` e passou a ser `PROJECT_DIR`; a aba Versões passou a
  mostrar dois repositórios (o seu conteúdo e a ferramenta) em vez de três.
- **`estacao.json` saiu do versionamento** e ganhou um `estacao.exemplo.json`
  como ponto de partida. Sem ele o servidor sobe do mesmo jeito e o Embarque
  abre sozinho — que é exatamente o caminho de quem acabou de clonar.
- **`README.md` e `LICENSE`** (Apache 2.0). O `readme-estacao.md` descrevia o
  app pré-fork e foi substituído.
- **`tests/test_publicacao.py`** — o guarda-corpo: falha se papel de trabalho,
  configuração local ou nome de pasta de projeto de terceiro for versionado.
  Cobra a **forma**, nunca uma lista de nomes.

**O histórico foi reescrito antes de publicar.** Os papéis de trabalho de quem
escreveu o produto — planos, propostas, análise de portfólio, backlogs e a
curadoria de `portfolio.json` — foram removidos de **todos** os commits, junto
com as menções a projetos de terceiros que existiam em comentários de código.
Cinco commits ficaram vazios (só tocavam nesses arquivos) e foram podados: 27
viraram 22, mais 8 vindos de `metodo` e do exemplo. Nenhum hash antigo
sobreviveu, e a verificação foi feita sobre a história inteira antes de existir
qualquer remoto.

## 0.8.0 — 2026-09-09

**A Estação vira produto.** Fork do navegador local que a precedeu, executado em nove trechos. O original continua existindo e servindo o caso para que foi escrito; ele foi somente leitura o tempo todo e não recebeu nenhum arquivo.

### A raiz deixou de ser adivinhada

- **`app/config.py`** (novo) — taxonomia e resolução da raiz num lugar só. A raiz resolve por `--raiz` → `ESTACAO_PLATAFORMA` → plataforma ativa no `estacao.json` → erro em português. **O fallback `PROJECT_DIR.parent` foi removido**: fora da plataforma em que a Estação nasceu ele resolvia para uma pasta qualquer e fazia erro de configuração aparecer como "árvore vazia". Há teste cobrando que não voltou.
- **Onze módulos** deixaram de ter caminho escrito dentro deles. Todos leem `config.atual()` **na hora da chamada**, nunca no import — é isso que faz trocar de plataforma sem reiniciar.
- **Boot tolerante**: `reindex()` nunca levanta; `STATE` ganhou `plataforma_ok`; `_cached()` reconstrói dentro de `try/except` (antes um `OSError` com o índice vazio subia até o `do_GET` e virava traceback).
- **Seletor de plataforma** no topo da barra lateral (`GET /api/plataformas`, `POST /api/plataforma/ativar`).
- `projetos.PASTA_RE` (regex de prefixo) virou `_pasta_valida()`, que confere contra as pastas que existem no disco: allow-list de verdade, e sobrevive à taxonomia sem prefixo.

**Paridade medida, não afirmada:** com os dois lados rodando no mesmo instante contra a mesma plataforma, os resumos de índice, portfólio, métricas, pendências e workflow são iguais. As únicas diferenças são adições de propósito e **uma correção**: a contagem por tipo do Dashboard procurava o tipo em qualquer lugar da coluna Etapa/Tipo e contava o tipo do **destino** em toda linha que já tinha avançado — uma entrada crua, que não tem tipo, aparecia com o tipo do item para o qual a seta apontava. Inflava 8 das 128 linhas.

### Identidade própria, e o vocabulário privado saiu da tela

- **Tema padrão novo** (verde-petróleo sobre cinza-frio) e a paleta dourado/areia anterior preservada como o tema nomeado `areia`. Dois eixos independentes: tema × modo claro/escuro, quatro blocos de token.
- **17 valores de cor** que viviam fora do `:root` (incluindo `#185fa5`, o azul da paleta anterior à migração de agosto) viraram **zero** — e isso virou `tests/test_design_tokens.py`.
- **Duas escalas de cor**: tipo de arquivo na árvore (tokenizado, com par claro/escuro) e `--estagio-1..4`, uma escala de maturidade do apagado ao saturado, no trem e no Portfólio. O itinerário tratava as duas como a mesma coisa; não são — um `backlog-app.md` é do tipo *backlog* **e** está no estágio *projetos*.
- **Escala fechada** de espaço, raio e tipografia. Eram 42 valores de `padding` e 18 tamanhos de letra distintos.
- **As três fontes vendorizadas** (223 KB, subsets latin e latin-ext, licenças OFL 1.1 conferidas nos repositórios de origem). Com o app aberto, **todas** as requisições vão para `127.0.0.1`.
- Rótulo de dashboard, contadores, nome do pipeline e caminho no breadcrumb: tudo saía escrito no código e passou a sair da plataforma ativa. A aba **Fluxo** foi reescrita — era um checklist de passos fixos, agora são N-1 passagens montadas do config.
- **`docs/design-system.md`** e os quatro mockups de aprovação em `docs/mockups/`.

### Duas abas novas

- **🚂 Embarque** (`app/embarque.py`, `POST /api/embarque/prompt`) — cinco paradas, e a pessoa sai com o texto que cria a primeira plataforma. Módulo próprio, com guardrails próprios (não apague nada, se a pasta tiver conteúdo pare e mostre, não commite, caminhos absolutos). **Não escreve em disco.** Abre sozinha quando não há plataforma. Testado executando o prompt gerado, não lendo.
- **📦 Versões** (`app/versoes.py`, `GET /api/versoes`) — painel de respostas a quatro perguntas nos repositórios, não um cliente de git. **Allow-list de subcomando**, todos de leitura; degrada em português quando falta git, remoto ou upstream. A **rede de proteção** ficou visível com as três camadas nomeadas. Os botões geram prompt com o `git status` real embutido; a Estação nunca executa git.

### Versionamento

- O guardrail dos briefings dizia **"Nunca commite automaticamente"** — o oposto da regra 6 da doutrina, escrita depois de perda real de trabalho. Corrigido, e o teste cobra as duas metades.
- O `CLAUDE.md` que o Embarque gera **já nasce com a regra dentro**: é isso que faz a IA do usuário salvar sozinha desde o dia um.
- `metodo/versionamento.md` e `metodo/salvar-tudo.md` (a rotina de fechamento) no hub.

### Launcher e testes

- **A porta tem uma fonte só** (`config.PORTA`). O `.bat` pergunta ao Python; o `launch.json` é o único lugar que repete o número, e um teste cobra que concordem.
- `iniciar-estacao.bat`: confere o Python **antes** (com `pause` se faltar), avisa se a porta está ocupada, e o navegador abre pelo **próprio servidor**, depois de o socket estar escutando.
- **47 → 137 testes.** Novos: `test_config.py`, `test_embarque.py`, `test_versoes.py`, `test_design_tokens.py`, `test_exemplo.py` (o indexer contra plataforma de exemplo, incluindo a cadeia 1→2→3→4 inteira). Os testes deixaram de monkeypatchar constante de módulo e passaram a **aplicar uma configuração** — o mesmo caminho do servidor.


---

**Antes da 0.8.0** a Estação não era um produto: era um navegador local escrito
para um único corpus, com o vocabulário daquele corpus em cada tela e em cada
módulo. A 0.8.0 é o fork que a tornou genérica, e é onde a história deste
repositório começa. As versões anteriores não estão aqui porque descreviam
aquele caso aplicado, que é privado.
