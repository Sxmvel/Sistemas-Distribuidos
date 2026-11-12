# Relatório do laboratório da AP8

Gerado por `laboratorio.ps1`. Nó local Anvil 1.9.0 (chain id 31337), bloco gênese em 2026-11-09 12:00:00 UTC e intervalo fixo de 12 s entre blocos. Com esses parâmetros, endereços, hashes e gas são idênticos a cada execução.

## Implantação

| Campo | Valor |
| --- | --- |
| Endereço do contrato | `0x5FbDB2315678afecb367f032d93F642f64180aa3` |
| Hash da transação | `0x232206da9c822baffd91aebff7d2cb53f3db9c8af7df182bb082c6f3c7936df9` |
| Bloco | 1 |
| Gas | 1091005 |
| Bytecode implantado | 4571 bytes |
| Implantado por | dono (`0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`) |

## Transações que alteram estado

| # | Passo | Assinada por | Função | Bloco | Gas | Eventos | Status | Hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | dono autoriza a bibliotecária | dono | `definirBibliotecario` | 2 | 47841 | 1 | sucesso | `0x3f08bc30879090eb8f2900e0c34dac3cfce711ea5e57c1a2a469353dec5dc77a` |
| 2 | bibliotecária cadastra Dom Casmurro (2 exemplares) | bibliotecaria | `cadastrarLivro` | 3 | 94240 | 1 | sucesso | `0x3967abb37fbebd4f851575af0c3f618297d5bb54864167dbd57f843b1a18aa5e` |
| 3 | bibliotecária cadastra Memorias Postumas (1 exemplar) | bibliotecaria | `cadastrarLivro` | 4 | 77368 | 1 | sucesso | `0xe12b8de4c865e2b991764c5c8df815e71dd3ce0f5da6454561ef3b3996b49488` |
| 4 | empresta Dom Casmurro para Ana | bibliotecaria | `emprestar` | 5 | 77374 | 1 | sucesso | `0x5f3dfad735b4a06f9c26e3a874555c0a30acfe2ae635a55d076b961c2f1a0fed` |
| 5 | empresta Dom Casmurro para Bruno | bibliotecaria | `emprestar` | 6 | 77386 | 1 | sucesso | `0x6e541c3cfcf7cf1469dc2a96e1f9848a4797b8015c2a6f16933d628615928eec` |
| 6 | empresta Memorias Postumas para Ana | bibliotecaria | `emprestar` | 7 | 60274 | 1 | sucesso | `0x34828d8e5e632ac3e7a5c68c3f46db6329ee847cf4e54003535b72caecae1533` |
| 7 | Ana renova o próprio empréstimo de Dom Casmurro | ana | `renovar` | 8 | 29432 | 1 | sucesso | `0xaa40484460fd13f883c61fd475fcdb8448921f24c2ad3efd59af00881fcda0ed` |
| 8 | Bruno devolve Dom Casmurro com atraso | bibliotecaria | `devolver` | 9 | 34190 | 1 | sucesso | `0x9f1949eec2ced0bd73781dc468512d6a899a60ef6c3e3f672568b9fe9a946f56` |
| 9 | Ana devolve Dom Casmurro dentro do prazo renovado | bibliotecaria | `devolver` | 10 | 37499 | 1 | sucesso | `0x1989b694b946e81a724030385e7c918ce4483beb1b06d174050115623f104258` |

Entre as transações 7 e 8, `evm_setNextBlockTimestamp` adiantou o relógio do nó em 20 dias (2026-11-09 12:01:36 UTC -> 2026-11-29 12:01:36 UTC).

## Gas por operação

| Operação | Gas medido no Anvil |
| --- | --- |
| implantação | 1091005 |
| `definirBibliotecario` | 47841 |
| `cadastrarLivro` | 77368 / 94240 |
| `emprestar` | 60274 / 77374 / 77386 |
| `renovar` | 29432 |
| `devolver` | 34190 / 37499 |
| `devolver` revertido por falta de permissão | 24167 |
| funções `view` via `eth_call` | 0 (sem transação, bloco 10 -> 10) |

## Eventos observados

| Evento | Ocorrências |
| --- | --- |
| `DonoAlterado` | 1 |
| `TransferenciaDeDonoIniciada` | 0 |
| `BibliotecarioAlterado` | 2 |
| `LivroCadastrado` | 2 |
| `LivroEmprestado` | 3 |
| `EmprestimoRenovado` | 1 |
| `LivroDevolvido` | 2 |

