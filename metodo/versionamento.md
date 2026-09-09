# Versionamento — salvar, publicar e o que fazer quando der ruim

> **Para quem nunca usou git.** Este documento existe porque versionamento é a
> parte mais opaca do sistema para quem não é programador — e é justamente o que
> garante que nada se perde. Ninguém precisa entender git para trabalhar aqui.
> Mas ficar sem entender **nada** deixa a pessoa incapaz de pedir ajuda, então
> este documento traduz o vocabulário uma vez e depois usa os nomes de verdade.

---

## A regra que vale mais que todas as outras

**Salvar é automático. Publicar é decisão.**

São duas operações opostas, e o erro que custou trabalho de verdade foi tratá-las
com o mesmo cadeado.

| | O que é | Sai do seu computador? | Tem desfazer? |
|---|---|---|---|
| **Salvar** (commit) | guardar um ponto de retorno | **não** | sim, e barato |
| **Publicar** (push) | mandar para a nuvem | **sim** | difícil |

Por isso:

- **A sessão de IA salva sozinha**, sem pedir autorização, ao terminar cada
  coisa e ao encerrar. Ela **avisa** o que entrou; não pergunta.
- **Publicar sempre exige você dizer sim**, uma vez para cada.
- Os arquivos entram **um a um, pelo nome**. Nunca `git add .`.
- Você nunca precisa pensar em *stage*.[^stage]

### Por que salvar sozinho é seguro

Um ponto salvo que não foi publicado **se desfaz inteiro** com um comando, e as
suas mudanças continuam exatamente onde estavam:

```
git reset --soft HEAD~1
```

O custo de um ponto salvo a mais é **zero**. O custo de um a menos já foi
trabalho perdido. É por isso que a operação que protege não pode ter portão.

### A regra antiga, e por que ela era um erro

A regra anterior era *"a IA nunca commita sem pedir"*. Ela parecia prudente.
O que ela fez, na prática, foi transformar a operação que **protege** num
pedido de licença — e, como todo atrito, o resultado foi ela deixar de
acontecer. Trabalho se perdeu por causa disso, em 2026-09-08.

Prudência é sobre publicar. Salvar é sobre não perder.

---

## As três camadas que protegem você

Elas protegem de coisas diferentes, e **uma não substitui a outra**. A aba
**📦 Versões** da Estação mostra as três, porque proteção invisível não
tranquiliza ninguém.

| Camada | O que é | Protege de |
|---|---|---|
| **Backup automático** | a Estação copia o arquivo antes de toda escrita, em `cache/backups/` | o erro **de agora** — você acabou de estragar um arquivo |
| **Ponto salvo** (commit) | o histórico no seu computador | o erro **de ontem** — você quer voltar a como estava |
| **Cópia na nuvem** (remoto) | uma cópia fora daqui | o computador que **morreu** |

A primeira você já tem e provavelmente não sabia. A terceira é a única que exige
uma decisão sua.

---

## O vocabulário, traduzido uma vez

Depois desta tabela, este documento usa os **nomes de verdade** — esconder o nome
deixa você sem conseguir pesquisar, pedir ajuda ou ler qualquer tutorial.

| Nome de verdade | O que é |
|---|---|
| **repositório** | a pasta versionada. Tem um `.git` dentro, que é o histórico |
| **commit** | um ponto salvo: uma foto de tudo, com data, autor e uma frase explicando |
| **branch** | uma linha de trabalho paralela, para experimentar sem mexer no que funciona |
| **remoto** | a cópia na nuvem (GitHub, por exemplo) |
| **push** | mandar os seus pontos salvos para a nuvem |
| **pull** | trazer para o seu computador o que está na nuvem |
| **merge** | juntar duas linhas de trabalho numa só |

**Uma linha de trabalho só** (`master`) até existir um motivo concreto para a
segunda. Ramificar sem necessidade é a complexidade que faz a pessoa desistir.

