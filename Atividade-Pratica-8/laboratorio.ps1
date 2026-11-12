param(
    [int]$Porta = 8545,
    [switch]$PularTestes
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:NO_COLOR = "1"

$binFoundry = Join-Path $HOME ".foundry\bin"
if (-not (Get-Command forge -ErrorAction SilentlyContinue)) {
    $env:PATH = "$binFoundry;$env:PATH"
}
foreach ($ferramenta in @("forge", "cast", "anvil")) {
    if (-not (Get-Command $ferramenta -ErrorAction SilentlyContinue)) {
        throw "$ferramenta não encontrado. Instale o Foundry (ver README)."
    }
}

$raiz = $PSScriptRoot
$evidencias = Join-Path $raiz "evidencias"
$rpc = "http://127.0.0.1:$Porta"
$genese = 1794225600
$intervaloDeBloco = 12
$utf8 = New-Object System.Text.UTF8Encoding($false)

$contas = [ordered]@{
    dono          = @{ endereco = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"; chave = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" }
    bibliotecaria = @{ endereco = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"; chave = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d" }
    ana           = @{ endereco = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"; chave = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a" }
    bruno         = @{ endereco = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"; chave = "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6" }
    intruso       = @{ endereco = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"; chave = "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a" }
}

$assinaturasDeEventos = [ordered]@{
    DonoAlterado                = "DonoAlterado(address indexed anterior, address indexed novo)"
    TransferenciaDeDonoIniciada = "TransferenciaDeDonoIniciada(address indexed dono, address indexed pendente)"
    BibliotecarioAlterado       = "BibliotecarioAlterado(address indexed conta, bool autorizado)"
    LivroCadastrado             = "LivroCadastrado(uint256 indexed livroId, string titulo, uint32 exemplares)"
    LivroEmprestado             = "LivroEmprestado(uint256 indexed livroId, address indexed leitor, uint64 vencimento)"
    EmprestimoRenovado          = "EmprestimoRenovado(uint256 indexed livroId, address indexed leitor, uint64 vencimento)"
    LivroDevolvido              = "LivroDevolvido(uint256 indexed livroId, address indexed leitor, uint64 diasAtraso)"
}

$script:contrato = $null
$script:transacoes = New-Object System.Collections.Generic.List[object]
$script:tentativas = New-Object System.Collections.Generic.List[object]
$script:verificacoes = New-Object System.Collections.Generic.List[object]
$script:arquivoAtual = $null

function Citar([string]$valor) {
    if ($valor -eq "") { return '""' }
    if ($valor -match '[\s"]') { return '"' + ($valor -replace '"', '\"') + '"' }
    return $valor
}

function Executar([string]$programa, [string[]]$argumentos) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = (Get-Command $programa).Source
    $info.Arguments = ($argumentos | ForEach-Object { Citar $_ }) -join " "
    $info.WorkingDirectory = $raiz
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = $utf8
    $info.StandardErrorEncoding = $utf8
    $processo = [System.Diagnostics.Process]::Start($info)
    $erro = $processo.StandardError.ReadToEndAsync()
    $saida = $processo.StandardOutput.ReadToEnd()
    $processo.WaitForExit()
    [pscustomobject]@{
        saida  = $saida.TrimEnd()
        erro   = $erro.Result.TrimEnd()
        codigo = $processo.ExitCode
    }
}

function Abrir([string]$arquivo, [string]$titulo) {
    $script:arquivoAtual = Join-Path $evidencias $arquivo
    [System.IO.File]::WriteAllText($script:arquivoAtual, "", $utf8)
    Write-Host ""
    Write-Host "== $titulo" -ForegroundColor Cyan
    Escrever "# $titulo"
    Escrever ""
}

function Escrever([string]$texto) {
    [System.IO.File]::AppendAllText($script:arquivoAtual, $texto + "`n", $utf8)
}

function Mostrar([string]$texto) {
    Write-Host $texto
    Escrever $texto
}

function Verificar([string]$descricao, [bool]$condicao) {
    $script:verificacoes.Add([pscustomobject]@{ descricao = $descricao; ok = $condicao })
    $marca = if ($condicao) { "[ok]" } else { "[FALHOU]" }
    $cor = if ($condicao) { "Green" } else { "Red" }
    Write-Host "  $marca $descricao" -ForegroundColor $cor
    Escrever "  $marca $descricao"
}

function Hex([string]$valor) {
    $limpo = $valor -replace '^0x', ''
    if ($limpo.Length -gt 15) { $limpo = $limpo.Substring($limpo.Length - 15) }
    if ($limpo -eq "") { return [int64]0 }
    return [Convert]::ToInt64($limpo, 16)
}

function Primeiro([string]$linha) {
    $texto = $linha.Trim()
    if ($texto.StartsWith('"')) { return $texto.Trim('"') }
    return ($texto -split '\s+')[0]
}

function FormatarData([int64]$segundos) {
    return [DateTimeOffset]::FromUnixTimeSeconds($segundos).UtcDateTime.ToString("yyyy-MM-dd HH:mm:ss 'UTC'")
}

function NomeDaConta([string]$endereco) {
    foreach ($nome in $contas.Keys) {
        if ($contas[$nome].endereco -ieq $endereco) { return $nome }
    }
    return $endereco
}

function ErroDecodificado([string]$mensagem) {
    $final = [regex]::Match($mensagem, ':\s*([A-Z][A-Za-z]+(\([^()]*\))?)\s*$')
    if ($final.Success) { return $final.Groups[1].Value }
    $achados = [regex]::Matches($mensagem, '([A-Z][A-Za-z]+)\(([^()]*)\)')
    if ($achados.Count -eq 0) { return $null }
    return $achados[$achados.Count - 1].Value
}

function Blocos() {
    return [int64](Primeiro (Executar cast @("block-number", "--rpc-url", $rpc)).saida)
}

function Enviar([string]$passo, [string]$conta, [string]$assinatura, [string[]]$parametros) {
    $argumentos = @("send", $script:contrato, $assinatura) + $parametros + @("--private-key", $contas[$conta].chave, "--rpc-url", $rpc, "--json")
    $r = Executar cast $argumentos
    if ($r.codigo -ne 0) { throw "falha em '$passo': $($r.erro)" }
    $recibo = $r.saida | ConvertFrom-Json
    $item = [pscustomobject]@{
        numero = $script:transacoes.Count + 1
        passo  = $passo
        conta  = $conta
        funcao = ($assinatura -split '\(')[0]
        hash   = $recibo.transactionHash
        bloco  = Hex $recibo.blockNumber
        gas    = Hex $recibo.gasUsed
        status = if ($recibo.status -eq "0x1") { "sucesso" } else { "revert" }
        eventos = @($recibo.logs).Count
    }
    $script:transacoes.Add($item)
    Mostrar ("[{0:00}] {1}" -f $item.numero, $passo)
    Mostrar "     cast send <contrato> `"$assinatura`" $($parametros -join ' ')  (assinada por: $conta)"
    Mostrar "     tx $($item.hash)"
    Mostrar "     bloco $($item.bloco) | gas $($item.gas) | status $($item.status) | eventos emitidos $($item.eventos)"
    Escrever ""
    return $item
}

function Consultar([string]$assinatura, [string[]]$parametros) {
    $r = Executar cast (@("call", $script:contrato, $assinatura) + $parametros + @("--rpc-url", $rpc))
    if ($r.codigo -ne 0) { throw "falha na consulta $($assinatura): $($r.erro)" }
    return , @($r.saida -split "`r?`n" | ForEach-Object { Primeiro $_ })
}

function Tentar([string]$descricao, [string]$conta, [string]$assinatura, [string[]]$parametros, [string]$erroEsperado) {
    $antes = Blocos
    $r = Executar cast (@("send", $script:contrato, $assinatura) + $parametros + @("--private-key", $contas[$conta].chave, "--rpc-url", $rpc))
    $depois = Blocos
    $obtido = ErroDecodificado $r.erro
    Mostrar "- $descricao"
    Mostrar "  cast send <contrato> `"$assinatura`" $($parametros -join ' ')  (assinada por: $conta)"
    Mostrar "  saída do cast: $($r.erro -replace '\s+', ' ')"
    $nomeObtido = if ($obtido) { ($obtido -split '\(')[0] } else { "" }
    Verificar "$descricao -> revert $erroEsperado" ($r.codigo -ne 0 -and $nomeObtido -eq $erroEsperado)
    Verificar "nenhuma transação chegou à cadeia (bloco $antes -> $depois)" ($antes -eq $depois)
    Escrever ""
    $script:tentativas.Add([pscustomobject]@{
        descricao = $descricao; conta = $conta; funcao = ($assinatura -split '\(')[0]
        esperado = $erroEsperado; obtido = $obtido; minerada = $false; gas = 0; hash = "-"
    })
}

if (-not (Test-Path $evidencias)) { New-Item -ItemType Directory $evidencias | Out-Null }
Get-ChildItem $evidencias -File |
    Where-Object { -not ($PularTestes -and $_.Name -eq "02-testes.log") } |
    Remove-Item -Force

$ocupada = Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue
if ($ocupada) { throw "a porta $Porta já está em uso. Feche o processo ou use -Porta." }

Abrir "01-compilacao.log" "Compilação"
Mostrar "> forge build --force"
$r = Executar forge @("build", "--force")
Mostrar $r.saida
if ($r.erro) { Mostrar $r.erro }
Verificar "contrato compila" ($r.codigo -eq 0)
if ($r.codigo -ne 0) { throw "compilação falhou" }

if (-not $PularTestes) {
    Abrir "02-testes.log" "Testes automatizados e relatório de gas"
    Mostrar "> forge test --gas-report"
    Write-Host "  (rodando 25 testes + 2 invariantes, leva menos de 1 min)"
    $r = Executar forge @("test", "--gas-report")
    Escrever $r.saida
    if ($r.erro) { Escrever $r.erro }
    $resumo = ($r.saida -split "`r?`n" | Where-Object { $_ -match 'tests passed|test suites' }) -join " "
    Write-Host "  $resumo"
    Verificar "todos os testes passam" ($r.codigo -eq 0)
}

$logAnvil = Join-Path $evidencias "anvil.log"
$logAnvilErro = Join-Path $evidencias "anvil-erro.log"
$anvil = Start-Process -FilePath (Get-Command anvil).Source `
    -ArgumentList @("--port", $Porta, "--timestamp", $genese) `
    -RedirectStandardOutput $logAnvil -RedirectStandardError $logAnvilErro `
    -WindowStyle Hidden -PassThru

try {
    $pronto = $false
    for ($i = 0; $i -lt 50 -and -not $pronto; $i++) {
        Start-Sleep -Milliseconds 200
        $pronto = (Executar cast @("chain-id", "--rpc-url", $rpc)).codigo -eq 0
    }
    if (-not $pronto) { throw "o Anvil não respondeu em $rpc" }
    Executar cast @("rpc", "anvil_setBlockTimestampInterval", "$intervaloDeBloco", "--rpc-url", $rpc) | Out-Null

    Abrir "03-implantacao.log" "Implantação no nó local (Anvil)"
    $versaoAnvil = Primeiro ((Executar anvil @("--version")).saida -split "`r?`n" | Select-Object -First 1).Replace("anvil Version:", "")
    $chainId = Primeiro (Executar cast @("chain-id", "--rpc-url", $rpc)).saida
    Mostrar "nó: Anvil $versaoAnvil em $rpc | chain id $chainId | gênese $(FormatarData $genese) | +$intervaloDeBloco s por bloco"
    Mostrar "> forge create src/Biblioteca.sol:Biblioteca --rpc-url $rpc --private-key <chave do dono> --broadcast"
    $r = Executar forge @("create", "src/Biblioteca.sol:Biblioteca", "--rpc-url", $rpc, "--private-key", $contas.dono.chave, "--broadcast")
    $r.saida -split "`r?`n" | Where-Object { $_ -match '^(Deployer|Deployed to|Transaction hash):' } | ForEach-Object { Mostrar $_ }
    if ($r.codigo -ne 0) { throw "implantação falhou: $($r.erro)" }
    $script:contrato = [regex]::Match($r.saida, 'Deployed to:\s*(0x[0-9a-fA-F]{40})').Groups[1].Value
    $hashImplantacao = [regex]::Match($r.saida, 'Transaction hash:\s*(0x[0-9a-fA-F]{64})').Groups[1].Value
    $recibo = (Executar cast @("receipt", $hashImplantacao, "--rpc-url", $rpc, "--json")).saida | ConvertFrom-Json
    $implantacao = [pscustomobject]@{
        endereco = $script:contrato; hash = $hashImplantacao
        bloco = Hex $recibo.blockNumber; gas = Hex $recibo.gasUsed
        status = $recibo.status; tamanho = 0
    }
    $codigo = (Executar cast @("code", $script:contrato, "--rpc-url", $rpc)).saida
    $implantacao.tamanho = ($codigo.Length - 2) / 2
    Mostrar ""
    Mostrar "> cast receipt $hashImplantacao"
    Mostrar "  bloco $($implantacao.bloco) | gas $($implantacao.gas) | status $($recibo.status) | contractAddress $($recibo.contractAddress)"
    Mostrar "> cast code $($script:contrato)  -> $($implantacao.tamanho) bytes de bytecode implantado"
    Verificar "implantação confirmada (status 0x1)" ($recibo.status -eq "0x1")
    Verificar "há bytecode no endereço do contrato" ($implantacao.tamanho -gt 0)
    Verificar "o dono é a conta que implantou" ((Consultar "dono()(address)" @())[0] -ieq $contas.dono.endereco)

    Abrir "04-transacoes.log" "Transações que alteram estado"
    Enviar "dono autoriza a bibliotecária" "dono" "definirBibliotecario(address,bool)" @($contas.bibliotecaria.endereco, "true") | Out-Null
    Enviar "bibliotecária cadastra Dom Casmurro (2 exemplares)" "bibliotecaria" "cadastrarLivro(string,uint32)" @("Dom Casmurro", "2") | Out-Null
    Enviar "bibliotecária cadastra Memorias Postumas (1 exemplar)" "bibliotecaria" "cadastrarLivro(string,uint32)" @("Memorias Postumas de Bras Cubas", "1") | Out-Null
    $emprestimoAna = Enviar "empresta Dom Casmurro para Ana" "bibliotecaria" "emprestar(uint256,address)" @("1", $contas.ana.endereco)
    Enviar "empresta Dom Casmurro para Bruno" "bibliotecaria" "emprestar(uint256,address)" @("1", $contas.bruno.endereco) | Out-Null
    Enviar "empresta Memorias Postumas para Ana" "bibliotecaria" "emprestar(uint256,address)" @("2", $contas.ana.endereco) | Out-Null
    Enviar "Ana renova o próprio empréstimo de Dom Casmurro" "ana" "renovar(uint256)" @("1") | Out-Null

    $ultimoInstante = [int64](Primeiro (Executar cast @("block", "latest", "--field", "timestamp", "--rpc-url", $rpc)).saida)
    $proximoInstante = $ultimoInstante + 20 * 86400
    Mostrar ">> cast rpc evm_setNextBlockTimestamp $proximoInstante   (20 dias se passam no nó local: $(FormatarData $ultimoInstante) -> $(FormatarData $proximoInstante))"
    Executar cast @("rpc", "evm_setNextBlockTimestamp", "$proximoInstante", "--rpc-url", $rpc) | Out-Null
    Escrever ""

    Enviar "Bruno devolve Dom Casmurro com atraso" "bibliotecaria" "devolver(uint256,address)" @("1", $contas.bruno.endereco) | Out-Null
    Enviar "Ana devolve Dom Casmurro dentro do prazo renovado" "bibliotecaria" "devolver(uint256,address)" @("1", $contas.ana.endereco) | Out-Null
    Verificar "todas as transações confirmadas" (@($script:transacoes | Where-Object { $_.status -ne "sucesso" }).Count -eq 0)

    Abrir "05-consultas.log" "Consultas (funções view, via eth_call)"
    $blocoAntes = Blocos
    $nonceAntes = Primeiro (Executar cast @("nonce", $contas.dono.endereco, "--rpc-url", $rpc)).saida
    Mostrar "antes das consultas: bloco $blocoAntes | nonce do dono $nonceAntes"
    Mostrar ""
    foreach ($id in 1..2) {
        $livro = Consultar "consultarLivro(uint256)(string,uint32,uint32)" @("$id")
        Mostrar "> cast call <contrato> `"consultarLivro(uint256)(string,uint32,uint32)`" $id"
        Mostrar "  livro $id | titulo `"$($livro[0])`" | exemplares $($livro[1]) | disponiveis $($livro[2])"
    }
    $consultasEmprestimo = @(
        @{ livro = "1"; leitor = "ana" },
        @{ livro = "1"; leitor = "bruno" },
        @{ livro = "2"; leitor = "ana" }
    )
    $situacao = @{}
    foreach ($c in $consultasEmprestimo) {
        $e = Consultar "consultarEmprestimo(uint256,address)(bool,uint64,bool,uint64)" @($c.livro, $contas[$c.leitor].endereco)
        $situacao["$($c.livro)|$($c.leitor)"] = $e
        $vence = if ($e[0] -eq "true") { FormatarData ([int64]$e[1]) } else { "-" }
        Mostrar "> cast call <contrato> `"consultarEmprestimo(uint256,address)(bool,uint64,bool,uint64)`" $($c.livro) <$($c.leitor)>"
        Mostrar "  livro $($c.livro) / $($c.leitor) | ativo $($e[0]) | vence $vence | renovado $($e[2]) | dias de atraso $($e[3])"
    }
    $totalLivros = (Consultar "totalLivros()(uint256)" @())[0]
    $ativosAna = (Consultar "emprestimosAtivos(address)(uint8)" @($contas.ana.endereco))[0]
    $ehBibliotecaria = (Consultar "bibliotecario(address)(bool)" @($contas.bibliotecaria.endereco))[0]
    Mostrar "> totalLivros() = $totalLivros | emprestimosAtivos(ana) = $ativosAna | bibliotecario(bibliotecaria) = $ehBibliotecaria"
    $blocoDepois = Blocos
    $nonceDepois = Primeiro (Executar cast @("nonce", $contas.dono.endereco, "--rpc-url", $rpc)).saida
    Mostrar ""
    Mostrar "depois das consultas: bloco $blocoDepois | nonce do dono $nonceDepois"
    $livro1 = Consultar "consultarLivro(uint256)(string,uint32,uint32)" @("1")
    $livro2 = Consultar "consultarLivro(uint256)(string,uint32,uint32)" @("2")
    Verificar "Dom Casmurro voltou a ter 2 de 2 exemplares" ($livro1[2] -eq "2")
    Verificar "Memorias Postumas segue com 0 de 1 exemplar" ($livro2[2] -eq "0")
    Verificar "empréstimo de Memorias Postumas com Ana ativo e atrasado" ($situacao["2|ana"][0] -eq "true" -and [int]$situacao["2|ana"][3] -gt 0)
    Verificar "Ana tem 1 empréstimo ativo" ($ativosAna -eq "1")
    Verificar "consultas não criaram blocos" ($blocoAntes -eq $blocoDepois)
    Verificar "consultas não consumiram nonce" ($nonceAntes -eq $nonceDepois)

    Abrir "06-eventos.log" "Eventos observados (cast logs)"
    $contagem = [ordered]@{}
    foreach ($nome in $assinaturasDeEventos.Keys) {
        $r = Executar cast @("logs", "--from-block", "0", "--to-block", "latest", "--address", $script:contrato, $assinaturasDeEventos[$nome], "--rpc-url", $rpc)
        $quantos = ([regex]::Matches($r.saida, '(?m)^- address:')).Count
        $contagem[$nome] = $quantos
        Mostrar "> cast logs --from-block 0 --address <contrato> `"$($assinaturasDeEventos[$nome])`""
        Mostrar "  $quantos ocorrência(s)"
        if ($quantos -gt 0) { Escrever $r.saida }
        Escrever ""
    }
    Mostrar "> filtro por tópico indexado: só LivroEmprestado do livro 1"
    $r = Executar cast @("logs", "--from-block", "0", "--to-block", "latest", "--address", $script:contrato, $assinaturasDeEventos.LivroEmprestado, "1", "--rpc-url", $rpc)
    $filtrados = ([regex]::Matches($r.saida, '(?m)^- address:')).Count
    Mostrar "  $filtrados ocorrência(s), filtradas pelo nó a partir do topic1 = livroId"
    Escrever $r.saida
    $atrasoBruno = [regex]::Match((Executar cast @("logs", "--from-block", "0", "--address", $script:contrato, $assinaturasDeEventos.LivroDevolvido, "1", $contas.bruno.endereco, "--rpc-url", $rpc)).saida, 'diasAtraso:\s*(\d+)').Groups[1].Value
    Verificar "1 DonoAlterado, 2 BibliotecarioAlterado, 2 LivroCadastrado" ($contagem.DonoAlterado -eq 1 -and $contagem.BibliotecarioAlterado -eq 2 -and $contagem.LivroCadastrado -eq 2)
    Verificar "3 LivroEmprestado, 1 EmprestimoRenovado, 2 LivroDevolvido" ($contagem.LivroEmprestado -eq 3 -and $contagem.EmprestimoRenovado -eq 1 -and $contagem.LivroDevolvido -eq 2)
    Verificar "filtro pelo livro 1 devolve só os 2 empréstimos dele" ($filtrados -eq 2)
    Verificar "evento de devolução do Bruno registra atraso ($atrasoBruno dias)" ([int]$atrasoBruno -gt 0)

    Abrir "07-reverts.log" "Tentativas inválidas e revert"
    Mostrar "Sem --gas-limit, o cast estima o gas antes de assinar. A estimativa executa a chamada,"
    Mostrar "encontra o revert e a transação nem é enviada."
    Mostrar ""
    Tentar "intruso tenta cadastrar livro" "intruso" "cadastrarLivro(string,uint32)" @("Livro Falso", "100") "SomenteBibliotecario"
    Tentar "Ana tenta registrar a própria devolução" "ana" "devolver(uint256,address)" @("2", $contas.ana.endereco) "SomenteBibliotecario"
    Tentar "bibliotecária tenta se autopromover a dono das permissões" "bibliotecaria" "definirBibliotecario(address,bool)" @($contas.intruso.endereco, "true") "SomenteDono"
    Tentar "bibliotecária empresta livro sem exemplar disponível" "bibliotecaria" "emprestar(uint256,address)" @("2", $contas.bruno.endereco) "SemExemplarDisponivel"
    Tentar "bibliotecária registra devolução duplicada" "bibliotecaria" "devolver(uint256,address)" @("1", $contas.bruno.endereco) "EmprestimoInexistente"
    Tentar "Ana tenta renovar empréstimo atrasado" "ana" "renovar(uint256)" @("2") "EmprestimoAtrasado"
    Tentar "bibliotecária cadastra livro sem título" "bibliotecaria" "cadastrarLivro(string,uint32)" @("", "1") "TituloInvalido"
    Tentar "bibliotecária empresta livro inexistente" "bibliotecaria" "emprestar(uint256,address)" @("99", $contas.bruno.endereco) "LivroInexistente"

    Mostrar "Com --gas-limit fixo, o cast pula a estimativa. A transação é minerada, reverte e paga o gas."
    $devolvidosAntes = $contagem.LivroDevolvido
    $r = Executar cast @("send", $script:contrato, "devolver(uint256,address)", "2", $contas.ana.endereco, "--private-key", $contas.intruso.chave, "--rpc-url", $rpc, "--gas-limit", "100000", "--json")
    $forcado = $r.saida | ConvertFrom-Json
    $gasForcado = Hex $forcado.gasUsed
    $blocoForcado = Hex $forcado.blockNumber
    $reexecucao = Executar cast @("run", $forcado.transactionHash, "--rpc-url", $rpc)
    $erroForcado = ErroDecodificado ($reexecucao.saida + " " + $reexecucao.erro)
    Mostrar "- intruso força a devolução do empréstimo de Ana"
    Mostrar "  cast send <contrato> `"devolver(uint256,address)`" 2 <ana> --gas-limit 100000  (assinada por: intruso)"
    Mostrar "  tx $($forcado.transactionHash)"
    Mostrar "  bloco $blocoForcado | gas $gasForcado | status $($forcado.status) | eventos emitidos $(@($forcado.logs).Count)"
    Mostrar "  cast run (reexecução da transação): $erroForcado"
    $ainda = Consultar "consultarEmprestimo(uint256,address)(bool,uint64,bool,uint64)" @("2", $contas.ana.endereco)
    $devolvidosDepois = ([regex]::Matches((Executar cast @("logs", "--from-block", "0", "--address", $script:contrato, $assinaturasDeEventos.LivroDevolvido, "--rpc-url", $rpc)).saida, '(?m)^- address:')).Count
    Verificar "transação forçada foi minerada com status 0x0" ($forcado.status -eq "0x0")
    Verificar "o revert ainda custou $gasForcado de gas ao intruso" ($gasForcado -gt 21000)
    Verificar "erro na reexecução é SomenteBibliotecario" ($erroForcado -like "SomenteBibliotecario*")
    Verificar "empréstimo de Ana continua ativo" ($ainda[0] -eq "true")
    Verificar "nenhum LivroDevolvido novo ($devolvidosAntes -> $devolvidosDepois)" ($devolvidosAntes -eq $devolvidosDepois)
    $script:tentativas.Add([pscustomobject]@{
        descricao = "intruso força a devolução do empréstimo de Ana"; conta = "intruso"; funcao = "devolver"
        esperado = "SomenteBibliotecario"; obtido = $erroForcado; minerada = $true; gas = $gasForcado; hash = $forcado.transactionHash
    })

    Abrir "08-indexador.log" "Indexador off-chain reconstruindo o estado pelos eventos"
    Mostrar "O indexador só lê logs (eth_getLogs). Ele não chama nenhuma função do contrato para montar o estado."
    Mostrar ""
    $brutos = New-Object System.Collections.Generic.List[object]
    foreach ($nome in @("LivroCadastrado", "LivroEmprestado", "EmprestimoRenovado", "LivroDevolvido")) {
        $r = Executar cast @("logs", "--from-block", "0", "--to-block", "latest", "--address", $script:contrato, $assinaturasDeEventos[$nome], "--rpc-url", $rpc, "--json")
        $lista = $r.saida | ConvertFrom-Json
        foreach ($log in $lista) {
            $brutos.Add([pscustomobject]@{ nome = $nome; bloco = Hex $log.blockNumber; indice = Hex $log.logIndex; log = $log })
        }
    }
    $catalogo = [ordered]@{}
    $ativos = [ordered]@{}
    foreach ($ev in ($brutos | Sort-Object bloco, indice)) {
        $livroId = Hex $ev.log.topics[1]
        if ($ev.nome -eq "LivroCadastrado") {
            $campos = (Executar cast @("abi-decode", "f()(string,uint32)", $ev.log.data)).saida -split "`r?`n"
            $titulo = Primeiro $campos[0]
            $catalogo["$livroId"] = $titulo
            Mostrar ("bloco {0,2} | {1,-18} | livro {2} `"{3}`" com {4} exemplar(es)" -f $ev.bloco, $ev.nome, $livroId, $titulo, (Primeiro $campos[1]))
            continue
        }
        $leitor = NomeDaConta ("0x" + $ev.log.topics[2].Substring(26))
        $valor = Hex $ev.log.data
        $chave = "$livroId|$leitor"
        switch ($ev.nome) {
            "LivroEmprestado" { $ativos[$chave] = $valor; $detalhe = "vence $(FormatarData $valor)" }
            "EmprestimoRenovado" { $ativos[$chave] = $valor; $detalhe = "novo vencimento $(FormatarData $valor)" }
            "LivroDevolvido" { $ativos.Remove($chave); $detalhe = "$valor dia(s) de atraso" }
        }
        Mostrar ("bloco {0,2} | {1,-18} | livro {2} / {3,-5} | {4}" -f $ev.bloco, $ev.nome, $livroId, $leitor, $detalhe)
    }
    Mostrar ""
    Mostrar "Empréstimos ativos segundo o indexador, conferidos com a função view:"
    $confere = $true
    foreach ($chave in $ativos.Keys) {
        $livroId, $leitor = $chave -split '\|'
        $naCadeia = Consultar "consultarEmprestimo(uint256,address)(bool,uint64,bool,uint64)" @($livroId, $contas[$leitor].endereco)
        $igual = ($naCadeia[0] -eq "true" -and [int64]$naCadeia[1] -eq $ativos[$chave])
        if (-not $igual) { $confere = $false }
        $marca = if ($igual) { "confere" } else { "DIVERGE" }
        Mostrar "  livro $livroId `"$($catalogo[$livroId])`" com $leitor, vence $(FormatarData $ativos[$chave]) -> $marca (view: ativo $($naCadeia[0]), atraso $($naCadeia[3]) dia(s))"
    }
    Verificar "indexador encontrou exatamente 1 empréstimo ativo" ($ativos.Count -eq 1)
    Verificar "estado reconstruído pelos eventos confere com o estado on-chain" $confere
    Verificar "catálogo reconstruído tem os 2 títulos" ($catalogo.Count -eq 2)

    $relatorio = New-Object System.Collections.Generic.List[string]
    $relatorio.Add("# Relatório do laboratório da AP8")
    $relatorio.Add("")
    $relatorio.Add("Gerado por ``laboratorio.ps1``. Nó local Anvil $versaoAnvil (chain id $chainId), bloco gênese em $(FormatarData $genese) e intervalo fixo de $intervaloDeBloco s entre blocos. Com esses parâmetros, endereços, hashes e gas são idênticos a cada execução.")
    $relatorio.Add("")
    $relatorio.Add("## Implantação")
    $relatorio.Add("")
    $relatorio.Add("| Campo | Valor |")
    $relatorio.Add("| --- | --- |")
    $relatorio.Add("| Endereço do contrato | ``$($implantacao.endereco)`` |")
    $relatorio.Add("| Hash da transação | ``$($implantacao.hash)`` |")
    $relatorio.Add("| Bloco | $($implantacao.bloco) |")
    $relatorio.Add("| Gas | $($implantacao.gas) |")
    $relatorio.Add("| Bytecode implantado | $($implantacao.tamanho) bytes |")
    $relatorio.Add("| Implantado por | dono (``$($contas.dono.endereco)``) |")
    $relatorio.Add("")
    $relatorio.Add("## Transações que alteram estado")
    $relatorio.Add("")
    $relatorio.Add("| # | Passo | Assinada por | Função | Bloco | Gas | Eventos | Status | Hash |")
    $relatorio.Add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    foreach ($t in $script:transacoes) {
        $relatorio.Add("| $($t.numero) | $($t.passo) | $($t.conta) | ``$($t.funcao)`` | $($t.bloco) | $($t.gas) | $($t.eventos) | $($t.status) | ``$($t.hash)`` |")
    }
    $relatorio.Add("")
    $relatorio.Add("Entre as transações 7 e 8, ``evm_setNextBlockTimestamp`` adiantou o relógio do nó em 20 dias ($(FormatarData $ultimoInstante) -> $(FormatarData $proximoInstante)).")
    $relatorio.Add("")
    $relatorio.Add("## Gas por operação")
    $relatorio.Add("")
    $relatorio.Add("| Operação | Gas medido no Anvil |")
    $relatorio.Add("| --- | --- |")
    $relatorio.Add("| implantação | $($implantacao.gas) |")
    foreach ($grupo in ($script:transacoes | Group-Object funcao)) {
        $valores = ($grupo.Group | ForEach-Object { $_.gas } | Sort-Object -Unique) -join " / "
        $relatorio.Add("| ``$($grupo.Name)`` | $valores |")
    }
    $relatorio.Add("| ``devolver`` revertido por falta de permissão | $gasForcado |")
    $relatorio.Add("| funções ``view`` via ``eth_call`` | 0 (sem transação, bloco $blocoAntes -> $blocoDepois) |")
    $relatorio.Add("")
    $relatorio.Add("## Eventos observados")
    $relatorio.Add("")
    $relatorio.Add("| Evento | Ocorrências |")
    $relatorio.Add("| --- | --- |")
    foreach ($nome in $contagem.Keys) { $relatorio.Add("| ``$nome`` | $($contagem[$nome]) |") }
    $relatorio.Add("")
    $relatorio.Add("## Tentativas inválidas")
    $relatorio.Add("")
    $relatorio.Add("| Tentativa | Conta | Função | Erro esperado | Erro obtido | Chegou à cadeia? |")
    $relatorio.Add("| --- | --- | --- | --- | --- | --- |")
    foreach ($t in $script:tentativas) {
        $cadeia = if ($t.minerada) { "sim, status 0x0, $($t.gas) de gas, ``$($t.hash)``" } else { "não, barrada na estimativa de gas" }
        $relatorio.Add("| $($t.descricao) | $($t.conta) | ``$($t.funcao)`` | ``$($t.esperado)`` | ``$($t.obtido)`` | $cadeia |")
    }
    $relatorio.Add("")
    $falhas = @($script:verificacoes | Where-Object { -not $_.ok }).Count
    $relatorio.Add("## Verificações")
    $relatorio.Add("")
    $relatorio.Add("**$($script:verificacoes.Count) verificações, $falhas falha(s).**")
    $relatorio.Add("")
    foreach ($v in $script:verificacoes) {
        $marca = if ($v.ok) { "ok" } else { "FALHOU" }
        $relatorio.Add("- [$marca] $($v.descricao)")
    }
    [System.IO.File]::WriteAllLines((Join-Path $evidencias "relatorio.md"), $relatorio, $utf8)
}
finally {
    if ($anvil -and -not $anvil.HasExited) { Stop-Process -Id $anvil.Id -Force }
    if ((Test-Path $logAnvilErro) -and (Get-Item $logAnvilErro).Length -eq 0) { Remove-Item $logAnvilErro -Force }
}

$falhas = @($script:verificacoes | Where-Object { -not $_.ok }).Count
Write-Host ""
$cor = if ($falhas -eq 0) { "Green" } else { "Red" }
Write-Host "$($script:verificacoes.Count) verificações, $falhas falha(s). Evidências em $evidencias" -ForegroundColor $cor
if ($falhas -gt 0) { exit 1 }
