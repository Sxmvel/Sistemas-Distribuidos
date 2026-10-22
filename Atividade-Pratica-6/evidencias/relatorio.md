# Evidências da AP6

Arquivo gerado por `ExecutarTodos`. Não edite à mão: rode os experimentos de novo. A semente é fixa, então duas execuções produzem os mesmos arquivos.

## Tabela de experimentos

| Experimento | Manipulação | Esperado | Obtido | Verificações |
| --- | --- | --- | --- | --- |
| E01 — Execução da cadeia didática e hashes de referência | Cadeia do PDF (gênese + 3 transações); depois gênese + 24 transações geradas com semente 2026. | Hashes e saídas idênticos aos do explorar_cadeia.py; cadeia de referência válida. | 4/4 hashes iguais aos do Python; cadeia de referência com 25 blocos, cadeia válida. | 9/9 ✔ |
| E02 — Efeito avalanche: alterar 1 caractere | "bloco A" → "bloco a" (hash_demo.py do PDF); último dígito do valor de cada um dos 24 blocos gerados; reconstrução da cadeia a partir do bloco 10. | Cerca de 50% dos 256 bits mudam, sem relação visível com a entrada; todos os hashes a partir do bloco alterado mudam. | média de 129,0 de 256 bits (50,4%), mínimo 116, máximo 151; a mudança no bloco 10 alterou todos os hashes seguintes. | 5/5 ✔ |
| E03 — Adulteração de bloco antigo e intermediário | Valor da transação trocado para 1000 nos blocos [1, 5, 12, 23], sem recalcular nenhum hash (como `cadeia[1].dados = ...` no PDF). | validar() acusa "hash inválido" exatamente no bloco alterado; nenhum outro bloco é acusado. | as 4 adulterações foram detectadas, cada uma exatamente no bloco alterado; os blocos seguintes continuaram ligados. | 9/9 ✔ |
| E04 — Reescrita: a cadeia adulterada volta a ser válida | Bloco 5 fraudado para "G->C:1000"; depois o atacante ressela o bloco e, por fim, recalcula todos os hashes do 5 ao 24. | O erro migra de "hash inválido" para "ligação inválida" e some; a cadeia reescrita passa na validação, mas diverge da referência a partir do bloco 5. | depois de recalcular 20 hashes a cadeia fraudada responde "cadeia válida"; comparada à referência, diverge a partir do bloco 5. | 10/10 ✔ |
| E05 — Réplicas divergentes e regra de reconciliação | Réplicas partindo de um prefixo comum de 15 blocos (0 a 14), em quatro cenários: omissão de mensagem, partição, empate e réplica bizantina. Regra: cadeia válida mais longa vence; empate decidido pelo menor hash da ponta. | Cada cópia continua válida localmente; a regra faz as réplicas convergirem, mas descarta blocos do ramo perdedor e aceita uma fraude reescrita que seja mais longa. | as réplicas convergiram nos 5 casos; a partição descartou 4 blocos de sul e a réplica bizantina venceu ao apresentar uma fraude reescrita mais longa. | 21/21 ✔ |


## E01 — Execução da cadeia didática e hashes de referência

**Objetivo.** Reproduzir em Java a cadeia didática do PDF com os mesmos hashes do Python e gerar a cadeia de referência usada por todos os outros experimentos.

**Manipulação.** Cadeia do PDF (gênese + 3 transações); depois gênese + 24 transações geradas com semente 2026.

**Esperado.** Hashes e saídas idênticos aos do explorar_cadeia.py; cadeia de referência válida.

**Obtido.** 4/4 hashes iguais aos do Python; cadeia de referência com 25 blocos, cadeia válida.

### Cadeia do PDF: Java × Python

| Bloco | Dados | Hash em Java | Hash em Python | Iguais |
| --- | --- | --- | --- | --- |
| 0 | genesis | 776ebbe7ffb6… | 776ebbe7ffb6… | sim |
| 1 | A->B:10 | 9bbeddfb50de… | 9bbeddfb50de… | sim |
| 2 | B->C:3 | df5f4d5552dd… | df5f4d5552dd… | sim |
| 3 | C->D:1 | a0a5d1d2f291… | a0a5d1d2f291… | sim |

