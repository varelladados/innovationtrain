# CENTRAL.md — Central

> **Documento** · v0.14.2 · atualizado em 2026-09-19
>
> Este arquivo é lido automaticamente por qualquer sessão do Claude Code que
> abrir nesta pasta — pelo `CLAUDE.md` ao lado, que só contém `@CENTRAL.md`.
> Todo outro arquivo deste tipo continua se chamando `CLAUDE.md`; o da raiz da
> Central é a exceção, e o ponteiro existe porque o Claude Code só carrega
> sozinho um arquivo com aquele nome exato.

## O que é este projeto

A **Central** é onde uma pessoa opera as próprias ideias sem abrir uma sessão de
IA — e de onde ela dispara a sessão quando quiser. Começou como navegador local
de um corpus de markdown: índice, árvore, busca, e um único write (toggle de
checkbox de backlog). Hoje também:

- **captura nota** crua (aba Nota) — a triagem confere o texto antes de gravar:
  o que é trabalho e não carrega dado de ninguém vira item do primeiro estágio,
  com identificador e linha no registro; o resto vai para a espera ou para a
  estação privada, por escolha de quem está na tela;
- **mostra a espera** (aba Triagem) — os lotes que chegaram e ainda não entraram,
  com o que cada um ainda pergunta;
- **responde pendência** (aba Workflow) — grava a opção no próprio `.md`, e a
  rodada seguinte da automação encaminha; o app nunca fecha a pendência;
- **abre projeto** (pelo Portfólio) — maturidade, backlogs com toggle, e anotação
  que vira linha de checkbox no backlog do projeto;
- **gera briefing pra IA** — texto pronto pra colar numa sessão de IA, com
  caminhos reais e os guardrails do método embutidos;
- **mostra o fluxo** (aba Fluxo) — as passagens entre estágios e os critérios de
  promoção;
- **cria as estações padrão** (aba Embarque) — Plataforma, Admin_empresa e
  Vida_Pessoal; cinco perguntas, um prompt.

São nove abas: Workflow, Dashboard, Portfólio, Fluxo, Nota, Triagem, Versões,
Tour e Embarque.

A taxonomia padrão tem **cinco** estágios desde a 0.9.0 (capturas → notas →
ideias → funcionalidades → projetos). O quarto é a unidade de trabalho: uma
funcionalidade ou **se acopla** a um projeto que já existe (mesmo identificador,
linha no backlog do projeto) ou é a semente de um projeto novo. Nada no código
sabe disso por nome — vem de `config.PADROES`, como o resto.

É por isso que ela funciona como **sub-harness**: a IA não roda aqui dentro; a
Central prepara o que entra (contexto + guardrail) e recebe o que sai (decisão,
nota, anotação), sempre no formato que a automação já lê.

## Como rodar

```
python app/server.py
```

Abre em `http://127.0.0.1:8744`. `app/templates/index.html` é lido fresco do
disco a cada request — não precisa reiniciar o servidor pra mudança de
HTML/CSS/JS, só pra mudança em arquivo `.py`.

## A raiz não é adivinhada — ela é resolvida

A Central **não assume** que mora dentro da estação que lê. A raiz resolve
nesta ordem, em `config.resolver()`:

1. `--raiz <pasta>` na linha de comando;
2. a variável de ambiente `CENTRAL_ESTACAO`;
3. a estação marcada `ativa` no `central.json` do hub;
4. erro em português, dizendo as três saídas acima.

Os nomes até a 0.9 continuam valendo nesta versão, só para leitura:
`ESTACAO_PLATAFORMA`, `ESTACAO_HUB`, o `estacao.json` na raiz da Central, a chave
`plataformas`, o `plataforma.json` de cada estação e o `metodo/plataforma.py` —
que virou um shim de poucas linhas para `estacao.py`. Há estações de fora deste
repositório que ainda usam esses nomes; a escrita é sempre no nome novo.

**Não existe fallback para `PROJECT_DIR.parent`**, e a ausência dele é
deliberada: fora da estação em que a Central nasceu ele resolvia para uma
pasta qualquer e fazia erro de configuração aparecer como "árvore vazia". Há um
teste que cobra que ele não voltou (`test_config.py`).

Quando **nada** resolve — o caso de quem acabou de clonar — `config.iniciar()`
não levanta: devolve `sem_estacao()`, o servidor sobe e a aba Embarque abre
sozinha. É o único caminho que faz sentido oferecer a quem chega.

## As estações padrão

