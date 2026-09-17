# O contrato e sua evolução

## 1. Por que o contrato vem antes

O `.proto` foi escrito antes de qualquer linha de servidor ou cliente. Ele define ao mesmo
tempo a superfície do serviço e o formato dos dados, e o código dos dois lados é derivado
dele. Em nenhum momento um lado "combina" um formato com o outro fora do arquivo.

## 2. O serviço

```protobuf
service Emprestimos {
  rpc RegistrarEmprestimo (RegistrarEmprestimoRequest) returns (RegistrarEmprestimoResponse);
  rpc ConsultarEmprestimo (ConsultarEmprestimoRequest) returns (ConsultarEmprestimoResponse);
  rpc RegistrarDevolucao  (RegistrarDevolucaoRequest)  returns (RegistrarDevolucaoResponse);
  rpc CalcularMultas      (CalcularMultasRequest)      returns (CalcularMultasResponse);
  rpc ListarEmprestimos   (ListarEmprestimosRequest)   returns (stream Emprestimo);
}
```

Cada método tem tipos de pedido e resposta **próprios**, mesmo quando a resposta hoje teria um
único campo. Isso é deliberado: adicionar `exemplares_disponiveis` a
`RegistrarEmprestimoResponse` foi uma mudança compatível; se o método devolvesse `Emprestimo`
direto, o mesmo acréscimo exigiria poluir a entidade com um campo que não é dela.

O `package` é `biblioteca.emprestimos.v1`. A versão está no nome do pacote porque ela faz parte
do caminho da RPC no fio (`/biblioteca.emprestimos.v1.Emprestimos/RegistrarEmprestimo`).
Uma quebra real de contrato vira `v2` e passa a conviver com a `v1` no mesmo servidor.

## 3. Escolha dos tipos

| Campo | Tipo | Por quê |
| --- | --- | --- |
| `isbn` | `string` | identificador com zeros à esquerda e dígito verificador; número perderia a forma |
| `dias` | `int32` | faixa pequena; o contrato não restringe a faixa, o serviço restringe |
| `multa` | `double` | valor monetário pequeno derivado de multiplicação; em sistema real seria centavos em `int64` |
| `emprestado_em` | `string` ISO-8601 | data sem hora; legível no fio e sem dependência de fuso |
| `situacao` | `enum Situacao` | conjunto fechado, e o valor 0 é `SITUACAO_NAO_INFORMADA` |
| `codigos` | `repeated string` | lista homogênea de tamanho variável |

Duas decisões que merecem defesa:

**`double` para dinheiro.** É a escolha do laboratório da apostila e é aceitável aqui porque a
multa é sempre `dias × 0,50` com poucos dias. Em um sistema real, `int64` em centavos evita o
erro de arredondamento acumulado.

**Data como `string`.** `google.protobuf.Timestamp` seria o tipo canônico, mas traz precisão de
nanossegundos para um domínio cuja unidade é o dia — e obriga o cliente a importar um `.proto`
do runtime do protobuf. Em troca, o serviço precisa validar o formato (`validar_data`), e ele
valida: uma data `16/09/2026` devolve `INVALID_ARGUMENT` com `x-campo: devolvido_em`.

## 4. O enum e o valor zero

```protobuf
enum Situacao {
  SITUACAO_NAO_INFORMADA = 0;
  SITUACAO_ATIVO = 1;
  SITUACAO_DEVOLVIDO = 2;
}
```

Em proto3 o primeiro valor é obrigatoriamente 0 e é o default de qualquer campo não enviado.
Reservar o 0 para "não informado" evita que um cliente que esqueceu de preencher `situacao`
acabe pedindo silenciosamente a lista de ativos. Em `ListarEmprestimos`, `situacao = 0`
significa "sem filtro", e isso é uma decisão consciente, não um acidente.

## 5. Números reservados

```protobuf
message Emprestimo {
  reserved 15;
  reserved "telefone_do_leitor";
  ...
}
```

