# CLAUDE.md — Exemplo — cozinha e fotografia

> **Isto é a plataforma de exemplo que começa vazia.** Só há capturas: quem
> faz o trem andar é quem está usando. A irmã dela,
> `plataformas/exemplo-precos`, já vem povoada em todos os estágios — uma
> existe para ser dirigida, a outra para ser lida.
>
> **Reiniciar devolve esta pasta ao estado de origem** (`plataforma.py
> reiniciar --raiz . --confirmar`). Nada aqui é irreversível.

> Este arquivo é lido automaticamente por qualquer sessão do Claude Code
> que abrir nesta pasta. O que estiver aqui vale como contexto; o que
> não estiver, a sessão não sabe.

## O que é esta pasta

Uma plataforma da Estação: capturas → notas → ideias → funcionalidades → projetos. Toda ideia
entra crua no primeiro estágio e vai amadurecendo. A porta de entrada é o
`_indice.md`.

**Estado atual: nove capturas, nada mais.** Notas, ideias e projetos nascem
quando alguém avança — pela ação **avançar** do app, que faz a mecânica, ou à
mão seguindo `metodo/classificar.md`.

Se você for uma sessão de IA trabalhando aqui: o que falta é **escrever o
conteúdo de cada estagio**, não a mecânica. O arquivo que a ação avançar cria
nasce com o esqueleto do template e o texto de origem colado embaixo, numa seção
`## Texto de origem, a organizar` — organizar aquilo e apagar a seção é o
trabalho.

## As regras que valem aqui

- **O registro é append-only.** Nunca edite nem apague linha existente;
  continuação usa o mesmo identificador com sufixo `-N`.
- **Apagar é lógico, nunca físico.** Encerrar é mover para o
  `_historico/` do estágio, não remover.
- **Nenhum item pula estágio:** CAP → NOT → IDE → FUN → PRJ em ordem, cada um com
  identificador próprio e linha própria no registro.
- **Identificador só pelo utilitário**, nunca montado à mão.
- **Nenhuma decisão se fecha por inferência** — só a marcação explícita
  da pessoa fecha uma pendência.

## Como esta sessão salva o trabalho

**Salvar é automático; publicar é decisão.**

- **Commite sem pedir autorização** ao terminar um artefato e ao encerrar
  a sessão. **Avise** numa linha o que entrou — não pergunte.
- Adicione os arquivos **nominalmente**. Nunca `git add .`, nunca
  `git add -A`.
- Mudança que não foi você quem fez: liste no aviso e **deixe de fora**.
- **Push só com autorização explícita e separada**, uma por vez.
- Nunca commite segredo (chave, senha, `.env`, token) — sai do arquivo
  mas fica no histórico.
- **Nunca encerre a sessão deixando mudança sua sem commit.**

Isto não é zelo excessivo: a regra oposta ("só commite depois que eu
mandar") já custou trabalho perdido. Commit local não publicado se desfaz
inteiro com `git reset --soft HEAD~1`, que mantém tudo no lugar — o custo
de um commit a mais é zero.
