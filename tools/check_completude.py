#!/usr/bin/env python3
"""
Aguarda o middleware processar todas as requisições do run atual
e calcula a completude de deleção em cada microsserviço.
Usa `docker compose exec` para consultar os bancos (sem psql no host).
"""
import argparse
import json
import subprocess
import time


def psql(container: str, db: str, query: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", container,
         "psql", "-U", "user", "-d", db, "-t", "-c", query],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def wait_finished(request_ids: list, timeout: int = 300) -> tuple:
    """Aguarda até todas as requisições do run ficarem FINISHED."""
    total = len(request_ids)
    if total == 0:
        return 0, 0
    ids_sql = ", ".join(f"'{i}'" for i in request_ids)
    waited = 0
    finished = 0
    while waited < timeout:
        finished = int(psql(
            "middleware_db", "middlewaredb",
            f"SELECT COUNT(*) FROM privacy_requests WHERE status='FINISHED' AND id = ANY(ARRAY[{ids_sql}]::text[]);"
        ) or 0)
        print(f"    FINISHED={finished} / TOTAL={total} ({waited}s)")
        if finished == total:
            break
        time.sleep(5)
        waited += 5
    return finished, total


def count_remaining(container: str, db: str, table: str, col: str, ids: list) -> int:
    """Conta registros que ainda existem no microsserviço (deveriam ter sido deletados)."""
    if not ids:
        return -1
    ids_sql = ", ".join(f"'{i}'" for i in ids)
    result = psql(container, db, f"SELECT COUNT(*) FROM {table} WHERE {col} = ANY(ARRAY[{ids_sql}]::text[]);")
    return int(result or 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--account-ids", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ts-inicio", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    with open(args.account_ids) as f:
        data_ids = json.load(f)
    account_ids = data_ids.get("account_ids", [])
    request_ids = [r for r in data_ids.get("deletion_requests", {}).get("request_ids", []) if r]

    print("  [completude] Aguardando processamento finalizar...")
    finished, total = wait_finished(request_ids)
    errors = total - finished
    completude = round(finished / total * 100, 2) if total > 0 else 0.0

    print("  [completude] Verificando registros nos microsserviços...")
    remaining = {
        "accounts_users":       count_remaining("accounts_db",  "accounts_db",  "users",      "account_id", account_ids),
        "payments_orders":      count_remaining("payments_db",  "payments_db",  "orders",     "account_id", account_ids),
        "crm_user_info":        count_remaining("crm_db",       "crm_db",       "user_info",  "account_id", account_ids),
        "delivery_deliveries":  count_remaining("delivery_db",  "delivery_db",  "deliveries", "customer_id", account_ids),
    }

    data = {
        "run": args.run,
        "timestamp_inicio": args.ts_inicio,
        "middleware": {
            "total_submetido": total,
            "finished": finished,
            "erros": errors,
            "completude_pct": completude,
        },
        "registros_restantes_por_servico": remaining,
        "nota": "registros_restantes = 0 indica delecao 100% bem-sucedida no microsservico",
    }

    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
    print(json.dumps(data, indent=2))

    # Append ao summary CSV
    with open(args.summary, "a") as f:
        f.write(f"{args.run},{args.ts_inicio},{total},{finished},{errors},{completude},\n")


if __name__ == "__main__":
    main()
