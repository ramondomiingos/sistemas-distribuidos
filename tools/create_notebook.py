#!/usr/bin/env python3
"""
Gera output-benchmark/analise_benchmark.ipynb com todas as análises do benchmark.

Uso:
    python tools/create_notebook.py
    jupyter notebook output-benchmark/analise_benchmark.ipynb
"""

import json, os, sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Células do notebook
# ---------------------------------------------------------------------------

CELLS = []

def md(source: str):
    CELLS.append({"cell_type": "markdown", "metadata": {}, "source": source.strip()})

def code(source: str):
    CELLS.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip(),
    })

# ===========================================================================
# CABEÇALHO
# ===========================================================================

md("""
# Análise do Benchmark — Middleware LGPD 2PC
**Dissertação de Mestrado · Ramon Domingos · UFRN 2026**

Este notebook analisa todos os dados gerados pelo `tools/benchmark.sh`:
- **Benchmark principal** — 20 runs × 900 requisições (4 serviços)
- **Experimento de escalabilidade** — 80 runs × 4 configurações (1→4 serviços)
- **Latência 2PC** — extraída do banco de dados exportado
- **Latência HTTP de submissão** — extraída dos arquivos JTL do JMeter
- **Análises cruzadas** — correlações, estabilidade, CV, conformidade com RNFs
""")

md("""
## Requisitos Não Funcionais (RNFs)

Os critérios abaixo foram definidos previamente (capítulo 4.5.1 da dissertação) e guiam
a interpretação de todos os resultados deste notebook.

| ID | Atributo (ISO/IEC 25010) | Critério | Métrica | Limiar |
|---|---|---|---|---|
| **RNF01** | Confiabilidade — Completude | % de requisições com status `FINISHED` | `completude_%` por run | **≥ 99,5%** |
| **RNF02** | Desempenho — Latência 2PC | Tempo total entre criação e resolução da requisição | P95 de `updated_at − created_at` | **≤ 10 s** |
| **RNF03** | Desempenho — Latência HTTP | Tempo de resposta ao POST de submissão | P99 do JMeter JTL (`elapsed`) | **≤ 500 ms** |
| **RNF04** | Eficiência — Uso de CPU | CPU do container `middleware` durante a fase de pico | Máximo observado | **≤ 70%** |
| **RNF05** | Escalabilidade — Eficiência | E(n) = Speedup(n) / n, com n = número de serviços | E(4) mínimo | **≥ 70%** |
| **RNF06** | Observabilidade | Traces e métricas disponíveis via Grafana/OpenTelemetry | Verificação qualitativa | Presença confirmada |
| **RNF07** | Estabilidade | Variação do tempo de processamento entre runs independentes | CV = σ/μ × 100% | **≤ 15%** |

> Os serviços de infraestrutura (`kafka-ui`, `otel-collector`, `zookeeper`) são excluídos
> das análises de recursos — apenas os componentes funcionais do sistema são avaliados.
""")

# ===========================================================================
# 1. SETUP
# ===========================================================================

md("## 1. Configuração e Funções Auxiliares")

code("""
import os, re, json, glob, warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings('ignore')
pd.set_option('display.float_format', '{:.3f}'.format)
pd.set_option('display.max_columns', 25)
pd.set_option('display.width', 140)

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 120, 'savefig.dpi': 150,
                     'figure.figsize': (12, 4)})

# Diretórios
BASE     = Path('..') / 'output-benchmark'
SCALE_D  = BASE / 'scalability'
DB_D     = BASE / 'db_export'
FIG_D    = BASE / 'figures'
FIG_D.mkdir(parents=True, exist_ok=True)

print('Diretório base:', BASE.resolve())
print('Figuras serão salvas em:', FIG_D.resolve())
""")

code("""
# ── Funções auxiliares ──────────────────────────────────────────────────────

def parse_pct(s):
    try:    return float(str(s).replace('%', '').strip())
    except: return np.nan

def parse_mem_mb(s):
    try:
        part = str(s).split('/')[0].strip()
        val  = float(re.sub(r'[^\\d.]', '', part))
        unit = re.sub(r'[\\d.\\s]', '', part).upper()
        return val * {'KIB':1/1024,'KB':1/1024,'MIB':1,'MB':1,'GIB':1024,'GB':1024}.get(unit, 1)
    except: return np.nan

def parse_io_mb(s):
    def to_mb(x):
        x   = x.strip()
        val = float(re.sub(r'[^\\d.]', '', x) or 0)
        unit = re.sub(r'[\\d.\\s]', '', x).upper()
        return val * {'B':1/1e6,'KB':1/1024,'KIB':1/1024,
                      'MB':1,'MIB':1,'GB':1024,'GIB':1024}.get(unit, 1)
    try:
        p = str(s).split('/')
        return to_mb(p[0]), to_mb(p[1])
    except: return np.nan, np.nan

def bootstrap_ci(data, n_boot=2000, ci=0.95, seed=42, stat=np.mean):
    rng  = np.random.default_rng(seed)
    data = np.asarray(data, float)
    data = data[~np.isnan(data)]
    if len(data) < 2: return np.nan, np.nan
    boots = [stat(rng.choice(data, len(data), replace=True)) for _ in range(n_boot)]
    a = (1 - ci) / 2
    return float(np.quantile(boots, a)), float(np.quantile(boots, 1 - a))

def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 2: return np.nan
    mx, my = x.mean(), y.mean()
    num = ((x - mx)*(y - my)).sum()
    den = np.sqrt(((x - mx)**2).sum() * ((y - my)**2).sum())
    return float(num / den) if den > 0 else np.nan

def fit_amdahl(n_list, t_list):
    t1 = t_list[0]
    best_p, best_err = 0.0, float('inf')
    for p in np.linspace(0, 1, 1001):
        err = sum((t1*(p+(1-p)/n) - t)**2 for n, t in zip(n_list, t_list))
        if err < best_err:
            best_err, best_p = err, p
    return best_p, [t1*(best_p+(1-best_p)/n) for n in n_list]

def summary_stats(series, label=''):
    s = pd.to_numeric(series, errors='coerce').dropna()
    lo, hi = bootstrap_ci(s)
    return {'Métrica': label, 'n': len(s),
            'Média': s.mean(), 'DP': s.std(),
            'CV%': s.std()/s.mean()*100 if s.mean() else np.nan,
            'P25': s.quantile(.25), 'Mediana': s.median(),
            'P75': s.quantile(.75), 'P90': s.quantile(.90),
            'P95': s.quantile(.95), 'P99': s.quantile(.99),
            'IQR': s.quantile(.75)-s.quantile(.25),
            'IC95_lo': lo, 'IC95_hi': hi}

def savefig(name):
    path = FIG_D / name
    plt.savefig(path, bbox_inches='tight')
    print(f'  Figura salva: {path}')

print('Funções auxiliares prontas.')
""")

# ===========================================================================
# 2. CARREGAMENTO DOS DADOS
# ===========================================================================

md("## 2. Carregamento dos Dados")

