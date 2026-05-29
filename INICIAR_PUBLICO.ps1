# ================================================================
# AUSTIN LEAGUE CORE — Acesso Publico via Cloudflare Tunnel
# Script PowerShell completo:
#   - Inicia o Flask se nao estiver a correr
#   - Inicia o cloudflared e cria tunel publico
#   - Extrai o URL automaticamente
#   - Mostra o URL de forma destacada
#   - Copia o URL para a area de transferencia
#   - Abre o browser automaticamente
# ================================================================
# Como usar:
#   Clica com botao direito -> "Executar com PowerShell"
#   OU no terminal:
#   powershell -ExecutionPolicy Bypass -File INICIAR_PUBLICO.ps1
# ================================================================

# ── Configuracoes ────────────────────────────────────────────
$PORTA        = 5026                    # Porta do Flask
$CF_EXE       = "cf.exe"               # Nome do executavel cloudflared
$FLASK_SCRIPT = "austinapp.py"         # Script principal do Flask
$TIMEOUT_CF   = 30                     # Segundos a aguardar pelo URL do tunel
$TIMEOUT_FLASK = 8                     # Segundos a aguardar Flask arrancar

# ── Funcoes auxiliares ───────────────────────────────────────

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Cyan
    Write-Host "   AUSTIN LEAGUE CORE  |  ACESSO PUBLICO  |  Cloudflare" -ForegroundColor Cyan
    Write-Host "  ============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Num, [string]$Msg)
    Write-Host "  [$Num] $Msg" -ForegroundColor Yellow
}

function Write-OK {
    param([string]$Msg)
    Write-Host "  [OK] $Msg" -ForegroundColor Green
}

function Write-Info {
    param([string]$Msg)
    Write-Host "  [INFO] $Msg" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "  [AVISO] $Msg" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Msg)
    Write-Host "  [ERRO] $Msg" -ForegroundColor Red
}

# ── Mudar para a pasta do script ─────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Banner

# ================================================================
# PASSO 1 — Verificar cloudflared.exe
# ================================================================
Write-Step "1/4" "A verificar cloudflared ($CF_EXE)..."

if (-not (Test-Path $CF_EXE)) {
    Write-Err "$CF_EXE nao encontrado em: $scriptDir"
    Write-Host ""
    Write-Host "  Faz download em: https://github.com/cloudflare/cloudflared/releases" -ForegroundColor White
    Write-Host "  Coloca o ficheiro cloudflared.exe nesta pasta com o nome cf.exe" -ForegroundColor White
    Write-Host ""
    Read-Host "  Prima ENTER para sair"
    exit 1
}

# Obter versao do cloudflared
$cfVersion = & ".\$CF_EXE" --version 2>&1 | Select-Object -First 1
Write-OK "$CF_EXE encontrado — $cfVersion"

# ================================================================
# PASSO 2 — Verificar / Iniciar Flask
# ================================================================
Write-Host ""
Write-Step "2/4" "A verificar servidor Flask (porta $PORTA)..."

# Verificar se a porta esta em uso
$portaEmUso = netstat -ano 2>$null | Select-String ":$PORTA\s.*LISTENING"

