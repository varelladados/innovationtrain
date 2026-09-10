---
id: trilha
tipo: trilha
---

# Trilha — como esta plataforma funciona

## Parada 1 — O que é isto

Uma plataforma de exemplo sobre um assunto de trabalho: acompanhar o preço dos
concorrentes e descobrir quem está se passando pela sua loja.

A loja, os concorrentes, os domínios e as pessoas são **inventados**. O que é
real é a forma: como uma frase solta vira nota, como uma nota vira ideia, e como
uma ideia vira projeto com backlog — ou não vira, e fica no meio do caminho.

Ela é irmã de `plataformas/exemplo` (cozinha e fotografia). As duas usam o mesmo
método em assuntos opostos de propósito: uma é doméstica e sem prazo, a outra
tem dinheiro e advogada envolvidos.

## Parada 2 — Os cinco estágios

`1-capturas/` é o que chegou e ninguém tratou: um áudio transcrito sem revisão,
domínios colados de um grupo de WhatsApp, um print. Texto cru, sem forma.

`2-notas/` é o mesmo material depois de lido: a reclamação de preço vira "as
reclamações se concentram no fim de semana, e a causa é mecânica".

`3-ideias/` tem forma própria e serve de insumo: "guardar a série, não o print".

`4-funcionalidades/` diz o que vai existir quando estiver pronto, e onde entra:
"uma coleta por dia, de 20 produtos, com preço e frete — num projeto novo". Ou,
no caso do alerta de queda, "dentro do monitor, que já existe".

`5-projetos/` ganhou corpo — pasta, `CLAUDE.md`, backlog.

A regra que faz isso funcionar: **capturar é barato, organizar é uma etapa
própria.** Quem tenta organizar na hora de capturar acaba não capturando.

## Parada 3 — Nada é apagado

Quando um item avança, ele é **copiado** para o estágio seguinte e o original vai
para o `_historico/` daquele estágio, com um rodapé dizendo para onde foi.

Duas coisas ficam garantidas: o texto de cada estágio se preserva como estava, e
a parte ativa da pasta continua respondendo "tem coisa por tratar?" de relance.

## Parada 4 — Siga um grão

Abra `1-capturas/_historico/26.07.20-CAP-001-cliente-reclamou-do-preco-4c19.md`.
É um desabafo depois do terceiro cliente reclamando de preço.

O rodapé dele leva à nota. A nota leva à ideia. A ideia leva à funcionalidade —
a coleta diária, com critério de pronto. A funcionalidade leva ao projeto
`exemplo-monitor-de-precos`, com backlog e uma lista de produtos observados, e
ela é a primeira linha desse backlog.

Cinco cliques, e você viu uma irritação virar trabalho. Repare que o backlog do
projeto **cita as notas** que decidiram cada item: "guardar frete junto com o
preço" já está marcado como feito, decidido por uma nota antes de existir uma
linha de código.

## Parada 5 — O que ficou pelo caminho

Esta é a parada que o exemplo da cozinha não tem, e é a mais realista.

Olhe `_sem-destino.md`: nove itens sem destino. Um deles é
`26.07.14-CAP-001-audio-transcrito-do-fornecedor` — de **julho**. Tem os números
do reajuste do fornecedor, e é justamente o que falta para o alerta de margem
(`26.09.07-IDE-001`) sair da ideia.

Ou seja: uma captura não tratada está bloqueando um projeto, e isso fica
visível. Não porque alguém escreveu um lembrete — mas porque o registro não
mente sobre o que não avançou.

## Parada 6 — As decisões

`_pendencias/` guarda o que depende de você. A pendência aberta aqui é real no
sentido que importa: **notificar toda cópia encontrada, ou só quando o volume
justificar?**

Ela trava a ideia `26.08.30-IDE-001`, e a ideia diz isso em voz alta no próprio
texto. Ninguém fecha uma pendência por inferência — só a resposta explícita
fecha.

## Links

- `_indice.md` — a porta de entrada desta plataforma
- `metodo/classificar.md` — os critérios de cada passagem