Toda Central começa com três estações, e as três são trens: a
**Plataforma** (os cinco estágios — o trem de inovação), a **Admin_empresa**
e a **Vida_Pessoal** (captura, nota, ideia). Quais são mora em
`config.MODELOS`, a cópia executável de `metodo/taxonomia.md`; a chave
`modelo` do `estacao.json` diz qual cada estação segue, e sem ela vale
`plataforma`.

Três regras que o código cobra:

- **`"projetos": null` não é `"pasta": ""`.** O primeiro diz "não há
  projetos" e tira o Portfólio da barra; o segundo diz que os projetos moram
  na raiz.
- **A estação privada não sai daqui.** `config.recusar_se_privada()` barra o
  snapshot estático e a vitrine; a aba Versões não oferece git; o `.gitignore`
  da Central deixa de fora toda estação criada em `estacoes/` que não seja
  exemplo. Quem cobra as três é `tests/test_estacoes_padrao.py`.
- **A espera mora na privada.** O Embarque escreve a chave `triagem` em cada
  estação que cria, com os caminhos vistos da raiz dela: `pessoal` e `espera`
  apontam para a Vida_Pessoal e para `_triagem/` dentro dela; `administrativo`,
  para a Admin_empresa. Que estação recebe cada esfera está no campo `esfera`
  de `config.MODELOS`; o nome da pasta, em `config.ESPERA`. Estação que a pessoa
  já tinha não vira espera — o texto não tem como conferir que ela é privada.
  Quem cobra é `tests/test_embarque.py`, executando o texto.

## Nada de estação fica escrito no código

Tudo que é nome de estação sai de `config.atual()`, **lido na hora da
chamada**, nunca no import — é isso que faz o seletor trocar de estação sem
reiniciar o servidor. Isso vale para seis famílias de coisa, e a terceira é a que
se esquece:

| Família | Onde é declarada | Exemplos |
|---|---|---|
| **Taxonomia** | `estagios`, `siglas`, `tipos`, `historico` | pastas, nomes, siglas dos estágios |
| **Caminhos** | as chaves opcionais (`perfis`, `trilha`, `pendencias`, `manifesto`…) | onde cada coisa mora dentro da estação |
| **Campos de frontmatter** | `frontmatter.processado` · `.nucleo` · `.origem` | os nomes de campo que o app **lê e escreve** |
| **Siglas de uma taxonomia anterior** | `siglas_legadas` | `{sigla: nº do estágio}` — lidas em todo lugar, nunca emitidas |
| **Duplicatas que o acervo já trouxe** | `duplicatas_historicas` | identificadores repetidos de antes da convenção `-N`: viram AVISO, não PROBLEMA |
| **Triagem** | `triagem` | onde ficam a espera e a estação pessoal, o de-para dos projetos (esfera e apelidos) e o vocabulário de cada esfera |

A terceira existe porque nome de campo é comportamento, não prosa: o app grava
`<processado>: <id>` no arquivo que cria e procura esse mesmo campo depois. Se
ele estivesse escrito no código, uma estação com convenção própria só poderia
ser lida mudando o produto. Chave ausente degrada: sem `nucleo`, a métrica
correspondente simplesmente **sai** do dashboard, em vez de contar zero como se
fosse informação.

O `config.PADROES` é a cópia executável de `metodo/taxonomia.md`. Mudou lá, muda
aqui — e há um teste que compara os dois.

## Estrutura

```
central/                  ← a raiz do repositório É o hub
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
│   ├── embarque.py       POST /api/embarque/prompt — o texto que cria as estações padrão
│   ├── versoes.py        GET /api/versoes — leitura do git, allow-list de subcomando, só leitura
│   ├── trilha.py         a trilha das estações de exemplo — restaura instantâneos, não promove nada
│   ├── triagem_ui.py     o portão da aba Nota e a aba Triagem — importa metodo/triagem.py, detector é um só
│   └── templates/
│       ├── index.html    UI de página única
│       └── vendor/       marked.min.js + mermaid.min.js e as três fontes .woff2 — sem CDN
├── metodo/               princípios, regras, taxonomia, classificar, maturidade, promoção, triagem, versionamento, salvar-tudo e os templates
│   ├── estacao.py        o utilitário: novo-id, gerar-sem-destino, verificar, reiniciar
│   ├── plataforma.py     o nome dele até a 0.9 — poucas linhas que chamam o estacao.py
│   ├── trava.py          a trava do registro: uma captura por vez na estação, entre processos
│   └── triagem.py        o passo antes da captura: levantamento, relatório e aplicar
├── estacoes/            as de exemplo; as suas, que o Embarque cria aqui, ficam fora do git
│   ├── exemplo/          cozinha e fotografia — começa vazia, com uma trilha de 7 passos
│   ├── exemplo-precos/   preços e lojas clone — já povoada, para ser lida
│   ├── _inicial/         cópias intactas das duas: é delas que "voltar ao início" copia
│   └── _passos/          os estados seguintes da trilha do exemplo
├── tests/                a suíte, stdlib, sem dependência
├── docs/                 design-system.md e os mockups de aprovação
├── cache/                index.json + backups/, gitignored
├── CENTRAL.md            este arquivo — e CLAUDE.md, a linha que aponta para ele
├── README.md  LICENSE    a porta de entrada pública e a Apache 2.0
├── VERSION               a versão, e changelog-central.md o que mudou em cada uma
├── iniciar-central.bat   o duplo clique do Windows — confere o Python e pergunta a porta a ele
├── central.exemplo.json  template — copie como central.json (que é gitignored)
├── .githooks/ .github/   o guarda-corpo antes do commit e o CI em Linux e Windows
├── .claude/launch.json   o servidor para o painel de pré-visualização do Claude Code
└── pendencias/           decisões de quem usa; fora do versionamento
```