if ($portaEmUso) {
    Write-OK "Flask ja esta a correr na porta $PORTA."
} else {
    Write-Info "Flask nao esta a correr. A iniciar..."

    # Detectar Python do venv ou sistema
    $python = $null
    if (Test-Path ".venv\Scripts\python.exe") {
        $python = ".venv\Scripts\python.exe"
        Write-Info "Python encontrado: .venv\Scripts\python.exe"
    } elseif (Test-Path "venv\Scripts\python.exe") {
        $python = "venv\Scripts\python.exe"
        Write-Info "Python encontrado: venv\Scripts\python.exe"
    } else {
        $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCheck) {
            $python = "python"
            Write-Info "Python do sistema encontrado."
        } else {
            Write-Err "Python nao encontrado! Instala Python ou activa o venv."
            Read-Host "  Prima ENTER para sair"
            exit 1
        }
    }

    # Verificar se o script Flask existe
    if (-not (Test-Path $FLASK_SCRIPT)) {
        Write-Err "Script Flask nao encontrado: $FLASK_SCRIPT"
        Read-Host "  Prima ENTER para sair"
        exit 1
    }

    # Iniciar Flask numa janela separada
    $flaskArgs = "/k `"cd /d `"$scriptDir`" && `"$python`" $FLASK_SCRIPT`""
    Start-Process cmd -ArgumentList $flaskArgs -WindowStyle Normal
    Write-Info "Aguardando Flask arrancar ($TIMEOUT_FLASK segundos)..."

    # Aguardar Flask com verificacao progressiva
    $flaskOk = $false
    for ($i = 1; $i -le $TIMEOUT_FLASK; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "  ." -NoNewline -ForegroundColor DarkGray
        $check = netstat -ano 2>$null | Select-String ":$PORTA\s.*LISTENING"
        if ($check) {
            $flaskOk = $true
            break
        }
    }
    Write-Host ""

    if ($flaskOk) {
        Write-OK "Flask iniciado com sucesso na porta $PORTA!"
    } else {
        Write-Warn "Flask pode ainda estar a arrancar. A continuar mesmo assim..."
        Write-Info "Se o tunel falhar, aguarda mais uns segundos e tenta de novo."
    }
}

# ================================================================
# PASSO 3 — Terminar tuneis anteriores (evitar conflitos)
# ================================================================
Write-Host ""
Write-Step "3/4" "A verificar tuneis Cloudflare existentes..."

$cfProcessos = Get-Process -Name "cf" -ErrorAction SilentlyContinue
if ($cfProcessos) {
    Write-Warn "Encontrado(s) $($cfProcessos.Count) processo(s) cf.exe a correr."
    Write-Info "A terminar para evitar conflitos..."
    $cfProcessos | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-OK "Processos anteriores terminados."
} else {
    Write-OK "Nenhum tunel anterior encontrado."
}

# ================================================================
# PASSO 4 — Iniciar Cloudflare Tunnel e capturar URL
# ================================================================
Write-Host ""
Write-Step "4/4" "A criar tunel Cloudflare publico..."
Write-Host ""
Write-Host "  Aguarda 10-20 segundos enquanto o tunel e criado..." -ForegroundColor DarkGray
Write-Host ""

# Ficheiro temporario para capturar o output do cloudflared
$logFile = Join-Path $env:TEMP "austin_cf_tunnel_$PID.log"

# Remover log anterior se existir
if (Test-Path $logFile) { Remove-Item $logFile -Force }

# Iniciar cloudflared em background, redirecionando stderr para o log
# (cloudflared escreve o URL no stderr)
$cfProcess = Start-Process -FilePath ".\$CF_EXE" `
    -ArgumentList "tunnel --url http://localhost:$PORTA" `
    -RedirectStandardError $logFile `
    -PassThru `
    -WindowStyle Hidden

Write-Info "Processo cloudflared iniciado (PID: $($cfProcess.Id))"

# ── Aguardar e extrair o URL ─────────────────────────────────
$publicUrl = $null
$elapsed   = 0
$dots      = 0

Write-Host "  A aguardar URL" -NoNewline -ForegroundColor Yellow

while (-not $publicUrl -and $elapsed -lt $TIMEOUT_CF) {
    Start-Sleep -Milliseconds 500
    $elapsed += 0.5
    $dots++

    # Mostrar progresso
    if ($dots % 2 -eq 0) {
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }

    # Verificar se o processo ainda esta a correr
    if ($cfProcess.HasExited) {
        Write-Host ""
        Write-Err "cloudflared terminou inesperadamente!"
        if (Test-Path $logFile) {
            Write-Host ""
            Write-Host "  Log do erro:" -ForegroundColor Red
            Get-Content $logFile | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkRed }
        }
        Read-Host "`n  Prima ENTER para sair"
        exit 1
    }

    # Tentar ler o log e extrair o URL
    if (Test-Path $logFile) {
        $logContent = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
        if ($logContent) {
            # Padrao do URL do Cloudflare Tunnel
            if ($logContent -match 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com') {
                $publicUrl = $Matches[0]
            }
        }
    }
}

