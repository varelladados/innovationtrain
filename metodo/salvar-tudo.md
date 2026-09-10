# salvar-tudo — a rotina de fechamento de sessão

> **Invoque pelo nome:** diga *"roda o salvar-tudo"* numa sessão de IA que esteja
> trabalhando nesta plataforma. A sessão segue o que está escrito aqui.
>
> É a peça mais importante do versionamento, e não é a tela: é isto. Uma regra
> escrita num documento que ninguém lê não protege ninguém. Esta rotina **roda**,
> e é ela que faz a [regra 7](regras.md#7-salvar-é-automático-publicar-é-decisão)
> acontecer de fato no fim de toda sessão.

---

## O que ela faz, em uma frase

Varre os repositórios, separa o que **esta sessão** mudou do que mudou por outra
origem, salva o que é da sessão, e **reporta**. Nunca pergunta.

---

## Quando roda

- **Ao encerrar a sessão.** Sempre. Nunca encerre deixando mudança sua sem
  ponto salvo.
- **Ao terminar um artefato** — um plano, um relatório, uma análise.
- **Antes de operação de risco** — renomear em massa, migrar, mexer em muitos
  arquivos de uma vez.

---

## Os passos

### 1. Descubra quais repositórios existem

Podem ser mais de um. O caso comum:

- a **plataforma** (esta pasta);
- cada **projeto** dentro de `5-projetos/`, quando tem `.git` próprio;
- e, se você estiver mexendo neles, o **método** e a **aplicação** do hub.

Para cada um, rode `git status --porcelain=v1 -b` e guarde a saída.

### 2. Separe o que é seu do que não é

Esta é a parte que exige julgamento, e é o motivo de a rotina não ser um script.

**É da sessão:** todo arquivo que **você** criou ou editou nesta conversa. Você
sabe quais são — não deduza pela data de modificação.

**Não é da sessão:** tudo o mais. Um editor aberto noutra janela, uma automação
agendada, outra sessão de IA rodando em paralelo, o próprio usuário mexendo em
outra coisa. Isso acontece de verdade e não é hipótese.

**O que não é da sessão fica de fora**, e entra no relatório numa lista à parte.
A pessoa decide o que fazer com aquilo; você não.

### 3. Salve o que é da sessão

Um ponto salvo por repositório.

- **`git add` nominal**, arquivo por arquivo. **Nunca `git add .`, nunca
  `git add -A`.**
- A mensagem sai **do que mudou de verdade**, não do que foi pedido. Leia o
  `git diff` se precisar. Uma linha dizendo o quê e por quê; corpo, se houver
  decisão que valha explicar.
- **Nunca commite segredo** (chave, senha, `.env`, token). Se você encontrar um
  num arquivo que ia entrar: **pare, não commite, e avise**.
- Se o repositório ainda não existe (`.git` ausente) numa pasta que devia ser
  versionada, **avise em vez de criar** — `git init` é decisão da pessoa.

### 4. **Não publique**

`push` só acontece se a pessoa pedir, explicitamente, naquela sessão, para
aquele repositório. Não "aproveite que está aqui".

### 5. Reporte — em uma linha por repositório

Não pergunte. Não peça confirmação. **Avise:**

```
salvo:
  plataforma        "organiza as capturas da semana"          3 arquivos
  projeto/receitas  "primeira tela do protótipo"              2 arquivos

deixado de fora (não foi esta sessão que mexeu):
  plataforma        _registro.md   — modificado às 12:31, provavelmente a rotina agendada

nada publicado.
```

Se não houve nada a salvar, uma linha basta: `nada mudou nesta sessão.`

---

## O que esta rotina nunca faz

- **Nunca pergunta se pode salvar.** Salvar é a operação que protege; pedir
  licença para proteger foi o erro que custou trabalho.
- **Nunca dá push** sem pedido explícito.
- **Nunca usa `git add .`**, por mais tentador que pareça quando são muitos
  arquivos. Muitos arquivos é exatamente quando entra o que não devia.
- **Nunca commita mudança que não é da sessão.** Lista e deixa lá.
- **Nunca roda `reset --hard`, `checkout -- .` ou `push --force`.** Ver
  [`versionamento.md`](versionamento.md#o-que-nunca-fazer-e-por-quê).

---

## Como tornar isto invocável por nome no Claude Code

O texto acima é a fonte. Para a sessão descobrir sozinha, crie um arquivo
`SKILL.md` numa pasta de skills do seu ambiente (por exemplo
`.claude/skills/salvar-tudo/SKILL.md`) com um cabeçalho curto — nome, descrição
e quando usar — apontando para este documento. Assim a regra continua num lugar
só, e a skill é apenas o atalho.

Isso é específico do Claude Code. Em outra ferramenta, o equivalente é qualquer
mecanismo que carregue este texto quando você disser *"salvar-tudo"* — e, na
falta de um, dizer *"siga o `metodo/salvar-tudo.md`"* funciona igual.

---

## Links

- [`versionamento.md`](versionamento.md) — o porquê, o vocabulário e o que fazer quando der ruim
- [`regras.md`](regras.md) — as regras permanentes
