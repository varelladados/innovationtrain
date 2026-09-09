---
titulo: Trilha desta plataforma
---

# Trilha — como esta plataforma funciona

## Parada 1 — O que é isto

Uma plataforma é um espaço de trabalho: um lugar onde as suas ideias entram
cruas e vão amadurecendo. Esta aqui é um **exemplo**, com conteúdo sobre
cozinha e fotografia, para você ver como fica quando está sendo usada.

A Estação — o app que você está olhando agora — opera plataformas. Ela pode
operar várias; o seletor no topo da barra lateral troca entre elas.

## Parada 2 — Os quatro estágios

Toda ideia entra pelo mesmo lugar e vai subindo:

**Captura** → chegou, ninguém tratou. Colar mal formatado aqui é o
comportamento certo.

**Nota** → alguém leu e organizou. Já dá para entender sem esforço.

**Ideia** → tem forma própria. Serve de insumo para outra coisa sem
reprocessar.

**Projeto** → ganhou corpo: pasta, backlog, histórico próprio.

As pastas são numeradas (`1-capturas`, `2-notas`, `3-ideias`, `4-projetos`)
porque a numeração carrega a sequência.

## Parada 3 — Nada é apagado

Quando um item avança, ele é **copiado** para o estágio seguinte e o original
vai para o `_historico/` daquele estágio. Duas coisas ficam garantidas: o texto
de cada estágio se preserva exatamente como estava, e a parte ativa da pasta
continua respondendo "tem coisa por tratar?" de relance.

Abra `1-capturas/_historico/` e depois `1-capturas/`. A diferença entre as duas
é a diferença entre o que já foi tratado e o que espera.

## Parada 4 — Siga um grão

Vá em `1-capturas/_historico/` e abra
`26.08.24-CAP-001-ideia-no-onibus-4f21`. É um rabisco de ônibus: "comprei
coentro de novo".

Ele virou uma nota, que virou uma ideia, que virou o projeto
`exemplo-app-de-receitas`. Cada arquivo diz de onde veio, no campo `origem:`, e
para onde foi, no `avancou_para:`. O `_registro.md` mostra a mesma cadeia em
forma de tabela.

Essa é a coisa toda: **nenhuma ideia se perde entre "tive um insight" e "estou
fazendo"**.

## Parada 5 — O registro e o que falta

`_registro.md` é a linha do tempo. Append-only: linha nenhuma é editada ou
apagada — quando algo avança, a linha antiga ganha uma seta e o item novo ganha
linha própria.

`_sem-destino.md` é **gerado** a partir dele: é a lista do que ainda não
avançou. Se ela está grande, é sinal de caixa de entrada acumulando — não de
erro.

## Parada 6 — As decisões

Nem toda dúvida se resolve sozinha. Quando uma decisão depende de você, ela
vira uma **pendência**: uma pergunta objetiva, com opções e o motivo de cada
uma, esperando na aba Workflow.

Tem uma aberta agora. Ela é real: pergunta se a lista de compras pelo cardápio
é um projeto próprio ou uma tela do app de receitas. Responda ali e veja o que
acontece.

## Links

- `_indice.md` — a porta de entrada desta plataforma
