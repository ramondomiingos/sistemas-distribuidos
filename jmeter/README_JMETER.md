# 🚀 Testes de Estresse com Apache JMeter

## 📋 Visão Geral

Este diretório contém testes de estresse para o endpoint de requisições de privacidade LGPD usando Apache JMeter.

Dada a natureza assíncrona da arquitetura proposta, a medição do throughput
requer uma definição precisa do que constitui uma “operação concluída”. E não um retorno do endpoint chamado, então após rodar o test de estresse énecessário fazer consultas no banco de dados.
## 🎯 Cenários de Teste

O plano de teste `Privacy_Request_Stress_Test.jmx` executa **4 cenários** sequenciais:

| Cenário | Threads | Ramp-up | Delay | Objetivo |
|---------|---------|---------|-------|----------|
| **Cenário 1** | 1 | 1s | 0s | Teste funcional básico |
| **Cenário 2** | 10 | 2s | 5s | Carga leve |
| **Cenário 3** | 100 | 10s | 15s | Carga moderada |
| **Cenário 4** | 900 | 30s | 30s | **Estresse máximo** |

### 📊 Detalhes dos Cenários

#### Cenário 1: 1 Requisição
- **Objetivo:** Validação funcional
- **Threads:** 1 usuário
- **Descrição:** Verifica se o endpoint responde corretamente

#### Cenário 2: 10 Requisições
- **Objetivo:** Carga leve
- **Threads:** 10 usuários simultâneos
- **Ramp-up:** 2 segundos (5 usuários/segundo)
- **Delay:** 5 segundos após cenário anterior

#### Cenário 3: 100 Requisições
- **Objetivo:** Carga moderada
- **Threads:** 100 usuários simultâneos
- **Ramp-up:** 10 segundos (10 usuários/segundo)
- **Delay:** 15 segundos após cenário anterior

#### Cenário 4: 900 Requisições (Estresse)
- **Objetivo:** Estresse máximo do sistema
- **Threads:** 900 usuários simultâneos
- **Ramp-up:** 30 segundos (30 usuários/segundo)
- **Delay:** 30 segundos após cenário anterior
- **⚠️ ATENÇÃO:** Este cenário pode causar alta carga no sistema

## 🔧 Configuração

### Variáveis Globais

Editáveis no plano de teste:

```properties
BASE_URL=localhost
PORT=8000
API_PATH=/api/v1/privacy-requests/
```

### Requisições HTTP

Todas as requisições usam:
- **Método:** POST
- **Content-Type:** application/json
- **Timeout de conexão:** 5000ms
- **Timeout de resposta:** 30000ms

### Payload JSON

```json
{
  "account_id": "USER_{UUID único}",
  "operation": "DELETE",
  "description": "Teste JMeter - Cenario X - Thread Y"
}
```

Cada thread gera um `account_id` único usando `${__UUID()}`.

## 📦 Instalação do JMeter

### macOS (Homebrew)

```bash
brew install jmeter
```

### Linux (Ubuntu/Debian)

```bash
# Instalar Java (requisito)
sudo apt update
sudo apt install default-jdk -y

# Baixar e instalar JMeter
wget https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.tgz
tar -xzf apache-jmeter-5.6.3.tgz
sudo mv apache-jmeter-5.6.3 /opt/jmeter
echo 'export PATH=$PATH:/opt/jmeter/bin' >> ~/.bashrc
source ~/.bashrc
```


## 🚀 Executando os Testes

### Modo GUI (Interface Gráfica)

```bash
cd jmeter
jmeter -t Privacy_Request_Stress_Test.jmx
```

**⚠️ Importante:** Use o modo GUI apenas para **desenvolvimento e debug**. Para testes de carga reais, use o modo CLI.

### Modo CLI (Linha de Comando) - RECOMENDADO

```bash
# Criar diretório de resultados
mkdir -p results

# Executar teste completo
jmeter -n -t Privacy_Request_Stress_Test.jmx \
  -l results/results_$(date +%Y%m%d_%H%M%S).jtl \
  -e -o results/html_report_$(date +%Y%m%d_%H%M%S)

# Executar com log detalhado
jmeter -n -t Privacy_Request_Stress_Test.jmx \
  -l results/results.jtl \
  -j results/jmeter.log \
  -e -o results/html_report
```