code("""
# ── Benchmark principal — séries de recursos ────────────────────────────────
run_files = sorted(glob.glob(str(BASE / 'benchmark_run_*.csv')))
print(f'Arquivos de run principal: {len(run_files)}')

res_dfs = []
for path in run_files:
    m = re.search(r'benchmark_run_(\\d+)_', path)
    run_num = int(m.group(1)) if m else 0
    try:
        df = pd.read_csv(path)
        if 'CPU_%' not in df.columns:
            print(f'  AVISO: {os.path.basename(path)} ignorado (sem cabeçalho)')
            continue
        df['run'] = run_num
        res_dfs.append(df)
    except Exception as e:
        print(f'  AVISO: {os.path.basename(path)} -> {e}')

if res_dfs:
    res = pd.concat(res_dfs, ignore_index=True)
    res['cpu_pct']     = res['CPU_%'].apply(parse_pct)
    res['mem_mb']      = res['Mem_Usage'].apply(parse_mem_mb)
    res['mem_pct']     = res['Mem_%'].apply(parse_pct)
    io_net             = res['Net_IO'].apply(parse_io_mb)
    res['net_tx_mb']   = io_net.apply(lambda x: x[0])
    res['net_rx_mb']   = io_net.apply(lambda x: x[1])
    io_blk             = res['Block_IO'].apply(parse_io_mb)
    res['blk_rd_mb']   = io_blk.apply(lambda x: x[0])
    res['blk_wr_mb']   = io_blk.apply(lambda x: x[1])
    res['container']   = res['Nome'].str.extract(r'sistemas-distribuidos-(.+?)-\\d+$')[0].fillna(res['Nome'])

    # Exclui serviços de infraestrutura — não fazem parte do sistema avaliado
    _INFRA = r'kafka.ui|otel|zookeeper|grafana|prometheus'
    before = len(res)
    res = res[~res['container'].str.lower().str.contains(_INFRA, regex=True, na=False)].copy()
    print(f'  Containers de infraestrutura removidos: {before - len(res):,} amostras')

    print(f'  Amostras totais : {len(res):,}')
    print(f'  Runs            : {sorted(res["run"].unique())}')
    print(f'  Fases           : {list(res["Fase"].unique())}')
    print(f'  Containers      : {sorted(res["container"].unique())}')
else:
    print('  AVISO: nenhum arquivo de run encontrado.')
    res = pd.DataFrame()
""")

code("""
# ── Benchmark summary ────────────────────────────────────────────────────────
summary_path = BASE / 'benchmark_summary.csv'
if summary_path.exists():
    summary = pd.read_csv(summary_path)
    print('benchmark_summary.csv carregado:')
    display(summary.head())
else:
    print('AVISO: benchmark_summary.csv não encontrado.')
    summary = pd.DataFrame()
""")

code("""
# ── Escalabilidade ───────────────────────────────────────────────────────────
# NOTA: o CSV de escalabilidade tem colunas variáveis porque a coluna "servicos"
# é escrita como valores separados por vírgula (ex: account,payment,crm), não
# como um campo único. O parser abaixo reconstrói o DataFrame corretamente.
scale_path = SCALE_D / 'scalability_summary.csv'

def _load_scalability_csv(path):
    \"\"\"Parser robusto para scalability_summary.csv com colunas variáveis.\"\"\"
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(',')
            # Ignora linhas de cabeçalho ou inválidas (primeira coluna deve ser inteiro)
            if not parts or not parts[0].strip().isdigit():
                continue
            n = int(parts[0])
            # Colunas fixas no fim: run, timestamp, submitted, finished, erro, completude, tempo (7 campos)
            if len(parts) < n + 8:   # 1(n_svcs) + n(svc_names) + 7(métricas)
                continue
            servicos = '|'.join(parts[1:n + 1])
            rest = parts[n + 1:]     # [run, ts, submitted, finished, erro, completude, tempo]
            try:
                rows.append({
                    'n_servicos':          n,
                    'servicos':            servicos,
                    'run':                 int(rest[0]),
                    'timestamp_inicio':    rest[1],
                    'total_submetido':     int(rest[2]),
                    'total_finished':      int(rest[3]),
                    'total_erro':          int(rest[4]),
                    'completude_%':        float(rest[5]),
                    'tempo_processamento_s': int(rest[6]),
                })
            except (ValueError, IndexError):
                continue
    return pd.DataFrame(rows)

if scale_path.exists():
    scale_sum = _load_scalability_csv(scale_path)
    print(f'scalability_summary.csv carregado: {len(scale_sum)} linhas')
    print(f'  n_servicos únicos: {sorted(scale_sum["n_servicos"].unique())}')
    display(scale_sum.head(8))

    scale_run_files = sorted(glob.glob(str(SCALE_D / 'run_*.csv')))
    print(f'Arquivos de run de escalabilidade: {len(scale_run_files)}')
    s_dfs = []
    skipped = 0
    for path in scale_run_files:
        m = re.search(r'run_(\\d+)svcs_(\\d+)_', path)
        if not m: continue
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f'  AVISO: {os.path.basename(path)} ignorado ({e})')
            skipped += 1
            continue
        if 'CPU_%' not in df.columns:
            # Arquivo sem cabeçalho (run interrompida antes da escrita do header)
            skipped += 1
            continue
        df['n_svcs'] = int(m.group(1))
        df['scale_run'] = int(m.group(2))
        df['cpu_pct'] = df['CPU_%'].apply(parse_pct)
        df['mem_mb']  = df['Mem_Usage'].apply(parse_mem_mb)
        df['container'] = df['Nome'].str.extract(r'sistemas-distribuidos-(.+?)-\\d+$')[0].fillna(df['Nome'])
        s_dfs.append(df)
    if skipped:
        print(f'  {skipped} arquivo(s) sem cabeçalho ignorado(s) (runs interrompidas)')
    scale_res = pd.concat(s_dfs, ignore_index=True) if s_dfs else pd.DataFrame()
    if not scale_res.empty:
        _INFRA = r'kafka.ui|otel|zookeeper|grafana|prometheus'
        scale_res = scale_res[~scale_res['container'].str.lower().str.contains(_INFRA, regex=True, na=False)].copy()
    print(f'  Amostras escalabilidade: {len(scale_res):,}')
else:
    print('AVISO: scalability_summary.csv não encontrado.')
    scale_sum  = pd.DataFrame()
    scale_res  = pd.DataFrame()
""")

code("""
# ── DB export — latência 2PC ─────────────────────────────────────────────────
pr_path  = DB_D / 'privacy_requests.csv'
prs_path = DB_D / 'privacy_requests_services.csv'

if pr_path.exists():
    pr = pd.read_csv(pr_path)
    for col in ['created_at', 'updated_at']:
        if col in pr.columns:
            pr[col] = pd.to_datetime(pr[col], utc=True, errors='coerce')
    if 'created_at' in pr.columns and 'updated_at' in pr.columns:
        pr['latencia_2pc_s'] = (pr['updated_at'] - pr['created_at']).dt.total_seconds()
    print(f'privacy_requests.csv: {len(pr):,} registros')
    print(f'  Status: {pr["status"].value_counts().to_dict()}')
    display(pr.head(3))
else:
    print('AVISO: privacy_requests.csv não encontrado.')
    pr = pd.DataFrame()

if prs_path.exists():
    prs = pd.read_csv(prs_path)
    print(f'privacy_requests_services.csv: {len(prs):,} registros')
else:
    prs = pd.DataFrame()
""")

code("""
# ── JTL — latência HTTP de submissão ─────────────────────────────────────────
jtl_files = sorted(glob.glob(str(BASE / '*.jtl')))
print(f'Arquivos JTL encontrados: {len(jtl_files)}')

jtl_dfs = []
for path in jtl_files:
    m = re.search(r'benchmark_run_(\\d+)_', path)
    run_num = int(m.group(1)) if m else 0
    try:
        df = pd.read_csv(path)
        df['run'] = run_num
        jtl_dfs.append(df)
    except Exception as e:
        print(f'  AVISO: {os.path.basename(path)} -> {e}')

if jtl_dfs:
    jtl = pd.concat(jtl_dfs, ignore_index=True)
    jtl.columns = [c.lower().strip() for c in jtl.columns]
    print(f'  Amostras JTL totais: {len(jtl):,}')
    print(f'  Colunas: {list(jtl.columns)}')
else:
    print('  AVISO: nenhum arquivo JTL encontrado.')
    jtl = pd.DataFrame()
""")

