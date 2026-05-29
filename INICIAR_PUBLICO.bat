@echo off
:: ================================================================
:: AUSTIN LEAGUE CORE — Acesso Publico via Cloudflare Tunnel
:: Inicia o Flask + cria tunel publico automaticamente
:: ================================================================
title AUSTIN LEAGUE CORE — Acesso Publico
color 0A
cls

echo.
echo  ============================================================
echo   AUSTIN LEAGUE CORE  ^|  ACESSO PUBLICO  ^|  Cloudflare
echo  ============================================================
echo.

:: ── Mudar para a pasta do script ─────────────────────────────
cd /d "%~dp0"

:: ── Verificar se cloudflared (cf.exe) existe ─────────────────
if not exist "cf.exe" (
    echo  [ERRO] cf.exe nao encontrado nesta pasta!
    echo  Certifica-te que o ficheiro cf.exe esta em:
    echo  %~dp0
    echo.
    pause
    exit /b 1
)
echo  [OK] cf.exe encontrado.

:: ── Detectar Python do venv ou sistema ───────────────────────
set PYTHON=
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo  [OK] Python encontrado: .venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    echo  [OK] Python encontrado: venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON=python
        echo  [OK] Python do sistema encontrado.
    ) else (
        echo  [ERRO] Python nao encontrado!
        echo  Instala Python ou activa o ambiente virtual.
        pause
        exit /b 1
    )
)

:: ── Verificar se Flask ja esta a correr na porta 5026 ────────
echo.
echo  [1/3] A verificar servidor Flask (porta 5026)...
netstat -ano | findstr ":5026" | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Flask ja esta a correr na porta 5026.
) else (
    echo  [INFO] Flask nao esta a correr. A iniciar...
    :: Iniciar Flask numa janela separada que fica aberta
    start "AUSTIN Flask Server" cmd /k "cd /d "%~dp0" && %PYTHON% austinapp.py"
    echo  [INFO] Aguardando Flask arrancar (5 segundos)...
    timeout /t 5 /nobreak >nul
    :: Verificar novamente
    netstat -ano | findstr ":5026" | findstr "LISTENING" >nul 2>&1
    if %errorlevel% == 0 (
        echo  [OK] Flask iniciado com sucesso na porta 5026.
    ) else (
        echo  [AVISO] Flask pode ainda estar a arrancar...
        echo  Se o tunel falhar, aguarda mais uns segundos e tenta de novo.
    )
)

:: ── Verificar se ja existe um tunel activo ───────────────────
echo.
echo  [2/3] A verificar tuneis existentes...
tasklist /FI "IMAGENAME eq cf.exe" 2>nul | findstr /I "cf.exe" >nul
if %errorlevel% == 0 (
    echo  [AVISO] Ja existe um processo cf.exe a correr.
    echo  A terminar instancia anterior para evitar conflitos...
    taskkill /F /IM cf.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo  [OK] Instancia anterior terminada.
)

:: ── Iniciar tunel Cloudflare ─────────────────────────────────
echo.
echo  [3/3] A criar tunel Cloudflare...
echo.
echo  ============================================================
echo.
echo   Aguarda 10-20 segundos...
echo   O teu link publico vai aparecer assim:
echo.
echo     https://xxxx-xxxx-xxxx.trycloudflare.com
echo.
echo   Copia esse link e partilha com qualquer pessoa!
echo   Funciona em telemovel, tablet, qualquer dispositivo.
echo.
echo  ============================================================
echo.
echo  [Para parar tudo: fecha esta janela]
echo.

:: Iniciar cloudflared em foreground para ver o URL
cf.exe tunnel --url http://localhost:5026

:: Se chegou aqui, o tunel foi encerrado
echo.
echo  [INFO] Tunel encerrado.
pause