Write-Host ""

# ================================================================
# RESULTADO
# ================================================================

if ($publicUrl) {

    # ── Sucesso! Mostrar URL de forma destacada ───────────────
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host "                                                              " -ForegroundColor Green
    Write-Host "   TUNEL ACTIVO! O teu sistema esta acessivel publicamente." -ForegroundColor Green
    Write-Host "                                                              " -ForegroundColor Green
    Write-Host "   URL PUBLICO:" -ForegroundColor White
    Write-Host ""
    Write-Host "   >>> $publicUrl <<<" -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "   Partilha este link com qualquer pessoa no mundo!" -ForegroundColor Green
    Write-Host "   Funciona em telemovel, tablet, qualquer dispositivo." -ForegroundColor Green
    Write-Host "                                                              " -ForegroundColor Green
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host ""

    # ── Copiar URL para clipboard ─────────────────────────────
    try {
        $publicUrl | Set-Clipboard
        Write-OK "URL copiado para a area de transferencia!"
    } catch {
        Write-Warn "Nao foi possivel copiar automaticamente. Copia manualmente:"
        Write-Host "  $publicUrl" -ForegroundColor White
    }

    # ── Abrir browser automaticamente ────────────────────────
    Write-Host ""
    Write-Info "A abrir browser em $publicUrl ..."
    Start-Sleep -Seconds 2
    try {
        Start-Process $publicUrl
        Write-OK "Browser aberto!"
    } catch {
        Write-Warn "Nao foi possivel abrir o browser automaticamente."
        Write-Host "  Abre manualmente: $publicUrl" -ForegroundColor White
    }

    # ── Informacoes adicionais ────────────────────────────────
    Write-Host ""
    Write-Host "  ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  Acesso local:   http://127.0.0.1:$PORTA" -ForegroundColor DarkGray
    Write-Host "  Acesso publico: $publicUrl" -ForegroundColor DarkGray
    Write-Host "  ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  NOTA: O URL muda cada vez que reinicias o tunel." -ForegroundColor DarkGray
    Write-Host "  Para URL fixo, cria conta gratuita em cloudflare.com" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [Tunel activo. Fecha esta janela para parar o tunel.]" -ForegroundColor Yellow
    Write-Host ""

    # ── Manter o tunel activo ─────────────────────────────────
    # Monitorizar o processo e avisar se cair
    while (-not $cfProcess.HasExited) {
        Start-Sleep -Seconds 10

        # Verificar se Flask ainda esta a correr
        $flaskCheck = netstat -ano 2>$null | Select-String ":$PORTA\s.*LISTENING"
        if (-not $flaskCheck) {
            Write-Host ""
            Write-Warn "Flask parece ter parado! O tunel continua mas o site pode nao responder."
        }
    }

    Write-Host ""
    Write-Warn "O tunel Cloudflare foi encerrado."

} else {

    # ── Falhou a obter URL — mostrar em foreground como fallback
    Write-Host ""
    Write-Warn "Nao foi possivel extrair o URL automaticamente em $TIMEOUT_CF segundos."
    Write-Host ""
    Write-Info "A tentar em modo visivel para poderes ver o URL manualmente..."
    Write-Host ""

    # Terminar o processo em background
    if (-not $cfProcess.HasExited) {
        $cfProcess.Kill()
        Start-Sleep -Seconds 1
    }

    # Mostrar log se existir
    if (Test-Path $logFile) {
        $logContent = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
        if ($logContent) {
            Write-Host "  Log do cloudflared:" -ForegroundColor DarkGray
            Write-Host $logContent -ForegroundColor DarkGray
        }
    }

    Write-Host ""
    Write-Host "  A iniciar cloudflared em modo visivel..." -ForegroundColor Yellow
    Write-Host "  Procura a linha com 'trycloudflare.com' no output abaixo:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

    # Correr em foreground para o utilizador ver o URL
    & ".\$CF_EXE" tunnel --url "http://localhost:$PORTA"
}

# ── Limpeza ──────────────────────────────────────────────────
if (Test-Path $logFile) {
    Remove-Item $logFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Read-Host "  Prima ENTER para sair"