### Saídas do roteiro do PDF

| Passo | Python | Java |
| --- | --- | --- |
| print(validar(cadeia)) | (True, 'cadeia válida') | (True, 'cadeia válida') |
| cadeia[1].dados = "A->B:1000"; print(validar(cadeia)) | (False, 'hash inválido no bloco 1') | (False, 'hash inválido no bloco 1') |

### Cadeia de referência (25 blocos)

| Bloco | Dados | hash_anterior | hash |
| --- | --- | --- | --- |
| 0 | genesis | 000000000000… | `776ebbe7ffb61b6a4b5fe534692f2334e70a07088209788e1176fc6970483ee4` |
| 1 | E->B:38 | 776ebbe7ffb6… | `dfe17b083a9b941da9703db24a65359786f781d1ffb7ea83123f939e4363a8a7` |
| 2 | B->D:44 | dfe17b083a9b… | `4d4d5ffbc6ac6ad3a8178c4841caa6127fb95d9ccd7f56dec928cbe8675bd392` |
| 3 | E->F:65 | 4d4d5ffbc6ac… | `ad1d1370743b49f27036dc2dea5093b36b6371873c516b85a72d33ec609f7c34` |
| 4 | A->E:9 | ad1d1370743b… | `8f829a332307243da225efa7b7f295c5609646381c32d7f62dc732ad6fb469c0` |
| 5 | G->C:64 | 8f829a332307… | `2ced206ff4e52414313eff080cfa6204f94b1cbccc72a519712987c94c6a703a` |
| 6 | C->B:86 | 2ced206ff4e5… | `1c0a658ef44ed33db5a1eca167eb77d2137311b189195dfbf7b90185364dbc6a` |
| 7 | F->H:53 | 1c0a658ef44e… | `90faa1d1dfc8393c4573c01f1341b6e8c737bf6104fffccd3d9dd121ff470485` |
| 8 | A->G:31 | 90faa1d1dfc8… | `cc5762fef76fef9a964134f99f37155e559cdfcea3891133a7dccc2d45440ab8` |
| 9 | A->C:75 | cc5762fef76f… | `c2caa427513621677f065197658deec2fdd671c49aeb47b1b5175454135cb2b0` |
| 10 | C->A:37 | c2caa4275136… | `8c20f73bd1d4eb06078c7eba2e8f11b848c3887b9ff50aaf5b17f6515c691f12` |
| 11 | F->E:20 | 8c20f73bd1d4… | `e08ee448f95e37ff0ca3b1987a81cd6fbdb60981eacf54e1630b198913513c4a` |
| 12 | B->A:54 | e08ee448f95e… | `c9feb00b5cc0b048ee624c4371b80d10c275f68d85b16186eca02dd4007c1159` |
| 13 | E->H:10 | c9feb00b5cc0… | `79e7ed07bf5b7d226b2e2295c8a5b7e0835319c030be2b55c3183ee0549d0acd` |
| 14 | G->E:90 | 79e7ed07bf5b… | `a8fb30bdd0f67eec52a1adad1cc829094765bf1d137bed381d935cb381b83115` |
| 15 | C->F:29 | a8fb30bdd0f6… | `b3f40a31d906f39e23597fd5c67c3aff1fe8fab2fa446e396d374974d84b362e` |
| 16 | E->F:94 | b3f40a31d906… | `b5ce257efad5451ac45ba36bcc4d3bee50577e63722688961826ffd0a26f38d7` |
| 17 | H->E:53 | b5ce257efad5… | `a4abf963b3b79d712f91486c2fbc46a720fa776711c0d50e82eb28069e210f37` |
| 18 | D->A:55 | a4abf963b3b7… | `f7fd85a5b13ecfa789958fed94ac09c52cb903fb2f60159931bd4aa55847e27b` |
| 19 | A->H:37 | f7fd85a5b13e… | `44e2d6ed3eac868d28ae530c8bad0b4ab4818c5e628dc9d2305f824d59329c3f` |
| 20 | B->C:48 | 44e2d6ed3eac… | `71c8e44bd8bd7c4569b20510494496f0c954fb53f17368a7379fa5a8ff9deaae` |
| 21 | E->D:75 | 71c8e44bd8bd… | `e9c30615f5d1250fd2e02a260f5c5ab24264c05bdd4d907083f8600a5bda8443` |
| 22 | G->A:56 | e9c30615f5d1… | `7592f03f319b146ba4a047f7b78276fbc78772bf5c56f7ee48878ad9d16d3a5e` |
| 23 | D->C:92 | 7592f03f319b… | `67e8c2893edea0358aeebebb166a0db36685b82b94c58f76d540d940f5646510` |
| 24 | F->B:73 | 67e8c2893ede… | `8aaeebc05af1dc13ddba2144eb03a9f04ff46d1c8b3cc1b5ba5f4412ac79efe2` |

