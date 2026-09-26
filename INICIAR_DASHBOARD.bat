@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Dashboard ITBI Fortaleza
cd /d "%~dp0"

rem ===================================================================
rem  Dashboard ITBI Fortaleza - Seminario 01 de Inteligencia de Negocios
rem  Ciencias Atuariais - UFC - 2026.2
rem
rem  O que este arquivo faz, na ordem:
rem   0. se o servidor ja estiver no ar, apenas abre o navegador;
rem   1. procura o Python e instala se nao encontrar;
rem   2. instala as bibliotecas do requirements.txt se faltar alguma;
rem   3. prepara as bases (CSV para Parquet) se ainda nao existirem;
rem   4. sobe o servidor e abre o dashboard no navegador.
rem
rem  Sem acentos de proposito: evita problemas de codificacao no console.
rem ===================================================================

set "PY_INSTALADOR=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PY="

echo.
echo  ================================================================
echo   DASHBOARD ITBI FORTALEZA
echo   Seminario 01 - Inteligencia de Negocios - UFC 2026.2
echo  ================================================================
echo.

rem --- 0. Escolher a porta e ver se o dashboard ja esta no ar ------
rem Se o dashboard ja estiver respondendo, so abrimos o navegador. Se a
rem porta estiver ocupada por outro programa, passamos para a seguinte,
rem em vez de esperar o Streamlit falhar ao subir.
for %%P in (8501 8502 8503 8504) do (
    set "PORTA=%%P"
    set "URL=http://localhost:%%P"
    call :servidor_ativo
    if not errorlevel 1 goto :ja_no_ar
    call :porta_livre
    if not errorlevel 1 goto :porta_escolhida
)
echo  [ERRO] As portas 8501 a 8504 estao ocupadas por outros programas.
echo         Feche-os e rode este arquivo novamente.
goto :fim_erro

:ja_no_ar
echo  [ok] O dashboard ja esta rodando na porta %PORTA%.
goto :abrir_navegador

:porta_escolhida

rem --- 1. Python ---------------------------------------------------
echo  [1/4] Procurando o Python...
call :procurar_python
if defined PY goto :python_encontrado

echo        Python nao encontrado neste computador.
echo        Iniciando a instalacao automatica...
echo.
call :instalar_python
call :procurar_python
if defined PY goto :python_encontrado
goto :erro_python

:python_encontrado
set "VERSAO=?"
for /f "delims=" %%v in ('%PY% -c "import sys;print(sys.version.split()[0])" 2^>nul') do set "VERSAO=%%v"
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if errorlevel 1 goto :erro_versao
echo        Python %VERSAO% encontrado.

rem --- 2. Bibliotecas ----------------------------------------------
echo  [2/4] Verificando as bibliotecas...
call :bibliotecas_ok
if not errorlevel 1 (
    echo        Bibliotecas ja instaladas.
    goto :etapa_dados
)

echo        Faltam bibliotecas. Instalando o requirements.txt.
echo        A primeira vez pode levar alguns minutos.
echo.
%PY% -m pip install --upgrade pip --disable-pip-version-check --quiet
%PY% -m pip install --disable-pip-version-check -r requirements.txt
call :bibliotecas_ok
if not errorlevel 1 goto :bibliotecas_prontas

echo.
echo        Tentando novamente com instalacao apenas para este usuario...
%PY% -m pip install --user --disable-pip-version-check -r requirements.txt
call :bibliotecas_ok
if errorlevel 1 goto :erro_bibliotecas

:bibliotecas_prontas
echo.
echo        Bibliotecas instaladas com sucesso.

rem --- 3. Bases de dados -------------------------------------------
:etapa_dados
echo  [3/4] Verificando as bases de dados...
if not exist "dados\itbi_operacoes_tratadas.parquet" goto :preparar_dados
if not exist "dados\itbi_imoveis_distintos.parquet" goto :preparar_dados
echo        Bases prontas.
goto :etapa_servidor

:preparar_dados
echo        Preparando as bases (CSV para Parquet)...
%PY% preparar_dados.py
if errorlevel 1 goto :erro_dados

rem --- 4. Servidor -------------------------------------------------
:etapa_servidor
echo  [4/4] Iniciando o dashboard...
start "Servidor do dashboard ITBI - NAO FECHE ESTA JANELA" /min %PY% -m streamlit run app.py --server.port %PORTA% --server.address localhost --server.headless true --server.runOnSave true --browser.gatherUsageStats false

set /a TENTATIVAS=0
:aguardar_servidor
call :servidor_ativo
if not errorlevel 1 goto :abrir_navegador
set /a TENTATIVAS+=1
if !TENTATIVAS! GEQ 60 goto :erro_servidor
ping -n 2 127.0.0.1 >nul
goto :aguardar_servidor