## Tentativas inválidas

| Tentativa | Conta | Função | Erro esperado | Erro obtido | Chegou à cadeia? |
| --- | --- | --- | --- | --- | --- |
| intruso tenta cadastrar livro | intruso | `cadastrarLivro` | `SomenteBibliotecario` | `SomenteBibliotecario(0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65)` | não, barrada na estimativa de gas |
| Ana tenta registrar a própria devolução | ana | `devolver` | `SomenteBibliotecario` | `SomenteBibliotecario(0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)` | não, barrada na estimativa de gas |
| bibliotecária tenta se autopromover a dono das permissões | bibliotecaria | `definirBibliotecario` | `SomenteDono` | `SomenteDono(0x70997970C51812dc3A010C7d01b50e0d17dc79C8)` | não, barrada na estimativa de gas |
| bibliotecária empresta livro sem exemplar disponível | bibliotecaria | `emprestar` | `SemExemplarDisponivel` | `SemExemplarDisponivel(2)` | não, barrada na estimativa de gas |
| bibliotecária registra devolução duplicada | bibliotecaria | `devolver` | `EmprestimoInexistente` | `EmprestimoInexistente(1, 0x90F79bf6EB2c4f870365E785982E1f101E93b906)` | não, barrada na estimativa de gas |
| Ana tenta renovar empréstimo atrasado | ana | `renovar` | `EmprestimoAtrasado` | `EmprestimoAtrasado(2, 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)` | não, barrada na estimativa de gas |
| bibliotecária cadastra livro sem título | bibliotecaria | `cadastrarLivro` | `TituloInvalido` | `TituloInvalido` | não, barrada na estimativa de gas |
| bibliotecária empresta livro inexistente | bibliotecaria | `emprestar` | `LivroInexistente` | `LivroInexistente(99)` | não, barrada na estimativa de gas |
| intruso força a devolução do empréstimo de Ana | intruso | `devolver` | `SomenteBibliotecario` | `SomenteBibliotecario(0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65)` | sim, status 0x0, 24167 de gas, `0x06f3063725a7b24bb17c19357305301d9d552b55a6417358c5953b0beb9ed40f` |

## Verificações

**40 verificações, 0 falha(s).**

- [ok] contrato compila
- [ok] todos os testes passam
- [ok] implantação confirmada (status 0x1)
- [ok] há bytecode no endereço do contrato
- [ok] o dono é a conta que implantou
- [ok] todas as transações confirmadas
- [ok] Dom Casmurro voltou a ter 2 de 2 exemplares
- [ok] Memorias Postumas segue com 0 de 1 exemplar
- [ok] empréstimo de Memorias Postumas com Ana ativo e atrasado
- [ok] Ana tem 1 empréstimo ativo
- [ok] consultas não criaram blocos
- [ok] consultas não consumiram nonce
- [ok] 1 DonoAlterado, 2 BibliotecarioAlterado, 2 LivroCadastrado
- [ok] 3 LivroEmprestado, 1 EmprestimoRenovado, 2 LivroDevolvido
- [ok] filtro pelo livro 1 devolve só os 2 empréstimos dele
- [ok] evento de devolução do Bruno registra atraso (7 dias)
- [ok] intruso tenta cadastrar livro -> revert SomenteBibliotecario
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] Ana tenta registrar a própria devolução -> revert SomenteBibliotecario
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] bibliotecária tenta se autopromover a dono das permissões -> revert SomenteDono
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] bibliotecária empresta livro sem exemplar disponível -> revert SemExemplarDisponivel
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] bibliotecária registra devolução duplicada -> revert EmprestimoInexistente
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] Ana tenta renovar empréstimo atrasado -> revert EmprestimoAtrasado
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] bibliotecária cadastra livro sem título -> revert TituloInvalido
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] bibliotecária empresta livro inexistente -> revert LivroInexistente
- [ok] nenhuma transação chegou à cadeia (bloco 10 -> 10)
- [ok] transação forçada foi minerada com status 0x0
- [ok] o revert ainda custou 24167 de gas ao intruso
- [ok] erro na reexecução é SomenteBibliotecario
- [ok] empréstimo de Ana continua ativo
- [ok] nenhum LivroDevolvido novo (2 -> 2)
- [ok] indexador encontrou exatamente 1 empréstimo ativo
- [ok] estado reconstruído pelos eventos confere com o estado on-chain
- [ok] catálogo reconstruído tem os 2 títulos