# ===========================================================================
# 3. BENCHMARK PRINCIPAL — COMPLETUDE
# ===========================================================================

md("## 3. Benchmark Principal — Completude e Throughput")

code("""
if not summary.empty:
    # Força tipos numéricos (previne leitura como string em alguns ambientes)
    for _c in summary.columns:
        if _c not in ('timestamp_inicio',):
            summary[_c] = pd.to_numeric(summary[_c], errors='coerce')

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Completude por run
    ax = axes[0]
    # Preferência explícita; fallback por padrão no nome (excluindo timestamp)
    col_comp = next(
        (c for c in ['completude_%', 'completude_pct', 'completude']
         if c in summary.columns),
        next((c for c in summary.columns
              if ('completude' in c.lower() or 'pct' in c.lower())
              and 'timestamp' not in c.lower()), None)
    )
    if col_comp:
        bars = ax.bar(summary.index + 1, summary[col_comp], color='steelblue', edgecolor='white')
        ax.axhline(99.5, color='red', linestyle='--', linewidth=1, label='Critério RNF01 (≥99.5%)')
        ax.set_xlabel('Run'); ax.set_ylabel('Completude (%)'); ax.set_title('Completude por Run')
        ax.set_ylim(0, 105); ax.legend(fontsize=9)
        for bar, val in zip(bars, summary[col_comp]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=8)

    # Tempo de processamento por run
    ax = axes[1]
    # 'time' é substring de 'timestamp_inicio' — excluir explicitamente
    col_tempo = next(
        (c for c in ['tempo_processamento_s', 'tempo_s', 'tempo']
         if c in summary.columns),
        next((c for c in summary.columns
              if 'tempo' in c.lower()
              and 'timestamp' not in c.lower()), None)
    )
    if col_tempo:
        ax.plot(summary.index + 1, summary[col_tempo], 'o-', color='darkorange')
        ax.axhline(summary[col_tempo].mean(), color='gray', linestyle='--',
                   linewidth=1, label=f'Média: {summary[col_tempo].mean():.0f}s')
        ax.set_xlabel('Run'); ax.set_ylabel('Tempo (s)'); ax.set_title('Tempo de Processamento por Run')
        ax.legend(fontsize=9)

    # Distribuição do tempo
    ax = axes[2]
    if col_tempo:
        sns.histplot(summary[col_tempo], bins=10, kde=True, ax=ax, color='steelblue')
        ax.set_xlabel('Tempo (s)'); ax.set_title('Distribuição do Tempo de Processamento')
        lo, hi = bootstrap_ci(summary[col_tempo])
        ax.axvspan(lo, hi, alpha=0.15, color='red', label=f'IC95% [{lo:.0f}, {hi:.0f}]s')
        ax.legend(fontsize=9)

    plt.suptitle('Benchmark Principal — Completude e Tempo de Processamento', fontsize=13, y=1.01)
    plt.tight_layout()
    savefig('completude_throughput.png')
    plt.show()

    print('\\n── Estatísticas de Completude ──')
    if col_comp:
        print(pd.DataFrame([summary_stats(summary[col_comp], 'Completude (%)')]).to_string(index=False))
    if col_tempo:
        print('\\n── Estatísticas de Tempo de Processamento ──')
        print(pd.DataFrame([summary_stats(summary[col_tempo], 'Tempo (s)')]).to_string(index=False))
else:
    print('Dados de summary não disponíveis.')
""")

# ===========================================================================
# 4. RECURSOS POR FASE — CPU
# ===========================================================================

md("""
### Interpretação — Completude e Tempo de Processamento

O gráfico de **completude por run** mostra o percentual de requisições com status `FINISHED` em cada execução independente. A linha tracejada vermelha é o critério do **RNF01 (≥ 99,5%)**. Todos os runs devem ultrapassar esse limiar para confirmar que o protocolo 2PC executa o direito ao esquecimento com plena cobertura nos microsserviços participantes.

O **tempo de processamento por run** revela a estabilidade temporal do sistema. Uma linha próxima da média com baixa dispersão indica comportamento determinístico; picos isolados podem refletir contenção no Kafka ou variação de carga do sistema operacional do host.

A **distribuição do tempo** (histograma + KDE) permite identificar a forma da distribuição: uma curva próxima da normal com baixo desvio indica sistema previsível. O intervalo de confiança 95% bootstrap (área sombreada) quantifica a incerteza sobre a média real sem assumir normalidade.
""")

md("## 4. Recursos por Fase — CPU")

code("""
if not res.empty:
    mw = res[res['container'].str.contains('middleware', case=False, na=False)].copy()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    fase_order  = ['repouso', 'pico', 'pos']
    fase_colors = {'repouso': 'steelblue', 'pico': 'tomato', 'pos': 'goldenrod'}

    # Boxplot CPU middleware por fase
    ax = axes[0]
    data_fase = [mw[mw['Fase']==f]['cpu_pct'].dropna() for f in fase_order]
    bp = ax.boxplot(data_fase, labels=fase_order, patch_artist=True,
                    medianprops={'color':'black','linewidth':2})
    for patch, fase in zip(bp['boxes'], fase_order):
        patch.set_facecolor(fase_colors.get(fase, 'gray'))
    ax.set_ylabel('CPU (%)'); ax.set_title('CPU Middleware por Fase')
    ax.axhline(70, color='red', linestyle='--', linewidth=1, label='Critério RNF04 (≤70%)')
    ax.legend(fontsize=9)

    # CPU por fase e run (heatmap)
    ax = axes[1]
    pivot = mw[mw['Fase'].isin(fase_order)].groupby(['run','Fase'])['cpu_pct'].mean().unstack()
    pivot = pivot.reindex(columns=fase_order)
    sns.heatmap(pivot, ax=ax, cmap='YlOrRd', annot=True, fmt='.1f',
                linewidths=.5, cbar_kws={'label':'CPU%'})
    ax.set_title('CPU Middleware por Run × Fase'); ax.set_xlabel('Fase'); ax.set_ylabel('Run')

    # CPU todos os containers, fase pico
    ax = axes[2]
    pico = res[res['Fase']=='pico'].copy()
    ordem = pico.groupby('container')['cpu_pct'].median().sort_values(ascending=False).index
    sns.boxplot(data=pico, x='container', y='cpu_pct', order=ordem,
                palette='muted', ax=ax)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    ax.set_xlabel(''); ax.set_ylabel('CPU (%)'); ax.set_title('CPU por Container — Fase Pico')

    plt.suptitle('Utilização de CPU', fontsize=13, y=1.01)
    plt.tight_layout()
    savefig('cpu_por_fase.png')
    plt.show()

    print('\\n── Estatísticas CPU Middleware por Fase ──')
    rows = []
    for f in fase_order:
        d = mw[mw['Fase']==f]['cpu_pct']
        rows.append(summary_stats(d, f'CPU middleware — {f}'))
    display(pd.DataFrame(rows).set_index('Métrica'))

    # ── Degradação do repouso ao longo dos runs ──────────────────────────────
    # O heatmap mostra CPU crescente no repouso? Isso indica backlog acumulado.
    rep_por_run = mw[mw['Fase']=='repouso'].groupby('run')['cpu_pct'].mean().reset_index()
    if len(rep_por_run) > 1:
        from scipy import stats as _stats
        slope, intercept, r, p, _ = _stats.linregress(rep_por_run['run'], rep_por_run['cpu_pct'])
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(rep_por_run['run'], rep_por_run['cpu_pct'], 'o-', color='steelblue',
                label='CPU repouso média por run')
        x_fit = rep_por_run['run']
        ax.plot(x_fit, intercept + slope * x_fit, '--', color='tomato', linewidth=1.5,
                label=f'Tendência linear (slope={slope:+.3f}%/run, r={r:.2f}, p={p:.3f})')
        ax.set_xlabel('Run'); ax.set_ylabel('CPU (%) — fase repouso')
        ax.set_title('CPU no Repouso por Run\\n'
                     '(crescimento indica backlog acumulado de requisições não finalizadas)')
        ax.legend(fontsize=9)

        if p < 0.05 and slope > 0:
            ax.text(0.02, 0.93,
                    '⚠ Tendência de crescimento estatisticamente significativa (p<0.05)\\n'
                    '   Causa provável: requisições presas em PENDING/PROCESSING acumulam\\n'
                    '   entre runs e mantêm os consumers Kafka ativos no repouso.',
                    transform=ax.transAxes, fontsize=9, color='tomato',
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', fc='#fff3f3', alpha=0.85))

        plt.tight_layout()
        savefig('cpu_repouso_degradacao.png')
        plt.show()
        print(f'Regressão linear CPU repouso × run: slope={slope:+.4f}%/run, r={r:.3f}, p={p:.4f}')
else:
    print('Dados de recursos não disponíveis.')
""")