**Verificações**

- [x] hash do bloco 0 igual ao do Python
- [x] hash do bloco 1 igual ao do Python
- [x] hash do bloco 2 igual ao do Python
- [x] hash do bloco 3 igual ao do Python
- [x] saída da cadeia íntegra igual à do Python
- [x] saída da cadeia adulterada igual à do Python
- [x] pelo menos 20 blocos com dados gerados (24)
- [x] cadeia de referência válida
- [x] gerar a referência de novo produz a mesma cadeia

**Observações**

- A forma canônica de cada bloco é, por exemplo, `{"dados": "A->B:10", "hash_anterior": "776ebbe7ffb61b6a4b5fe534692f2334e70a07088209788e1176fc6970483ee4", "indice": 1}`: chaves em ordem alfabética e separadores `", "` e `": "`, exatamente como o `json.dumps(sort_keys=True)` do Python. Por isso os hashes coincidem byte a byte.
- Os hashes de referência do Python saem de `referencia/explorar_cadeia.py`, o código do PDF sem alteração (o comando está no README).
- A semente fixa torna a cadeia de referência idêntica em toda execução: o hash da ponta é sempre `8aaeebc05af1dc13ddba2144eb03a9f04ff46d1c8b3cc1b5ba5f4412ac79efe2`.

Log completo dos hashes: [`e01.log`](e01.log)

Anexo: [`cadeia-referencia.json`](cadeia-referencia.json)

## E02 — Efeito avalanche: alterar 1 caractere

**Objetivo.** Medir quanto o hash muda quando a entrada muda em um único caractere e como essa mudança se propaga pelo encadeamento.

**Manipulação.** "bloco A" → "bloco a" (hash_demo.py do PDF); último dígito do valor de cada um dos 24 blocos gerados; reconstrução da cadeia a partir do bloco 10.

**Esperado.** Cerca de 50% dos 256 bits mudam, sem relação visível com a entrada; todos os hashes a partir do bloco alterado mudam.

**Obtido.** média de 129,0 de 256 bits (50,4%), mínimo 116, máximo 151; a mudança no bloco 10 alterou todos os hashes seguintes.

### hash_demo.py do PDF

| Entrada | SHA-256 |
| --- | --- |
| bloco A | `f3497207237fe7561d45dedcf193a63d3bfb813cae792a3b6ce2e538bb1ed874` |
| bloco a | `f2f5ebf391ecca1218188d7233fcfb25274447fdabc12ddfcfda55f38b017d97` |
| diferença | 122 de 256 bits (47,7%); 58 de 64 dígitos hexadecimais |

### Um caractere alterado em cada bloco gerado

