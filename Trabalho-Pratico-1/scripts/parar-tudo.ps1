param(
    [switch]$LimparDados
)

$raiz = Split-Path -Parent $PSScriptRoot

$processos = Get-CimInstance Win32_Process -Filter "name='java.exe'" |
    Where-Object { $_.CommandLine -like "*-Dbarragem.componente=*" }

foreach ($processo in $processos) {
    $nome = [regex]::Match($processo.CommandLine, "-Dbarragem\.componente=(\S+)").Groups[1].Value
    Stop-Process -Id $processo.ProcessId -Force
    Write-Host "Parado: $nome (PID $($processo.ProcessId))"
}

if (-not $processos) {
    Write-Host "Nenhum componente em execucao."
}

if ($LimparDados) {
    Remove-Item -LiteralPath (Join-Path $raiz "dados") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Armazenamento dos controladores apagado."
}
