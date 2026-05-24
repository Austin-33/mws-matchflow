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
start "ALC Flask Server" python app.py

timeout /t 3 /nobreak >nul

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
echo  INICIAR_TUNEL_PUBLICO.bat
echo.
pause