**Isto era três repositórios até 2026-09-09** (`app`, `metodo`,
`estacoes/exemplo`, dentro de um hub). Na publicação viraram um só: quem
clona pega o produto inteiro e ele funciona de primeira. O efeito colateral bom
é que os testes de `test_exemplo.py` e o de taxonomia deixaram de pular em
silêncio — antes dependiam de repositórios irmãos que um clone não trazia.

## Convenção de nomes que o indexer pressupõe (fonte de verdade: `indexer.py`)

O classificador é escrito em cima desta convenção — não invente exceção sem
atualizar os dois juntos:

| Padrão de nome | Tipo | Observação |
|---|---|---|
| `<prefixo>*.md` | `orquestra` | o prefixo de índice é declarado pela estação (`indice_prefixo`); sinaliza "isto é um índice de pasta" |
| o documento de `trilha` | `trilha` | **caso único** — abre na aba Tour, não como markdown comum |
| `CLAUDE.md` | `orquestra` | **exceção sem prefixo** — nome fixado pelo Claude Code (auto-carrega como contexto do projeto); nunca renomear |
| `CENTRAL.md` | `orquestra` | o arquivo da raiz da Central — o `CLAUDE.md` ao lado dele é só `@CENTRAL.md` |
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

Uma estação pode dividir um estágio em subpastas de **triagem**, ortogonais à
etapa: o que entrou e ninguém tocou, o que está pendente, o que já foi
encaminhado. A estação declara quais são em `ciclo_vida`; o indexer expõe
isso como `entry.lifecycle_stage`, derivado só do caminho
(`indexer.py::lifecycle_stage`), e a UI mostra um badge de cor por estágio. Na
taxonomia padrão a única subpasta é o `_historico/` de cada estágio.

## Exclusões do indexer

O padrão está em `config.PADROES["excluir"]` (`.git`, `node_modules`,
`__pycache__`, `.claude`, `dist`, `build`) e **cada estação acrescenta o que
quiser** no `estacao.json` dela — acervos externos, pastas de build de
projetos, o que não deve entrar em varredura. Nada disso é escrito no código.

## A trilha de exemplo — e por que ela não é um motor

As duas estações de exemplo declaram `estado_inicial`, e a de cozinha declara
também `tutorial.passos`. Isso liga duas coisas na interface: **voltar ao
início** e **avançar a trilha**.

**Não há promoção acontecendo.** Cada passo é uma pasta em `estacoes/_passos/`
com a estação inteira já naquele estado; avançar copia essa pasta por cima. A
lógica destrutiva mora num lugar só — `metodo/estacao.py reiniciar`, chamado
por subprocess, o mesmo caminho de `novo-id`.

A fronteira é deliberada e vale a pena entender antes de propor mudá-la: numa
estação de verdade, a passagem entre estágios é **decisão** (os critérios de
`metodo/classificar.md`) e **escrita** (o texto do estágio novo). Um botão não faz
nenhuma das duas. Automatizar a mecânica sem elas produziria notas que são cópia
da captura — ruído com identificador. A trilha mostra **como fica**; quem faz
acontecer numa estação sua é uma sessão de IA com o briefing da aba 📋.

| Peça | Onde |
|---|---|
| Quais são os passos, e em qual estamos | `app/trilha.py` |
| Apagar e restaurar | `metodo/estacao.py reiniciar [--de <pasta>]` |
| O portão | a chave `estado_inicial` — **uma estação sua não a declara** |

