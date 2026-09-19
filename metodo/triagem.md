# Triagem — o passo antes da captura

> **O que é isto.** A pergunta que toda entrada responde **antes** de ganhar
> identificador numa estação: *isto é trabalho ou vida pessoal — e carrega dado
> de outra pessoa ou um segredo?* Os cinco estágios cuidam de amadurecer uma
> ideia; a triagem cuida de ela chegar na estação certa, e de o que não é seu
> não chegar em lugar nenhum.
>
> Ver [`regras.md`](regras.md), regra 9, e [`taxonomia.md`](taxonomia.md), as
> estações de uma Central. O utilitário é [`triagem.py`](triagem.py).

---

## Por que existe

Uma Central começa com três estações — Plataforma, Admin_empresa e Vida_Pessoal
— e sabe mover uma ideia **da** vida pessoal **para** a Plataforma, reescrita. O
que ela não sabia era o caminho contrário: impedir que o pessoal chegue na
Plataforma **antes** de alguém olhar.

E ele chega. A entrada real não vem separada: vem um ditado que junta a reunião
do projeto e um compromisso de família, um dump do dia com uma senha colada no
meio, um export de conversa cujo **nome de arquivo** é o telefone do contato,
dezenas de fotos que tanto podem ser pesquisa de mercado quanto uma procura pessoal. Numa
estação versionada, a captura entra no git no primeiro commit automático — e o
histórico não desfaz barato.

## As regras da triagem

1. **Acontece fora de lugar versionado.** O bruto chega numa **área de espera**
   dentro da estação privada (`<vida_pessoal>/_triagem/<lote>/`), nunca direto
   no `1-capturas/` de uma estação versionada.
2. **A unidade é o trecho, não o arquivo.** Arquivo misto é fatiado; cada
   trecho segue o seu destino.
3. **Três perguntas por trecho:**
   - **esfera** — profissional, pessoal ou administrativa (da empresa);
   - **dado pessoal de terceiro** — nome, telefone, e-mail, documento, endereço,
     rosto, placa, saúde, religião, família de alguém;
   - **segredo** — senha, chave, token.
4. **Dado pessoal de terceiro nunca entra literal numa estação profissional.**
   Entra só a versão **reescrita** sem ele, e o frontmatter da captura diz o que
   saiu (`triagem: {lote: ..., removido: [telefone, nome]}`). O original fica na
   espera.
5. **Segredo não entra em lugar nenhum**, nem na estação privada em claro. Vira
   alerta: a resposta certa para senha exposta é trocar a senha.
