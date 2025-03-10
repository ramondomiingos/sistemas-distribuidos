import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

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
    }
}

# Inicializa o Faker para gerar dados fictícios
fake = Faker()

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
def populate_payments(conn, account_id):
    
    cur = conn.cursor()
    
    order_id = fake.uuid4()
    status = random.choice(["confirmed", "pending", "cancelled", "delayed"])
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
def populate_delivery(conn, account_id, order_id):
    cur = conn.cursor()
    status = random.choice(["out_for_delivery", "delivered", "pending"])
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

# Função principal
def main():
    # Gera um account_id único para todos os registros
    for _ in range(10):
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

        print(f"Dados populados com sucesso para account_id: {account_id}")

if __name__ == "__main__":
    main()