O passo atual **não é guardado**: é deduzido comparando o `_registro.md` da
estação com o de cada instantâneo. Sem arquivo de controle para
dessincronizar, e quem editar o exemplo à mão vê "fora dos passos" em vez de um
número mentiroso.

Editou um arquivo constante do exemplo (`_indice.md`, `CLAUDE.md`…)? **Propague
para os instantâneos**, senão o primeiro "voltar ao início" desfaz a edição em
silêncio — `tests/test_trilha.py` cobra isso.

## Endpoints de escrita — tabela

| endpoint | escreve | módulo | trava de segurança |
|---|---|---|---|
| `POST /api/backlog/toggle` | `- [ ]`/`- [x]` em backlog | `server.py` | tipo `backlog` no índice + `expected_text` (409) + backup |
| `POST /api/nota/nova` | item novo no estágio de entrada + linha no registro **ou**, conforme `destino`, lote na espera / captura na estação privada | `notas.py`, `triagem_ui.py` | **triagem antes de gravar** (409 com o que ela viu, mascarado; terceiro e segredo nunca viram captura profissional). Por destino: **profissional** — identificador via utilitário (subprocess) + trava do registro (vale entre processos) + arquivo atômico + registro append-only com backup; **pessoal** — o mesmo, com o registro gravado de uma vez e **sem cópia para o cache** (o `cache/` é da estação aberta, e a pessoal é outra); **espera** — pasta nova + linha append-only no `_lotes.md`, nada é sobrescrito |
| `POST /api/pendencia/responder` | opção / "Outra resposta" de pendência | `pendencias.py` | `ref` validado + linha tem que ser opção + `expected_text` (409) + backup |
| `POST /api/projeto/anotar` | `- [ ] …` no backlog do projeto | `projetos.py` | allow-list do índice + `expected_sha1` (409) + backup |
| `POST /api/exemplo/passo` | a estação de exemplo inteira, no passo pedido da trilha | `trilha.py` → `metodo/estacao.py reiniciar` | só existe em estação que declara `estado_inicial` (uma sua não declara); cada passo é um instantâneo pronto — nada é calculado, e o de origem continua em `estacoes/_inicial/` |

`POST /api/estacao/ativar` e `POST /api/embarque/registrar` escrevem **só no
`central.json` do hub** — que é config de quem usa, não corpus de estação. Por
isso não passam pela disciplina acima; a trava deles é outra: caminho tem que
estar registrado (ou ser acrescentado por eles), e nada é tocado dentro de
estação nenhuma.

### Endpoints que **não escrevem em disco** — e é de propósito

| endpoint | o que faz | por que não escreve |
|---|---|---|
| `GET /api/briefing` | texto pra colar numa sessão de IA | a IA é que executa, com o humano olhando |
| `POST /api/embarque/prompt` | texto que **cria as estações padrão** | é POST porque a entrada é um objeto de respostas, não porque escreve |
| `GET /api/embarque/modelos` | nome, pasta e propósito das estações padrão | é leitura de `config.MODELOS` |
| `GET /api/versoes` | estado do git dos repositórios | allow-list de subcomando, todos de leitura |
| `GET /api/versoes/prompt` | "salvar um ponto", "mandar pra nuvem", "linha nova" | a Central lê o git e gera o texto; **nunca o executa** |
| `GET /api/triagem` | os lotes na espera, o que cada um já leu e as perguntas abertas | aplicar um destino é trabalho do utilitário, com o `decisoes.json` respondido; o snapshot estático recusa a rota, porque a espera mora na estação privada |

Sobre `versoes/prompt`: automatismo de commit mora onde a IA está, não numa
interface web onde um botão um dia é clicado sem querer. Ver
`metodo/versionamento.md`.

`POST /api/launch` abre executável local (efeito colateral, não escreve arquivo).
Toda escrita nova segue a mesma disciplina — ver a seção abaixo antes de somar a
sexta.

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
solto, sem sessão de IA. Regras (`app/notas.py`): o utilitário da estação é
chamado via `subprocess` (nunca import — `novo-id` faz `sys.exit()` em erro, o
que mataria o servidor); grava o `.md` com gravação atômica (`os.replace`);
acrescenta uma linha na seção do dia do registro central — nunca edita linha
existente (o registro é append-only), lê e escreve sem tradução de fim de linha
pra preservar LF/CRLF do arquivo original. Nunca classifica: o item nasce sempre
no primeiro estágio — ou, se a triagem mandar, na espera ou na estação privada,
nunca em outro estágio.