| Bloco | Original | Alterado | Hash original | Hash alterado | Bits diferentes | % dos bits |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | E->B:38 | E->B:39 | dfe17b083a9b… | cd389676d597… | 125 | 48,8% |
| 2 | B->D:44 | B->D:45 | 4d4d5ffbc6ac… | 09efca48c37a… | 116 | 45,3% |
| 3 | E->F:65 | E->F:66 | ad1d1370743b… | 984a807ef66c… | 121 | 47,3% |
| 4 | A->E:9 | A->E:0 | 8f829a332307… | 7657fe63b9b8… | 118 | 46,1% |
| 5 | G->C:64 | G->C:65 | 2ced206ff4e5… | b7039428ab40… | 132 | 51,6% |
| 6 | C->B:86 | C->B:87 | 1c0a658ef44e… | c3d11a007808… | 131 | 51,2% |
| 7 | F->H:53 | F->H:54 | 90faa1d1dfc8… | 2b12629a7a8c… | 131 | 51,2% |
| 8 | A->G:31 | A->G:32 | cc5762fef76f… | 047280bfcc8d… | 125 | 48,8% |
| 9 | A->C:75 | A->C:76 | c2caa4275136… | 82e90ef23b7b… | 128 | 50,0% |
| 10 | C->A:37 | C->A:38 | 8c20f73bd1d4… | f546ef90c339… | 127 | 49,6% |
| 11 | F->E:20 | F->E:21 | e08ee448f95e… | 836ef9db954f… | 132 | 51,6% |
| 12 | B->A:54 | B->A:55 | c9feb00b5cc0… | 960efed1551e… | 151 | 59,0% |
| 13 | E->H:10 | E->H:11 | 79e7ed07bf5b… | 13e3b430dbcd… | 119 | 46,5% |
| 14 | G->E:90 | G->E:91 | a8fb30bdd0f6… | a5336959f769… | 130 | 50,8% |
| 15 | C->F:29 | C->F:20 | b3f40a31d906… | dcffdfa37e5a… | 136 | 53,1% |
| 16 | E->F:94 | E->F:95 | b5ce257efad5… | c9a13f8a1171… | 139 | 54,3% |
| 17 | H->E:53 | H->E:54 | a4abf963b3b7… | d3f91d80552a… | 136 | 53,1% |
| 18 | D->A:55 | D->A:56 | f7fd85a5b13e… | 5c9e860fc5cb… | 119 | 46,5% |
| 19 | A->H:37 | A->H:38 | 44e2d6ed3eac… | 1895e90477cf… | 133 | 52,0% |
| 20 | B->C:48 | B->C:49 | 71c8e44bd8bd… | 2f55907a9d3d… | 127 | 49,6% |
| 21 | E->D:75 | E->D:76 | e9c30615f5d1… | 635bd030be0b… | 138 | 53,9% |
| 22 | G->A:56 | G->A:57 | 7592f03f319b… | 8b36643b7293… | 127 | 49,6% |
| 23 | D->C:92 | D->C:93 | 67e8c2893ede… | c5bd4e5b2915… | 128 | 50,0% |
| 24 | F->B:73 | F->B:74 | 8aaeebc05af1… | 5fd7e5805af7… | 127 | 49,6% |

### Propagação: bloco 10 alterado e cadeia reconstruída

| Faixa | Hashes que mudaram |
| --- | --- |
| blocos 0 a 9 | 0 de 10 |
| blocos 10 a 24 | 15 de 15 |

### Resumo das 24 amostras

| Medida | Bits | % de 256 |
| --- | --- | --- |
| mínimo | 116 | 45,3% |
| média | 129,0 | 50,4% |
| máximo | 151 | 59,0% |
| desvio padrão | 7,7 | — |
| esperado para hash ideal | 128 ± 8 | 50,0% |

**Verificações**

- [x] "bloco A" e "bloco a" produzem hashes diferentes
- [x] nenhum hash anterior ao bloco 10 muda
- [x] todos os hashes a partir do bloco 10 mudam
- [x] média de bits alterados entre 46% e 54% (50,4%)
- [x] toda amostra altera mais de 25% dos bits (mínimo 116)

**Observações**

- Mudar um caractere troca cerca de metade dos bits, e não os bits "vizinhos" da mudança. Não há como prever o novo hash a partir do antigo, o que torna qualquer adulteração visível ao recalcular.
- A avalanche age dentro de um bloco; o encadeamento a estende para a cadeia. Como o hash de um bloco entra no conteúdo do seguinte, mudar um bloco muda todos os hashes posteriores, e nenhum anterior.

Log completo dos hashes: [`e02.log`](e02.log)

## E03 — Adulteração de bloco antigo e intermediário

**Objetivo.** Verificar se a validação local detecta a alteração de um bloco já encadeado e registrar qual parte da cadeia é afetada.