6. **Na dúvida, não decide.** Fica na espera e vira **pergunta** no relatório,
   com opções e o motivo de cada uma ([regra 8](regras.md#8-decisão-não-se-fecha-por-inferência)).
   Respondida, o relatório é refeito.
7. **A linhagem profissional cita o lote, nunca o caminho pessoal.** Nome de
   arquivo e de pasta também carregam dado.
8. **Dois relatórios.** O que vai para lugar versionado é mascarado; o que tem
   nomes fica no lote, na espera.
9. **O script levanta sinais; a leitura decide.** Detector de telefone não sabe
   de quem é o telefone.
10. **Dado de exemplo nunca é derivado de dado real** — nem com o DDD trocado,
    nem com duas letras a menos. Teste, protótipo e documentação usam números
    inventados do zero. Os dígitos de um telefone real continuam identificando
    a pessoa em qualquer DDD; e um exemplo que nasce de um caso real vai parar
    em lugar versionado sem passar por triagem nenhuma. Já aconteceu: foi a
    própria varredura desta triagem que pegou.

## Matriz de destino

| Esfera \ o que carrega | nada de terceiro | dado de terceiro | segredo |
|---|---|---|---|
| **profissional** | `1-capturas/` da Plataforma | reescrever sem o dado → `1-capturas/`; original fica na espera | alerta; o resto segue a coluna ao lado |
| **administrativa** | `1-capturas/` da Admin_empresa | idem, reescrito | alerta |
| **pessoal** | `1-capturas/` da Vida_Pessoal | Vida_Pessoal (é privada; o dado pode ficar) | alerta; mascarar antes de gravar |
| **dúvida** | espera + pergunta | espera + pergunta | espera + alerta + pergunta |

A Admin_empresa é versionada. Quem ainda não tem a estação de administração
decide, na primeira vez, se o administrativo vai para a Vida_Pessoal ou espera.

## Especialização por tipo de entrada

Cada mídia tem uma extração antes da pergunta, e riscos que só ela tem.

| Entrada | Extração | Riscos típicos | O script | A leitura |
|---|---|---|---|---|
| **Nota simples** | nenhuma | assuntos misturados, senha colada, telefone solto | sinais, vocabulário, apelidos | fatiar, decidir esfera |
| **Dump do dia** | quebrar pelos separadores | o mesmo, em volume | sinais por linha | um trecho por ideia |
| **Transcrição** | já é texto | nomes próprios; nome de projeto quebrado pela transcrição | apelidos com tolerância a erro | corrigir o nome do projeto, fatiar |
| **Áudio** | transcrever — local, de preferência | voz de outra pessoa, conversa gravada | detecta a mídia | transcrever e tratar como transcrição |
| **Vídeo** | depende: **com fala** → transcrever; **sem fala** → quadros; **imagem parada com música** (status de rede social) → um quadro basta | rosto, placa, tela com dado | `ffprobe`: duração, quadros, faixa de áudio | ver o quadro ou transcrever |
| **Imagem, print, foto** | ler o texto e o conteúdo | nome e telefone impressos, rosto, documento fotografado | agrupa duplicadas por hash | ler e transcrever só o que serve |
| **Export de conversa** | separar mensagens de mídias | **contato no nome do arquivo**; a conversa inteira é de outra pessoa também | participantes (mascarados), apagadas, mídia omitida | decidir se a conversa é de trabalho |
| **Link** | baixar só o texto, com permissão | página com login; dado pessoal na própria URL | extrai as URLs | ler e resumir |
| **Documento** | extrair texto | CPF, contrato, dado bancário | sinais | ler |
| **Planilha** | cabeçalho e amostra | uma coluna inteira de telefone ou CPF | sinais | decidir se entra agregada |
| **Pacote (zip)** | abrir | tudo acima, empilhado | lista o conteúdo | triar cada arquivo |

## A configuração — chave `triagem` do `estacao.json`

```json
"triagem": {
  "pessoal": "../vida_pessoal",
  "espera": "../vida_pessoal/_triagem",
  "administrativo": "../admin_empresa",
  "projetos": {
    "Fotolivro": {"esfera": "profissional", "apelidos": ["foto livro", "album de fotos"]},
    "Horta":     {"esfera": "pessoal",      "apelidos": ["hortinha"]}
  },
  "palavras_pessoais": [],
  "palavras_profissionais": []
}
```

- **`projetos`** é o **de-para** da estação: cada projeto com a esfera a que
  pertence e os nomes pelos quais ele aparece na fala e na escrita. Um projeto
  de família dentro de uma estação profissional aparece aqui como `pessoal` — e
  é o sinal de que ele está no lugar errado.
- `esfera` aceita `profissional`, `pessoal`, `administrativo` e `misto`.
- Os caminhos são relativos à raiz da estação.
- **O Embarque já escreve esta chave** nas estações que cria juntas, com os
  caminhos vistos da raiz de cada uma — `.` é a própria estação: a Vida_Pessoal
  declara `"pessoal": "."` e `"espera": "_triagem"`. A espera nasce em
  `vida_pessoal/_triagem/`. Estação que você já tinha fica de fora: o Embarque
  não tem como conferir se ela é mesmo privada, e a espera não pode cair em lugar
  versionado. Se ela for a sua privada, declare `pessoal` e `espera` à mão nas
  outras.

## Como rodar

```
python metodo/triagem.py <pasta-ou-arquivos> --raiz <estação> --lote "nome" --saida relatorio.md
python metodo/triagem.py <...> --mostrar --saida <espera>/<lote>/levantamento-privado.md
python metodo/triagem.py <...> --estrito        # sai com 1 se houver terceiro ou segredo
```

O `--estrito` serve para varrer o que **já** entrou: rodado sobre o
`1-capturas/` de uma estação versionada, ele diz se alguma coisa passou sem
triagem.

### Decidir e aplicar — o relatório e os destinos saem de um arquivo

A leitura grava o que decidiu em `<lote>/decisoes.json`. Dali em diante, nada
se escreve à mão:

```
python metodo/triagem.py decidir <lote> --mascarado <onde o versionado mora>
python metodo/triagem.py aplicar <lote> --raiz <estação> --responder P1=A --responder P3=A
python metodo/triagem.py aplicar <lote> --raiz <estação> --responder P1=A --responder P3=A --confirmar
```

- **`decidir`** escreve o relatório completo (`<lote>/relatorio-v<N>.md`) e, se
  pedido, o mascarado. **Recusa** gravar o mascarado se o texto — conferido
  antes da máscara — ainda tiver dado de terceiro ou segredo.
- **`aplicar`** registra as respostas, aplica os **efeitos** de cada opção nos
  trechos e leva ao destino o que ficou pronto: captura com identificador pelo
  utilitário, linha no registro sob `## Entradas <data> — triagem`, e no
  frontmatter `triagem: {lote, trecho, removido}`. Sem `--confirmar`, só
  simula. **Recusa** texto que vai para estação não privada e ainda tem sinal
  de terceiro. Rodar de novo não duplica — nem depois de uma captura que falhou
  no meio: o que já tinha seguido vai para o `decisoes.json` antes de o erro
  aparecer, e a rodada seguinte leva só o que faltou. Ao terminar, sobe a versão
  e refaz os relatórios. Pode rodar com a Central aberta: cada captura segura a
  trava do registro da estação de destino (`trava.py`), a mesma que a aba Nota
  usa.

O formato, no essencial:

```json
{
  "lote": "2099-01-01-assunto", "versao": 1, "nota_versao": "primeira leitura",
  "chegou_em": "…", "origem": "…", "em_uma_frase": "…",
  "saida_mascarado": "<caminho do relatório versionado, relativo à estação>",
  "chegou":   [{"grupo": "…", "itens": 2, "midia": "…", "extracao": "…", "achado": "…"}],
  "trechos":  [{"id": "A", "descricao": "…", "esfera": "duvida", "terceiro": ["nome"],
                "segredo": false, "motivo": "…", "depende_de": ["P1"], "removido": ["nome"],
                "saidas": []}],
  "secoes":   [{"titulo": "…", "texto": "…", "privado": false}],
  "alertas":  ["…"],
  "perguntas": [{"id": "P1", "titulo": "…", "resposta": null, "opcoes": [
      {"id": "A", "texto": "…", "efeitos": [{"trecho": "A", "saidas": [
          {"destino": "profissional", "texto": "rascunhos/a-{P2}.md", "slug": "duas palavras"}]}]}]}],
  "seguiu": []
}
```

`destino` é `profissional`, `pessoal`, `administrativo` ou `encerrar`. `{P2}`
no caminho do texto vira a letra respondida na P2 — é como uma pergunta escolhe
a variante preparada para a resposta da outra. Um trecho só segue quando todas
as perguntas de `depende_de` estão respondidas. Uma **saída** também pode ter
`depende_de` próprio — para a resposta em que a outra pergunta não importa não
travar o trecho inteiro.

## Na Central — a aba Nota e a aba Triagem

A captura pela interface era a última porta que escrevia direto no primeiro
estágio. Desde a 0.13.0:

- **A aba Nota passa pela triagem antes de gravar.** Se ela para, nada é escrito:
  a tela mostra o que foi visto, **mascarado**, e as saídas que o método prevê —
  guardar na espera, mandar para a estação privada, ou (só quando o que pesou foi
  vocabulário de vida pessoal) seguir como captura profissional. Dado de terceiro
  e segredo **não têm** o botão de seguir: o primeiro exige reescrita, o segundo
  não entra em lugar nenhum.
- **A aba Triagem mostra a espera**: cada lote, o que já foi lido, quantos trechos
  seguiram e **o que cada um ainda pergunta**, com o comando pronto do `aplicar`.
  É leitura pura — responder e aplicar continuam no utilitário, porque decisão não
  se fecha por inferência (regra 8) e escrever em duas estações de uma vez não é
  coisa de botão.
- O **snapshot estático** recusa a rota: a espera mora dentro da estação privada, e
  snapshot é publicação.

## O ciclo de um lote

1. **Chegou** — o bruto vai para `_triagem/<AAAA-MM-DD>-<assunto>/`, cópia; a
   origem não se mexe.
2. **Levantamento** — `triagem.py`, duas vezes: mascarado (vai para o
   relatório) e sem máscara (fica no lote).
3. **Extração** — o que o levantamento marcou como "ler antes": transcrever,
   olhar a imagem, ver o quadro.
4. **Leitura** — fatiar e responder as três perguntas de cada trecho.
5. **Destino** — pela matriz. O que é certo, segue; o que é dúvida, fica.
6. **Relatório** — do [modelo](templates/relatorio-triagem.md), com as
   perguntas.
7. **Respostas** — cada resposta fecha uma dúvida; o relatório é refeito com o
   número de versão acima, e o que destravou segue a matriz.

O lote nunca é apagado: quando tudo nele tem destino, ele vai para
`_triagem/_historico/`.

## Links

- [`regras.md`](regras.md) — regra 9
- [`taxonomia.md`](taxonomia.md) — as três estações e a passagem entre elas
- [`classificar.md`](classificar.md) — o que acontece depois da triagem
- [`templates/relatorio-triagem.md`](templates/relatorio-triagem.md)
