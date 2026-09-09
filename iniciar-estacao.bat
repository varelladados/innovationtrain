@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title Estacao

rem ---------------------------------------------------------------------
rem  Antes de qualquer coisa: o Python existe?
rem  Se nao existir, a janela precisa CONTAR ISSO e ficar aberta. Antes ela
rem  abria o navegador, dava erro de comando nao encontrado e sumia.
rem ---------------------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo   A Estacao precisa do Python, e ele nao esta instalado
  echo   neste computador ^(ou nao esta no PATH^).
  echo.
  echo   Baixe em https://www.python.org/downloads/ e, na primeira
  echo   tela do instalador, marque "Add Python to PATH".
  echo.
  echo   Depois de instalar, feche esta janela e abra de novo.
  echo.
  pause
  exit /b 1
)

rem ---------------------------------------------------------------------
rem  A porta vem do config, nao daqui: fonte unica.
rem ---------------------------------------------------------------------
set PORTA=
for /f "usebackq delims=" %%p in (`python -c "import sys;sys.path.insert(0,'app');import config;print(config.PORTA)" 2^>nul`) do set PORTA=%%p
if "%PORTA%"=="" (
  echo   Nao consegui ler a porta do app/config.py — usando 8744.
  set PORTA=8744
)

rem ---------------------------------------------------------------------
rem  A porta ja esta ocupada? Quase sempre e a propria Estacao ja aberta.
rem ---------------------------------------------------------------------
netstat -ano | findstr /r /c:"127.0.0.1:%PORTA% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo   A porta %PORTA% ja esta ocupada.
  echo.
  echo   Quase sempre isso quer dizer que a Estacao ja esta aberta
  echo   noutra janela. Vou abrir o navegador nela em vez de subir
  echo   um segundo servidor.
  echo.
  start "" http://127.0.0.1:%PORTA%
  timeout /t 4 >nul
  exit /b 0
)

rem ---------------------------------------------------------------------
rem  O navegador e aberto pelo PROPRIO servidor (--abrir), depois que o
rem  socket ja esta escutando. Abrir daqui antes fazia a primeira coisa
rem  que a pessoa via ser "nao foi possivel acessar este site".
rem ---------------------------------------------------------------------
echo.
echo   Subindo a Estacao em http://127.0.0.1:%PORTA%
echo   Feche esta janela para desligar.
echo.
python app\server.py --abrir

rem  Se o servidor caiu na hora, a janela precisa ficar aberta para a
rem  pessoa ler o motivo.
if errorlevel 1 (
  echo.
  echo   A Estacao encerrou com erro. A mensagem esta acima.
  echo.
  pause
)
endlocal
