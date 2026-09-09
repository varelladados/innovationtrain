# Regras permanentes

> **O que é isto.** As regras que valem para toda plataforma, o tempo todo, para
> qualquer pessoa ou automação que mexa nela. Elas não são preferência de
> organização: cada uma existe porque a falta dela custou alguma coisa.
>
> Derivadas da doutrina do `C:\Plataforma`, traduzidas para o vocabulário do produto
> (ver [`taxonomia.md`](taxonomia.md)). Uma sessão de IA que abre numa
> plataforma tem que seguir estas regras sem que você precise pedir.

---

## 1. Apagar é sempre lógico, nunca físico

Um item **nunca** é apagado do disco. Apagar significa marcá-lo como encerrado
ou consolidado num índice, e movê-lo para o `_historico/` do estágio onde ele
estava — nunca remover a pasta nem destruir o conteúdo.

Dentro dessa regra, estas operações são normais e esperadas:

- **renomear** a pasta de um projeto;
- **fundir** N itens num só;
- **desmembrar** um item em N.

**Por quê:** o valor de uma ideia velha só aparece meses depois, quando outra
coisa esbarra nela. Uma pasta que some leva junto a chance de esbarrar.

## 2. O registro é append-only

Linhas do `_registro.md` **não se apagam nem se editam**. Se um item for
desmembrado ou consolidado, isso **não** reescreve o registro antigo: cria-se
uma **linha nova**, ligada à origem pelo marcador de linhagem `→`.

Se o mesmo grão volta a se mover sem mudar de estágio, a linha nova usa o
**mesmo identificador com sufixo `-1`, `-2`…** — nunca repete a string igual,
porque aí vira duplicata e o `verificar` acusa.

**Por quê:** o registro é a única coisa que diz *de onde veio*. Um histórico
que pode ser reescrito não é histórico.

## 3. Tudo é o mesmo grão

Uma captura que virou nota, que virou ideia, que virou projeto **continua sendo
o mesmo grão**. Os quatro estágios não são categorias excludentes: são estados
no fluxo da mesma coisa.

Por isso a separação entre o que ainda está cru e o que já avançou tem que ser
**visível** — pelo `_historico/` de cada estágio e pelo marcador `→` no
registro.

## 4. Nenhum item pula estágio

Uma ideia que já nasce madura passa pelos quatro assim mesmo. As quatro
passagens podem acontecer na mesma sessão, minutos uma depois da outra — mas
cada uma ganha identificador próprio e linha própria no registro.

**Por quê:** "virtualmente" não significa "sem registro". Pular a etapa é como
se perde a rastreabilidade de onde a coisa veio, e é sempre no dia seguinte
que alguém precisa dela.

Os critérios de cada passagem estão em [`classificar.md`](classificar.md).

## 5. Identificador só pelo utilitário

Nunca monte um identificador à mão. Use:

```
python metodo/plataforma.py novo-id --raiz <plataforma> --etapa <SIGLA> --slug "duas ou três palavras"
```

E **grave a linha do registro antes de pedir o próximo** — a sequência do dia é
lida do registro no momento da chamada; dois pedidos seguidos sem gravar nascem
com o mesmo número.

**Por quê:** já aconteceu. É uma corrida de verdade, não uma hipótese.

## 6. Artefato de sessão vive no repositório

Documento, plano, relatório ou análise produzido numa sessão **não está salvo**
enquanto estiver só na conversa ou numa pasta de rascunho fora do git. Copie
para a pasta do projeto a que pertence, com o nome da convenção local
(`plano-<assunto>-<AAAA-MM-DD>.md`), e commite **na mesma sessão que o gerou**.

**Por quê:** arquivo fora do git, com nome gerado automaticamente, é
indistinguível de perdido.

## 7. Salvar é automático; publicar é decisão

**Commit e push não são a mesma coisa e nunca devem ter o mesmo cadeado.**

- **Commit acontece sem pedir autorização.** Toda sessão que mudou arquivo
  versionado termina com commit. A IA **avisa** o que entrou; não pergunta.
- **Push exige autorização explícita e separada**, uma por vez.
- `git add` **nominal**, nunca `git add .` nem `git add -A`.
- Arquivo que a sessão não tocou não entra caladamente: é listado no aviso e
  fica de fora.
- **Nunca commitar segredo** (chave, senha, `.env`, token). Sai do arquivo mas
  fica no histórico — é o único erro desta lista sem desfazer barato.

**Por quê:** a regra antiga era o oposto ("nunca commite sem pedir"), tratava a
operação que **protege** como se fosse a que **publica**, e o resultado foi
trabalho perdido de verdade. Commit local não publicado se desfaz inteiro com
`git reset --soft HEAD~1`, que mantém todas as mudanças no lugar: o custo de um
commit a mais é zero.

O detalhe todo está em [`versionamento.md`](versionamento.md).

## 8. Decisão não se fecha por inferência

Uma pendência só se resolve quando a pessoa marca a resposta. Ninguém — nem a
IA, nem uma automação — decide "pelo contexto" o que ela queria. "Deixar para
depois" é adiamento **visível**: conta uma vez a mais e a pendência volta na
rodada seguinte, mais no topo.

---

## Links

- [`taxonomia.md`](taxonomia.md) — os nomes: estágios, siglas, arquivos de sistema
- [`classificar.md`](classificar.md) — quando um item passa de estágio
- [`versionamento.md`](versionamento.md) — salvar, publicar e o que fazer quando der ruim
- [`plataforma.py`](plataforma.py) — o utilitário que gera identificador e confere as invariantes
