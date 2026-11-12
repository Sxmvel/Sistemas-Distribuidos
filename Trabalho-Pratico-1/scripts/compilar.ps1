$raiz = Split-Path -Parent $PSScriptRoot
mvn -q -f (Join-Path $raiz "pom.xml") install -DskipTests
if ($LASTEXITCODE -eq 0) {
    Write-Host "Compilacao concluida."
}