### Parâmetros CLI

- `-n` : Modo não-GUI (CLI)
- `-t` : Arquivo de teste (.jmx)
- `-l` : Arquivo de log de resultados (.jtl)
- `-j` : Log do JMeter
- `-e` : Gerar relatório dashboard
- `-o` : Diretório de saída do relatório HTML

### Executar Cenários Individuais

Para executar apenas um cenário específico, edite o arquivo `.jmx` e desabilite os outros Thread Groups (set `enabled="false"`).

## 📈 Relatórios Gerados

### Relatórios em Tempo Real (Modo GUI)

1. **View Results Tree** - Detalhes de cada requisição
2. **Summary Report** - Resumo estatístico
3. **Aggregate Report** - Métricas agregadas (média, mediana, percentis)
4. **Graph Results** - Gráfico de desempenho
5. **Response Time Graph** - Gráfico de tempo de resposta

### Relatório HTML (Modo CLI)

Após executar com `-e -o`, abra:

```bash
open results/html_report/index.html
```

O relatório HTML inclui:
- ✅ Dashboard interativo
- ✅ Estatísticas de throughput
- ✅ Tempos de resposta (média, mediana, percentis)
- ✅ Taxa de erro
- ✅ Gráficos temporais
- ✅ Distribuição de tempo de resposta

## 📊 Métricas Importantes



## 🔍 Monitoramento do Sistema

### Durante o Teste, Monitore:

#### 1. Docker Stats (Containers)

```bash
docker stats
```

#### 2. Logs do Middleware

```bash
docker logs -f middleware-refactor
```

#### 3. Kafka Consumer Lag

```bash
docker exec -it kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --all-groups
```

#### 4. PostgreSQL Connections

```bash
docker exec -it middleware-db psql -U postgres -d middleware -c \
  "SELECT count(*) FROM pg_stat_activity;"
```





## 🐛 Troubleshooting

### Erro: "Address already in use"

```bash
# Verificar se o middleware está rodando
curl http://localhost:8000/api/v1/privacy-requests/
```

### Erro: "Connection refused"

```bash
# Verificar se o Docker está rodando
docker compose ps

# Iniciar serviços
docker compose up -d
```

### Performance Lenta

```bash
# Aumentar memória do JMeter
export JVM_ARGS="-Xms1024m -Xmx4096m"
jmeter -n -t Privacy_Request_Stress_Test.jmx -l results/results.jtl
```

### Too Many Open Files

```bash
# Linux/macOS
ulimit -n 10000

# Verificar
ulimit -n
```

## 📝 Boas Práticas

### ✅ DO:

- ✅ Usar modo CLI para testes de carga
- ✅ Executar testes em ambiente isolado
- ✅ Monitorar recursos durante testes
- ✅ Fazer warm-up antes de testes críticos
- ✅ Analisar logs após cada execução
- ✅ Documentar resultados

### ❌ DON'T:

- ❌ Usar modo GUI para testes pesados (> 100 threads)
- ❌ Executar em produção sem aviso
- ❌ Ignorar timeouts e erros
- ❌ Esquecer de limpar dados de teste
- ❌ Executar múltiplos testes simultaneamente

## 📂 Estrutura de Diretórios

```
jmeter/
├── Privacy_Request_Stress_Test.jmx  # Plano de teste principal
├── README_JMETER.md                 # Esta documentação
└── results/                          # Resultados dos testes (gerado)
    ├── *.jtl                        # Logs de resultados
    ├── *.csv                        # Relatórios CSV
    ├── *.xml                        # Resultados XML
    └── html_report_*/               # Relatórios HTML
        └── index.html               # Dashboard principal
```

## 🔗 Referências

- [Apache JMeter Documentation](https://jmeter.apache.org/usermanual/index.html)
- [JMeter Best Practices](https://jmeter.apache.org/usermanual/best-practices.html)
- [JMeter Functions](https://jmeter.apache.org/usermanual/functions.html)

## 📧 Suporte

Para dúvidas ou problemas:
- Abrir issue no repositório
- Verificar documentação oficial do JMeter

---

**Desenvolvido para:** Middleware de Privacidade   
**Autor:** Ramon Domingos  
**Data:** Janeiro 2026  
**Versão:** 1.0.0
