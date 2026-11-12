param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("broker", "atuadores", "sensores", "controlador", "painel", "cli")]
    [string]$Componente,
    [string]$Perfil = ""
)

$raiz = Split-Path -Parent $PSScriptRoot

$jars = @{
    broker      = "campo\broker-mqtt\target\broker-mqtt.jar"
    atuadores   = "campo\atuadores\target\atuadores.jar"
    sensores    = "campo\sensores\target\sensores.jar"
    controlador = "middleware\controlador\target\controlador.jar"
    painel      = "clientes\painel-web\target\painel-web.jar"
    cli         = "clientes\cliente-cli\target\cliente-cli.jar"
}

$titulos = @{
    broker      = "Broker MQTT"
    atuadores   = "Atuadores"
    sensores    = "Sensores"
    controlador = "Controlador $Perfil"
    painel      = "Painel Web (Cliente 1)"
    cli         = "CLI Defesa Civil (Cliente 2)"
}

$jar = Join-Path $raiz $jars[$Componente]
if (-not (Test-Path -LiteralPath $jar)) {
    throw "Jar nao encontrado: $jar. Rode scripts\compilar.ps1 antes."
}

$opcoes = @("-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-Dbarragem.componente=$Componente$Perfil")
$versao = (Get-Command java).Version.Major
if ($versao -ge 23) {
    $opcoes += "--sun-misc-unsafe-memory-access=allow"
}

$linha = "java " + (($opcoes | ForEach-Object { "'$_'" }) -join " ") + " -jar '$jar'"
if ($Perfil) {
    $linha += " '--spring.profiles.active=$Perfil'"
}

$comando = "chcp 65001 > `$null; `$Host.UI.RawUI.WindowTitle = '$($titulos[$Componente])'; Set-Location -LiteralPath '$raiz'; $linha"
Start-Process powershell -WorkingDirectory $raiz -ArgumentList "-NoExit", "-NoProfile", "-Command", $comando
