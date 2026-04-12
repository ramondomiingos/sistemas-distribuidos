#!/usr/bin/env python3
"""
Análise completa dos resultados do benchmark.

Seções geradas:
  1. Completude — completude_% e tempo de processamento por run, com stats agregadas
  2. Latência   — updated_at - created_at de todas as requisições FINISHED (via DB)
  3. Recursos   — CPU e memória a partir dos CSVs de docker stats, analisados por:
       • fase (repouso / pico / pos)
       • container
       • fase × container (tabela cruzada)
  4. Escalabilidade — speedup, efficiency e fit da Lei de Amdahl por n_servicos
  5. Análises Cruzadas — correlação CPU×latência, estabilidade de memória, net/block IO, CV

Saída: output-benchmark/benchmark_analysis.json  +  tabela no terminal.

Uso:
  python3 tools/analyze_results.py [--output-dir output-benchmark] [--skip-db]
"""

import argparse
import csv
import json
import math
import random
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Funções estatísticas (sem dependências externas)
# ---------------------------------------------------------------------------

def _percentile(data: list, p: float) -> float:
    s = sorted(data)
    n = len(s)
    if n == 1:
        return float(s[0])
    idx = (p / 100.0) * (n - 1)
    lo, hi = int(idx), int(idx) + 1
    frac = idx - lo
    return float(s[lo]) if hi >= n else float(s[lo]) + frac * (float(s[hi]) - float(s[lo]))


def _bootstrap_ci(data: list, n_boot: int = 2000, ci: float = 0.95) -> tuple:
    n = len(data)
    if n < 2:
        v = data[0] if n == 1 else 0.0
        return float(v), float(v)
    rng = random.Random(42)
    boots = sorted(sum(rng.choice(data) for _ in range(n)) / n for _ in range(n_boot))
    alpha = (1.0 - ci) / 2.0
    return boots[int(alpha * n_boot)], boots[min(int((1 - alpha) * n_boot), n_boot - 1)]


def compute_stats(data: list, higher_is_better: bool = True) -> dict:
    """Estatísticas descritivas completas."""
    n = len(data)
    if n == 0:
        return {}
    mean = sum(data) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in data) / (n - 1)) if n > 1 else 0.0
    p25, p50, p75 = _percentile(data, 25), _percentile(data, 50), _percentile(data, 75)
    p90, p95, p99 = _percentile(data, 90), _percentile(data, 95), _percentile(data, 99)
    ci_lo, ci_hi = _bootstrap_ci(data)
    if higher_is_better:
        best_idx, worst_idx = data.index(max(data)), data.index(min(data))
    else:
        best_idx, worst_idx = data.index(min(data)), data.index(max(data))
    return {
        "n": n,
        "mean": round(mean, 3), "std": round(std, 3),
        "median_p50": round(p50, 3),
        "p25": round(p25, 3), "p75": round(p75, 3), "iqr": round(p75 - p25, 3),
        "p90": round(p90, 3), "p95": round(p95, 3), "p99": round(p99, 3),
        "ci95_lo": round(ci_lo, 3), "ci95_hi": round(ci_hi, 3),
        "min": round(min(data), 3), "max": round(max(data), 3),
        "best_run": best_idx + 1, "worst_run": worst_idx + 1,
    }


def compute_stats_simple(data: list, higher_is_better: bool = False) -> dict:
    """Stats sem best/worst run (para dados de recursos sem indexação por run)."""
    s = compute_stats(data, higher_is_better)
    s.pop("best_run", None)
    s.pop("worst_run", None)
    return s


# ---------------------------------------------------------------------------
# Leitura e deduplicação de arquivos por run
# ---------------------------------------------------------------------------

def _latest_per_run(files: list, run_field: int) -> dict:
    """
    Dado uma lista de Paths com padrão *_run_N_timestamp.ext,
    retorna {run_n: Path} com o arquivo mais recente por run.
    """
    by_run: dict = defaultdict(list)
    for f in files:
        parts = f.stem.split("_")
        try:
            n = int(parts[run_field])
            by_run[n].append(f)
        except (IndexError, ValueError):
            pass
    return {n: sorted(paths)[-1] for n, paths in by_run.items()}


def load_completude_runs(output_dir: Path) -> list:
    """Carrega os JSONs de completude, um por run (mais recente se duplicados)."""
    files = list(output_dir.glob("completude_run_*.json"))
    if not files:
        print(f"AVISO: nenhum completude_run_*.json em {output_dir}/", file=sys.stderr)
        return []
    latest = _latest_per_run(files, run_field=2)
    runs = []
    for n in sorted(latest):
        with open(latest[n]) as fp:
            runs.append(json.load(fp))
    return runs


def load_run_timestamps(output_dir: Path) -> dict:
    """
    Lê benchmark_summary.csv e retorna {run_n: timestamp_inicio_str}.
    Ex: {1: '2026-04-06 10:43:53', 2: '2026-04-06 10:48:38', ...}
    """
    summary = output_dir / "benchmark_summary.csv"
    timestamps: dict = {}
    if not summary.exists():
        return timestamps
    for line in summary.read_text().strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            run_n = int(parts[0])
            ts = parts[1].strip()
            if ts:
                timestamps[run_n] = ts
        except (ValueError, IndexError):
            continue
    return timestamps


