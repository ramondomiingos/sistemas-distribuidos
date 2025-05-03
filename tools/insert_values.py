import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta
import requests

# Configurações do banco de dados
DATABASES = {
    "payments": {
        "dbname": "payments_db",
        "user": "user",
        "password": "password",
        "host": "localhost",
        "port": "5435"
    },
    "accounts": {
        "dbname": "accounts_db",
        "user": "user",
        "password": "password",
        "host": "localhost",
        "port": "5436"
    },
    "crm": {
        "dbname": "crm_db",
        "user": "user",
        "password": "password",
        "host": "localhost",
        "port": "5433"
    },
    "delivery": {
        "dbname": "delivery_db",
        "user": "user",
        "password": "password",
        "host": "localhost",
        "port": "5434"
    },
     "middleware": {
        "dbname": "middlewaredb",
        "user": "user",
        "password": "password",
        "host": "localhost",
        "port": "5437"
    }
}

# Inicializa o Faker para gerar dados fictícios
fake = Faker()

# Cores ANSI para o terminal
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'

# Função para conectar ao banco de dados
def connect_db(db_config):
    conn = psycopg2.connect(
        dbname=db_config["dbname"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
    )
    return conn

# Função para popular a tabela de PAYMENTS
def populate_payments(conn, account_id, status=random.choice(["confirmed", "pending", "cancelled", "delayed"])):

    cur = conn.cursor()

    order_id = fake.uuid4()
    amount = round(random.uniform(100, 1000), 2)
    currency = "BRL"
    payment_method = random.choice(["PIX", "Credit Card", "Bank Transfer"])
    transaction_id = fake.uuid4()
    payment_date = fake.date_time_between(start_date="-1y", end_date="now")

    cur.execute(
            """
            INSERT INTO orders (order_id, status, amount, currency, payment_method, transaction_id, payment_date, account_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (order_id, status, amount, currency, payment_method, transaction_id, payment_date, account_id)
        )
    conn.commit()
    cur.close()
    return order_id

# Função para popular a tabela de ACCOUNTS
def populate_accounts(conn, account_id):
    cur = conn.cursor()
    name = fake.name()
    email = fake.email()

    cur.execute(
        """
        INSERT INTO users (name, email, account_id)
        VALUES (%s, %s, %s)
        """,
        (name, email, account_id)
    )
    conn.commit()
    cur.close()

# Função para popular a tabela de CRM
def populate_crm(conn, account_id):
    cur = conn.cursor()
    birth_day = fake.date_of_birth(minimum_age=18, maximum_age=65)
    religion = random.choice(["Catholic", "Protestant", "Jewish", "Muslim", "Atheist"])

    cur.execute(
        """
        INSERT INTO user_info (birth_day, account_id, religion)
        VALUES (%s, %s, %s)
        """,
        (birth_day, account_id, religion)
    )
    conn.commit()
    cur.close()

# Função para popular a tabela de DELIVERY
def populate_delivery(conn, account_id, order_id, status = random.choice(["out_for_delivery", "delivered", "pending"])):
    cur = conn.cursor()
    tracking_code = fake.uuid4()
    estimated_delivery = fake.date_time_between(start_date="now", end_date="+30d")
    carrier = random.choice(["Transportadora XYZ", "Logística ABC", "Entregas Rápidas"])
    shipping_address = {
            "street": fake.street_name(),
            "number": fake.building_number(),
            "complement": fake.secondary_address(),
            "neighborhood": fake.city_suffix(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.postcode(),
            "country": "Brasil"
    }

    cur.execute(
            """
            INSERT INTO deliveries (order_id, status, tracking_code, estimated_delivery, carrier, customer_id, shipping_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (order_id, status, tracking_code, estimated_delivery, carrier, account_id, str(shipping_address))
        )
    conn.commit()
    cur.close()

# Função para popular a tabela de Services Middleware, por API
def populate_middleware_services():
    print(f"{Colors.BOLD}{Colors.CYAN}\n--- Populando Serviços cadastrados no Middleware via API ---\n{Colors.RESET}")
    services = [
    {
        "service_name": "payment",
        "description": "Gerencia o fluxo de valor monetário entre entidades. Implementa protocolos de comunicação seguros (e.g., HTTPS, TLS) para autorização, captura e reembolso de transações financeiras. Mantém registros de transações e integra-se com gateways de pagamento e instituições financeiras via APIs (e.g., REST, SOAP)."
    },
    {
        "service_name": "delivery",
        "description": "Coordena a movimentação física de bens do ponto de origem ao destino. Envolve o gerenciamento de rotas, agendamento de coletas e entregas, rastreamento em tempo real da localização dos itens e comunicação com transportadoras através de APIs ou sistemas de gerenciamento de transporte (TMS)."
    },
    {
        "service_name": "account",
        "description": "Autentica e autoriza o acesso de usuários a recursos e funcionalidades do sistema. Gerencia informações de perfil de usuários, credenciais de acesso (e.g., senhas, tokens), e controla permissões e papéis dentro da plataforma. Pode implementar protocolos de autenticação como OAuth 2.0 e armazenar dados de forma segura (e.g., utilizando criptografia)."
    },
    {
        "service_name": "crm",
        "description": "Centraliza e organiza dados relacionados a interações com clientes (atuais e potenciais). Permite o registro e acompanhamento de leads, oportunidades de venda, histórico de comunicação, e atividades de marketing e suporte. Facilita a automação de processos de vendas e marketing e pode integrar-se com outras plataformas (e.g., e-mail, redes sociais) via APIs."
    }
    ]

    for service in services:
        try:
            res = requests.post('http://localhost:8000/api/v1/services/', json=service)
            status_color = Colors.GREEN if 200 <= res.status_code < 300 else Colors.RED
            print(f"Serviço: {Colors.BOLD}{service['service_name']}{Colors.RESET} - Status: {Colors.BOLD}{status_color}{res.status_code}{Colors.RESET}")
        except requests.exceptions.ConnectionError as e:
            print(f"{Colors.RED}Erro ao conectar com o middleware para o serviço {service['service_name']}: {e}{Colors.RESET}")


def populate_scenario_1():
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Cenário 1: Exclusão permitida por todos os microsserviços ---\n{Colors.RESET}")
    account_id = fake.uuid4()

    # Popula dados em todos os microsserviços
    accounts_conn = connect_db(DATABASES["accounts"])
    populate_accounts(accounts_conn, account_id)
    accounts_conn.close()

    payments_conn = connect_db(DATABASES["payments"])
    populate_payments(payments_conn, account_id, status="confirmed") # Cria uma ordem confirmada
    payments_conn.close()

    crm_conn = connect_db(DATABASES["crm"])
    populate_crm(crm_conn, account_id)
    crm_conn.close()

    delivery_conn = connect_db(DATABASES["delivery"])
    order_id = fake.uuid4() # Precisa de um order_id para delivery
    populate_delivery(delivery_conn, account_id, order_id, status="delivered") # Cria uma entrega confirmada
    delivery_conn.close()

    print(f"{Colors.GREEN}Dados populados para account_id: {Colors.BOLD}{account_id}{Colors.RESET}")
    print("Execute os passos do cenário 1 no middleware (publicar PREPARE_DELETE e PERFORM_DELETE).")
    print("Após a execução, verifique se os dados foram excluídos em todos os microsserviços.")
    # Não podemos simular a comunicação com Kafka e a lógica do middleware aqui.
    # Isso precisaria ser testado separadamente ou com uma integração maior.

def populate_scenario_2():
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Cenário 2: Exclusão negada por um microsserviço (payment) ---\n{Colors.RESET}")
    account_id = fake.uuid4()

    # Popula dados em todos os microsserviços
    accounts_conn = connect_db(DATABASES["accounts"])
    populate_accounts(accounts_conn, account_id)
    accounts_conn.close()

    payments_conn = connect_db(DATABASES["payments"])
    populate_payments(payments_conn, account_id, status="pending") # Cria uma ordem pendente
    payments_conn.close()

    crm_conn = connect_db(DATABASES["crm"])
    populate_crm(crm_conn, account_id)
    crm_conn.close()

    delivery_conn = connect_db(DATABASES["delivery"])
    order_id = fake.uuid4() # Precisa de um order_id para delivery
    populate_delivery(delivery_conn, account_id, order_id, status="delivered") # Cria uma entrega confirmada
    delivery_conn.close()

    print(f"{Colors.YELLOW}Dados populados para account_id: {Colors.BOLD}{account_id}{Colors.RESET} (com ordem pendente em PAYMENTS)")
    print("Execute o passo do cenário 2 no middleware (publicar PREPARE_DELETE).")
    print("Verifique se o PAYMENTS responde can_delete=false.")
    print("Verifique se o middleware não publica PERFORM_DELETE e nenhum dado é excluído.")
    # Novamente, a lógica do middleware não pode ser totalmente simulada aqui.

def populate_scenario_3():
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Cenário 3: Exclusão Parcial (Dados Inexistentes em Alguns Microsserviços) ---\n{Colors.RESET}")
    account_id = fake.uuid4()

    # Popula dados apenas em PAYMENTS e ACCOUNTS
    accounts_conn = connect_db(DATABASES["accounts"])
    populate_accounts(accounts_conn, account_id)
    accounts_conn.close()

    payments_conn = connect_db(DATABASES["payments"])
    populate_payments(payments_conn, account_id, status="confirmed") # Cria uma ordem confirmada
    payments_conn.close()

    print(f"{Colors.MAGENTA}Dados populados para account_id: {Colors.BOLD}{account_id}{Colors.RESET} (apenas em PAYMENTS e ACCOUNTS)")
    print("Execute os passos do cenário 3 no middleware (publicar PREPARE_DELETE e PERFORM_DELETE).")
    print("Verifique se os dados foram excluídos em PAYMENTS e ACCOUNTS e não em CRM e DELIVERY.")

def populate_scenario_4():
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Cenário 4: Falha na Comunicação com um Microsserviço ---\n{Colors.RESET}")
    account_id = fake.uuid4()

    # Popula dados em todos os microsserviços (para simular a existência)
    accounts_conn = connect_db(DATABASES["accounts"])
    populate_accounts(accounts_conn, account_id)
    accounts_conn.close()

    payments_conn = connect_db(DATABASES["payments"])
    populate_payments(payments_conn, account_id)
    payments_conn.close()

    crm_conn = connect_db(DATABASES["crm"])
    populate_crm(crm_conn, account_id)
    crm_conn.close()

    delivery_conn = connect_db(DATABASES["delivery"])
    order_id = fake.uuid4() # Precisa de um order_id para delivery
    populate_delivery(delivery_conn, account_id, order_id)
    delivery_conn.close()

    print(f"{Colors.YELLOW}Dados populados para account_id: {Colors.BOLD}{account_id}{Colors.RESET}")
    print("Simule o microsserviço CRM estando offline, pode desligar o container antes de iniciar a requisição /api/v1/privacy_request/.")
    print("Execute o passo do cenário 4 no middleware (publicar PREPARE_DELETE).")
    print("Verifique se o middleware não recebe resposta do CRM e não publica PERFORM_DELETE.")
    print("Verifique se nenhum dado é excluído imediatamente.")
    print("Após simular o CRM voltando online, o middleware (se implementado corretamente com Kafka) deve processar a mensagem.")

def populate_cenary_tests():
    print(f"{Colors.BOLD}{Colors.GREEN}\n--- Iniciando População dos Cenários de Teste ---\n{Colors.RESET}")
    populate_scenario_1()
    populate_scenario_2()
    populate_scenario_3()
    populate_scenario_4()
    print(f"{Colors.BOLD}{Colors.GREEN}\n--- População dos Cenários de Teste Concluída ---\n{Colors.RESET}")


# Função principal
def main():
    print(f"{Colors.BOLD}{Colors.YELLOW}\n--- Iniciando População Inicial do Banco de Dados ---\n{Colors.RESET}")
    for i in range(3): # Reduzi para 3 para não poluir muito a saída inicial
        account_id = fake.uuid4()

        # Popula ACCOUNTS
        accounts_conn = connect_db(DATABASES["accounts"])
        populate_accounts(accounts_conn, account_id)
        accounts_conn.close()

        # Popula PAYMENTS
        payments_conn = connect_db(DATABASES["payments"])
        order_id = populate_payments(payments_conn, account_id)
        payments_conn.close()

        # Popula CRM
        crm_conn = connect_db(DATABASES["crm"])
        populate_crm(crm_conn, account_id)
        crm_conn.close()

        # Popula DELIVERY
        delivery_conn = connect_db(DATABASES["delivery"])
        populate_delivery(delivery_conn, account_id,order_id)
        delivery_conn.close()

        print(f"{Colors.GREEN}Dados populados com sucesso para account_id: {Colors.BOLD}{account_id}{Colors.RESET}")
    populate_middleware_services()
    print(f"{Colors.BOLD}{Colors.YELLOW}\n--- População Inicial do Banco de Dados Concluída ---\n{Colors.RESET}")

if __name__ == "__main__":
    main()
    populate_cenary_tests()