# ===========================================================================
# 5. RECURSOS POR FASE — MEMÓRIA
# ===========================================================================

md("""
### Interpretação — Utilização de CPU

O **boxplot de CPU por fase** revela o perfil de carga do middleware ao longo de um run típico. A fase `repouso` captura o consumo basal (consumers Kafka ativos, sem mensagens); `pico` reflete o processamento concorrente das 900 requisições; `pos` mostra a recuperação após o JMeter concluir. A linha tracejada vermelha marca o critério do **RNF04 (≤ 70%)**.

O **heatmap CPU por run × fase** permite identificar tendências entre runs. Um gradiente crescente na coluna `repouso` indica acúmulo de requisições presas em `PENDING/PROCESSING` — o consumer Kafka permanece ativo aguardando respostas que nunca chegam.

O **boxplot por container na fase pico** compara o peso computacional de cada serviço. É esperado que o middleware consuma mais CPU por ser o orquestrador 2PC — publica e consome em quatro tópicos Kafka simultaneamente.

O **gráfico de tendência do repouso** quantifica degradação entre runs via regressão linear. Inclinação positiva com p < 0,05 confirma que o crescimento é estatisticamente significativo — diagnóstico direto de backlog acumulado. Após a correção no `pacote_privacy` (remoção do `finally: await self.stop()`) esse padrão não deve ocorrer.
""")

md("## 5. Recursos por Fase — Memória")

code("""
if not res.empty:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Boxplot memória middleware por fase
    ax = axes[0]
    mw_mem = mw.copy()
    data_mem = [mw_mem[mw_mem['Fase']==f]['mem_mb'].dropna() for f in fase_order]
    bp = ax.boxplot(data_mem, labels=fase_order, patch_artist=True,
                    medianprops={'color':'black','linewidth':2})
    for patch, fase in zip(bp['boxes'], fase_order):
        patch.set_facecolor(fase_colors.get(fase,'gray'))
    ax.set_ylabel('Memória (MiB)'); ax.set_title('Memória Middleware por Fase')
    ax.axhline(75, color='red', linestyle='--', linewidth=1, label='Referência 75 MiB')
    ax.legend(fontsize=9)

    # Memória por run (estabilidade) — fase repouso
    ax = axes[1]
    rep = mw[mw['Fase']=='repouso'].groupby('run')['mem_mb'].mean()
    ax.plot(rep.index, rep.values, 'o-', color='steelblue', label='Média no repouso')
    ax.fill_between(rep.index,
                    rep.values - rep.std(),
                    rep.values + rep.std(),
                    alpha=0.2, color='steelblue')
    ax.set_xlabel('Run'); ax.set_ylabel('MiB')
    ax.set_title('Estabilidade de Memória entre Runs (fase repouso)')
    ax.legend(fontsize=9)

    cv_mem = rep.std() / rep.mean() * 100
    ax.text(0.98, 0.05, f'CV = {cv_mem:.1f}%',
            transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round', fc='white', alpha=0.7))

    plt.tight_layout()
    savefig('memoria_por_fase.png')
    plt.show()

    print('\\n── Estatísticas Memória Middleware por Fase ──')
    rows = [summary_stats(mw[mw['Fase']==f]['mem_mb'], f'Memória — {f}') for f in fase_order]
    display(pd.DataFrame(rows).set_index('Métrica'))
    print(f'\\nCV memória repouso entre runs: {cv_mem:.2f}%')
""")

# ===========================================================================
# 6. NET IO E BLOCK IO
# ===========================================================================

md("""
### Interpretação — Memória

O **boxplot de memória por fase** mostra que o middleware (FastAPI + aiokafka) tende a manter alocação relativamente estável entre fases. O Python libera memória de objetos de curta duração ao final de cada requisição, mas o pool de conexões com o banco e os buffers Kafka permanecem alocados.

A **curva de estabilidade entre runs** revela se há vazamento de memória acumulado. A faixa sombreada (±1σ) deve permanecer estreita ao longo das 20 execuções. O **CV** no canto do gráfico quantifica a variação relativa: CV < 15% atende ao critério de estabilidade do **RNF07**.
""")

md("## 6. I/O de Rede e Disco")

code("""
if not res.empty:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Net IO do Kafka (maior trafego de rede)
    kafka = res[res['container'].str.contains('kafka', case=False, na=False)]
    ax = axes[0]
    if not kafka.empty:
        pico_kafka = kafka[kafka['Fase']=='pico']
        sns.boxplot(data=pico_kafka, x='run', y='net_rx_mb', color='steelblue', ax=ax)
        ax.set_xlabel('Run'); ax.set_ylabel('Net RX (MiB cumulativo)')
        ax.set_title('Net IO Recebido — Kafka (fase pico)')
    else:
        ax.set_title('Kafka não encontrado nos dados')

    # Block IO do middleware_db
    db = res[res['container'].str.contains('middleware_db', case=False, na=False)]
    ax = axes[1]
    if not db.empty:
        pico_db = db[db['Fase']=='pico']
        sns.boxplot(data=pico_db, x='run', y='blk_wr_mb', color='darkorange', ax=ax)
        ax.set_xlabel('Run'); ax.set_ylabel('Block Write (MiB cumulativo)')
        ax.set_title('Block IO Escrita — middleware_db (fase pico)')
    else:
        ax.set_title('middleware_db não encontrado nos dados')

    plt.tight_layout()
    savefig('io_rede_disco.png')
    plt.show()
""")

# ===========================================================================
# 7. LATÊNCIA 2PC
# ===========================================================================