def load_tempos(output_dir: Path, runs: list) -> dict:
    """
    Lê benchmark_summary.csv e retorna {run_n: tempo_s}.

    Lida com o bug histórico onde completude e tempo foram fundidos numa
    única coluna (ex: '100.0178' = completude '100.0' + tempo '178').
    Usa os valores de completude dos JSONs para desambiguar.
    """
    summary = output_dir / "benchmark_summary.csv"
    tempos: dict = {}
    if not summary.exists():
        return tempos

    completude_by_run = {r["run"]: r["middleware"]["completude_pct"] for r in runs}

    for line in summary.read_text().strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) < 6:
            continue
        try:
            run_n = int(parts[0])
        except ValueError:
            continue

        # Formato correto: 7 colunas
        if len(parts) >= 7 and parts[6].strip():
            try:
                tempos[run_n] = float(parts[6])
                continue
            except ValueError:
                pass

        # Formato com bug: completude e tempo fundidos na coluna 5
        merged = parts[5].strip()
        completude = completude_by_run.get(run_n)
        if completude is not None:
            cstr = str(completude)          # ex: "100.0"
            if merged.startswith(cstr):
                remainder = merged[len(cstr):]
                if remainder.isdigit():
                    tempos[run_n] = float(remainder)

    return tempos


# ---------------------------------------------------------------------------
# Parse dos CSVs de recursos
# ---------------------------------------------------------------------------

