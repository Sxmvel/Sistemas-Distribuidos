# TP1 — Middleware de alarme para barragem de rejeito

Sistema de monitoramento e alarme de uma barragem de rejeito de minério (a **Barragem Serra Azul**, fictícia), até o momento da ruptura. Sensores e atuadores conversam por **MQTT**. Três **controladores replicados** tomam as decisões. Os clientes acessam o sistema por **invocação remota de métodos (gRPC)**.

O tema foi motivado pelos rompimentos de Mariana (2015) e Brumadinho (2019). Em Brumadinho as sirenes não tocaram. Por isso o projeto trata a confiabilidade do alarme como requisito central: o alarme precisa disparar mesmo com controladores caindo ou mentindo.

**Stack:** Java 21+, Spring Boot 3.5, gRPC 1.68, MQTT (broker Moquette embutido, cliente Paho) e H2 (um banco por controlador).

---

## Arquitetura

```
 CLIENTES (gRPC)                   MIDDLEWARE                          CAMPO (MQTT)
┌──────────────────┐        ┌─────────────────────────────┐
│ Cliente 1        │◄──────►│ Controlador c1 ── H2 (c1)   │◄──┐
│ painel-web       │        │      ▲ heartbeat/replicação │   │      ┌──────────┐    ┌────────────┐
│ (centro monit.)  │        │      ▼                      │   ├─────►│  Broker  │◄──►│  Sensores  │
├──────────────────┤        │ Controlador c2 ── H2 (c2)   │◄──┤      │   MQTT   │    │ (8 sensores│
│ Cliente 2        │◄──────►│      ▲                      │   │      │ :1883    │◄──►│  Atuadores │
│ cliente-cli      │        │      ▼                      │   │      └──────────┘    │ (5 atuad.) │
│ (Defesa Civil)   │        │ Controlador c3 ── H2 (c3)   │◄──┘                      └────────────┘
└──────────────────┘        └─────────────────────────────┘
```

| Peça | Função |
|---|---|
| **Sensores** | 3 piezômetros, 2 medidores de deslocamento, nível do reservatório, pluviômetro e turbidez da drenagem. Publicam a cada 1 s, com cada leitura **assinada por HMAC-SHA256** |
| **Controladores** | Os 3 assinam as leituras e calculam o nível (NORMAL → ATENÇÃO → N1 → N2 → N3) de forma independente. Comandos de operador são sequenciados por um **líder** e **replicados** |
| **Atuadores** | 2 sirenes, painel de rota de fuga, cancela de acesso à ZAS e bomba de rebaixamento. Só mudam de estado com **quórum de 2 controladores** |
| **Clientes** | Consultam as 3 réplicas e aceitam o que a **maioria** responde. Comandos têm **id único** e **failover** automático |

## Estrutura de pastas

O projeto é dividido em **camadas do sistema** (pastas de cima) e, dentro de cada módulo, em **camadas de código**:

```
Trabalho-Pratico-1/
├── compartilhado/
│   ├── contrato-grpc/        .proto dos serviços (cliente, replicação, laboratório)
│   └── comum/                tópicos MQTT, mensagens, HMAC, catálogo de dispositivos
├── campo/
│   ├── broker-mqtt/          Moquette na porta 1883
│   ├── sensores/             simulador com cenários
│   └── atuadores/            quórum de comandos
├── middleware/
│   └── controlador/          3 instâncias (perfis c1, c2, c3)
├── clientes/
│   ├── cliente-core/         biblioteca: votação, failover, id de requisição
│   ├── painel-web/           Cliente 1 — http://localhost:8080
│   └── cliente-cli/          Cliente 2 — terminal
└── scripts/                  compilar, iniciar, parar
```

Camadas dentro de cada módulo:

| Pacote | Conteúdo | Exemplo no controlador |
|---|---|---|
| `dominio/` | Regras puras, sem framework | `EstadoBarragem` (máquina de estados), `AvaliadorRisco`, `VisaoCluster` |
| `aplicacao/` | Casos de uso e **portas** (interfaces) | `ServicoComandos`, `ServicoCluster`, `porta/ComunicacaoPares` |
| `infraestrutura/` | O que **sai**: banco, MQTT, gRPC para os pares | `persistencia/`, `mqtt/`, `grpc/` |
| `entrada/` | O que **chega**: serviços gRPC, MQTT, agendadores, web | `grpc/EntradaBarragemGrpc`, `mqtt/ReceptorLeiturasMqtt` |
| `config/` | Montagem dos beans | `ServidorGrpcConfig`, `DominioConfig` |

## Como executar

Pré-requisitos: **JDK 21 ou superior** e **Maven 3.9**. Não precisa instalar broker MQTT nem banco de dados.

