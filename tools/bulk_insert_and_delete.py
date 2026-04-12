import psycopg2
from faker import Faker
import random
import requests
import json
import time
from datetime import datetime

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

MIDDLEWARE_URL = "http://localhost:8000"
NUM_ACCOUNTS = 900
ACCOUNT_IDS_FILE = "tools/account_ids.json"

fake = Faker()


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'


def connect_db(db_config):
    return psycopg2.connect(
        dbname=db_config["dbname"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
    )


def insert_account(conn, account_id):
    cur = conn.cursor()
    # Garante email único usando o account_id como sufixo
    email = f"{account_id[:8]}@{fake.domain_name()}"
    cur.execute(
        "INSERT INTO users (name, email, account_id) VALUES (%s, %s, %s)",
        (fake.name(), email, account_id)
    )
    conn.commit()
    cur.close()


def insert_payment(conn, account_id):
    cur = conn.cursor()
    order_id = fake.uuid4()
    cur.execute(
        """INSERT INTO orders (order_id, status, amount, currency, payment_method, transaction_id, payment_date, account_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            order_id,
            "confirmed",
            round(random.uniform(100, 1000), 2),
            "BRL",
            random.choice(["PIX", "Credit Card", "Bank Transfer"]),
            fake.uuid4(),
            fake.date_time_between(start_date="-1y", end_date="now"),
            account_id
        )
    )
    conn.commit()
    cur.close()
    return order_id


def insert_crm(conn, account_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_info (birth_day, account_id, religion) VALUES (%s, %s, %s)",
        (
            fake.date_of_birth(minimum_age=18, maximum_age=65),
            account_id,
            random.choice(["Catholic", "Protestant", "Jewish", "Muslim", "Atheist"])
        )
    )
    conn.commit()
    cur.close()


def insert_delivery(conn, account_id, order_id):
    cur = conn.cursor()
    shipping_address = {
        "street": fake.street_name(),
        "number": fake.building_number(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "zip_code": fake.postcode(),
        "country": "Brasil"
    }
    cur.execute(
        """INSERT INTO deliveries (order_id, status, tracking_code, estimated_delivery, carrier, customer_id, shipping_address)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            order_id,
            "delivered",
            fake.uuid4(),
            fake.date_time_between(start_date="now", end_date="+30d"),
            random.choice(["Transportadora XYZ", "Logística ABC", "Entregas Rápidas"]),
            account_id,
            str(shipping_address)
        )
    )
    conn.commit()
    cur.close()


def bulk_insert(n=NUM_ACCOUNTS):
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Fase 1: Inserindo {n} contas em todos os microsserviços ---\n{Colors.RESET}")

    account_ids = []
    errors = 0

    conns = {name: connect_db(cfg) for name, cfg in DATABASES.items() if name != "middleware"}

    try:
        for i in range(n):
            account_id = str(fake.uuid4())
            try:
                insert_account(conns["accounts"], account_id)
                order_id = insert_payment(conns["payments"], account_id)
                insert_crm(conns["crm"], account_id)
                insert_delivery(conns["delivery"], account_id, order_id)
                account_ids.append(account_id)

                if (i + 1) % 100 == 0:
                    print(f"  {Colors.GREEN}✓ {i + 1}/{n} contas inseridas{Colors.RESET}")
            except Exception as e:
                errors += 1
                print(f"  {Colors.RED}✗ Erro ao inserir conta {i + 1}: {e}{Colors.RESET}")
                for conn in conns.values():
                    conn.rollback()
    finally:
        for conn in conns.values():
            conn.close()

    print(f"\n{Colors.BOLD}{Colors.GREEN}Inserção concluída: {len(account_ids)} sucesso, {errors} erros{Colors.RESET}")

    with open(ACCOUNT_IDS_FILE, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat(),
            "total": len(account_ids),
            "account_ids": account_ids
        }, f, indent=2)
    print(f"{Colors.CYAN}Account IDs salvos em: {ACCOUNT_IDS_FILE}{Colors.RESET}")

    return account_ids


def bulk_delete(account_ids):
    n = len(account_ids)
    print(f"{Colors.BOLD}{Colors.BLUE}\n--- Fase 2: Solicitando {n} exclusões ao middleware ---\n{Colors.RESET}")

    results = {"submitted": 0, "errors": 0, "request_ids": []}

    for i, account_id in enumerate(account_ids):
        try:
            res = requests.post(
                f"{MIDDLEWARE_URL}/api/v1/privacy-requests/",
                json={
                    "account_id": account_id,
                    "operation": "DELETE",
                },
                timeout=10
            )
            if 200 <= res.status_code < 300:
                results["submitted"] += 1
                results["request_ids"].append(res.json().get("id"))
            else:
                results["errors"] += 1
                print(f"  {Colors.RED}✗ account {account_id}: HTTP {res.status_code}{Colors.RESET}")
        except requests.exceptions.RequestException as e:
            results["errors"] += 1
            print(f"  {Colors.RED}✗ account {account_id}: {e}{Colors.RESET}")

        if (i + 1) % 100 == 0:
            print(f"  {Colors.YELLOW}→ {i + 1}/{n} requisições enviadas{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.GREEN}Exclusões submetidas: {results['submitted']}, erros: {results['errors']}{Colors.RESET}")

    # Persiste os request_ids junto aos account_ids
    with open(ACCOUNT_IDS_FILE, "r") as f:
        data = json.load(f)
    data["deletion_requests"] = {
        "submitted_at": datetime.utcnow().isoformat(),
        "total_submitted": results["submitted"],
        "request_ids": results["request_ids"]
    }
    with open(ACCOUNT_IDS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"{Colors.CYAN}Request IDs salvos em: {ACCOUNT_IDS_FILE}{Colors.RESET}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--insert-only", action="store_true",
                        help="Apenas insere contas; delecao fica a cargo do JMeter")
    args = parser.parse_args()

    account_ids = bulk_insert(NUM_ACCOUNTS)
    if not args.insert_only:
        bulk_delete(account_ids)