**Manipulação.** Valor da transação trocado para 1000 nos blocos [1, 5, 12, 23], sem recalcular nenhum hash (como `cadeia[1].dados = ...` no PDF).

**Esperado.** validar() acusa "hash inválido" exatamente no bloco alterado; nenhum outro bloco é acusado.

**Obtido.** as 4 adulterações foram detectadas, cada uma exatamente no bloco alterado; os blocos seguintes continuaram ligados.

### Adulteração por posição

| Bloco | Original | Adulterado | Hash armazenado | Hash recalculado | validar() | Blocos acusados na auditoria |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | E->B:38 | E->B:1000 | dfe17b083a9b… | d3bd1b276515… | hash inválido no bloco 1 | [1] |
| 5 | G->C:64 | G->C:1000 | 2ced206ff4e5… | b66da1e54af2… | hash inválido no bloco 5 | [5] |
| 12 | B->A:54 | B->A:1000 | c9feb00b5cc0… | 217a83da604b… | hash inválido no bloco 12 | [12] |
| 23 | D->C:92 | D->C:1000 | 67e8c2893ede… | 74039cd464e2… | hash inválido no bloco 23 | [23] |

### Estado de cada bloco depois de adulterar o bloco 5

| Bloco | Dados | Hash confere | Liga no anterior |
| --- | --- | --- | --- |
| 3 | E->F:65 | sim | sim |
| 4 | A->E:9 | sim | sim |
| 5 | G->C:1000 | não | sim |
| 6 | C->B:86 | sim | sim |
| 7 | F->H:53 | sim | sim |
| 8 | A->G:31 | sim | sim |

**Verificações**

- [x] bloco 1: validar() responde "hash inválido no bloco 1"
- [x] bloco 1: auditoria acusa só o bloco 1
- [x] bloco 5: validar() responde "hash inválido no bloco 5"
- [x] bloco 5: auditoria acusa só o bloco 5
- [x] bloco 12: validar() responde "hash inválido no bloco 12"
- [x] bloco 12: auditoria acusa só o bloco 12
- [x] bloco 23: validar() responde "hash inválido no bloco 23"
- [x] bloco 23: auditoria acusa só o bloco 23
- [x] a cadeia de referência continua válida (a adulteração gerou uma cópia)

**Observações**

- A detecção é local: basta recalcular o hash do bloco e comparar com o armazenado. Não é preciso consultar outra réplica.
- O impacto fica restrito ao bloco alterado porque o atacante não trocou o hash armazenado; o bloco seguinte continua apontando para esse hash, então a ligação segue íntegra. A falha só se espalha quando o atacante tenta esconder a fraude (E04).
- A posição não muda o resultado: um bloco antigo (1) é detectado da mesma forma que um recente (23). O custo de esconder a fraude, sim, depende da posição.

Log completo dos hashes: [`e03.log`](e03.log)

## E04 — Reescrita: a cadeia adulterada volta a ser válida

**Objetivo.** Mostrar que um atacante que controla a cópia local consegue esconder a adulteração recalculando os hashes, e que só uma referência externa revela a fraude.

**Manipulação.** Bloco 5 fraudado para "G->C:1000"; depois o atacante ressela o bloco e, por fim, recalcula todos os hashes do 5 ao 24.

**Esperado.** O erro migra de "hash inválido" para "ligação inválida" e some; a cadeia reescrita passa na validação, mas diverge da referência a partir do bloco 5.

**Obtido.** depois de recalcular 20 hashes a cadeia fraudada responde "cadeia válida"; comparada à referência, diverge a partir do bloco 5.

### Estágios do ataque ao bloco 5

| Estágio | Ação do atacante | Hashes recalculados | validar() | Auditoria | Ponta igual à referência |
| --- | --- | --- | --- | --- | --- |
| 0 | nenhuma (referência) | 0 | cadeia válida | [] | sim |
| 1 | troca os dados do bloco 5 | 0 | hash inválido no bloco 5 | [5] | sim |
| 2 | recalcula só o hash do bloco 5 | 1 | ligação inválida no bloco 6 | [6] | sim |
| 3 | recalcula os blocos 5 a 24 | 20 | cadeia válida | [] | não |

### Referência × cadeia reescrita

