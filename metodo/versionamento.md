# Versionamento — salvar, publicar e o que fazer quando der ruim

> **Este documento ainda não está escrito.** Ele é o Trecho 8 do
> `plano-hub-estacao-e-embarque-2026-09-08.md`, e mora aqui porque é método,
> não código. O arquivo existe desde já para que
> [`regras.md`](regras.md) e [`classificar.md`](classificar.md) não apontem
> para o vazio.

O núcleo, que já vale enquanto o resto não chega — é a
[regra 7](regras.md#7-salvar-é-automático-publicar-é-decisão):

- **Commit acontece sem pedir autorização.** A sessão avisa o que entrou.
- **Push exige autorização explícita e separada**, uma por vez.
- `git add` **nominal**, nunca `git add .` nem `git add -A`.
- Você nunca precisa pensar em *stage*.
- **Salvei sem querer?** `git reset --soft HEAD~1` desfaz o commit e mantém
  todas as mudanças no lugar. É por isso que o automatismo é seguro.

O que falta escrever aqui: a tradução do vocabulário (repositório, commit,
branch, remoto, merge, push, pull) numa tabela; a lista do que nunca fazer,
com o motivo junto; e o que fazer quando o estado sai do caminho feliz.
