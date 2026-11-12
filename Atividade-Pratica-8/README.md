# AP8 — Contrato inteligente de empréstimos de biblioteca

Contrato inteligente da Atividade Prática 8 de Sistemas Distribuídos, escrito em **Solidity 0.8.28**
com **Foundry** (forge, cast e anvil). O domínio é o mesmo das atividades 2 a 5: o acervo e os
empréstimos de uma biblioteca. Desta vez o estado não fica num servidor. Fica num contrato que
todo nó da rede executa e precisa calcular igual: livros, exemplares disponíveis, empréstimos
ativos com vencimento e as permissões de quem pode alterar cada coisa.

O contrato parte da ideia do `RegistroLeituras` do enunciado (um registro que guarda estado e emite
evento), mas muda tudo: tem papéis de acesso, treze erros customizados que revertem a transação,
prazo com atraso calculado on-chain e sete eventos.

As respostas às questões de análise, os riscos de segurança e a comparação com a API REST da AP2
estão em [`Questoes-de-Analise-AP8.docx`](Questoes-de-Analise-AP8.docx). As evidências do
laboratório estão em [`evidencias/`](evidencias/).

---

## Execução

### Requisitos

| Ferramenta | Versão usada | Observação |
| --- | --- | --- |
| Foundry (`forge`, `cast`, `anvil`) | 1.9.0 (`6056c58`) | release estável de 2026-11-02 |
| Compilador Solidity | 0.8.28 | fixado no `foundry.toml`, baixado pelo forge na primeira compilação |
| forge-std | v1.17.0 | biblioteca de testes, instalada em `lib/` (fora do git) |
| PowerShell | 5.1 ou 7 | só para o `laboratorio.ps1` |

**Instalação do Foundry no Windows.** O caminho oficial é o `foundryup`, que roda no Git Bash. Aqui
o binário foi instalado direto da release, conferindo o checksum publicado:

```powershell
$v = "v1.9.0"
$base = "https://github.com/foundry-rs/foundry/releases/download/$v"
Invoke-WebRequest "$base/foundry_${v}_win32_amd64.zip" -OutFile foundry.zip
Invoke-WebRequest "$base/foundry_${v}_win32_amd64.sha256" -OutFile foundry.sha256
(Get-FileHash foundry.zip -Algorithm SHA256).Hash   # deve bater com foundry.sha256
Expand-Archive foundry.zip "$HOME\.foundry\bin" -Force
$env:PATH = "$HOME\.foundry\bin;$env:PATH"
forge --version
```

**Dependência de testes.** A pasta `lib/` não é versionada. Depois de clonar, instale a forge-std
na versão fixada:

```powershell
forge install foundry-rs/forge-std@v1.17.0 --no-git
```

### Compilar e testar

```powershell
forge build
forge test                 # 25 testes + 2 invariantes
forge test -vvv --match-test test_revertQuandoIntrusoRegistraDevolucaoFalsa
forge test --gas-report    # custo de gas por função
```

### Laboratório completo (roteiro 8 a 14 do enunciado)

```powershell
.\laboratorio.ps1              # compila, testa, sobe o Anvil, implanta, executa e grava evidencias/
.\laboratorio.ps1 -PularTestes # pula o forge test (~40 s) e mantém o 02-testes.log anterior
.\laboratorio.ps1 -Porta 8546  # se a 8545 estiver ocupada
```

O script sobe um Anvil próprio e o derruba no final. Ele termina com código 1 se alguma das **40
verificações** falhar. O Anvil sobe com bloco gênese fixo (`--timestamp 1794225600`, 2026-11-09
12:00 UTC) e com intervalo fixo de 12 s entre blocos (`anvil_setBlockTimestampInterval`). Por isso
o endereço do contrato, os hashes das transações, os blocos e o gas são **idênticos a cada
execução**. Duas execuções seguidas geraram os arquivos `03` a `08` e o `relatorio.md` iguais byte
a byte. Só mudam os tempos de compilação e de teste (`01`, `02`) e a ordem de algumas chamadas
de polling no `anvil.log`.

### Os mesmos passos à mão

É o fluxo do enunciado, em dois terminais. As chaves são as contas de teste públicas do Anvil,
sem valor real.

