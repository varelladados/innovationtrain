---
id: trilha
tipo: trilha
---

# Trilha — como esta plataforma funciona

## Parada 1 — Esta plataforma está vazia, e isso é o exercício

Nove capturas, nada mais. Sem notas, sem ideias, sem projetos.

A outra plataforma de exemplo (`exemplo-precos`) já tem tudo: cadeias inteiras,
cadeias que empacaram, uma decisão em aberto. Ela existe para ser **lida**. Esta
existe para ser **dirigida**: você avança, e vê os objetos nascerem.

E quando quiser recomeçar, **reiniciar** devolve tudo ao estado de agora. Nada
aqui é irreversível — mexa sem medo.

## Parada 2 — O que é uma captura

Abra qualquer arquivo de `1-capturas/`. São textos crus: um braindump digitado no
ônibus com três assuntos misturados, um áudio do feirante transcrito sem revisão,
um print de conversa de grupo, o export mal formatado de um caderno antigo.

**Nada disso está arrumado, e está certo assim.** Arrumar é exatamente o que a
passagem para Nota faz. Quem arruma na hora de capturar acaba não capturando —
e a captura é a operação que precisa ser barata, porque é a que acontece com
pressa.

## Parada 3 — A trilha, sete passos

Na barra lateral tem um painel: **trilha de exemplo, passo 0 de 7**. Clique em
**▶** e a plataforma passa para o estado seguinte.

Os passos 1 a 4 seguem um grão: a captura `ideia-no-onibus` — aquela de voltar
da feira pensando em cozinhar com o que já tem — vira a nota **app de receitas
pela despensa**, depois ideia, depois a funcionalidade **busca pelo que tem em
casa** — o momento em que a ideia diz o que vai existir, como se sabe que ficou
pronto, e onde entra —, depois o projeto `exemplo-app-de-receitas`, com pasta,
`CLAUDE.md` e backlog. Repare no passo 4: a funcionalidade é a **primeira
linha** do backlog do projeto que ela fez nascer.

Os passos 5 a 7 fazem um **segundo** grão andar, o da `conversa-sobre-curso`, e
é aí que fica interessante: com dois projetos na mesa, disputando as mesmas
noites da mesma pessoa, nasce a primeira **pendência**. Uma plataforma com um
projeto só não tem decisão nenhuma para tomar.

**Nada é calculado.** Cada passo é uma pasta com a plataforma inteira já naquele
estado, e o botão só a restaura. É um slideshow, não um motor.

Isso é honesto sobre o que a Estação faz e o que ela não faz: numa plataforma
sua, a passagem é **decisão** (os critérios da aba 🧩 Fluxo) e **escrita** (o
texto do estágio novo). Nenhuma das duas cabe num botão. A aba **📋** gera o
briefing para uma sessão de IA fazer a parte da escrita, com você olhando.

**↺ voltar ao início** desfaz tudo, a qualquer momento — então percorra à
vontade.

## Parada 4 — Nada é apagado

Depois do passo 1, repare no que aconteceu com o original: ele não sumiu. Foi
para o `_historico/` do estágio, com o texto preservado como estava e um rodapé
dizendo para onde foi.

Duas coisas ficam garantidas: o texto de cada estágio se preserva, e a parte
ativa da pasta esvazia — que é o que a faz responder "tem coisa por tratar?" de
relance.

Clique no rodapé. Você acabou de percorrer a linhagem, e ela funciona nos dois
sentidos: o item novo tem `origem:` apontando de volta.

## Parada 5 — O registro conta a verdade

`_registro.md` é append-only: linha nenhuma se apaga. A única edição que a
doutrina autoriza é acrescentar o `→` na linha de origem quando algo avança — e
é ela que faz o `_sem-destino.md` parar de cobrar aquele item.

Abra o `_sem-destino.md` agora. No passo 0 ele lista as nove capturas. Depois do
passo 1, oito capturas e uma nota. **Ele é gerado, nunca editado à mão** — é o
retrato honesto do que ainda está por tratar, e ele muda sozinho a cada passo.

## Parada 6 — Quando aparecer uma dúvida de verdade

A pasta `_pendencias/` está vazia no passo 0, de propósito: uma plataforma com
um projeto só não tem decisão para tomar.

Chegue ao **passo 7** e ela deixa de estar. Com o app de receitas e o curso na
mesa ao mesmo tempo, aparece a pergunta que o braindump do ônibus já tinha feito
sem perceber: *"eu fico planejando as seis semanas / as 50 telas em vez de fazer
a primeira"*. Qual dos dois recebe as próximas duas semanas?

A pendência vira carta na aba **🔀 Workflow**, e você responde ali mesmo.

Outro exemplo, de outro tipo, está em `plataformas/exemplo-precos/_pendencias/`:
lá a decisão **trava uma ideia**, e a ideia diz isso no próprio texto.

Ninguém fecha uma pendência por inferência: só a resposta explícita fecha.

## Links

- `_indice.md` — a porta de entrada, com sugestões de por onde começar
- `metodo/classificar.md` — os critérios de cada passagem
- `plataformas/exemplo-precos` — a mesma estrutura, depois de meses de uso
