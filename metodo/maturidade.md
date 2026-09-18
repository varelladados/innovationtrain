# Maturidade e ordem de ataque

> Duas medidas que o método usa depois que um item vira projeto: **o quanto ele
> já existe** (maturidade, de 0 a 5 em seis dimensões) e **o que atacar
> primeiro** quando há mais trabalho do que tempo (o score de ordem de ataque).
> A aba Portfólio da Central lê a maturidade dos perfis que a estação declara
> (chave `perfis` do `estacao.json`).

## 1. Maturidade de um projeto — 0 a 5, medida pelo disco

| Nível | Produto | Código | Docs | UX | Dados | Operação |
|---|---|---|---|---|---|---|
| 0 | só ideia | nada | nada | nada | nada | nada |
| 1 | esboço, proposta | script solto | orquestra mínima | tela rabiscada | amostra manual | roda na mão |
| 2 | protótipo | módulos, sem teste | orquestra e backlog vivos | protótipo navegável | fonte real, sem pipeline | script único |
| 3 | usável por quem fez | testes básicos | leia-me e changelog | fluxo principal redondo | pipeline reprodutível | agendado ou monitorado |
| 4 | usável por outra pessoa | testes e CI | manual ou tour | acessível, responsivo, erro tratado | validado com dado real | deploy documentado |
| 5 | produto | release versionada | docs públicas | pesquisa com usuário | governança e proteção de dados | observabilidade e compromisso de nível de serviço |

**A regra que não se negocia: mede-se o disco, nunca a intenção.** Se o backlog
promete e o disco não tem, a maturidade é a do disco. A média é a média simples
das seis dimensões, com uma casa decimal.

O status declarado do projeto deve bater com a média — **esboço** até 1,5 ·
**inicial** de 1,5 a 3 · **ativo** a partir de 3 · **versão X.Y** quando há
release. Quando não bate, quem decide o status é o dono; a medida só aponta.

### O perfil

A medida vive num perfil por projeto (um JSON na pasta `perfis` da estação):
identidade, proposta de valor, público, stack, estrutura, maturidade nas seis
dimensões, capacidades reutilizáveis, lacunas, riscos e ligações com os outros
projetos — mais a data em que foi medido. Perfis são cruzáveis: um índice
gerado a partir deles mostra o portfólio inteiro, e cada nova rodada de medição
lê o índice da anterior.

## 2. Ordem de ataque — o que fazer primeiro

A passagem entre estágios decide **se** um item pode subir. Entre vários que
podem, este score decide **qual primeiro**:

```
Score = Impacto × Autonomia × Essencial × (1 + 0,25 × Adiada) ÷ (1 + Minutos ÷ 30)
```

| Fator | Valores | Pergunta que responde |
|---|---|---|
| **Impacto** | 1 cosmético · 2 melhora · 3 destrava trabalho · 4 bloqueia uma entrega · 5 bloqueia produção | O que acontece se ninguém fizer? |
| **Autonomia** | 1,0 resolve sozinho · 0,6 adianta 70 % ou mais · 0,2 só o dono decide | Dá para fazer sem perguntar? |
| **Essencial** | 1,5 se é pré-requisito para entregar, senão 1,0 | Está marcado como essencial? |
| **Adiada** | quantas vezes o dono disse "depois" | Adiar sobe, não esconde |
| **Minutos** | tempo realista de execução autônoma | 0 → divide por 1; 30 → por 2; 90 → por 4 |

Faixas: **3 ou mais**, ataque imediato · **de 1 a 3**, entra se sobrar
orçamento · **menos de 1**, é pergunta ou trabalho longo. Um item de impacto 5
e essencial que só o dono pode decidir dá 1,5 — ele aparece no topo da lista de
**perguntas**, nunca na de execução.

É um RICE simplificado em que o *alcance* virou *essencial* e a *confiança*
virou *autonomia*: num sistema operado por agente, a incerteza que importa é
"posso fazer isto sem perguntar?".

## 3. O tamanho de uma rodada autônoma

| Parâmetro | Valor | Por quê |
|---|---|---|
| Fatia executada sem perguntar | de 20 % a 50 % dos itens válidos (alvo: 35 %) | acima da metade, cresce o risco de decidir pelo dono |
| Agentes em paralelo | um por projeto, nunca dois no mesmo repositório | evita escrita concorrente |
| Salvar | commit local automático, só dos arquivos que a rodada tocou ([regra 7](regras.md)) | salvar é segurança |
| Publicar | push sempre com autorização separada | publicar é decisão |
| Perguntas | todas de uma vez, no fim, cada uma com duas ou três opções e uma recomendação | o dono responde num sentar só |

## 4. Os objetos de processo

| Objeto | Função |
|---|---|
| Pendência-formulário | pergunta com opções e fonte estável — o agente nunca a fecha por inferência ([regra 8](regras.md)) |
| Lista única com score | uma tabela: o que o agente faz, o que espera resposta, as perguntas, o que sai |
| Perfil de projeto | maturidade, capacidades, lacunas e ligações — cruzável entre projetos |
| Propostas por projeto | melhorias e features com plano — modelo em [`templates/propostas.md`](templates/propostas.md) |
| Índice de portfólio | gerado dos perfis; lido por cada nova rodada |

## Links

- [`classificar.md`](classificar.md) — as passagens entre estágios, que vêm antes disto
- [`principios.md`](principios.md) — por que a medida é do disco e as perguntas vão para o dono
- [`templates/propostas.md`](templates/propostas.md) — o modelo de propostas por projeto