```powershell
# terminal 1
anvil

# terminal 2
$rpc  = "http://127.0.0.1:8545"
$dono = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
$bib  = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
$ana  = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

forge create src/Biblioteca.sol:Biblioteca --rpc-url $rpc --private-key $dono --broadcast
$c = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

cast send $c "definirBibliotecario(address,bool)" 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 true --private-key $dono --rpc-url $rpc
cast send $c "cadastrarLivro(string,uint32)" "Dom Casmurro" 2 --private-key $bib --rpc-url $rpc
cast send $c "emprestar(uint256,address)" 1 $ana --private-key $bib --rpc-url $rpc

cast call $c "consultarLivro(uint256)(string,uint32,uint32)" 1 --rpc-url $rpc
cast call $c "consultarEmprestimo(uint256,address)(bool,uint64,bool,uint64)" 1 $ana --rpc-url $rpc

cast logs --from-block 0 --address $c "LivroEmprestado(uint256 indexed livroId, address indexed leitor, uint64 vencimento)" --rpc-url $rpc

# tentativa inválida: Ana tentando registrar a própria devolução
cast send $c "devolver(uint256,address)" 1 $ana --private-key 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a --rpc-url $rpc
# Error: Failed to estimate gas: ... SomenteBibliotecario(0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)
```

---

## Modelagem: estado e invariantes

| Estado | Tipo | Para que serve |
| --- | --- | --- |
| `dono`, `donoPendente` | `address` | quem administra os papéis; transferência em duas etapas |
| `bibliotecario` | `mapping(address => bool)` | quem pode cadastrar, emprestar e registrar devolução |
| `livros` | `mapping(uint256 => Livro)` | título, exemplares e exemplares disponíveis |
| `totalLivros` | `uint256` | gera o id sequencial do próximo livro |
| `emprestimos` | `mapping(uint256 => mapping(address => Emprestimo))` | vencimento e renovação de cada par livro/leitor |
| `emprestimosAtivos` | `mapping(address => uint8)` | quantos livros cada leitor tem em mãos |

`Emprestimo` guarda `uint64 vencimento` e `bool renovado`, que juntos ocupam um único slot de 32
bytes. `exemplares` e `disponiveis` são `uint32` e também dividem um slot. Um empréstimo ativo é
um vencimento diferente de zero, e a devolução apaga o registro (`delete`). Assim a cadeia guarda
só o que está aberto, e o histórico completo fica nos eventos.

**Invariantes** que o contrato precisa manter depois de qualquer sequência de transações:

1. `disponiveis <= exemplares` para todo livro.
2. Para cada livro, `exemplares - disponiveis` é igual ao número de leitores com empréstimo ativo
   daquele livro.
3. A soma de `emprestimosAtivos` de todos os leitores é igual à soma dos exemplares fora da
   biblioteca.
4. Nenhum leitor passa de `limitePorLeitor = 3` empréstimos, nem tem dois exemplares do mesmo título.
5. Só o dono altera papéis, só bibliotecários alteram acervo e empréstimos, e só o próprio leitor
   renova o próprio empréstimo, uma única vez e antes de vencer.

As invariantes 1 a 4 são verificadas por `test/BibliotecaInvariante.t.sol`: 256 sequências
aleatórias de 50 chamadas (cadastrar, emprestar, renovar, devolver e avançar o tempo), e as
invariantes conferidas depois de cada chamada. A 5 é coberta pelos testes de revert.

---

## O contrato — [`src/Biblioteca.sol`](src/Biblioteca.sol)

