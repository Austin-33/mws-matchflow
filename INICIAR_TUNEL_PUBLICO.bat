@echo off
title AUSTIN LEAGUE CORE — Tunel Publico
color 0A
cls

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║      AUSTIN LEAGUE CORE — ACESSO PUBLICO  🌍         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  IMPORTANTE: O servidor Flask tem de estar a correr!
echo  Se ainda nao iniciaste, corre primeiro: INICIAR_SERVIDOR.bat
echo.
echo  A criar tunel publico com Cloudflare...
echo.
echo  ════════════════════════════════════════════════════════
echo  Quando aparecer a linha:
echo.
echo    https://xxxx.trycloudflare.com
echo.
echo  Esse e o teu link publico — partilha com quem quiseres!
echo  Funciona em qualquer dispositivo com internet.
echo  ════════════════════════════════════════════════════════
echo.

cd /d "%~dp0"
cf.exe tunnel --url http://127.0.0.1:5026

pause