def _parse_pct(s: str):
    try:
        return float(s.replace("%", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_mem_mib(s: str):
    """'75.2MiB / 1.5GiB' → 75.2 (MiB)"""
    try:
        usage = s.split("/")[0].strip()
        if "GiB" in usage:
            return float(usage.replace("GiB", "").strip()) * 1024
        if "MiB" in usage:
            return float(usage.replace("MiB", "").strip())
        if "KiB" in usage or "kB" in usage:
            return float(usage.replace("KiB", "").replace("kB", "").strip()) / 1024
        if "B" in usage:
            return float(usage.replace("B", "").strip()) / (1024 * 1024)
    except (ValueError, AttributeError):
        pass
    return None


def _parse_bytes_mb(s: str) -> tuple:
    """
    '10.3kB / 5.2MB' → (sent_mb, recv_mb) floats.
    Retorna (None, None) em caso de erro.
    """
    try:
        parts = s.split("/")
        if len(parts) != 2:
            return None, None

        def _to_mb(val: str) -> float:
            val = val.strip()
            for suffix, factor in [("GiB", 1024), ("GB", 1024),
                                    ("MiB", 1.0), ("MB", 1.0),
                                    ("KiB", 1/1024), ("kB", 1/1024), ("KB", 1/1024),
                                    ("B", 1/(1024*1024))]:
                if suffix in val:
                    return float(val.replace(suffix, "").strip()) * factor
            return float(val) / (1024 * 1024)

        return _to_mb(parts[0]), _to_mb(parts[1])
    except (ValueError, AttributeError):
        return None, None


def _short_name(container_name: str) -> str:
    """
    'sistemas-distribuidos-middleware-1' → 'middleware'
    'sistemas-distribuidos-middleware_db-1' → 'middleware_db'
    'kafka-ui' → 'kafka-ui'  (container_name override, sem réplica)
    """
    parts = container_name.split("-")
    if parts and parts[-1].isdigit():
        return parts[-2] if len(parts) >= 2 else container_name
    return container_name


def load_resource_records(output_dir: Path) -> list:
    """
    Lê todos benchmark_run_N_*.csv e retorna lista de dicts:
    {run, fase, container, short, cpu_pct, mem_mib, mem_pct}
    """
    files = list(output_dir.glob("benchmark_run_*.csv"))
    latest = _latest_per_run(files, run_field=2)
    records = []
    for run_n in sorted(latest):
        with open(latest[run_n], newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                cpu = _parse_pct(row.get("CPU_%", ""))
                mem = _parse_mem_mib(row.get("Mem_Usage", ""))
                mem_pct = _parse_pct(row.get("Mem_%", ""))
                fase = row.get("Fase", "").strip()
                name = row.get("Nome", "").strip()
                short = _short_name(name)
                if cpu is None or not name or not fase:
                    continue
                if short in IGNORE_CONTAINERS:
                    continue
                net_tx, net_rx = _parse_bytes_mb(row.get("Net_IO", ""))
                blk_r, blk_w = _parse_bytes_mb(row.get("Block_IO", ""))
                records.append({
                    "run": run_n,
                    "fase": fase,
                    "container": name,
                    "short": short,
                    "cpu_pct": cpu,
                    "mem_mib": mem,
                    "mem_pct": mem_pct,
                    "net_tx_mb": net_tx,
                    "net_rx_mb": net_rx,
                    "blk_read_mb": blk_r,
                    "blk_write_mb": blk_w,
                })
    return records


# ---------------------------------------------------------------------------
# Análise de recursos
# ---------------------------------------------------------------------------

FASE_ORDER = ["repouso", "pico", "pos"]

# Containers complementares — excluídos das análises de recursos
IGNORE_CONTAINERS = {"otel", "zookeeper", "kafka-ui"}


def analyze_resources(records: list) -> dict:
    """
    Retorna:
      by_phase              : {fase → {cpu_pct: stats, mem_mib: stats}}
      by_container          : {short → {cpu_pct: stats, mem_mib: stats}}
      by_phase_x_container  : {fase → {short → {cpu_pct: stats, mem_mib: stats}}}
    Todos os stats são sobre TODOS os runs (amostras brutas de 1 s/sample).
    """
    phase_cpu: dict = defaultdict(list)
    phase_mem: dict = defaultdict(list)
    cont_cpu: dict = defaultdict(list)
    cont_mem: dict = defaultdict(list)
    px_cpu: dict = defaultdict(lambda: defaultdict(list))
    px_mem: dict = defaultdict(lambda: defaultdict(list))

    for r in records:
        f, s, cpu, mem = r["fase"], r["short"], r["cpu_pct"], r["mem_mib"]
        phase_cpu[f].append(cpu)
        cont_cpu[s].append(cpu)
        px_cpu[f][s].append(cpu)
        if mem is not None:
            phase_mem[f].append(mem)
            cont_mem[s].append(mem)
            px_mem[f][s].append(mem)

    def _s(d, key):
        return compute_stats_simple(d[key]) if d[key] else {}

    by_phase = {
        f: {
            "cpu_pct": _s(phase_cpu, f),
            **({"mem_mib": _s(phase_mem, f)} if phase_mem[f] else {}),
        }
        for f in phase_cpu
    }

    by_container = {
        s: {
            "cpu_pct": compute_stats_simple(cont_cpu[s]),
            **({"mem_mib": compute_stats_simple(cont_mem[s])} if cont_mem[s] else {}),
        }
        for s in sorted(cont_cpu)
    }

    by_phase_x_container = {
        f: {
            s: {
                "cpu_pct": compute_stats_simple(px_cpu[f][s]),
                **({"mem_mib": compute_stats_simple(px_mem[f][s])} if px_mem[f][s] else {}),
            }
            for s in sorted(px_cpu[f])
        }
        for f in px_cpu
    }

    return {
        "by_phase": by_phase,
        "by_container": by_container,
        "by_phase_x_container": by_phase_x_container,
    }


# ---------------------------------------------------------------------------
# Latência via banco (docker compose exec)
# ---------------------------------------------------------------------------

def fetch_latencies_from_db(min_ts: str = None):
    """
    Consulta o middleware_db e retorna lista de latências (segundos) das
    requisições com status='FINISHED'.

    min_ts: filtro opcional 'YYYY-MM-DD HH:MM:SS' (UTC).
    Deve ser passado como o início do primeiro run do benchmark principal para
    excluir requests do experimento de escalabilidade e dados de testes anteriores.
    Sem esse filtro, todas as requisições FINISHED do banco são retornadas —
    incluindo as ~10.800 do experimento de escalabilidade, o que tornaria a
    latência global incomparável com as estatísticas segmentadas por run.
    """
    where = "status='FINISHED'"
    if min_ts:
        where += f" AND created_at >= '{min_ts}'"
    try:
        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T", "middleware_db",
                "psql", "-U", "user", "-d", "middlewaredb", "-t", "-A", "-c",
                f"SELECT EXTRACT(EPOCH FROM (updated_at - created_at))::numeric(10,3) "
                f"FROM privacy_requests WHERE {where};",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        latencies = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    latencies.append(float(line))
                except ValueError:
                    pass
        return latencies or None
    except Exception:
        return None


def fetch_latencies_per_run(run_timestamps: dict):
    """
    Retorna {run_n: [latencia_s, ...]} usando os timestamps de início de cada run
    para segmentar as requisições do banco.

    Estratégia: uma única query que traz created_at + latência de todos os
    registros FINISHED criados a partir do primeiro run; a atribuição ao run
    é feita em Python por faixa de tempo.
    """
    if not run_timestamps:
        return None

    sorted_runs = sorted(run_timestamps.keys())
    first_ts = run_timestamps[sorted_runs[0]]

    try:
        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T", "middleware_db",
                "psql", "-U", "user", "-d", "middlewaredb", "-t", "-A", "-c",
                "SELECT created_at::text, "
                "EXTRACT(EPOCH FROM (updated_at - created_at))::numeric(10,3) "
                "FROM privacy_requests "
                "WHERE status='FINISHED' AND created_at >= '" + first_ts + "' "
                "ORDER BY created_at;",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None
    except Exception:
        return None

    # Monta lista de (created_at_str, latency) e atribui ao run por faixa
    # Precisamos dos limites: run N vai de timestamps[N] até timestamps[N+1]
    from datetime import datetime as _dt
    fmt = "%Y-%m-%d %H:%M:%S"

    boundaries = []
    for n in sorted_runs:
        boundaries.append((_dt.strptime(run_timestamps[n], fmt), n))

    per_run = {n: [] for n in sorted_runs}

    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts_row = line.split("|")
        if len(parts_row) < 2:
            continue
        try:
            # created_at pode vir como '2026-04-06 10:43:53.123456'
            ts_str = parts_row[0].strip()[:19]
            row_ts = _dt.strptime(ts_str, fmt)
            lat = float(parts_row[1].strip())
        except (ValueError, IndexError):
            continue

        # Encontra o run: maior boundary <= row_ts
        assigned = None
        for boundary_ts, run_n in boundaries:
            if row_ts >= boundary_ts:
                assigned = run_n
            else:
                break
        if assigned is not None:
            per_run[assigned].append(lat)

    # Remove runs sem dados
    per_run = {k: v for k, v in per_run.items() if v}
    return per_run if per_run else None


def load_submission_order(output_dir: Path) -> dict:
    """
    Lê account_ids_run_N_*.json e retorna {run_n: [request_id_em_ordem]}.
    Posição 0 = primeira requisição enviada, posição N-1 = última.
    """
    files = list(output_dir.glob("account_ids_run_*.json"))
    latest = _latest_per_run(files, run_field=3)  # account_ids_run_<N>_<ts>.json
    result = {}
    for run_n in sorted(latest):
        try:
            with open(latest[run_n]) as fp:
                data = json.load(fp)
            req_ids = data.get("deletion_requests", {}).get("request_ids", [])
            if req_ids:
                result[run_n] = req_ids
        except Exception:
            continue
    return result


def fetch_latency_by_position(submission_order: dict):
    """
    Para cada run, consulta a latência de cada request_id no banco e associa
    à posição de submissão (1-indexed).

    Retorna {run_n: [(position, latency_s), ...]} — apenas posições com dado.
    """
    if not submission_order:
        return None

    # Coleta todos os IDs únicos para uma única query
    all_ids = []
    id_to_run_pos = {}  # request_id → (run_n, position_1indexed)
    for run_n, ids in submission_order.items():
        for pos, rid in enumerate(ids, start=1):
            if rid:
                all_ids.append(rid)
                id_to_run_pos[rid] = (run_n, pos)

    if not all_ids:
        return None

    ids_sql = ", ".join(f"'{rid}'" for rid in all_ids)
    query = (
        "SELECT id::text, EXTRACT(EPOCH FROM (updated_at - created_at))::numeric(10,3) "
        "FROM privacy_requests "
        "WHERE status='FINISHED' AND id IN (" + ids_sql + ");"
    )

    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "middleware_db",
             "psql", "-U", "user", "-d", "middlewaredb", "-t", "-A", "-c", query],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None
    except Exception:
        return None

    per_run = {rn: [] for rn in submission_order}
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts_row = line.split("|")
        if len(parts_row) < 2:
            continue
        try:
            rid = parts_row[0].strip()
            lat = float(parts_row[1].strip())
        except (ValueError, IndexError):
            continue
        if rid in id_to_run_pos:
            run_n, pos = id_to_run_pos[rid]
            per_run[run_n].append((pos, lat))

    # Ordena por posição e remove runs vazios
    for rn in per_run:
        per_run[rn].sort(key=lambda x: x[0])
    per_run = {k: v for k, v in per_run.items() if v}
    return per_run if per_run else None


# ---------------------------------------------------------------------------
# Escalabilidade
# ---------------------------------------------------------------------------

def load_scalability_summary(output_dir: Path) -> list:
    """
    Lê output-benchmark/scalability/scalability_summary.csv.
    Retorna lista de dicts com n_servicos, run, tempo_processamento_s, completude_pct, etc.
    """
    summary = output_dir / "scalability" / "scalability_summary.csv"
    if not summary.exists():
        return []
    rows = []
    for line in summary.read_text().strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) < 9:
            continue
        try:
            rows.append({
                "n_servicos":          int(parts[0]),
                "servicos":            parts[1].strip(),
                "run":                 int(parts[2]),
                "timestamp_inicio":    parts[3].strip(),
                "total_submetido":     int(parts[4]),
                "total_finished":      int(parts[5]),
                "total_erro":          int(parts[6]),
                "completude_pct":      float(parts[7]),
                "tempo_processamento_s": float(parts[8]),
            })
        except (ValueError, IndexError):
            continue
    return rows


def _pearson(xs: list, ys: list) -> float:
    """Coeficiente de correlação de Pearson."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den > 0 else 0.0


def _fit_amdahl(n_list: list, t_list: list) -> float:
    """
    Ajusta a Lei de Amdahl: T(n) = T(1) × (p + (1−p)/n).
    Retorna p_serial (fração serial, 0..1) que minimiza o erro quadrático.
    """
    t1 = t_list[0] if t_list else 1.0
    best_p, best_err = 0.5, float("inf")
    for trial in range(0, 1001):
        p = trial / 1000.0
        err = sum((t1 * (p + (1 - p) / n) - t) ** 2 for n, t in zip(n_list, t_list))
        if err < best_err:
            best_err, best_p = err, p
    return best_p


def analyze_scalability(scale_data: list) -> dict:
    """
    Dado output de load_scalability_summary(), calcula:
      - Média/std de tempo e completude por n_servicos
      - Speedup(n) = T_mean(1) / T_mean(n)
      - Efficiency(n) = speedup(n) / n
      - Throughput médio: total_submetido / tempo_s
      - Fit da Lei de Amdahl (p_serial)
    """
    from collections import defaultdict
    by_n: dict = defaultdict(list)
    for row in scale_data:
        by_n[row["n_servicos"]].append(row)

    per_n = {}
    for n in sorted(by_n):
        rows = by_n[n]
        tempos = [r["tempo_processamento_s"] for r in rows]
        comps  = [r["completude_pct"] for r in rows]
        total  = rows[0]["total_submetido"]
        thrput = [total / t for t in tempos if t > 0]
        per_n[n] = {
            "runs": len(rows),
            "tempo_mean": round(sum(tempos) / len(tempos), 2),
            "tempo_std":  round(math.sqrt(sum((t - sum(tempos)/len(tempos))**2 for t in tempos) / max(len(tempos)-1,1)), 2),
            "tempo_min":  round(min(tempos), 2),
            "tempo_max":  round(max(tempos), 2),
            "completude_mean": round(sum(comps) / len(comps), 2),
            "completude_min":  round(min(comps), 2),
            "throughput_mean": round(sum(thrput) / len(thrput), 3) if thrput else 0,
        }

    # Speedup e Efficiency
    t1 = per_n.get(1, {}).get("tempo_mean", 1.0)
    for n in per_n:
        tn = per_n[n]["tempo_mean"]
        sp = round(t1 / tn, 3) if tn > 0 else 0
        per_n[n]["speedup"]    = sp
        per_n[n]["efficiency"] = round(sp / n, 3)

    # Amdahl
    ns = sorted(per_n)
    ts = [per_n[n]["tempo_mean"] for n in ns]
    p_serial = _fit_amdahl(ns, ts) if len(ns) >= 2 else None

    # Speedup teórico Amdahl
    amdahl_theoretical = {}
    if p_serial is not None:
        for n in ns:
            sp_th = round(1.0 / (p_serial + (1 - p_serial) / n), 3)
            amdahl_theoretical[n] = sp_th

    return {
        "per_n_servicos": per_n,
        "amdahl_p_serial": round(p_serial, 4) if p_serial is not None else None,
        "amdahl_theoretical_speedup": amdahl_theoretical,
        "raw": scale_data,
    }


# ---------------------------------------------------------------------------
# Análises cruzadas
# ---------------------------------------------------------------------------

def analyze_cross_metrics(records: list, lat_per_run: dict, result: dict) -> dict:
    """
    Retorna dict com:
      correlacao_cpu_latencia: correlação Pearson entre CPU_pico_middleware e latência p99 por run
      memoria_estabilidade:   mem_mib do middleware no repouso por run (leak detection)
      cv_metricas:            coeficiente de variação das métricas principais
      net_io_kafka:           max net_io (tx+rx MB) do kafka por run
      blk_io_dbs:             max block_write_mb por DB container por run
    """
    from collections import defaultdict

    # --- CPU pico do middleware por run ---
    cpu_mw_pico: dict = defaultdict(list)
    mem_mw_repouso: dict = defaultdict(list)
    net_kafka: dict = defaultdict(list)
    blk_dbs: dict = defaultdict(lambda: defaultdict(list))

    for r in records:
        run = r["run"]
        s   = r["short"]
        f   = r["fase"]
        if s == "middleware" and f == "pico":
            cpu_mw_pico[run].append(r["cpu_pct"])
        if s == "middleware" and f == "repouso":
            if r["mem_mib"] is not None:
                mem_mw_repouso[run].append(r["mem_mib"])
        if s == "kafka":
            tx = r.get("net_tx_mb")
            rx = r.get("net_rx_mb")
            if tx is not None and rx is not None:
                net_kafka[run].append(tx + rx)
        if s in ("middleware_db", "accounts_db", "payments_db", "crm_db", "delivery_db"):
            bw = r.get("blk_write_mb")
            if bw is not None:
                blk_dbs[s][run].append(bw)

    # --- Correlação CPU × Latência p99 ---
    cpu_list, lat_list, run_pairs = [], [], []
    for run_n in sorted(cpu_mw_pico):
        if run_n not in (lat_per_run or {}):
            continue
        cpu_mean = sum(cpu_mw_pico[run_n]) / len(cpu_mw_pico[run_n])
        lat_p99  = lat_per_run[run_n].get("p99")
        if lat_p99 is not None:
            cpu_list.append(cpu_mean)
            lat_list.append(float(lat_p99))
            run_pairs.append({"run": run_n, "cpu_pico_mean": round(cpu_mean, 3), "lat_p99": float(lat_p99)})

    pearson_r = _pearson(cpu_list, lat_list) if len(cpu_list) >= 2 else None

    # --- Estabilidade de memória do middleware (repouso) ---
    mem_estabilidade = []
    for run_n in sorted(mem_mw_repouso):
        vals = mem_mw_repouso[run_n]
        mem_estabilidade.append({
            "run": run_n,
            "mem_mean_mib": round(sum(vals) / len(vals), 2),
            "mem_max_mib":  round(max(vals), 2),
        })

    # Trend: diferença entre último e primeiro run
    if len(mem_estabilidade) >= 2:
        delta_mem = mem_estabilidade[-1]["mem_mean_mib"] - mem_estabilidade[0]["mem_mean_mib"]
    else:
        delta_mem = None

    # --- Net IO Kafka ---
    kafka_io = []
    for run_n in sorted(net_kafka):
        vals = net_kafka[run_n]
        kafka_io.append({"run": run_n, "net_total_max_mb": round(max(vals), 3)})

    # --- Block IO por DB ---
    blk_io_dbs = {}
    for sname in sorted(blk_dbs):
        blk_io_dbs[sname] = []
        for run_n in sorted(blk_dbs[sname]):
            vals = blk_dbs[sname][run_n]
            blk_io_dbs[sname].append({"run": run_n, "blk_write_max_mb": round(max(vals), 3)})

    # --- CV das métricas principais ---
    cv_metricas = {}
    for key, label in [
        ("completude", "completude_pct"),
        ("completude", "tempo"),
    ]:
        pass  # calculado abaixo via result

    # Completude CV
    comp_vals = [r.get("completude_pct", 0) for r in result.get("completude", {}).get("per_run", [])]
    tempo_vals = [r.get("tempo_processamento_s", 0) for r in result.get("completude", {}).get("per_run", []) if "tempo_processamento_s" in r]

    def _cv(vals):
        if len(vals) < 2:
            return None
        m = sum(vals) / len(vals)
        if m == 0:
            return None
        s = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
        return round(s / m * 100, 3)

    cv_metricas["completude_pct"] = _cv(comp_vals)
    cv_metricas["tempo_processamento_s"] = _cv(tempo_vals)

    if lat_per_run:
        lat_means = [lat_per_run[r].get("mean", 0) for r in sorted(lat_per_run) if isinstance(lat_per_run[r], dict)]
        lat_p99s  = [lat_per_run[r].get("p99", 0) for r in sorted(lat_per_run) if isinstance(lat_per_run[r], dict)]
        cv_metricas["latencia_mean"] = _cv(lat_means)
        cv_metricas["latencia_p99"]  = _cv(lat_p99s)

    if cpu_list:
        cv_metricas["cpu_pico_middleware"] = _cv(cpu_list)

    return {
        "correlacao_cpu_latencia": {
            "pearson_r": round(pearson_r, 4) if pearson_r is not None else None,
            "interpretacao": (
                "forte positiva" if pearson_r and pearson_r > 0.7 else
                "moderada positiva" if pearson_r and pearson_r > 0.4 else
                "fraca" if pearson_r and abs(pearson_r) <= 0.4 else
                "moderada negativa" if pearson_r and pearson_r > -0.7 else
                "forte negativa"
            ) if pearson_r is not None else None,
            "por_run": run_pairs,
        },
        "memoria_estabilidade": {
            "por_run": mem_estabilidade,
            "delta_run1_run10_mib": round(delta_mem, 2) if delta_mem is not None else None,
            "tendencia": (
                "crescente (possível leak)" if delta_mem and delta_mem > 5 else
                "estavel" if delta_mem is not None and abs(delta_mem) <= 5 else
                "decrescente"
            ) if delta_mem is not None else None,
        },
        "net_io_kafka": kafka_io,
        "blk_io_dbs": blk_io_dbs,
        "cv_metricas": cv_metricas,
    }


# ---------------------------------------------------------------------------
# Impressão formatada
# ---------------------------------------------------------------------------

def _fmt(v) -> str:
    return f"{v:.2f}" if isinstance(v, float) else str(v)


def print_stats_block(label: str, s: dict, indent: int = 4, unit: str = "") -> None:
    pad = " " * indent
    u = f" {unit}" if unit else ""
    print(f"{pad}{label}:")
    print(f"{pad}  n={s['n']}   média={s['mean']}{u} ± {s['std']}{u}")
    print(f"{pad}  mediana(p50)={s['median_p50']}{u}   IQR=[{s['p25']}, {s['p75']}]{u}  ({s['iqr']}{u})")
    print(f"{pad}  p90={s['p90']}{u}   p95={s['p95']}{u}   p99={s['p99']}{u}")
    print(f"{pad}  IC 95% bootstrap = [{s['ci95_lo']}, {s['ci95_hi']}]{u}")
    best = s.get("best_run")
    worst = s.get("worst_run")
    suffix = f"   melhor=run{best}  pior=run{worst}" if best and worst else ""
    print(f"{pad}  min={s['min']}{u}   max={s['max']}{u}{suffix}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Análise completa do benchmark.")
    parser.add_argument("--output-dir", default="output-benchmark")
    parser.add_argument(
        "--skip-db", action="store_true",
        help="Não consulta o banco para latências (use se Docker não estiver rodando)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"ERRO: diretório '{output_dir}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    result: dict = {"generated_at": datetime.now().isoformat(timespec="seconds")}

    # ------------------------------------------------------------------
    # 1. Completude
    # ------------------------------------------------------------------
    runs = load_completude_runs(output_dir)
    tempos_map = load_tempos(output_dir, runs)
    run_timestamps = load_run_timestamps(output_dir)

    if runs:
        completudes = [r["middleware"]["completude_pct"] for r in runs]
        run_numbers = [r["run"] for r in runs]
        tempos = [tempos_map[n] for n in run_numbers if n in tempos_map]

        per_run = []
        for r in runs:
            entry = {
                "run": r["run"],
                "completude_pct": r["middleware"]["completude_pct"],
                "finished": r["middleware"]["finished"],
                "total": r["middleware"]["total_submetido"],
                "erros": r["middleware"]["erros"],
                "registros_restantes": r.get("registros_restantes_por_servico", {}),
            }
            if r["run"] in tempos_map:
                entry["tempo_processamento_s"] = tempos_map[r["run"]]
            per_run.append(entry)

        result["completude"] = {
            "total_runs": len(runs),
            "stats_completude_pct": compute_stats(completudes, higher_is_better=True),
            "per_run": per_run,
        }
        if tempos:
            result["completude"]["stats_tempo_processamento_s"] = compute_stats(
                tempos, higher_is_better=False
            )

    # ------------------------------------------------------------------
    # 2. Latência das requisições (DB)
    # ------------------------------------------------------------------
    if not args.skip_db:
        # Filtra apenas as requests do benchmark principal (exclui experimento de
        # escalabilidade e dados anteriores). Usa o timestamp do run 1 como limite.
        latencia_min_ts = run_timestamps.get(min(run_timestamps)) if run_timestamps else None
        print("\n  [latência] Consultando banco de dados...", end="", flush=True)
        latencies = fetch_latencies_from_db(min_ts=latencia_min_ts)
        if latencies:
            print(f" {len(latencies)} requisições FINISHED.")
            result["latencia_requests_s"] = compute_stats(latencies, higher_is_better=False)
        else:
            print(" não foi possível conectar (use --skip-db para ignorar).")

        if run_timestamps:
            print("  [latência/run] Segmentando por run...", end="", flush=True)
            lat_per_run = fetch_latencies_per_run(run_timestamps)
            if lat_per_run:
                print(f" {len(lat_per_run)} runs encontrados.")
                per_run_stats = {}
                for rn, lats in sorted(lat_per_run.items()):
                    per_run_stats[rn] = compute_stats(lats, higher_is_better=False)
                result["latencia_por_run"] = per_run_stats
            else:
                print(" falhou.")

        submission_order = load_submission_order(output_dir)
        if submission_order:
            print("  [latência/posição] Consultando latência por posição de submissão...", end="", flush=True)
            pos_data = fetch_latency_by_position(submission_order)
            if pos_data:
                total_pts = sum(len(v) for v in pos_data.values())
                print(f" {total_pts} pontos em {len(pos_data)} runs.")
                # Resumo: média de latência por bin de 100 posições (agregado entre runs)
                bin_size = 100
                bins = defaultdict(list)
                for rn, pairs in pos_data.items():
                    for pos, lat in pairs:
                        b = ((pos - 1) // bin_size) * bin_size + 1  # 1, 101, 201, ...
                        bins[b].append(lat)
                bin_summary = {
                    b: {"mean": round(sum(v) / len(v), 3), "n": len(v)}
                    for b, v in sorted(bins.items())
                }
                # Dados brutos por run (amostra: a cada 10 posições para não inflar o JSON)
                sampled = {}
                for rn, pairs in pos_data.items():
                    sampled[rn] = [(pos, lat) for pos, lat in pairs if pos % 10 == 1 or pos == len(pairs)]
                result["latencia_posicao"] = {
                    "bin_summary": bin_summary,
                    "por_run_amostrado": sampled,
                }
            else:
                print(" dados não disponíveis (rode após o benchmark).")

    # ------------------------------------------------------------------
    # 3. Recursos (CSVs)
    # ------------------------------------------------------------------
    print("  [recursos] Carregando CSVs...", end="", flush=True)
    records = load_resource_records(output_dir)
    if records:
        print(f" {len(records)} amostras de {len({r['run'] for r in records})} runs.")
        result["recursos"] = analyze_resources(records)
    else:
        print(" nenhum CSV encontrado.")

    # ------------------------------------------------------------------
    # 4. Escalabilidade
    # ------------------------------------------------------------------
    print("  [escalabilidade] Carregando scalability_summary.csv...", end="", flush=True)
    scale_data = load_scalability_summary(output_dir)
    if scale_data:
        print(f" {len(scale_data)} runs de escalabilidade.")
        result["escalabilidade"] = analyze_scalability(scale_data)
    else:
        print(" não encontrado.")

    # ------------------------------------------------------------------
    # 5. Análises cruzadas
    # ------------------------------------------------------------------
    if records:
        print("  [cruzado] Calculando análises cruzadas...", end="", flush=True)
        lat_pr_for_cross = result.get("latencia_por_run", {})
        result["analises_cruzadas"] = analyze_cross_metrics(records, lat_pr_for_cross, result)
        print(" OK.")

    # ------------------------------------------------------------------
    # Grava JSON
    # ------------------------------------------------------------------
    out_file = output_dir / "benchmark_analysis.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Impressão
    # ------------------------------------------------------------------
    W = 68
    print("\n" + "=" * W)
    print("  ANÁLISE COMPLETA DO BENCHMARK")
    print("=" * W)

    # --- Completude ---
    if "completude" in result:
        c = result["completude"]
        print(f"\n{'─'*W}")
        print(f"  COMPLETUDE  ({c['total_runs']} execuções)")
        print(f"{'─'*W}")
        print_stats_block("completude_%", c["stats_completude_pct"], unit="%")
        if "stats_tempo_processamento_s" in c:
            print_stats_block("tempo_processamento", c["stats_tempo_processamento_s"], unit="s")
        print("\n  Por execução:")
        for r in c["per_run"]:
            t = f"  tempo={r.get('tempo_processamento_s','?')}s" if "tempo_processamento_s" in r else ""
            print(
                f"    run {r['run']:>2}: completude={r['completude_pct']:6.2f}%  "
                f"finished={r['finished']}/{r['total']}  erros={r['erros']}{t}"
            )

    # --- Latência ---
    if "latencia_requests_s" in result:
        print(f"\n{'─'*W}")
        print("  LATÊNCIA DAS REQUISIÇÕES  (created_at → updated_at, status=FINISHED)")
        print(f"{'─'*W}")
        print_stats_block("segundos", result["latencia_requests_s"], unit="s")

    if "latencia_por_run" in result:
        print(f"\n  Por execução:")
        print(f"  {'run':>4}  {'n':>5}  {'média':>8}  {'p50':>8}  {'p90':>8}  {'p95':>8}  {'p99':>8}  {'max':>8}")
        for rn, s in sorted(result["latencia_por_run"].items()):
            print(
                f"  run{rn:>2}  {s['n']:>5}  {s['mean']:>7.2f}s  "
                f"{s['median_p50']:>7.2f}s  {s['p90']:>7.2f}s  "
                f"{s['p95']:>7.2f}s  {s['p99']:>7.2f}s  {s['max']:>7.2f}s"
            )

    # --- Recursos ---
    if "recursos" in result:
        res = result["recursos"]

        # CPU por fase
        print(f"\n{'─'*W}")
        print("  CPU % — POR FASE  (todos os containers, todos os runs)")
        print(f"{'─'*W}")
        print(f"  {'Fase':<10}  {'média':>7}  {'mediana':>8}  {'p90':>7}  {'p95':>7}  {'p99':>7}  {'IQR':>12}")
        for fase in FASE_ORDER:
            s = res["by_phase"].get(fase, {}).get("cpu_pct", {})
            if not s:
                continue
            print(
                f"  {fase:<10}  {s['mean']:>6.2f}%  {s['median_p50']:>7.2f}%  "
                f"{s['p90']:>6.2f}%  {s['p95']:>6.2f}%  {s['p99']:>6.2f}%  "
                f"[{s['p25']:.2f}, {s['p75']:.2f}]"
            )

        # CPU por container (todas as fases)
        print(f"\n{'─'*W}")
        print("  CPU % — POR CONTAINER  (todas as fases, todos os runs)")
        print(f"{'─'*W}")
        print(f"  {'Container':<25}  {'média':>7}  {'mediana':>8}  {'p95':>7}  {'max':>7}")
        for sname, data in res["by_container"].items():
            s = data.get("cpu_pct", {})
            if not s:
                continue
            print(
                f"  {sname:<25}  {s['mean']:>6.2f}%  {s['median_p50']:>7.2f}%  "
                f"{s['p95']:>6.2f}%  {s['max']:>6.2f}%"
            )

        # Memória por container
        print(f"\n{'─'*W}")
        print("  MEMÓRIA (MiB) — POR CONTAINER  (todas as fases, todos os runs)")
        print(f"{'─'*W}")
        print(f"  {'Container':<25}  {'média':>8}  {'mediana':>9}  {'p95':>8}  {'max':>8}")
        for sname, data in res["by_container"].items():
            s = data.get("mem_mib", {})
            if not s:
                continue
            print(
                f"  {sname:<25}  {s['mean']:>7.1f}   {s['median_p50']:>8.1f}   "
                f"{s['p95']:>7.1f}   {s['max']:>7.1f}"
            )

        # Tabela cruzada CPU: fase × container
        all_containers = sorted({
            sname
            for fase in res["by_phase_x_container"]
            for sname in res["by_phase_x_container"][fase]
        })
        print(f"\n{'─'*W}")
        print("  CPU % — TABELA FASE × CONTAINER  (média | p95)")
        print(f"{'─'*W}")
        col_w = 17
        header = f"  {'Container':<25}"
        for fase in FASE_ORDER:
            header += f"  {fase:^{col_w}}"
        print(header)
        subheader = f"  {'':<25}"
        for _ in FASE_ORDER:
            subheader += f"  {'média':>7}  {'p95':>7}  "
        print(subheader)
        for sname in all_containers:
            row = f"  {sname:<25}"
            for fase in FASE_ORDER:
                s = res["by_phase_x_container"].get(fase, {}).get(sname, {}).get("cpu_pct", {})
                mean_s = f"{s.get('mean', 0.0):>6.2f}%" if s else "    N/A"
                p95_s = f"{s.get('p95', 0.0):>6.2f}%" if s else "    N/A"
                row += f"  {mean_s}  {p95_s}  "
            print(row)

        # Tabela cruzada Memória: fase × container
        print(f"\n{'─'*W}")
        print("  MEMÓRIA MiB — TABELA FASE × CONTAINER  (média | max)")
        print(f"{'─'*W}")
        header = f"  {'Container':<25}"
        for fase in FASE_ORDER:
            header += f"  {fase:^{col_w}}"
        print(header)
        subheader = f"  {'':<25}"
        for _ in FASE_ORDER:
            subheader += f"  {'média':>7}  {'max':>7}  "
        print(subheader)
        for sname in all_containers:
            row = f"  {sname:<25}"
            for fase in FASE_ORDER:
                s = res["by_phase_x_container"].get(fase, {}).get(sname, {}).get("mem_mib", {})
                mean_s = f"{s.get('mean', 0.0):>6.1f}" if s else "    N/A"
                max_s = f"{s.get('max', 0.0):>6.1f}" if s else "    N/A"
                row += f"  {mean_s}  {max_s}  "
            print(row)

    print(f"\n  Resultados salvos em: {out_file}")
    print("=" * W + "\n")


if __name__ == "__main__":
    main()