md("""
### Interpretação — I/O de Rede e Disco

**Atenção**: os contadores de I/O do `docker stats` são **cumulativos desde o início do container**, não taxas por segundo. Os valores crescem monotonicamente dentro de uma execução. Os boxplots mostram a dispersão desses valores acumulados durante a fase `pico` — não a taxa de transferência instantânea.

O **Net RX do Kafka** representa o tráfego de entrada recebido pelo broker. Cada requisição 2PC gera pelo menos `2 × n_serviços` mensagens (validate-response + execute-response), portanto o volume total é proporcional ao número de participantes e à taxa de completude.

O **Block Write do middleware_db** reflete a escrita no PostgreSQL. A cada run são inseridas novas linhas em `privacy_requests` e `privacy_requests_services`, o que explica o crescimento acumulado observado.
""")

md("## 7. Latência de Processamento 2PC")

code("""
if not pr.empty and 'latencia_2pc_s' in pr.columns:
    finished = pr[pr['status']=='FINISHED']['latencia_2pc_s'].dropna()
    print(f'Requisições FINISHED com latência medida: {len(finished):,}')

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Histograma + KDE
    ax = axes[0]
    sns.histplot(finished, bins=40, kde=True, ax=ax, color='steelblue')
    ax.axvline(finished.median(), color='red', linestyle='--',
               label=f'Mediana: {finished.median():.2f}s')
    ax.axvline(finished.quantile(.95), color='orange', linestyle='--',
               label=f'P95: {finished.quantile(.95):.2f}s')
    ax.set_xlabel('Latência 2PC (s)'); ax.set_title('Distribuição da Latência 2PC')
    ax.legend(fontsize=9)

    # ECDF
    ax = axes[1]
    x_ecdf = np.sort(finished)
    y_ecdf = np.arange(1, len(x_ecdf)+1) / len(x_ecdf)
    ax.plot(x_ecdf, y_ecdf, color='steelblue', linewidth=1.5)
    for p, lbl, col in [(0.50,'P50','gray'),(0.90,'P90','orange'),(0.95,'P95','tomato'),(0.99,'P99','red')]:
        val = float(np.quantile(x_ecdf, p))
        ax.axvline(val, linestyle='--', color=col, linewidth=1, label=f'{lbl}: {val:.2f}s')
    ax.set_xlabel('Latência (s)'); ax.set_ylabel('Probabilidade acumulada')
    ax.set_title('ECDF — Latência 2PC'); ax.legend(fontsize=8)

    # Percentis por run (se houver coluna run linkável)
    ax = axes[2]
    if 'run' in pr.columns:
        per_run = pr[pr['status']=='FINISHED'].groupby('run')['latencia_2pc_s'].agg(
            mediana='median', p95=lambda x: x.quantile(.95)).reset_index()
        ax.plot(per_run['run'], per_run['mediana'], 'o-', label='Mediana', color='steelblue')
        ax.plot(per_run['run'], per_run['p95'],     's--', label='P95',    color='tomato')
        ax.set_xlabel('Run'); ax.set_ylabel('Latência (s)')
        ax.set_title('Mediana e P95 por Run'); ax.legend(fontsize=9)
    else:
        sns.boxplot(y=finished, ax=ax, color='steelblue')
        ax.set_ylabel('Latência 2PC (s)'); ax.set_title('Boxplot Latência 2PC')

    plt.suptitle('Latência de Processamento 2PC', fontsize=13, y=1.01)
    plt.tight_layout()
    savefig('latencia_2pc.png')
    plt.show()

    print('\\n── Estatísticas Latência 2PC (FINISHED) ──')
    display(pd.DataFrame([summary_stats(finished, 'Latência 2PC (s)')]))
else:
    print('Dados de latência 2PC não disponíveis (execute o benchmark e exporte o banco).')
""")

code("""
# Latência por serviço participante
if not prs.empty and not pr.empty:
    # Tenta identificar coluna de serviço e tempo
    print('Colunas em privacy_requests_services:', list(prs.columns))
    display(prs.head(3))
    # Se houver colunas de timestamp por serviço, calcular latência individual
    time_cols = [c for c in prs.columns if 'time' in c.lower() or 'at' in c.lower()]
    print('Colunas temporais encontradas:', time_cols)
""")

# ===========================================================================
# 8. LATÊNCIA HTTP (JTL)
# ===========================================================================

md("""
### Interpretação — Latência de Processamento 2PC

A **distribuição da latência 2PC** (`updated_at − created_at`, registrado no banco) captura o tempo total entre a criação da requisição e o status `FINISHED`. Inclui: enfileiramento no Kafka, processamento dos handlers de validação e execução em todos os microsserviços participantes, e escrita do status final.

O critério **RNF02 exige P95 ≤ 10 s**. No gráfico **ECDF**, encontre 0,95 no eixo Y e trace horizontalmente até a curva para ler o P95 diretamente. Uma cauda longa à direita pode indicar requisições que aguardaram o timeout de validação (30 s) antes de serem resolvidas.

O **gráfico de percentis por run** verifica a estabilidade da latência entre execuções independentes. Variações abruptas em um run específico podem indicar contenção de recursos no host durante aquele experimento.

> **Distinção importante**: latência 2PC (segundos, assíncrona) ≠ latência HTTP de submissão (milissegundos, síncrona). O `POST` retorna imediatamente com `201 CREATED`; o protocolo 2PC completo ocorre em background.
""")

md("## 8. Latência HTTP de Submissão (JMeter JTL)")

code("""
if not jtl.empty:
    elapsed_col = next((c for c in jtl.columns if 'elapsed' in c), None)
    success_col = next((c for c in jtl.columns if 'success' in c), None)

    if elapsed_col:
        jtl[elapsed_col] = pd.to_numeric(jtl[elapsed_col], errors='coerce')
        latencia_ms = jtl[elapsed_col].dropna()

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Distribuição
        ax = axes[0]
        sns.histplot(latencia_ms.clip(upper=latencia_ms.quantile(.99)),
                     bins=40, kde=True, ax=ax, color='teal')
        ax.axvline(latencia_ms.median(), color='red', linestyle='--',
                   label=f'Mediana: {latencia_ms.median():.0f}ms')
        ax.axvline(latencia_ms.quantile(.99), color='orange', linestyle='--',
                   label=f'P99: {latencia_ms.quantile(.99):.0f}ms')
        ax.set_xlabel('Latência HTTP (ms)'); ax.set_title('Distribuição Latência Submissão')
        ax.legend(fontsize=9)

        # ECDF
        ax = axes[1]
        x_e = np.sort(latencia_ms)
        y_e = np.arange(1, len(x_e)+1) / len(x_e)
        ax.plot(x_e, y_e, color='teal')
        for p, lbl, col in [(.50,'P50','gray'),(.90,'P90','orange'),(.95,'P95','tomato'),(.99,'P99','red')]:
            val = float(np.quantile(x_e, p))
            ax.axvline(val, linestyle='--', color=col, linewidth=1, label=f'{lbl}: {val:.0f}ms')
        ax.axvline(500, linestyle='-', color='black', linewidth=1.5, label='RNF03 (≤500ms)')
        ax.set_xlabel('ms'); ax.set_ylabel('Probabilidade acumulada')
        ax.set_title('ECDF — Latência HTTP'); ax.legend(fontsize=8)

        # Latência por run
        ax = axes[2]
        if 'run' in jtl.columns:
            per_run = jtl.groupby('run')[elapsed_col].agg(
                mediana='median', p99=lambda x: x.quantile(.99)).reset_index()
            ax.plot(per_run['run'], per_run['mediana'], 'o-', label='Mediana', color='teal')
            ax.plot(per_run['run'], per_run['p99'],     's--', label='P99',    color='tomato')
            ax.axhline(500, color='black', linestyle='--', linewidth=1, label='RNF03 (500ms)')
            ax.set_xlabel('Run'); ax.set_ylabel('ms')
            ax.set_title('Mediana e P99 por Run'); ax.legend(fontsize=9)

        plt.suptitle('Latência HTTP de Submissão (JMeter)', fontsize=13, y=1.01)
        plt.tight_layout()
        savefig('latencia_http_jmeter.png')
        plt.show()

        print('\\n── Estatísticas Latência HTTP (ms) ──')
        display(pd.DataFrame([summary_stats(latencia_ms, 'Latência HTTP (ms)')]))

        # Taxa de erro
        if success_col:
            total     = len(jtl)
            sucesso   = (jtl[success_col].astype(str).str.lower()=='true').sum()
            taxa_erro = (total - sucesso) / total * 100
            print(f'\\nTotal de requisições JMeter : {total:,}')
            print(f'Sucessos (HTTP 2xx/201)      : {sucesso:,}')
            print(f'Taxa de erro                 : {taxa_erro:.2f}%')
    else:
        print('Coluna "elapsed" não encontrada no JTL. Colunas disponíveis:', list(jtl.columns))
else:
    print('Arquivos JTL não encontrados. Execute o benchmark com JMeter configurado.')
""")

