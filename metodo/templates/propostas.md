# Modelo: `propostas-<AAAA-MM-DD>.md` de um projeto

Uma rodada de portfólio mede cada projeto pelo disco ([`../maturidade.md`](../maturidade.md))
e escreve, para cada um, um arquivo de propostas. **Uma feature proposta não é
item de backlog:** só vira quando o dono aceita. Toda feature diz qual
experiência ela muda — **UX** (uso), **CX** (a jornada de quem usa), **IX**
(interação e interface) ou **HX** (o humano: confiança, privacidade,
acessibilidade).

```markdown
---
projeto: <nome>
gerado_em: AAAA-MM-DD
origem: <quem gerou — rodada de portfólio de AAAA-MM-DD>
---

## Diagnóstico em 5 linhas

## O que mudou desde a rodada anterior
<!-- a maturidade antes → depois, e o que aconteceu com as propostas anteriores -->

## Propostas de melhoria
<!-- [SUST] sustentação ou [INCR] incremento · o quê / por quê / esforço / impacto -->

## N novas features
<!-- F1…FN: problema · para quem · lente (UX/CX/IX/HX) · plano (passos, horas,
     pronto quando…) · depende de · reaproveita de · [ ] aceita [ ] recusada [ ] depois -->

## Cruzamentos com o portfólio
<!-- o que este projeto dá aos outros e o que recebe -->

## Pendências que só o dono resolve
<!-- cada uma com duas ou três opções e a razão de ser pendência -->
```

**Regra de mistura:** pelo menos duas features com uso concreto de IA, pelo
menos uma de CX ou HX, e todas coerentes com a maturidade real do projeto — nada
de propor observabilidade para o que ainda é esboço.

As propostas de uma rodada ganham a data da rodada no nome, e as anteriores
ficam: apagar é sempre lógico ([regra 1](../regras.md)).
