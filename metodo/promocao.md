# Promoção — quando algo de uma estação vira parte do método

> Toda estação cria padrões próprios: um jeito de nomear, um modelo de
> documento, uma rotina, uma regra. A maioria deve ficar onde nasceu. Este
> documento diz quando um deles **sai** da estação e entra no método — e como
> as duas coisas continuam se alimentando sem uma engolir a outra.

## Os três critérios, juntos

1. **Provado em uso real três vezes**, em contextos ou projetos distintos — na
   mesma estação ou em estações diferentes.
2. **Estável por um ciclo completo** de revisão, sem mudar de escopo. Uso mostra
   que serve; estabilidade mostra que amadureceu.
3. **Genérico por acidente.** O teste é mecânico: tire do artefato todo o
   vocabulário próprio da estação (ver abaixo). Se ele continua servindo, é
   genérico; se depende daqueles nomes para fazer sentido, é da estação e fica
   nela.

**Exceção de nascimento:** o que já nasce genérico — nunca dependeu de
vocabulário de ninguém — pode entrar sem esperar os três usos. O critério vale
para padrões descobertos depois.

## O vocabulário próprio de uma estação

Uma estação pode chamar as coisas do seu jeito, e isso é identidade
([princípio 5](principios.md)). O método não pede que ela troque de nome: pede
que o nome dela seja **declarado**, não escrito no código. É o que a
configuração de cada estação faz:

| O método chama de | A estação pode chamar de outro jeito, declarando em |
|---|---|
| os estágios e as siglas | `estagios` do `estacao.json` |
| as siglas de uma taxonomia anterior | `siglas_legadas` — lidas sempre, nunca emitidas |
| os campos que o app lê e escreve no frontmatter | `frontmatter.processado` · `.nucleo` · `.origem` |
| o registro, o índice, a lista do que não tem destino | `arquivos.registro` · `.indice` · `.sem_destino` |
| a fila de dúvidas genuínas | um arquivo próprio, citado na orquestra da estação |

Por isso o teste do critério 3 é possível: o que é mecânico já está separado do
que é nome.

## Os dois sentidos

1. **Da estação para o método.** Um padrão que passa nos três critérios vira
   proposta para o método: vai para o backlog da Central, é escrito de forma
   genérica e só então entra — com teste, quando for código, e passando pelo
   guarda-corpo de publicação, porque o repositório é público. O registro da
   promoção é o `changelog-central.md`: a entrada diz o que entrou, de quantos
   usos ele veio e em que versão.
2. **Do método para a estação.** Quando o método muda — uma chave nova no
   `estacao.json`, um comando do utilitário, uma regra —, a estação decide se
   adota. **Nunca automaticamente**: a mudança é lida, o diff é revisado, e só
   então a estação muda.

Nenhum dos dois sentidos acontece sozinho. Quem não quer que a estação e o
método se afastem sem ninguém ver pode rodar, do lado da estação, uma checagem
periódica que compara os dois — os caminhos que a estação cita, os comandos que
ela usa, a versão da documentação — e transforma cada desvio em pendência.

## O que nunca entra no método

- O que só faz sentido com o vocabulário de alguém.
- O que foi provado uma vez só, por mais óbvio que pareça.
- Nome de estação, de projeto ou de pessoa — o repositório é público, e o
  guarda-corpo de publicação barra antes do commit.

## Links

- [`principios.md`](principios.md) — princípios 5 e 6
- [`taxonomia.md`](taxonomia.md) — o vocabulário do método
- [`regras.md`](regras.md) — as regras permanentes