| Bloco | Dados na referência | Dados na reescrita | Hash na referência | Hash na reescrita | Igual |
| --- | --- | --- | --- | --- | --- |
| 3 | E->F:65 | E->F:65 | ad1d1370743b… | ad1d1370743b… | sim |
| 4 | A->E:9 | A->E:9 | 8f829a332307… | 8f829a332307… | sim |
| 5 | G->C:64 | G->C:1000 | 2ced206ff4e5… | b66da1e54af2… | não |
| 6 | C->B:86 | C->B:86 | 1c0a658ef44e… | e4a514deca0d… | não |
| 7 | F->H:53 | F->H:53 | 90faa1d1dfc8… | 401db9941d4e… | não |
| … | … | … | … | … | … |
| 24 | F->B:73 | F->B:73 | 8aaeebc05af1… | f6085c424d02… | não |

### Custo de esconder a fraude por posição

| Bloco fraudado | Hashes a recalcular | Cadeia reescrita é válida | Ancestral comum com a referência |
| --- | --- | --- | --- |
| 1 | 24 | sim | 0 |
| 5 | 20 | sim | 4 |
| 12 | 13 | sim | 11 |
| 23 | 2 | sim | 22 |

**Verificações**

- [x] estágio 0: validar() responde "cadeia válida"
- [x] estágio 1: validar() responde "hash inválido no bloco 5"
- [x] estágio 2: validar() responde "ligação inválida no bloco 6"
- [x] estágio 3: validar() responde "cadeia válida"
- [x] comparada à referência, a reescrita aparece como fork
- [x] o ancestral comum é o bloco 4
- [x] fraude no bloco 1 reescrita passa na validação
- [x] fraude no bloco 5 reescrita passa na validação
- [x] fraude no bloco 12 reescrita passa na validação
- [x] fraude no bloco 23 reescrita passa na validação

**Observações**

- O hash garante que a cadeia é coerente consigo mesma, não que é a cadeia certa. Quem escreve a cópia local pode produzir outra história coerente.
- A fraude só aparece quando se compara a cópia com algo que o atacante não controla: outra réplica, um hash da ponta publicado antes ou um checkpoint.
- Para quem compara, a cadeia reescrita tem a mesma forma de um fork legítimo: um ancestral comum e dois ramos válidos. Decidir qual ramo vale é tarefa de um protocolo de consenso, não do hash.
- Sem prova de trabalho, recalcular é barato: o custo é um SHA-256 por bloco posterior, poucos microssegundos. Em redes reais é esse custo que se torna proibitivo.

Log completo dos hashes: [`e04.log`](e04.log)

## E05 — Réplicas divergentes e regra de reconciliação

**Objetivo.** Simular cópias da cadeia que recebem blocos diferentes, detectar a divergência e aplicar uma regra de reconciliação, observando o que ela resolve e o que ela não resolve.

**Manipulação.** Réplicas partindo de um prefixo comum de 15 blocos (0 a 14), em quatro cenários: omissão de mensagem, partição, empate e réplica bizantina. Regra: cadeia válida mais longa vence; empate decidido pelo menor hash da ponta.

**Esperado.** Cada cópia continua válida localmente; a regra faz as réplicas convergirem, mas descarta blocos do ramo perdedor e aceita uma fraude reescrita que seja mais longa.

**Obtido.** as réplicas convergiram nos 5 casos; a partição descartou 4 blocos de sul e a réplica bizantina venceu ao apresentar uma fraude reescrita mais longa.

### Resumo dos cenários

| Cenário | Modelo de falha | Divergência | Ancestral comum | Decisão | Vencedora | Blocos descartados | Transações órfãs | Convergiram |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | omissão de mensagem | uma cópia é prefixo da outra (atraso) | 15 | mais longa (18 contra 16 blocos) | norte | 0 | 0 | sim |
| B | partição de rede | ramos concorrentes (fork) | 14 | mais longa (21 contra 19 blocos) | norte | 4 | 4 | sim |
| C | partição com empate | ramos concorrentes (fork) | 14 | empate em 18 blocos; vence o menor hash da ponta | oeste | 3 | 3 | sim |
| D1 | bizantino sem reescrita | uma cópia é prefixo da outra (atraso) | 24 | cópia de mallory rejeitada: hash inválido no bloco 5 | honesta | 1 | 1 | sim |
| D2 | bizantino com reescrita | ramos concorrentes (fork) | 4 | mais longa (26 contra 25 blocos) | mallory | 20 | 1 | sim |