rem --- Abrir o navegador -------------------------------------------
:abrir_navegador
rem Selo unico por execucao. Sem ele, se ja existir uma aba aberta nesse
rem endereco, o navegador apenas traz a aba para a frente sem recarregar, e
rem a tela continua mostrando a versao anterior do dashboard.
set "SELO=%RANDOM%%TIME:~6,2%"
echo.
echo  Abrindo o dashboard em %URL%
start "" "%URL%/?v=%SELO%"
echo.
echo  ================================================================
echo   Pronto. O dashboard esta aberto no navegador.
echo.
echo   Para encerrar, feche a janela minimizada chamada
echo   "Servidor do dashboard ITBI".
echo.
echo   Se o dashboard aparecer desatualizado, feche essa janela do
echo   servidor e rode este arquivo de novo: isso forca um inicio limpo.
echo  ================================================================
ping -n 5 127.0.0.1 >nul
exit /b 0

rem ================= sub-rotinas ==================================

:servidor_ativo
rem Devolve 0 quando o Streamlit responde no endereco de saude.
curl.exe -s -f -m 2 -o nul "%URL%/_stcore/health" >nul 2>&1
exit /b %errorlevel%

:porta_livre
rem Devolve 0 quando nada esta escutando na porta escolhida.
netstat -ano | findstr /c:":%PORTA% " | findstr /c:"LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
exit /b 1

:bibliotecas_ok
rem Devolve 0 quando todas as bibliotecas do dashboard importam.
%PY% -c "import streamlit,plotly,pandas,pyarrow,pydeck" >nul 2>&1
exit /b %errorlevel%

:procurar_python
rem Procura o Python pelo lancador, pelo PATH e nas pastas usuais.
set "PY="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
    exit /b 0
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    exit /b 0
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%~D\python.exe" (
        set PY="%%~D\python.exe"
        exit /b 0
    )
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%~D\python.exe" (
        set PY="%%~D\python.exe"
        exit /b 0
    )
)
for /d %%D in ("C:\Python3*") do (
    if exist "%%~D\python.exe" (
        set PY="%%~D\python.exe"
        exit /b 0
    )
)
exit /b 1

:instalar_python
rem Tenta o winget primeiro; se nao der, baixa o instalador oficial.
where winget >nul 2>&1
if errorlevel 1 goto :baixar_python
echo        Instalando o Python pelo winget...
winget install --id Python.Python.3.12 --exact --source winget --accept-source-agreements --accept-package-agreements --disable-interactivity
if not errorlevel 1 goto :instalacao_concluida

:baixar_python
echo        Baixando o instalador oficial do Python (cerca de 26 MB)...
curl.exe -L --fail -o "%TEMP%\python-itbi-setup.exe" "%PY_INSTALADOR%"
if errorlevel 1 exit /b 1
echo        Instalando o Python (nao precisa de administrador)...
"%TEMP%\python-itbi-setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0
del /q "%TEMP%\python-itbi-setup.exe" >nul 2>&1

:instalacao_concluida
rem O PATH desta janela ainda nao conhece o Python novo; acrescentamos
rem os caminhos mais provaveis para que a busca o encontre agora.
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
exit /b 0

rem ================= mensagens de erro ============================

:erro_python
echo.
echo  [ERRO] Nao foi possivel instalar nem localizar o Python.
echo         Instale manualmente em https://www.python.org/downloads/
echo         marcando a opcao "Add python.exe to PATH" e rode este
echo         arquivo novamente.
goto :fim_erro

:erro_versao
echo.
echo  [ERRO] A versao encontrada do Python (%VERSAO%) e antiga demais.
echo         O dashboard precisa da versao 3.9 ou mais nova.
goto :fim_erro

:erro_bibliotecas
echo.
echo  [ERRO] Falha ao instalar as bibliotecas.
echo         Verifique a conexao com a internet e tente de novo.
echo         Se persistir, rode manualmente nesta pasta:
echo             %PY% -m pip install -r requirements.txt
goto :fim_erro

:erro_dados
echo.
echo  [ERRO] Nao foi possivel preparar as bases de dados.
echo         Confira se os dois arquivos abaixo estao na pasta
echo         aquivos_base_bi, ao lado desta:
echo             Compartilhada_itbi_operacoes_tratadas.csv
echo             Compartilhada_itbi_imoveis_distintos.csv
goto :fim_erro

:erro_servidor
echo.
echo  [ERRO] O servidor nao respondeu dentro do tempo esperado.
echo         Veja a janela "Servidor do dashboard ITBI" para a mensagem
echo         de erro, ou rode manualmente nesta pasta:
echo             %PY% -m streamlit run app.py
goto :fim_erro

:fim_erro
echo.
pause
exit /b 1