O campo 15 existiu e foi removido. Reservar o número **e** o nome impede que uma versão futura
reaproveite qualquer um dos dois: o número, porque os bytes antigos ainda circulam em filas,
logs e bancos; o nome, porque um campo novo com o mesmo nome e outro número confundiria quem
lê JSON gerado a partir do proto.

## 6. As três versões do contrato neste repositório

| Pasta | Papel | Diferença para a atual |
| --- | --- | --- |
| [`contratos/`](../contratos/) | contrato atual (v2), usado por servidor e cliente novo | — |
| [`contratos_legado/`](../contratos_legado/) | contrato anterior, usado pelo cliente antigo | sem `unidade` em `Emprestimo` (campo 9) e em `RegistrarEmprestimoRequest` (campo 5); sem `exemplares_disponiveis` |
| [`contratos_incompativel/`](../contratos_incompativel/) | contra-exemplo, nunca usado em produção | campo 4 renomeado de `leitor` para `unidade`; campo 3 mudou de `int32` para `string` |

As três declaram o mesmo `package`, então **não podem coexistir no mesmo processo**: o
descriptor pool do protobuf recusa símbolos duplicados com
`duplicate symbol 'biblioteca.emprestimos.v1.Situacao'`. O E07 verifica isso explicitamente.
Não é uma limitação do experimento — é como uma migração acontece na prática: o cliente antigo
é outro processo, muitas vezes em outra máquina, que ninguém recompilou ainda.

## 7. A mudança compatível, medida

A v2 adicionou `unidade` (campo 5 no pedido, campo 9 na resposta). O E07 roda o cliente legado
como subprocesso contra o servidor novo:

| Verificação | Resultado |
| --- | --- |
| Cliente antigo escreve no servidor novo | `OK` — o servidor recebe `unidade` vazio e aplica o default `central` |
| Cliente antigo lê recurso criado pelo cliente novo | `OK` |
| `leitor` chega correto no cliente antigo | `gabriela.dias` |
| Cliente antigo reserializa e preserva o campo 9 | 86 bytes idênticos |
| Server streaming continua funcionando | `OK` |
| Status de erro continua o mesmo | `INVALID_ARGUMENT` |

A quarta linha é a mais interessante: o stub antigo guardou o campo 9 como *unknown field* e o
devolveu intacto. Um proxy ou um gateway compilado com o contrato velho não apaga dados do
contrato novo ao repassar a mensagem.

## 8. A mudança incompatível, medida

O contra-exemplo em `contratos_incompativel/` faz duas mudanças proibidas e o E07 lê com ele
bytes gerados pela v2:

| Mudança | O que acontece |
| --- | --- |
| Campo 4: `leitor` vira `unidade`, outro significado com o mesmo tipo | parseia sem erro, e `unidade` vale `"gabriela.dias"` |
| Campo 3: `int32 dias` → `string dias` | parseia sem erro, e `dias` vale `""` — o 7 enviado some |

Nenhuma das duas levanta exceção. Não há status de erro, log ou aviso. A primeira produz dado
**corrompido**, a segunda produz dado **perdido**, e as duas passam despercebidas até alguém
notar o relatório errado semanas depois.

É por isso que a disciplina de evolução importa mais em contrato forte do que em contrato
fraco: o mesmo mecanismo que garante tipo em tempo de compilação não protege contra
renumeração, porque no fio não existe nome — existe número.

## 9. Regras de evolução adotadas

Compatível:

- adicionar campo novo com número novo e não usado;
- adicionar método novo ao serviço;
- adicionar valor novo ao fim de um enum (clientes antigos veem o número cru);
- renomear um campo **mantendo o mesmo significado e o mesmo número** — no fio nada muda; só o
  código gerado e o JSON derivado do proto mudam.

Incompatível:

- reutilizar o número de um campo removido;
- manter o número e trocar o **significado** do campo, mesmo mantendo o tipo — é o caso do
  campo 4 na seção 8, e é o mais perigoso porque o parser não reclama;
- mudar o tipo de um campo existente;
- mudar `repeated` para singular ou vice-versa;
- remover ou renumerar valores de enum;
- renomear o pacote, o serviço ou o método, porque isso muda o caminho da RPC.