# ===========================================================================
# 9. ESCALABILIDADE
# ===========================================================================

md("""
### Interpretação — Latência HTTP de Submissão

A **latência HTTP** mede o tempo de resposta do `POST /api/v1/privacy-requests/` — o endpoint que cria a requisição de exclusão. O middleware persiste no banco, publica no Kafka e retorna `201 CREATED` de forma síncrona; o processamento 2PC ocorre de forma assíncrona.

O critério **RNF03 exige P99 ≤ 500 ms**. A linha vertical preta no gráfico ECDF marca esse limiar. Latências de submissão tipicamente ficam em dezenas de milissegundos — o endpoint realiza apenas uma escrita no banco e uma publicação Kafka.

O **gráfico de latência por run** verifica que o P99 de submissão permanece estável sob carga crescente acumulada. Um aumento progressivo pode indicar contenção no connection pool do PostgreSQL.

A **taxa de erro JMeter** (requisições HTTP sem 2xx) é distinta da completude 2PC. Um `POST` pode retornar `200` e o 2PC ainda falhar; e um `POST` pode ser rejeitado por validação de payload antes do protocolo ser iniciado.
""")

md("## 9. Experimento de Escalabilidade")

code("""
if not scale_sum.empty:
    col_t    = 'tempo_processamento_s'
    col_comp = 'completude_%'

    scale_sum[col_t]    = pd.to_numeric(scale_sum[col_t],    errors='coerce')
    scale_sum[col_comp] = pd.to_numeric(scale_sum[col_comp], errors='coerce')

    # ── Tabela agregada por n_servicos ──────────────────────────────────────
    agg = scale_sum.groupby('n_servicos').agg(
        mean_t   =(col_t,    'mean'),
        std_t    =(col_t,    'std'),
        med_t    =(col_t,    'median'),
        mean_comp=(col_comp, 'mean'),
        min_comp =(col_comp, 'min'),
    ).reset_index().rename(columns={'n_servicos': 'n_svcs'})

    print('── Tabela agregada por n_servicos ──')
    display(agg.round(3))

    # Alertas de completude anômala
    for _, row in agg.iterrows():
        if row['mean_comp'] < 99.5:
            print(f'  ⚠  n={int(row["n_svcs"])}: completude média {row["mean_comp"]:.1f}% '
                  f'(mín {row["min_comp"]:.1f}%) — ABAIXO DO CRITÉRIO RNF01 (≥99.5%)')

    # ── Gráfico 1: Completude por run e configuração ─────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    colors_n = {1:'#4C9BE8', 2:'#5DBE8A', 3:'#E8924C', 4:'#E85C5C'}
    for n in sorted(scale_sum['n_servicos'].unique()):
        sub = scale_sum[scale_sum['n_servicos']==n].sort_values('run')
        ax.plot(sub['run'], sub[col_comp], 'o-', color=colors_n.get(n,'gray'),
                label=f'n={n} ({sub["servicos"].iloc[0].replace("|",",")})', linewidth=1.5, markersize=5)
    ax.axhline(99.5, color='red', linestyle='--', linewidth=1.2, label='RNF01 (≥99.5%)')
    ax.set_xlabel('Run'); ax.set_ylabel('Completude (%)')
    ax.set_title('Completude por Run e Configuração')
    ax.legend(fontsize=8, loc='lower left')
    ax.set_ylim(-5, 105)

    ax = axes[1]
    groups  = [scale_sum[scale_sum['n_servicos']==n][col_comp].dropna()
               for n in sorted(scale_sum['n_servicos'].unique())]
    n_labels = sorted(scale_sum['n_servicos'].unique())
    bp = ax.boxplot(groups, labels=n_labels, patch_artist=True,
                    medianprops={'color':'black','linewidth':2})
    for patch, n in zip(bp['boxes'], n_labels):
        patch.set_facecolor(colors_n.get(n,'gray'))
    ax.axhline(99.5, color='red', linestyle='--', linewidth=1.2, label='RNF01 (≥99.5%)')
    ax.set_xlabel('Número de serviços'); ax.set_ylabel('Completude (%)')
    ax.set_title('Distribuição da Completude por Configuração')
    ax.legend(fontsize=8)

    plt.suptitle('Escalabilidade — Completude', fontsize=13, y=1.01)
    plt.tight_layout()
    savefig('escalabilidade_completude.png')
    plt.show()

    # ── Gráfico 2: Tempo, Speedup, Eficiência (apenas configs com completude ok) ──
    # Inclui todas as configurações para análise de desempenho, mas marca as
    # que não atendem ao RNF01.
    t1 = agg.loc[agg['n_svcs']==1, 'mean_t'].values[0]
    agg['speedup']    = t1 / agg['mean_t']
    agg['eficiencia'] = agg['speedup'] / agg['n_svcs']

    p_serial, t_amdahl = fit_amdahl(agg['n_svcs'].tolist(), agg['mean_t'].tolist())

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    ax = axes[0]
    ax.errorbar(agg['n_svcs'], agg['mean_t'], yerr=agg['std_t'],
                fmt='o-', capsize=5, color='steelblue', label='Observado')
    ax.plot(agg['n_svcs'], t_amdahl, 's--', color='tomato',
            label=f'Amdahl (p={p_serial:.3f})')
    # Marcar configs com completude < 99.5%
    anom = agg[agg['mean_comp'] < 99.5]
    if not anom.empty:
        ax.scatter(anom['n_svcs'], anom['mean_t'], s=120, zorder=5,
                   marker='x', color='red', linewidths=2,
                   label='Completude < 99.5%')
    ax.set_xlabel('Número de Serviços'); ax.set_ylabel('Tempo médio (s)')
    ax.set_title('Tempo de Processamento × Serviços'); ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(agg['n_svcs'], agg['speedup'], 'o-', color='darkorange', label='Speedup observado')
    ax.plot(agg['n_svcs'], agg['n_svcs'],  '--', color='gray', alpha=.5, label='Ideal (linear)')
    ax.set_xlabel('n'); ax.set_ylabel('Speedup S(n)')
    ax.set_title('Speedup'); ax.legend(fontsize=9)

    ax = axes[2]
    bar_colors = [colors_n.get(n,'gray') for n in agg['n_svcs']]
    bars = ax.bar(agg['n_svcs'], agg['eficiencia']*100, color=bar_colors, edgecolor='white')
    ax.axhline(70, color='red', linestyle='--', linewidth=1, label='RNF05 (≥70%)')
    ax.set_xlabel('n'); ax.set_ylabel('Eficiência (%)')
    ax.set_title('Eficiência E(n)'); ax.legend(fontsize=9)
    for bar, val in zip(bars, agg['eficiencia']):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                f'{val*100:.0f}%', ha='center', va='bottom', fontsize=9)

    plt.suptitle('Escalabilidade — Tempo, Speedup, Eficiência', fontsize=13, y=1.01)
    plt.tight_layout()
    savefig('escalabilidade.png')
    plt.show()

    print(f'\\nFração serial estimada (Lei de Amdahl): p = {p_serial:.4f}')
    if p_serial > 0:
        print(f'Speedup máximo teórico (n→∞):           1/p = {1/p_serial:.1f}x')
    print('\\n── Tabela de Escalabilidade (speedup / eficiência) ──')
    display(agg[['n_svcs','mean_t','std_t','mean_comp','speedup','eficiencia']].round(3))
else:
    print('Dados de escalabilidade não disponíveis.')
    col_t = None
""")

