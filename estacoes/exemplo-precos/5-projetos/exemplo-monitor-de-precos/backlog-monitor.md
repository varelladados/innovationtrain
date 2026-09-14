# Backlog — Monitor de preços

> Itens marcados **[ESSENCIAL]** são pré-requisito para o projeto sair do papel.

## Agora

- [ ] **Coleta diária de preço e frete** — a funcionalidade que originou o projeto
      (`26.07.26-FUN-001-coleta-diaria-de-preco-e-frete-4e63`)
- [ ] **[ESSENCIAL]** Ler os termos de uso dos quatro sites antes de coletar
      qualquer coisa — se algum proibir, ele sai da lista
- [ ] **[ESSENCIAL]** Definir os 20 produtos observados (não o catálogo inteiro)
- [x] Guardar frete junto com o preço, desde a primeira coleta — decidido pela
      nota `26.09.06-NOT-001`, antes de existir uma linha de código
- [x] Fixar um CEP de referência para a simulação de frete

## Depois

- [ ] Destacar queda maior que 10% desde a última segunda — vai chegar
      como a funcionalidade `26.09.08-FUN-001-alerta-de-queda-acima-de-10-por-cento-3f7b`,
      ainda em `4-funcionalidades/`, esperando ser acoplada
- [ ] O que fazer quando o site muda de layout e a coleta quebra em silêncio
- [ ] Cadastrar custo de reposição — pré-requisito do alerta de margem
      (`26.09.07-IDE-001`, ainda em `3-ideias/`)

## Não vamos fazer

- [ ] ~~Coletar o catálogo inteiro dos concorrentes~~ — o estagiário já provou
      que volume sem regra vira dado sujo (`26.08.19-NOT-001`)
