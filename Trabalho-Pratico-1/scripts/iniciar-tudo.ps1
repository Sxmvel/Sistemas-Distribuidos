param(
    [switch]$ComCli,
    [switch]$LimparDados
)

$raiz = Split-Path -Parent $PSScriptRoot
$iniciar = Join-Path $PSScriptRoot "iniciar-componente.ps1"

if ($LimparDados) {
    Remove-Item -LiteralPath (Join-Path $raiz "dados") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Armazenamento dos controladores apagado."
}

Write-Host "[1/5] Broker MQTT"
& $iniciar -Componente broker
Start-Sleep -Seconds 4

Write-Host "[2/5] Atuadores"
& $iniciar -Componente atuadores

Write-Host "[3/5] Controladores c1, c2, c3"
& $iniciar -Componente controlador -Perfil c1
& $iniciar -Componente controlador -Perfil c2
& $iniciar -Componente controlador -Perfil c3
Start-Sleep -Seconds 12

Write-Host "[4/5] Sensores"
& $iniciar -Componente sensores

Write-Host "[5/5] Painel web"
& $iniciar -Componente painel
if ($ComCli) {
    & $iniciar -Componente cli
}

Start-Sleep -Seconds 10
Start-Process "http://localhost:8080"
Write-Host "Sistema no ar. Painel: http://localhost:8080"