| Função | Tipo | Quem pode | Reverte com | Evento |
| --- | --- | --- | --- | --- |
| `definirBibliotecario(conta, autorizado)` | transação | dono | `SomenteDono`, `EnderecoInvalido` | `BibliotecarioAlterado` |
| `transferirDono(novoDono)` | transação | dono | `SomenteDono`, `EnderecoInvalido` | `TransferenciaDeDonoIniciada` |
| `aceitarDono()` | transação | dono pendente | `SomenteDonoPendente` | `DonoAlterado` |
| `cadastrarLivro(titulo, exemplares)` | transação | bibliotecário | `TituloInvalido` (vazio ou > 100 bytes), `QuantidadeInvalida` | `LivroCadastrado` |
| `emprestar(livroId, leitor)` | transação | bibliotecário | `LivroInexistente`, `SemExemplarDisponivel`, `EmprestimoDuplicado`, `LimiteDeEmprestimos` | `LivroEmprestado` |
| `renovar(livroId)` | transação | o próprio leitor (`msg.sender`) | `EmprestimoInexistente`, `EmprestimoAtrasado`, `JaRenovado` | `EmprestimoRenovado` |
| `devolver(livroId, leitor)` | transação | bibliotecário | `EmprestimoInexistente` | `LivroDevolvido` (com dias de atraso) |
| `consultarLivro(livroId)` | `view` | qualquer um | `LivroInexistente` | — |
| `consultarEmprestimo(livroId, leitor)` | `view` | qualquer um | — | — |

Também são `view` os getters públicos `dono`, `donoPendente`, `totalLivros`, `bibliotecario` e
`emprestimosAtivos`. O prazo é de 14 dias e a renovação soma mais 14. O atraso é contado em dias
arredondados para cima: um segundo depois do vencimento já conta como um dia, como numa biblioteca
que cobra por dia iniciado.

### Decisões de projeto

**Quem registra a devolução é a bibliotecária, não o leitor.** O contrato não tem como saber que o
livro físico voltou para a estante. Se o leitor pudesse chamar `devolver`, ele "devolveria" sem
entregar o livro e liberaria o próprio limite. A bibliotecária atua como o oráculo da seção 14.11:
ela traz um fato do mundo físico para a cadeia, e a confiança fica nela.

**Renovar é do leitor, não da bibliotecária.** Aqui a autorização é ser dono do recurso. `renovar`
procura o empréstimo de `msg.sender`, então um terceiro nem encontra o que renovar
(`EmprestimoInexistente`).

**Erros customizados em vez de `require` com texto.** `revert SomenteBibliotecario(chamador)` é mais
barato que uma string, carrega o endereço que tentou e é decodificado pelo nome no `cast` e no
`vm.expectRevert`.

**Nenhum laço sobre estruturas que crescem.** Não há lista de empréstimos nem de livros on-chain.
Toda função tem custo constante, independentemente do tamanho do acervo. Listar e buscar fica a
cargo de um indexador off-chain que lê os eventos.

**Dono em duas etapas.** `transferirDono` só marca o pendente, e quem assume precisa chamar
`aceitarDono`. Um endereço digitado errado não tranca o contrato para sempre.

**Lints do forge excluídos no `foundry.toml`**, para não exigir comentários no código:

- `block-timestamp`: o prazo é de dias, e um validador só consegue mover o timestamp em segundos.
- `unsafe-typecast`: `uint64(block.timestamp)` só estoura daqui a 5,8 × 10¹¹ anos.
- `missing-events-access-control`: falso positivo, porque as duas alterações de `donoPendente`
  emitem evento.

---

## Testes

| Arquivo | Conteúdo |
| --- | --- |
| [`test/Biblioteca.t.sol`](test/Biblioteca.t.sol) | 8 de sucesso, 15 de falha esperada (`vm.expectRevert`) e 2 de fuzz (1000 execuções cada, semente fixa) |
| [`test/BibliotecaInvariante.t.sol`](test/BibliotecaInvariante.t.sol) | handler `OperadorDaBiblioteca` e 2 invariantes (256 × 50 = 12.800 chamadas) |

Os testes de falha cobrem as duas metades do controle de acesso da seção 14.10: a conta autorizada
consegue, e a não autorizada recebe revert. Isso vale para cadastrar, emprestar, devolver, alterar
papéis, revogar bibliotecário e aceitar a posse. Eles também conferem que um revert não deixa
efeito colateral.

Para saber se os testes pegam erro de verdade, cinco defeitos foram injetados numa cópia do contrato,
um de cada vez. Os cinco foram detectados:

