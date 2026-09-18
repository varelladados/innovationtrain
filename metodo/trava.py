"""A trava de gravação de uma estação — entre processos, não só entre threads.

Uma captura faz três coisas que não podem se misturar com as de outra: pede o
identificador ao utilitário (`novo-id` acha a sequência do dia **lendo o
registro**), grava o arquivo e reescreve o registro com a linha nova. Dois
processos capturando juntos sem trava deram os três defeitos possíveis, medidos
antes de esta trava existir: SEQ repetido, linha de registro perdida (a segunda
reescrita apaga a da primeira) e, no Windows, um processo morto por
`PermissionError` no `os.replace` do registro que o outro estava lendo.

Um `threading.Lock` só enxerga as threads do servidor, e a linha de comando da
triagem (`triagem.py aplicar`) é outro processo. Esta trava é do sistema
operacional — `fcntl.flock` no Linux e no macOS, `msvcrt.locking` no Windows —
sobre um arquivo **ao lado do registro**: `_registro.md.trava`. Duas decisões,
cada uma com o seu porquê:

- **Processo que morre não deixa a estação travada.** Quem solta a trava é o
  sistema, quando o processo acaba, de qualquer jeito que ele acabe. Não há PID
  gravado nem idade de arquivo para adivinhar: o arquivo que sobra de um
  processo morto não está travado por ninguém, e a próxima captura o usa.
- **O arquivo só existe enquanto alguém grava.** Quem solta, apaga. Uma trava
  permanente apareceria no `git status` de toda estação versionada, e o
  `.gitignore` de uma estação que já existe não é da Central para editar. O
  `*.trava` do `.gitignore` que o Embarque escreve (e do da Central, para os
  exemplos) é só cinto de segurança: cobre o instante da gravação e o que sobra
  de um processo que morreu no meio.

Apagar um arquivo de trava tem uma armadilha, e cada sistema pede a sua ordem.
No Linux, quem esperava com o arquivo antigo aberto pode ganhar a trava dele
depois que ele saiu do caminho, enquanto um terceiro cria o novo e ganha a
dele: dois donos. Lá, quem solta apaga **antes** de soltar, e quem pega confere
que o arquivo travado ainda é o do caminho. No Windows, arquivo aberto não se
apaga (o `os.open` não pede `FILE_SHARE_DELETE`): quem solta fecha antes, e se
outro processo já o abriu para esperar, o apagamento falha e fica para o
próximo dono.

**Não é reentrante**, e num processo com várias threads não substitui o
`threading.Lock`: em sistema de arquivos de rede o `flock` pode ser emulado por
trava de processo, que não separa uma thread da outra. O servidor segura
`notas._LOCK` antes desta.

Stdlib puro, como o resto do produto.
"""
import contextlib
import errno
import os
import sys
import time
from pathlib import Path

_WINDOWS = sys.platform == "win32"
if _WINDOWS:
    import msvcrt
else:
    import fcntl

#: Quanto quem chega espera por quem está gravando. Uma captura leva menos de um
#: segundo; o teto de quem segura é o `timeout` dos subprocessos que ela chama.
ESPERA = 30.0
INTERVALO = 0.05
SUFIXO = ".trava"

#: O que o sistema responde quando a trava está com outro: `EACCES` no Windows,
#: `EWOULDBLOCK`/`EAGAIN` no `flock`.
_OCUPADA = {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}


class TravaErro(Exception):
    """Não deu para pegar a trava."""


class TravaOcupada(TravaErro):
    """Outro processo segurou a trava por mais tempo que a espera."""


def caminho(registro):
    """O arquivo da trava de um registro: o nome dele com `.trava`, na mesma pasta."""
    registro = Path(registro)
    return registro.with_name(registro.name + SUFIXO)


@contextlib.contextmanager
def do_registro(registro, espera=ESPERA):
    """Segura a trava do `registro` durante o bloco.

    Espera até `espera` segundos por quem a tiver; passado isso, `TravaOcupada`.
    """
    alvo = caminho(registro)
    fd = _pegar(alvo, espera)
    try:
        yield alvo
    finally:
        _devolver(fd, alvo)


def _pegar(alvo, espera):
    limite = time.monotonic() + espera
    while True:
        try:
            fd = os.open(alvo, os.O_RDWR | os.O_CREAT, 0o666)
        except FileNotFoundError:
            raise TravaErro(f"a pasta do registro não existe: {alvo.parent}") from None
        except PermissionError as e:
            if not _WINDOWS:
                raise TravaErro(f"sem permissão para criar a trava {alvo}: {e}") from None
            # "apagar pendente": o último dono apagou o arquivo e outro programa
            # (antivírus, indexador) ainda o tem aberto — passa em instantes
            fd, motivo = None, f"o Windows ainda não liberou o arquivo da trava ({e})"
        else:
            motivo = "outra captura está gravando nesta estação"
            try:
                if _tentar(fd):
                    if _WINDOWS or _mesmo_arquivo(fd, alvo):
                        return fd
                    _soltar(fd)
            except BaseException:
                os.close(fd)
                raise
            os.close(fd)
        if time.monotonic() >= limite:
            raise TravaOcupada(
                f"{motivo} há mais de {espera:g} s — tente de novo em instantes. Se "
                f"continuar, há um processo vivo segurando a trava: {alvo}")
        time.sleep(INTERVALO)


def _tentar(fd):
    """Pega a trava sem esperar. False se ela está com outro."""
    try:
        if _WINDOWS:
            os.lseek(fd, 0, os.SEEK_SET)      # o msvcrt trava a partir da posição atual
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in _OCUPADA:
            return False
        raise
    return True


def _soltar(fd):
    if _WINDOWS:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _mesmo_arquivo(fd, alvo):
    """O arquivo travado ainda é o que está no caminho?

    É a conferência que torna seguro apagar a trava no Linux: quem esperava no
    arquivo antigo e o ganhou depois de ele ser apagado larga e tenta de novo.
    No Windows ela não é chamada — lá, arquivo aberto não sai do caminho.
    """
    try:
        no_caminho = os.stat(alvo)
    except FileNotFoundError:
        return False
    travado = os.fstat(fd)
    return (travado.st_dev, travado.st_ino) == (no_caminho.st_dev, no_caminho.st_ino)


def _devolver(fd, alvo):
    """Solta a trava e apaga o arquivo, na ordem que cada sistema pede."""
    if _WINDOWS:
        try:
            _soltar(fd)
        finally:
            os.close(fd)
        _apagar(alvo)
    else:
        try:
            _apagar(alvo)        # ainda segurando: ver `_mesmo_arquivo`
            _soltar(fd)
        finally:
            os.close(fd)


def _apagar(alvo):
    try:
        os.unlink(alvo)
    except OSError:
        pass    # outro processo já o abriu para esperar: quem apaga é o último da fila