code("""
# Variabilidade entre runs de escalabilidade (boxplot por n_svcs)
if not scale_sum.empty and 'tempo_processamento_s' in scale_sum.columns:
    col_t = 'tempo_processamento_s'
    fig, ax = plt.subplots(figsize=(9, 5))
    groups = [scale_sum[scale_sum['n_servicos']==n][col_t].dropna()
              for n in sorted(scale_sum['n_servicos'].unique())]
    colors_n = {1:'#4C9BE8', 2:'#5DBE8A', 3:'#E8924C', 4:'#E85C5C'}
    bp = ax.boxplot(groups, labels=sorted(scale_sum['n_servicos'].unique()),
                    patch_artist=True, medianprops={'color':'black','linewidth':2})
    for patch, n in zip(bp['boxes'], sorted(scale_sum['n_servicos'].unique())):
        patch.set_facecolor(colors_n.get(n,'gray'))
    ax.set_xlabel('Número de serviços participantes')
    ax.set_ylabel('Tempo de processamento (s)')
    ax.set_title('Distribuição do Tempo por Configuração de Serviços (20 runs cada)')
    plt.tight_layout()
    savefig('escalabilidade_boxplot.png')
    plt.show()
""")

# ===========================================================================
# 10. ANÁLISES CRUZADAS
# ===========================================================================

md("""
### Interpretação — Experimento de Escalabilidade

O experimento adiciona serviços **cumulativamente** (n=1→2→3→4), simulando o crescimento incremental de um sistema de produção. Cada configuração executa 20 runs independentes.

**Completude por configuração**: qualquer serviço que não responda ou bloqueie impede a conclusão de *todas* as requisições — semântica de unanimidade do 2PC. Uma queda de completude ao adicionar o serviço N indica que N impõe restrições de negócio mais restritivas ou apresenta instabilidade que precisa ser diagnosticada.

**Tempo, Speedup e Eficiência**: o "speedup" aqui não representa paralelismo de execução — representa a *variação do tempo de consenso* com mais participantes. Um speedup < 1 é esperado: mais participantes = mais roundtrips Kafka = maior latência de coordenação.

O **fitting pela Lei de Amdahl** estima a fração serial `p` do protocolo — o overhead intrínseco de coordenação que não se reduz com menos participantes. O speedup máximo teórico `1/p` é um limite assintótico para esse overhead.

**Eficiência E(n) = Speedup(n)/n**: mede quanto da capacidade "linear" é preservada. O critério **RNF05 exige E(4) ≥ 70%**. Configurações com X vermelho têm completude < 99,5% — os dados de tempo para essas configurações devem ser interpretados com cautela.

**Boxplot de variabilidade**: IQR crescente com n indica maior sensibilidade a variações de fila no Kafka ou latência de rede entre containers.
""")

md("## 10. Análises Cruzadas")

code("""
# ── Correlação CPU × Latência 2PC ───────────────────────────────────────────
if not res.empty and not pr.empty and 'latencia_2pc_s' in pr.columns:
    # CPU média do middleware na fase pico, por run
    cpu_pico = (res[(res['Fase']=='pico') &
                    res['container'].str.contains('middleware', case=False, na=False)]
                .groupby('run')['cpu_pct'].mean()
                .reset_index(name='cpu_pico_mean'))

    lat_run = pr[pr['status']=='FINISHED'].copy()
    if 'run' not in lat_run.columns:
        # Se não houver coluna run no DB export, pular
        print('Coluna "run" não disponível em privacy_requests — correlação por run não calculada.')
        cpu_lat = pd.DataFrame()
    else:
        lat_med = lat_run.groupby('run')['latencia_2pc_s'].median().reset_index(name='lat_mediana')
        cpu_lat = cpu_pico.merge(lat_med, on='run')

    if not cpu_lat.empty:
        r = pearson(cpu_lat['cpu_pico_mean'], cpu_lat['lat_mediana'])
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(cpu_lat['cpu_pico_mean'], cpu_lat['lat_mediana'],
                   color='steelblue', edgecolors='white', s=70, zorder=3)
        # Linha de tendência
        z = np.polyfit(cpu_lat['cpu_pico_mean'].dropna(),
                       cpu_lat['lat_mediana'].dropna(), 1)
        xp = np.linspace(cpu_lat['cpu_pico_mean'].min(), cpu_lat['cpu_pico_mean'].max(), 100)
        ax.plot(xp, np.polyval(z, xp), '--', color='tomato', linewidth=1.5)
        ax.set_xlabel('CPU média middleware — fase pico (%)')
        ax.set_ylabel('Latência 2PC mediana (s)')
        ax.set_title(f'Correlação CPU × Latência 2PC\\n(Pearson r = {r:.3f})')
        ax.text(0.05, 0.95, 'Observacional: correlação ≠ causalidade',
                transform=ax.transAxes, fontsize=9, color='gray',
                verticalalignment='top', style='italic')
        plt.tight_layout()
        savefig('correlacao_cpu_latencia.png')
        plt.show()
        print(f'Pearson r (CPU pico × latência 2PC mediana): {r:.4f}')
""")

code("""
# ── Coeficiente de Variação por métrica ─────────────────────────────────────
if not res.empty:
    mw_pico = res[(res['Fase']=='pico') &
                  res['container'].str.contains('middleware', case=False, na=False)]
    metricas = {
        'CPU (%)':        mw_pico['cpu_pct'],
        'Memória (MiB)':  mw_pico['mem_mb'],
        'Net TX (MiB)':   mw_pico['net_tx_mb'],
        'Net RX (MiB)':   mw_pico['net_rx_mb'],
    }
    cv_rows = []
    for nome, serie in metricas.items():
        s = serie.dropna()
        cv = s.std()/s.mean()*100 if s.mean() else np.nan
        cv_rows.append({'Métrica': nome, 'Média': s.mean(),
                        'DP': s.std(), 'CV (%)': cv,
                        'Estável (<15%)': '✓' if cv < 15 else ('⚠' if cv < 30 else '✗')})

    cv_df = pd.DataFrame(cv_rows)
    display(cv_df.set_index('Métrica').round(3))

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(cv_df['Métrica'], cv_df['CV (%)'],
                  color=['steelblue' if v < 15 else ('goldenrod' if v < 30 else 'tomato')
                         for v in cv_df['CV (%)']])
    ax.axhline(15, color='green',  linestyle='--', linewidth=1, label='CV=15% (estável)')
    ax.axhline(30, color='orange', linestyle='--', linewidth=1, label='CV=30% (atenção)')
    ax.set_ylabel('CV (%)'); ax.set_title('Coeficiente de Variação por Métrica — fase pico')
    ax.legend(fontsize=9)
    plt.tight_layout()
    savefig('cv_metricas.png')
    plt.show()
""")