| Defeito injetado | Testes que falharam |
| --- | --- |
| `devolver` sem `somenteBibliotecario` | 2 |
| limite com `>` no lugar de `>=` (deixa pegar 4 livros) | 2 |
| `devolver` sem decrementar `emprestimosAtivos` | 6 |
| sem a checagem de `JaRenovado` (renovação infinita) | 2 |
| atraso arredondado para baixo | 4 |

---

## Evidências do laboratório

| Arquivo em `evidencias/` | Passo do roteiro | Conteúdo |
| --- | --- | --- |
| `01-compilacao.log` | 10 | `forge build --force` |
| `02-testes.log` | 10 | `forge test --gas-report`: 26 testes e tabela de gas por função |
| `03-implantacao.log` | 11 | `forge create`, recibo, tamanho do bytecode |
| `04-transacoes.log` | 12 | 9 transações com hash, bloco, gas, status e quantidade de eventos |
| `05-consultas.log` | 12 | `cast call` nas funções `view`, provando que não criam bloco nem gastam nonce |
| `06-eventos.log` | 13 | `cast logs` decodificado de cada evento e filtro por tópico indexado |
| `07-reverts.log` | 14 | 8 tentativas inválidas barradas e 1 forçada, minerada com `status 0x0` |
| `08-indexador.log` | 13 | estado reconstruído só a partir dos eventos e conferido com a `view` |
| `anvil.log` | 11 | log do nó local, com cada transação, gas e bloco |
| [`relatorio.md`](evidencias/relatorio.md) | — | tabelas de implantação, transações, gas, eventos, reverts e as 40 verificações |

**Implantação:** contrato `0x5FbDB2315678afecb367f032d93F642f64180aa3`, transação
`0x232206da9c822baffd91aebff7d2cb53f3db9c8af7df182bb082c6f3c7936df9`, bloco 1, 1.091.005 de gas e
4.571 bytes de bytecode, no Anvil (chain id 31337).

| Operação | Gas medido | Por que varia |
| --- | --- | --- |
| implantação | 1.091.005 | grava o bytecode (200 gas por byte) e executa o construtor |
| `cadastrarLivro` | 94.240 / 77.368 | o primeiro tira `totalLivros` do zero, e escrever zero → não zero custa 22.100 contra 5.000 |
| `emprestar` | 77.374 / 77.386 / 60.274 | o 3º é o segundo livro da Ana: o contador dela vai de 1 para 2, não de 0 para 1 |
| `definirBibliotecario` | 47.841 | um slot de zero para não zero |
| `devolver` | 34.190 / 37.499 | apagar o empréstimo devolve gas (reembolso). Zerar o contador do Bruno devolve mais |
| `renovar` | 29.432 | só reescreve um slot que já existia |
| `devolver` revertido (intruso) | 24.167 | pago mesmo sem alterar nada: 21.000 de base + dados + execução até o revert |
| funções `view` por `eth_call` | 0 | nenhuma transação: bloco 10 → 10, nonce 2 → 2 |

O empréstimo de *Memórias Póstumas* para a Ana (6ª transação) nunca é devolvido, de propósito. No
fim do laboratório ele está vencido há 7 dias. O indexador encontra esse empréstimo pelos
eventos, e a `view` confirma.

---

## Estrutura

```text
Atividade-Pratica-8/
  src/Biblioteca.sol                 o contrato
  test/Biblioteca.t.sol              testes unitários e de fuzz
  test/BibliotecaInvariante.t.sol    handler e invariantes
  laboratorio.ps1                    roteiro 8–14: Anvil, implantação, transações, eventos, reverts, indexador
  evidencias/                        gerado pelo laboratorio.ps1
  foundry.toml                       solc 0.8.28, otimizador, semente do fuzz, lints
  Questoes-de-Analise-AP8.docx       questões, riscos de segurança e comparação com REST
  lib/ out/ cache/                   gerados (fora do git)
```

## Limitações

- Rede local de um nó só: não há consenso de verdade nem reorganização de blocos. O indexador não
  trata logs com `removed: true`.
- O leitor é identificado por um endereço. Não há cadastro de pessoa, e a correspondência entre
  endereço e pessoa fica fora da cadeia.
- O contrato não é atualizável. Corrigir um bug exige implantar outro contrato e migrar o estado.
- Não há multa nem pagamento. O atraso é só informado no evento e na consulta.