```powershell
.\scripts\compilar.ps1                 # gera os jars de todos os módulos
.\scripts\iniciar-tudo.ps1 -LimparDados # abre uma janela por componente e o painel no navegador
.\scripts\iniciar-tudo.ps1 -ComCli      # idem, abrindo também o cliente de terminal
.\scripts\parar-tudo.ps1               # encerra todos os componentes
```

Portas: broker `1883`, controladores `50051`/`50052`/`50053` (gRPC) e painel `8080`.

Componente avulso: `.\scripts\iniciar-componente.ps1 -Componente controlador -Perfil c2`.

## Roteiro de demonstração (pelo painel)

1. **Normal → ruptura.** Em *Laboratório*, clique em **Ruptura**. Em cerca de 1 minuto o nível sobe até **EMERGÊNCIA N3**, as sirenes tocam, a cancela fecha e o painel mostra "EVACUAR". Os 3 controladores mudam de nível no mesmo segundo, cada um calculando sozinho.
2. **Controlador invadido.** No card do **c2**, clique em **Malicioso**. Ele passa a dizer "NORMAL" e a pedir que as sirenes desliguem. O painel marca o c2 como **DIVERGENTE**, c1 e c3 o colocam em **QUARENTENA**, e as sirenes continuam tocando porque o pedido dele não tem quórum. Clique em **Honesto** para ele voltar depois de alguns segundos.
3. **Queda do líder no meio de um comando.** Clique em **Acionar evacuação derrubando o líder no meio**. O líder replica a operação e cai antes de responder. O *Rastro da requisição* mostra a tentativa 1 falhando e a tentativa 2, em outra réplica, devolvendo **sucesso deduplicado**: a evacuação não é executada duas vezes.
4. **Recuperação.** Clique em **Religar** no controlador que caiu. Ele restaura o próprio H2, **sincroniza** o que perdeu com os pares e volta ao cluster.
5. **Ataques ao campo.** **Leitura forjada** publica uma leitura com HMAC inválido, e os controladores a descartam. **Pico espúrio** publica um salto fisicamente impossível, também descartado pela checagem de plausibilidade.

## Como cada problema do enunciado foi resolvido

### 1. Réplicas dos dados
- Cada controlador tem seu próprio **H2 em arquivo** (`dados/c1`, `dados/c2`, `dados/c3`), com leituras, operações e auditoria.
- **Replicação ativa das leituras:** os 3 assinam o MQTT e processam as mesmas leituras, de forma determinística.
- **Primário-backup para os comandos:** o líder (menor id vivo e fora de quarentena) atribui um número de sequência e replica para os pares. Ele só confirma quando a **maioria (2 de 3)** gravou.
- Um controlador que volta ao ar restaura o próprio banco e **busca as operações que faltam** (`Sincronizar`) no par que estiver mais adiantado.

### 2. Resultado positivo mesmo se o controlador cair
- Todo comando leva um `requisicao_id` (UUID) gerado pelo cliente.
- O `cliente-core` tenta o líder conhecido e, se a chamada falhar, **reenvia o mesmo id** para as outras réplicas.
- Como a operação foi replicada **antes** da resposta, qualquer réplica sobrevivente já a conhece. Ela devolve o resultado original **sem executar de novo** (idempotência).
- O heartbeat de 1 s detecta a queda e elege o novo líder.

### 3. Controladores que respondem valores que não conferem
Há quatro defesas em camadas:
- **Votação no cliente:** nível aceito por maioria e sensores pela **mediana** das réplicas. A réplica que difere é apontada como divergente.
- **Quarentena entre réplicas:** no heartbeat, cada controlador compara o nível informado pelos pares. Quem diverge da maioria acumula suspeita, é **excluído da liderança** e tem a replicação recusada. Ele sai da quarentena quando volta a concordar. Isso cobre tanto a invasão (modo malicioso) quanto os erros intermitentes.
- **Quórum nos atuadores:** comandos **assinados por HMAC com a chave de cada controlador**. O atuador só muda de estado quando 2 controladores diferentes pedem a mesma coisa, então um controlador sozinho não silencia nem dispara a sirene.
- **Integridade do campo:** leituras de sensor com **HMAC**, rejeição de replay (janela de tempo e ordem) e **checagem de plausibilidade física** (faixa e taxa máxima de variação).

## Limitações conhecidas
- Com 3 réplicas, o sistema tolera **1** controlador falho ou malicioso por vez.
- Partições de rede não são tratadas: o cenário é local, e a eleição pelo menor id vivo pode divergir durante uma partição.
- As chaves HMAC são derivadas de segredos fixos no código, por ser um trabalho didático. Em produção viriam de um cofre ou de certificados.
- Os modos malicioso e intermitente são acionados pelo serviço gRPC `ServicoLaboratorio`, que existe apenas para a demonstração.