---

## O que nunca fazer, e por quê

O motivo importa mais que a proibição — sem ele, a regra vira superstição.

| Nunca | Por quê |
|---|---|
| `git reset --hard` | apaga trabalho **que não foi salvo**, e não tem desfazer |
| `git checkout -- .` | idem: descarta tudo que você mudou desde o último ponto salvo |
| `git push --force` | reescreve o que está na nuvem, e pode apagar trabalho que veio de outra máquina |
| `git add .` / `git add -A` | engole arquivo que não devia entrar — inclusive segredo e acervo pesado |
| commitar segredo (chave, senha, `.env`, token) | sai do arquivo mas **fica no histórico**. É o único erro desta lista sem desfazer barato |

Sobre o último: se acontecer, **troque o segredo** — considere-o vazado. Limpar o
histórico é possível, é chato, e não resolve o que já foi lido.

---

## O que fazer quando der ruim

Esta é a parte que falta em todo tutorial.

**"Salvei sem querer."**
```
git reset --soft HEAD~1
```
Desfaz o último ponto salvo e **mantém todas as suas mudanças no lugar**. É como
se o commit não tivesse acontecido.

**"Quero ver como estava ontem."**
```
git log
git show <os primeiros 8 caracteres do ponto>
```
`git log` lista os pontos salvos; `git show` mostra o que mudou em um deles. Os
dois só **leem** — não há como estragar nada.

**"Apaguei um arquivo sem querer, e ele estava salvo."**
```
git restore <caminho do arquivo>
```
Traz de volta a versão do último ponto salvo.

**"A Estação escreveu num arquivo e eu não gostei."**
Olhe em `cache/backups/` — ela copia antes de toda escrita. É a camada 1.

**"Está tudo estranho e eu não entendo."**
**Pare.** Não tente consertar por tentativa e erro: é assim que um problema
pequeno vira um grande. Abra uma sessão de IA, mostre a saída de `git status` e
`git log`, e descreva o que você estava fazendo. Sem exceção — esta é a resposta
certa, não a saída fácil.

---

## O limite honesto disto aqui

Dá para tornar transparente o caminho feliz: salvar, publicar, consultar,
desfazer. É o que este documento faz.

**Conflito de merge, histórico reescrito e submódulo não cabem numa explicação
simplificada**, e fingir que cabem é pior do que dizer que não cabem. Quando o
estado sair do caminho feliz, a aba Versões vai dizer isso claramente em vez de
improvisar — e a resposta certa é a de cima: pare e chame uma sessão de IA.

---

## Como isso viaja junto com a plataforma

Não adianta a regra existir num documento que ninguém lê. Ela viaja em três
lugares, para valer já na primeira sessão de quem acabou de instalar:

1. **O `CLAUDE.md` da plataforma** nasce com a regra dentro, em português e no
   imperativo. É isso que faz a IA salvar sozinha desde o dia um, sem você saber
   que existe uma regra.
2. **Os prompts que a Estação gera** carregam os guardrails junto — inclusive o
   `git add` nominal e a proibição de `push --force`.
3. **A rotina de fechamento** ([`salvar-tudo.md`](salvar-tudo.md)), que varre os
   repositórios, separa o que é da sessão do que não é, salva o que é da sessão
   e **reporta**.

---

## Links

- [`regras.md`](regras.md) — as regras permanentes; esta é a de número 7
- [`salvar-tudo.md`](salvar-tudo.md) — a rotina de fechamento de sessão
- A aba **📦 Versões** da Estação — o retrato do estado, em português

[^stage]: *Stage* (ou "área de preparação") é onde o git guarda o que vai entrar
    no próximo ponto salvo, antes de ele existir. É conceito de ferramenta, não
    de trabalho: por isso não aparece em lugar nenhum deste documento fora desta
    nota. Quem adiciona os arquivos é a sessão de IA, pelo nome.