# ===========================================================================
# 11. SUMÁRIO ESTATÍSTICO E CONFORMIDADE RNF
# ===========================================================================

md("""
### Interpretação — Análises Cruzadas

**Correlação CPU × Latência 2PC**: gráfico observacional entre CPU média do middleware na fase `pico` (por run) e latência 2PC mediana (por run). Um Pearson `r` positivo elevado sugere colinearidade, mas **não implica causalidade** — ambas podem ser determinadas por uma variável comum (ex.: tamanho da fila Kafka no momento da coleta).

**Coeficiente de Variação por métrica**: CV = σ/μ × 100%. Barras verdes (CV < 15%) indicam métricas estáveis — critério RNF07. Amarelo (15–30%) merece atenção; vermelho (> 30%) indica comportamento imprevisível. O Net IO tem CV naturalmente alto por ser cumulativo e sensível ao momento exato de amostragem dentro da fase `pico`.
""")

md("## 11. Sumário Estatístico e Conformidade com RNFs")

code("""
# ── Tabela de estatísticas consolidadas ─────────────────────────────────────
rows = []

if not res.empty:
    mw_pico = res[(res['Fase']=='pico') &
                  res['container'].str.contains('middleware', case=False, na=False)]
    rows.append(summary_stats(mw_pico['cpu_pct'],  'CPU middleware — pico (%)'))
    rows.append(summary_stats(mw_pico['mem_mb'],   'Memória middleware — pico (MiB)'))
    mw_rep = res[(res['Fase']=='repouso') &
                 res['container'].str.contains('middleware', case=False, na=False)]
    rows.append(summary_stats(mw_rep['cpu_pct'],   'CPU middleware — repouso (%)'))

if not pr.empty and 'latencia_2pc_s' in pr.columns:
    rows.append(summary_stats(
        pr[pr['status']=='FINISHED']['latencia_2pc_s'], 'Latência 2PC (s)'))

if not jtl.empty and elapsed_col in jtl.columns:
    rows.append(summary_stats(jtl[elapsed_col], 'Latência HTTP submissão (ms)'))

if not summary.empty and col_comp:
    rows.append(summary_stats(summary[col_comp], 'Completude (%)'))
if not summary.empty and col_tempo:
    rows.append(summary_stats(summary[col_tempo], 'Tempo processamento run (s)'))

if rows:
    stat_df = pd.DataFrame(rows).set_index('Métrica')
    print('\\n── Tabela Estatística Consolidada ──')
    display(stat_df.round(3))
    stat_df.round(3).to_csv(BASE / 'estatisticas_consolidadas.csv')
    print(f'\\nExportado: {BASE / "estatisticas_consolidadas.csv"}')
""")

code("""
# ── Conformidade com RNFs ────────────────────────────────────────────────────
rnf_check = []

def check(rnf_id, descricao, criterio, valor, ok):
    status = '✓ Atendido' if ok else '✗ Não atendido'
    rnf_check.append({'RNF': rnf_id, 'Critério': criterio,
                      'Valor Observado': valor, 'Status': status})

if not summary.empty and col_comp:
    v = summary[col_comp].min()
    check('RNF01', 'Completude', '≥ 99.5%', f'{v:.2f}%', v >= 99.5)

if not pr.empty and 'latencia_2pc_s' in pr.columns:
    v = pr[pr['status']=='FINISHED']['latencia_2pc_s'].quantile(.95)
    check('RNF02', 'Latência 2PC P95', '≤ 10s', f'{v:.2f}s', v <= 10)

if not jtl.empty and elapsed_col in jtl.columns:
    v = jtl[elapsed_col].quantile(.99)
    check('RNF03', 'Latência HTTP P99', '≤ 500ms', f'{v:.0f}ms', v <= 500)

if not res.empty:
    v = res[(res['Fase']=='pico') &
            res['container'].str.contains('middleware', case=False, na=False)]['cpu_pct'].max()
    check('RNF04', 'CPU máx middleware', '≤ 70%', f'{v:.1f}%', v <= 70)

if not scale_sum.empty and col_t and 'n_servicos' in scale_sum.columns:
    agg_e = scale_sum.groupby('n_servicos')[col_t].mean()
    t1_v  = agg_e.get(1, np.nan)
    t4_v  = agg_e.get(4, np.nan)
    if not np.isnan(t1_v) and not np.isnan(t4_v):
        ef = (t1_v / (4 * t4_v)) * 100
        check('RNF05', 'Eficiência escalabilidade', '≥ 70%', f'{ef:.1f}%', ef >= 70)

if not summary.empty and col_tempo:
    v = summary[col_tempo].std() / summary[col_tempo].mean() * 100
    check('RNF07', 'CV tempo de processamento', '≤ 15%', f'{v:.1f}%', v <= 15)

if rnf_check:
    rnf_df = pd.DataFrame(rnf_check)
    display(rnf_df.set_index('RNF'))
    rnf_df.to_csv(BASE / 'conformidade_rnf.csv', index=False)
    print(f'\\nExportado: {BASE / "conformidade_rnf.csv"}')

    total   = len(rnf_df)
    atendidos = rnf_df['Status'].str.contains('Atendido').sum()
    print(f'\\nRNFs atendidos: {atendidos}/{total}')
else:
    print('Dados insuficientes para verificação de RNFs.')
""")

# ===========================================================================
# 12. CONCLUSÃO DO NOTEBOOK
# ===========================================================================

md("""
## 12. Arquivos Gerados

Todos os arquivos foram salvos em `output-benchmark/`:

| Arquivo | Conteúdo |
|---|---|
| `figures/completude_throughput.png` | Completude e tempo por run |
| `figures/cpu_por_fase.png` | CPU por fase e container |
| `figures/memoria_por_fase.png` | Memória e estabilidade |
| `figures/io_rede_disco.png` | Net IO e Block IO |
| `figures/latencia_2pc.png` | Distribuição, ECDF e percentis da latência 2PC |
| `figures/latencia_http_jmeter.png` | Latência HTTP de submissão (JMeter) |
| `figures/escalabilidade.png` | Tempo, speedup e eficiência |
| `figures/escalabilidade_boxplot.png` | Variabilidade por configuração |
| `figures/correlacao_cpu_latencia.png` | Correlação observacional CPU × latência |
| `figures/cv_metricas.png` | Coeficiente de variação por métrica |
| `estatisticas_consolidadas.csv` | Tabela estatística completa (bootstrap IC95%) |
| `conformidade_rnf.csv` | Checklist de conformidade com os RNFs |

> **Próximo passo**: use os arquivos de figuras e tabelas diretamente na dissertação LaTeX.
""")

# ===========================================================================
# SERIALIZAÇÃO DO NOTEBOOK
# ===========================================================================

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.9.0"
        }
    },
    "cells": CELLS,
}

out_dir = Path(__file__).parent.parent / 'output-benchmark'
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / 'analise_benchmark.ipynb'

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print(f'Notebook gerado: {out_path.resolve()}')
print(f'Total de células: {len(CELLS)}')
print()
print('Para abrir:')
print(f'  jupyter notebook {out_path}')
print(f'  # ou')
print(f'  jupyter lab {out_path}')
