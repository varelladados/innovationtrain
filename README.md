# Estação

Um app local que organiza ideias em estágios — do que acabou de chegar até o que
virou projeto. Roda no seu computador, em Python puro, **sem instalar nada**.

A Estação **não tem IA dentro.** Você trabalha nela, e ela prepara o texto que
você cola numa sessão de IA quando quiser que algo seja feito. Separar *onde eu
penso* de *onde a IA executa* é a ideia central: a decisão fica visível, escrita
e esperando por você, em vez de acontecer em silêncio três telas atrás.

```
python app/server.py --abrir
```

Abre em `http://127.0.0.1:8744`. No Windows, um duplo clique em
`iniciar-estacao.bat` faz o mesmo — e confere se o Python existe antes de tentar.

---

## Três palavras

| Termo | O que é |
|---|---|
| **Estação** | a aplicação — o que se abre no navegador |
| **Plataforma** | um espaço de trabalho seu: uma pasta, com as suas ideias |
| **Projeto** | cada trabalho dentro de uma plataforma |

Uma Estação opera **várias** plataformas, e troca entre elas sem reiniciar.

## Os cinco estágios

Toda ideia entra crua e vai amadurecendo. As pastas numeradas são esse caminho:

| Pasta | O que tem aqui |
|---|---|
| `1-capturas/` | chegou e ninguém tratou — colado, transcrito, exportado |
| `2-notas/` | já foi lido e organizado |
| `3-ideias/` | tem forma e serve de insumo para outra coisa |
| `4-funcionalidades/` | diz o que vai existir quando estiver pronto, e **onde entra**: num projeto que já existe, ou num novo |
| `5-projetos/` | ganhou corpo próprio: pasta, backlog, git |

O quarto estágio é o que falta na maioria das taxonomias: a maior parte das
ideias com forma não é um projeto novo — é uma peça de um projeto que já
existe. A funcionalidade é a unidade de trabalho, com critério de pronto, que
ou **se acopla** a um projeto de pé ou é a **semente** do próximo.

Ao avançar, o item é **copiado** para o estágio seguinte e o original vai para o
`_historico/` daquele estágio. Duas coisas ficam garantidas: o texto de cada
estágio se preserva como estava, e a parte ativa da pasta continua respondendo
"tem coisa por tratar?" de relance.

**Nada é apagado.** Encerrar é mover para o histórico, nunca remover.

## Se você está começando

Abra o app e vá na aba **🚂 Embarque**. São cinco perguntas, e você sai com um
texto pronto para colar numa sessão de IA — é ele que cria a sua primeira
plataforma. A Estação não cria nada sozinha: ela escreve o pedido, você olha, a
sessão executa.

Sem plataforma nenhuma configurada, o servidor sobe assim mesmo e o Embarque
abre por conta própria — é o único caminho que faz sentido oferecer a quem
acabou de chegar.

**Para ver o sistema funcionando antes de criar o seu**, registre a plataforma
de exemplo:

```
cp estacao.exemplo.json estacao.json      # no Windows: copy
python app/server.py --abrir
```

São **duas**, e elas usam o mesmo método em assuntos opostos de propósito:

| Plataforma | Do que trata |
|---|---|
| `plataformas/exemplo` | cozinha e fotografia — doméstico, sem prazo. Começa com *"comprei coentro de novo"* rabiscado num ônibus e termina num projeto com backlog |
| `plataformas/exemplo-precos` | preços, concorrência e lojas clone — trabalho, com dinheiro e advogada envolvidos |

São duas de propósito, e elas se completam:

- **`plataformas/exemplo` começa vazia** — só nove capturas. Ela vem com uma
  **trilha de sete passos**: um clique e a plataforma inteira passa para o estado
  seguinte, até uma captura virar projeto com backlog — passando pela
  funcionalidade, que é onde a ideia diz o que vai existir e onde entra. **↺ voltar ao início**
  desfaz tudo. Nada é calculado: cada passo é um instantâneo pronto, e o botão só
  o restaura.
- **`plataformas/exemplo-precos` já rodou** — cinco cadeias, das quais **duas
  chegam a projeto e três empacam pelo caminho**, mais uma captura de julho nunca
  tratada que bloqueia uma delas. É o estado normal de uma plataforma de verdade,
  e é a metade que um exemplo costuma esconder.

Uma existe para ser dirigida, a outra para ser lida. Troque entre elas pelo
seletor no topo da barra lateral, sem reiniciar.

A trilha e o reiniciar **só existem nas plataformas de exemplo**: é uma chave do
`plataforma.json` que os libera, e uma plataforma sua não a declara.

## O que tem aqui

```
app/                       o servidor e a interface (stdlib puro, zero dependência)
metodo/                    as regras, a taxonomia, os templates e o utilitário
plataformas/exemplo/       cozinha e fotografia — começa vazia, com uma trilha de 7 passos
plataformas/exemplo-precos/ preços e lojas clone — já povoada, e o que ficou pelo caminho
docs/design-system.md  tokens, temas, fontes e a regra de ouro do CSS
tests/                 137 testes, stdlib, sem dependência
```

| Documento | Do que trata |
|---|---|
| [`metodo/taxonomia.md`](metodo/taxonomia.md) | os nomes: estágios, siglas, arquivos de sistema |
| [`metodo/regras.md`](metodo/regras.md) | as regras permanentes, cada uma com o porquê |
| [`metodo/classificar.md`](metodo/classificar.md) | quando um item passa de estágio |
| [`metodo/versionamento.md`](metodo/versionamento.md) | salvar, publicar, e o que fazer quando der ruim |
| [`CLAUDE.md`](CLAUDE.md) | como a aplicação funciona por dentro |

## Salvar é automático; publicar é decisão

A regra que vale mais que as outras aqui, e a que talvez surpreenda: **a sessão
de IA que trabalha numa plataforma commita sozinha e te avisa o que entrou.** Ela
nunca publica nada sem você dizer sim.

Isso não é descuido — é o oposto. Commit é operação de *segurança*: local,
reversível, não sai da máquina. Push é *publicação*. Tratar as duas com o mesmo
cadeado transforma a proteção em atrito, e o resultado é trabalho perdido. Um
ponto salvo que não foi publicado se desfaz inteiro com `git reset --soft
HEAD~1`, mantendo tudo no lugar: o custo de um commit a mais é zero.

O detalhe está em [`metodo/versionamento.md`](metodo/versionamento.md), escrito
para quem nunca usou git — com o vocabulário traduzido uma vez, o que nunca
fazer **com o motivo junto**, e a seção que falta em todo tutorial: o que fazer
quando der ruim.

## Princípios de construção

- **Stdlib puro.** Zero dependência no Python. No navegador, só `marked.js` e
  `mermaid.js`, vendorizados — nada de CDN.
- **Abre offline.** As três fontes são servidas do próprio repositório. Com o app
  aberto, toda requisição vai para `127.0.0.1`.
- **Nenhum valor literal de cor fora do bloco de tokens**, e há um teste que
  falha o build se um voltar.
- **A Estação lê o git, nunca o executa.** A aba Versões mostra o estado e gera o
  texto; quem roda é a sessão de IA, com você olhando.
- **Todo endpoint de escrita** tem allow-list, trava de concorrência por
  conteúdo (409) e backup antes de gravar.

## Se você for mexer no código

Instale o hook uma vez — ele roda o guarda-corpo antes de cada commit:

```
git config core.hooksPath .githooks
```

A suíte é stdlib pura, sem instalar nada:

```
python -m unittest discover tests
```

O mesmo roda no CI, em Linux e Windows, a cada push.

## Licença

[Apache 2.0](LICENSE).