### Cenário A — entregas de norte para sul

| Bloco | Mensagem | Resultado em sul |
| --- | --- | --- |
| 15 | entregue | aceito |
| 16 | perdida (omissão) | — |
| 17 | entregue | recusado: bloco 17 fora de ordem (esperado 16) |

### Cenário B — blocos em disputa depois do bloco 14

| Bloco | Dados em norte | Hash em norte | Dados em sul | Hash em sul |
| --- | --- | --- | --- | --- |
| 15 | E->C:40 | c45924d4b625… | E->F:71 | 4a1971862347… |
| 16 | H->E:16 | 5b537b366a3e… | G->A:27 | 1210bdfcda37… |
| 17 | B->F:25 | 25bbc35c2e68… | A->C:3 | 3231ae326be3… |
| 18 | E->G:28 | 465a1d31176d… | E->F:80 | 991e48f84576… |
| 19 | C->D:95 | 7ee72ec0c230… | — | — |
| 20 | G->D:62 | 2dd80fa73c40… | — | — |

![Duas réplicas divergentes depois de uma partição (E05, cenário B)](diagrama-replicas.png)

**Verificações**

- [x] A: sul recusa o bloco que chega depois da lacuna
- [x] A: as duas réplicas terminam com a mesma cadeia válida
- [x] A: divergência classificada como atraso, não fork
- [x] A: nenhum bloco descartado
- [x] B: a cópia de norte é válida localmente
- [x] B: a cópia de sul é válida localmente
- [x] B: sul não consegue simplesmente anexar o ramo de norte
- [x] B: as duas réplicas terminam com a mesma cadeia válida
- [x] B: divergência classificada como fork
- [x] B: ancestral comum é o bloco 14
- [x] B: norte (mais longa) vence
- [x] B: os 4 blocos de sul são descartados e as 4 transações ficam órfãs
- [x] C: leste e oeste chegam à mesma escolha aplicando a regra cada uma do seu lado
- [x] C: as duas réplicas terminam com a mesma cadeia válida
- [x] C: empate resolvido pelo menor hash da ponta
- [x] D1: as duas réplicas terminam com a mesma cadeia válida
- [x] D1: a cópia adulterada é rejeitada mesmo sendo mais longa
- [x] D2: as duas réplicas terminam com a mesma cadeia válida
- [x] D2: a fraude reescrita e mais longa vence
- [x] D2: a réplica honesta passa a guardar a transação fraudada
- [x] D2: a transação honesta original fica órfã

**Observações**

- Omissão: a validação local percebe a lacuna (o bloco seguinte chega fora de ordem), mas não há conflito. Basta sincronizar: uma cópia é prefixo da outra.
- Partição: os dois ramos são válidos e a validação local não tem como escolher entre eles. A regra converge as réplicas, mas o ramo perdedor é descartado e suas transações voltam a ficar pendentes. O que parecia confirmado em sul deixou de estar, por isso "incluído em um bloco" não significa "irreversível".
- Empate: o menor hash da ponta é um critério arbitrário, mas determinístico. Cada réplica aplica a regra sozinha e chega à mesma escolha, sem precisar combinar.
- D1 aparece como "atraso", e não como fork: o detector compara os hashes armazenados, e a adulteração sem reescrita não muda nenhum deles. Comparar hashes não basta; é a validação (recalcular cada hash) que revela a fraude, por isso o reconciliador valida as duas cópias antes de aplicar a regra.
- Bizantino: a validação barra a adulteração ingênua, mas a fraude reescrita com um bloco a mais vence. Uma regra sem custo pode ser fraudada por quem gera blocos de graça. Protocolos reais exigem trabalho acumulado (PoW) ou stake (PoS), assinaturas e maioria honesta.

Log completo dos hashes: [`e05.log`](e05.log)