**Uma captura por vez em cada estação, venha de onde vier.** `novo-id` acha a
sequência do dia lendo o registro, e a captura reescreve o registro com a linha
nova: duas ao mesmo tempo pegam o mesmo número, e a segunda reescrita apaga a
linha da primeira. São duas travas, e a ordem é sempre esta: um
`threading.Lock()` enfileira as threads do servidor, e a **trava do registro**
(`metodo/trava.py`) enfileira os processos — a linha de comando
(`triagem.py aplicar`) grava no mesmo registro que a interface. A segunda é do
sistema operacional (`flock` no Linux, `msvcrt.locking` no Windows) sobre um
`_registro.md.trava` ao lado do registro, e disso saem as duas propriedades que
importam:

- **processo que morre não trava a estação** — quem solta é o sistema, sem PID
  gravado nem idade de arquivo para adivinhar;
- **o arquivo só existe enquanto uma captura grava** — quem solta, apaga. Uma
  trava permanente apareceria no `git status` de toda estação versionada, e o
  `.gitignore` de uma estação que já existe não é da Central para editar. O
  `*.trava` do `.gitignore` do Embarque e do da Central cobre só esse instante, e
  o que sobra de um processo que morreu no meio (a captura seguinte o leva).

A captura **pessoal** (`triagem_ui.captura_pessoal` → `triagem.capturar`) segue
a mesma mecânica, com as mesmas duas travas (a do registro é a da estação
pessoal), e grava o arquivo e o registro de uma vez (temporário + `replace`),
recusa identificador que já existe e apaga o arquivo se o registro falhar. Ela
**não** copia o registro para `cache/backups/`: o `cache/`
guarda o que é da estação que a Central está operando, e a pessoal é outra — e
privada. A proteção é a gravação de uma vez; o histórico dela é o git dela.

### A disciplina que todo endpoint de escrita segue

`POST /api/backlog/toggle` foi o primeiro e definiu o padrão: só aceita arquivos
classificados `backlog`; confere concorrência otimista (a linha precisa bater com
o que foi lido antes de gravar, senão 409); troca só `- [ ] `/`- [x] ` naquela
linha específica; faz backup em `cache/backups/` antes de gravar. Qualquer
escrita nova precisa passar por esse mesmo cuidado primeiro.

Como cada projeto pode ter git próprio, marcar um checkbox lá aparece como
alteração não commitada naquele repositório — revisão e commit são de quem usa; a
Central nunca commita em nome de ninguém.

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
- **Este repositório é público, e nenhum nome de estação de ninguém entra
  nele.** São **quatro camadas**, e a ordem importa — cada uma pega o que a
  anterior deixou passar:

  | # | Camada | Onde | Pega o quê |
  |---|---|---|---|
  | 1 | **Não está na pasta** | `central.json` e `pendencias/` fora do versionamento | o que nunca entra não vaza |
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
- **Aba nova exige três pontos**, e esquecer o segundo é silencioso: o botão
  dentro de `<nav id="nav-abas">`, com o ícone em `<span class="ic">`; a chamada
  `marcarAba("<id-do-botão>")` na função que abre a aba — sem ela a aba abre e o
  botão não acende; e o listener no bloco final de `addEventListener`. O estilo
  vem de `#nav-abas button`, sem id nenhum no CSS. Ver `docs/design-system.md`.
- **Salvar é automático; publicar é decisão** — `metodo/regras.md`, regra 7,
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
- [`metodo/principios.md`](metodo/principios.md) — o que é permanente no método
- [`metodo/taxonomia.md`](metodo/taxonomia.md) — os nomes, e a fonte de `config.PADROES`
- [`metodo/maturidade.md`](metodo/maturidade.md) — a maturidade 0–5 × 6 que a aba Portfólio lê dos perfis, e a ordem de ataque
- [`metodo/promocao.md`](metodo/promocao.md) — quando um padrão de uma estação vira parte do método
- [`docs/roteiros.md`](docs/roteiros.md) — três roteiros para apresentar o método
- [`metodo/regras.md`](metodo/regras.md) — as regras permanentes, cada uma com o porquê
- [`metodo/triagem.md`](metodo/triagem.md) — pessoal × profissional, dado de terceiro e segredo, antes da captura (e a aba Triagem, que mostra a espera)
- [`metodo/versionamento.md`](metodo/versionamento.md) — salvar, publicar, e o que fazer quando der ruim
- [`docs/design-system.md`](docs/design-system.md) — tokens, temas, fontes e a regra de ouro do CSS
