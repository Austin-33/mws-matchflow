@echo off
title AUSTIN LEAGUE CORE — Servidor
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         AUSTIN LEAGUE CORE  ⚡  League Core Engine   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  A iniciar servidor Flask...
echo.

cd /d "%~dp0"

REM ── Usar Python do venv se existir, senão usar o do sistema ──
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo  Python: %PYTHON%
echo.

REM ── Iniciar servidor (janela separada para ver erros) ──
start "ALC Flask Server" cmd /k "%PYTHON% austinapp.py"

timeout /t 4 /nobreak >nul

echo  ✅ Servidor iniciado!
echo.
echo  ┌─────────────────────────────────────────────────────┐
echo  │  ACESSO LOCAL (este computador):                    │
echo  │  http://127.0.0.1:5026                              │
echo  │                                                     │
echo  │  ACESSO NA REDE (outros dispositivos):              │
echo  │  http://10.0.57.71:5026                             │
echo  │  http://192.168.8.31:5026                           │
echo  └─────────────────────────────────────────────────────┘
echo.
echo  Para acesso PUBLICO pela internet, corre:
echo  INICIAR_PUBLICO.bat  (simples)
echo  INICIAR_PUBLICO.ps1  (mostra URL automaticamente)
echo.

REM ── Abrir browser automaticamente ──
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5026

pause
