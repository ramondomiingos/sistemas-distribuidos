

# Projeto microsserviços

Este projeto é um exemplo de um sistema distribuído composto por 4 microsserviços independentes, cada um com seu próprio banco de dados, interligados via Docker Compose. O objetivo é simular um ambiente de microsserviços para estudos e teste de um middleware.

---

## Estrutura do Projeto

O projeto é composto por 4 microsserviços:

1. **PAYMENTS**: Gerencia informações sobre pagamentos.
2. **ACCOUNTS**: Gerencia informações sobre contas de usuários.
3. **CRM**: Armazena informações adicionais sobre usuários.
4. **DELIVERY**: Gerencia informações sobre entregas.

Cada microsserviço possui:
- Um banco de dados PostgreSQL independente.
- Uma API RESTful construída com FastAPI.
- Um `Dockerfile` para containerização.
- Dependências definidas em `requirements.txt`.

---

## Tecnologias Utilizadas

- **FastAPI**: Framework para construção das APIs.
- **PostgreSQL**: Banco de dados relacional para cada microsserviço.
- **Docker**: Containerização dos microsserviços e bancos de dados.
- **Docker Compose**: Orquestração dos containers.
- **SQLAlchemy**: ORM para interação com o banco de dados.
- **Pydantic**: Validação de dados nas APIs.

---

## Como Executar o Projeto

### Pré-requisitos

- Docker instalado ([https://www.docker.com/](https://www.docker.com/)).
- Docker Compose instalado (geralmente vem com o Docker).

### Passos para Execução

1. Clone o repositório ou crie a estrutura de pastas e arquivos conforme descrito no projeto.

2. Navegue até a pasta raiz do projeto (`nome_pasta`):

   ```bash
   cd nome_pasta
   ```

3. Execute o Docker Compose para construir e iniciar os containers:

   ```bash
   docker-compose up --build
   ```

4. Aguarde até que todos os serviços estejam rodando. Você verá mensagens no terminal indicando que cada microsserviço está online.

5. Os serviços estarão disponíveis nas seguintes portas, caso seja necessário em sua simulação voce pode alterar a propriedade `ports` no `docker-compose.yml` :
   - **PAYMENTS**: `http://localhost:8001`
   - **ACCOUNTS**: `http://localhost:8002`
   - **CRM**: `http://localhost:8003`
   - **DELIVERY**: `http://localhost:8004`



---

## Exemplos de Uso

Aqui estão exemplos de comandos `curl` para interagir com cada microsserviço:

### 1. **PAYMENTS**  
Rota: `/orders/`  
Criar uma nova ordem de pagamento:

```bash
curl -X POST "http://localhost:8001/orders/" \
-H "Content-Type: application/json" \
-d '{
   "order_id":"123456",
   "status":"confirmed",
   "amount":1500.75,
   "currency":"BRL",
   "payment_method":"PIX",
   "transaction_id":"abc123xyz",
   "payment_date":"2025-03-05T14:30:00Z",
   "account_id":"123456789"
}'
```

Buscar uma ordem por ID:

```bash
curl -X GET "http://localhost:8001/orders/123456"
```

---

### 2. **ACCOUNTS**  
Rota: `/users/`  
Criar um novo usuário:

```bash
curl -X POST "http://localhost:8002/users/" \
-H "Content-Type: application/json" \
-d '{
   "name":"joao da silva",
   "email":"joao@joao.com",
   "account_id":"123456789"
}'
```

Buscar um usuário por `account_id`:

```bash
curl -X GET "http://localhost:8002/users/123456789"
```

---

### 3. **CRM**  
Rota: `/info-users/`  
Criar informações de um usuário:

```bash
curl -X POST "http://localhost:8003/info-users/" \
-H "Content-Type: application/json" \
-d '{
   "birth_day":"2025-03-05",
   "account_id":"123",
   "religion":"catholic"
}'
```

Buscar informações por `account_id`:

```bash
curl -X GET "http://localhost:8003/info-users/123"
```

---

### 4. **DELIVERY**  
Rota: `/delivery/`  
Criar uma nova entrega:

```bash
curl -X POST "http://localhost:8004/delivery/" \
-H "Content-Type: application/json" \
-d '{
   "order_id":"987654",
   "status":"out_for_delivery",
   "tracking_code":"TRK123456789",
   "estimated_delivery":"2025-03-07T18:00:00Z",
   "carrier":"Transportadora XYZ",
   "customer_id":"1235",
   "shipping_address":{
      "street":"Rua das Flores",
      "number":"123",
      "complement":"Apto 202",
      "neighborhood":"Centro",
      "city":"Rio de Janeiro",
      "state":"RJ",
      "zip_code":"20000-000",
      "country":"Brasil"
   }
}'
```

Buscar uma entrega por `order_id`:

```bash
curl -X GET "http://localhost:8004/delivery/987654"
```

---

## Objetivo de Cada Microsserviço

1. **PAYMENTS**:
   - Gerencia transações financeiras.
   - Armazena informações como valor, método de pagamento, status e data.

2. **ACCOUNTS**:
   - Gerencia contas de usuários.
   - Armazena informações básicas como nome, e-mail e ID da conta.

3. **CRM**:
   - Armazena informações adicionais sobre usuários.
   - Exemplo: data de nascimento, religião, etc.

4. **DELIVERY**:
   - Gerencia informações sobre entregas.
   - Armazena detalhes como código de rastreamento, transportadora, endereço de entrega, etc.

---

## Estrutura de Pastas

```
mestrado/
├── docker-compose.yml
├── payments/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── requirements.txt
│   └── Dockerfile
├── accounts/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── requirements.txt
│   └── Dockerfile
├── crm/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── requirements.txt
│   └── Dockerfile
└── delivery/
    ├── app/
    │   ├── main.py
    │   ├── models.py
    │   ├── schemas.py
    │   └── database.py
    ├── requirements.txt
    └── Dockerfile
```

---

## Considerações Finais

Este projeto foi desenvolvido para estudos de sistemas distribuídos. Ele pode ser expandido para incluir funcionalidades adicionais, como autenticação, logs distribuídos, ou integração com outros sistemas.

Se tiver dúvidas ou sugestões, sinta-se à vontade para entrar em contato abrindo uma issue! 😊

---
