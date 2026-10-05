# Análise de segurança

Modelo de ameaças simplificado da API de biblioteca, no formato da seção 10.12 do material:
ativos, fronteiras de confiança, agentes, abusos possíveis e controles verificáveis.

## Ativos

| Ativo | Por que importa |
| --- | --- |
| acervo (livros e exemplares) | alteração indevida apaga ou falsifica o catálogo |
| empréstimos | empréstimo falso esgota exemplares e nega serviço a leitores reais (o mesmo efeito do E06) |
| tokens de acesso | quem tem o token tem o papel |
| disponibilidade do serviço | threads presas ou rajadas de requisições tiram a API do ar |
| logs | registram o que aconteceu; vazam o que não deveriam se forem descuidados |

## Fronteiras de confiança

```text
 [cliente qualquer] --HTTP--> [ API FastAPI ] ---> [ arquivo SQLite ]
        ^                           ^
   não confiável            confia no próprio processo e no banco local
        |
 [quem observa a rede]  (E10: o proxy no meio do caminho)
```

A única fronteira atravessada por dados não confiáveis é a requisição HTTP. Tudo o que chega por
ela — cabeçalhos, corpo, parâmetros de consulta — é tratado como entrada de atacante.

## Ameaças e controles

| Ameaça | Agente | Impacto | Controle | Propriedade | Evidência |
| --- | --- | --- | --- | --- | --- |
| alterar o acervo sem identidade | qualquer cliente na rede | integridade do catálogo | token Bearer obrigatório nas escritas | autenticidade | E10: sem token, token inválido, esquema Basic → 401 |
| funcionário usar operação fora da função | atendente ou consulta | elevação de privilégio | autorização por papel | autorização | E10: consulta e atendente no acervo → 403; atendente em empréstimo → 201 |
| forjar o token por tentativa | atacante | autenticação burlada | comparação em tempo constante (`hmac.compare_digest`); tokens gerados por execução | autenticidade | E10: token padrão do código → 401 nos experimentos |
| injetar campo de controle (`versao`) | cliente autenticado | burlar a concorrência otimista | `extra="forbid"` nos esquemas | integridade | E10: `versao=99` → 422 |
| corpo gigante ou fora de faixa | qualquer cliente | consumo de recurso, dado inválido persistido | limites de tamanho e faixa no Pydantic | integridade, disponibilidade | E10: título de 5000 caracteres e ano negativo → 422 |
| usar a rota de laboratório como arma | qualquer cliente | threads presas por minutos | rota desligada por padrão; `atraso_ms` ≤ 10 s | disponibilidade | E10: rota com laboratório desligado → 404; `atraso_ms=600000` → 422 |
| ler o token nos logs | quem acessa os logs | vazamento de credencial | o middleware não registra cabeçalhos | confidencialidade | E10: nenhum token encontrado nos logs do servidor |
| escutar o canal | quem está no caminho da rede | captura do token e reuso | **não tratado** — exige TLS | confidencialidade | E10: o proxy capturou o token em texto claro |
| repetir um comando capturado | quem capturou a requisição | empréstimo indevido | parcial: `Idempotency-Key` impede repetição da mesma intenção, mas não substitui TLS | integridade | E06 |

## Controle escolhido

**Token Bearer com autorização por papel**, implementado em
[`app/seguranca.py`](../app/seguranca.py):

| Papel | Leitura | Empréstimo e devolução | Cadastro, alteração e remoção de livros |
| --- | :-: | :-: | :-: |
| sem token | sim | não (401) | não (401) |
| consulta | sim | não (403) | não (403) |
| atendente | sim | sim | não (403) |
| bibliotecario | sim | sim | sim |

A distinção entre 401 e 403 é proposital e é o ponto central da análise: **401** responde
"não sei quem você é" (autenticidade) e vem com `WWW-Authenticate: Bearer`; **403** responde
"sei quem você é e você não pode" (autorização). Autenticar não é autorizar.

A leitura é pública por decisão de projeto: o catálogo de uma biblioteca não é segredo. O
controle protege a **integridade** — quem pode alterar o estado —, não a confidencialidade do
acervo.

## Ameaças residuais

1. **Canal sem TLS.** O E10 mostra o token do bibliotecário legível por um intermediário. Em uso
   real, TLS é pré-requisito do controle por token, não um complemento. TLS protegeria
   confidencialidade e integridade do canal e autenticaria o servidor; mTLS autenticaria também
   o cliente, ao custo de gestão de certificados.
2. **Token estático e sem expiração.** Um token vazado vale até alguém trocá-lo. Um sistema real
   usaria tokens com validade curta (por exemplo, JWT assinado) e revogação.
3. **Sem limitação de taxa.** Nada impede um cliente de enviar milhares de requisições. O E07
   mostra que até retries legítimos produzem rajadas; um limitador por cliente seria a próxima
   camada de disponibilidade.
4. **Auditoria sem identidade.** O log tem correlação, mas não registra qual papel executou cada
   escrita. Para não repúdio, o papel deveria ir para o log (o token, nunca).
5. **Leitura pública revela padrões.** A lista de empréstimos por livro expõe nomes de leitores
   sem autenticação. Se isso for considerado dado pessoal, a listagem de empréstimos deveria
   exigir o papel atendente.
