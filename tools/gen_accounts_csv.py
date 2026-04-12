#!/usr/bin/env python3
"""
Converte account_ids.json para CSV legível pelo JMeter (CSVDataSet).

O JMeter lê o CSV linha a linha, atribuindo cada account_id a uma thread.
Com 900 linhas e 900 threads (1 loop cada), cada thread recebe exatamente
um account_id único — garantindo que as requisições de exclusão correspondem
a dados reais pré-inseridos nos microsserviços.
"""

import json
import csv
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="tools/account_ids.json", dest="json_path")
    parser.add_argument("--csv",  default="tools/accounts_for_jmeter.csv", dest="csv_path")
    args = parser.parse_args()

    if not os.path.exists(args.json_path):
        print(f"ERRO: {args.json_path} não encontrado.", file=sys.stderr)
        sys.exit(1)

    with open(args.json_path) as f:
        data = json.load(f)

    account_ids = data.get("account_ids", [])
    if not account_ids:
        print("ERRO: lista account_ids vazia no JSON.", file=sys.stderr)
        sys.exit(1)

    with open(args.csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["account_id"])
        for aid in account_ids:
            writer.writerow([aid])

    print(f"  [jmeter] CSV gerado: {args.csv_path} ({len(account_ids)} account_ids)")


if __name__ == "__main__":
    main()
