#!/bin/bash

##############################################################################
# Script de Execução de Testes JMeter
# Middleware de Privacidade LGPD
##############################################################################

set -e  # Sair em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
JMETER_TEST="Privacy_Request_Stress_Test.jmx"
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="${RESULTS_DIR}/results_${TIMESTAMP}.jtl"
HTML_REPORT="${RESULTS_DIR}/html_report_${TIMESTAMP}"
LOG_FILE="${RESULTS_DIR}/jmeter_${TIMESTAMP}.log"

# Verificar se JMeter está instalado
check_jmeter() {
    echo -e "${BLUE}[1/7] Verificando instalação do JMeter...${NC}"
    if ! command -v jmeter &> /dev/null; then
        echo -e "${RED}❌ JMeter não encontrado!${NC}"
        echo -e "${YELLOW}Instale o JMeter com:${NC}"
        echo -e "  macOS: brew install jmeter"
        echo -e "  Linux: sudo apt install jmeter"
        exit 1
    fi
    echo -e "${GREEN}✅ JMeter instalado: $(jmeter --version 2>&1 | head -n 1)${NC}"
}

# Verificar se o middleware está rodando
check_middleware() {
    echo -e "${BLUE}[2/7] Verificando se o middleware está rodando...${NC}"
    if ! curl -s -f http://localhost:8000/docs > /dev/null; then
        echo -e "${RED}❌ Middleware não está respondendo em http://localhost:8000${NC}"
        echo -e "${YELLOW}Inicie o middleware com:${NC}"
        echo -e "  docker compose up -d"
        exit 1
    fi
    echo -e "${GREEN}✅ Middleware está rodando${NC}"
}

# Criar diretório de resultados
create_results_dir() {
    echo -e "${BLUE}[3/7] Criando diretório de resultados...${NC}"
    mkdir -p ${RESULTS_DIR}
    echo -e "${GREEN}✅ Diretório criado: ${RESULTS_DIR}/${NC}"
}

# Limpar resultados antigos (opcional)
cleanup_old_results() {
    echo -e "${BLUE}[4/7] Limpando resultados antigos...${NC}"
    read -p "Deseja limpar resultados antigos? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ${RESULTS_DIR}/results_*.jtl
        rm -rf ${RESULTS_DIR}/html_report_*
        rm -rf ${RESULTS_DIR}/jmeter_*.log
        echo -e "${GREEN}✅ Resultados antigos removidos${NC}"
    else
        echo -e "${YELLOW}⏭️  Mantendo resultados antigos${NC}"
    fi
}

# Mostrar informações do teste
show_test_info() {
    echo -e "${BLUE}[5/7] Informações do Teste${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "📝 Arquivo de Teste: ${JMETER_TEST}"
    echo -e "📊 Resultados: ${RESULTS_FILE}"
    echo -e "📈 Relatório HTML: ${HTML_REPORT}"
    echo -e "📋 Log: ${LOG_FILE}"
    echo -e ""
    echo -e "🎯 Cenários:"
    echo -e "  - Cenário 1: 1 requisição"
    echo -e "  - Cenário 2: 10 requisições (ramp-up 2s)"
    echo -e "  - Cenário 3: 100 requisições (ramp-up 10s)"
    echo -e "  - Cenário 4: 900 requisições (ramp-up 30s) 🔥"
    echo -e ""
    echo -e "⏱️  Tempo estimado: ~2-3 minutos"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Executar teste
run_test() {
    echo -e "${BLUE}[6/7] Executando teste...${NC}"
    echo -e "${YELLOW}⚠️  Não feche este terminal durante a execução!${NC}"
    echo ""
    
    # Aumentar limite de arquivos abertos
    ulimit -n 10000 2>/dev/null || true
    
    # Executar JMeter em modo CLI
    jmeter -n \
        -t ${JMETER_TEST} \
        -l ${RESULTS_FILE} \
        -j ${LOG_FILE} \
        -e \
        -o ${HTML_REPORT}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Teste executado com sucesso!${NC}"
    else
        echo -e "${RED}❌ Erro ao executar teste!${NC}"
        echo -e "${YELLOW}Verifique o log: ${LOG_FILE}${NC}"
        exit 1
    fi
}

# Gerar resumo
generate_summary() {
    echo -e "${BLUE}[7/7] Gerando resumo...${NC}"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "${RESULTS_FILE}" ]; then
        # Contar total de requisições
        TOTAL=$(awk -F',' 'END {print NR-1}' ${RESULTS_FILE})
        
        # Contar sucessos
        SUCCESS=$(awk -F',' '$8=="true" {count++} END {print count+0}' ${RESULTS_FILE})
        
        # Contar erros
        ERRORS=$((TOTAL - SUCCESS))
        
        # Calcular tempo médio
        AVG_TIME=$(awk -F',' 'NR>1 {sum+=$2; count++} END {print sum/count}' ${RESULTS_FILE})
        
        # Taxa de erro
        ERROR_RATE=$(awk -v errors=$ERRORS -v total=$TOTAL 'BEGIN {printf "%.2f", (errors/total)*100}')
        
        echo -e "📊 ${GREEN}Resumo dos Resultados${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "Total de Requisições: ${BLUE}${TOTAL}${NC}"
        echo -e "Requisições Sucedidas: ${GREEN}${SUCCESS}${NC}"
        echo -e "Requisições com Erro: ${RED}${ERRORS}${NC}"
        echo -e "Taxa de Erro: ${YELLOW}${ERROR_RATE}%${NC}"
        echo -e "Tempo Médio de Resposta: ${BLUE}${AVG_TIME} ms${NC}"
        echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Verificar taxa de erro
        if (( $(echo "$ERROR_RATE > 5.0" | bc -l) )); then
            echo -e "${RED}⚠️  ATENÇÃO: Taxa de erro acima de 5%!${NC}"
        elif (( $(echo "$ERROR_RATE > 0" | bc -l) )); then
            echo -e "${YELLOW}⚠️  Alguns erros detectados. Revise os logs.${NC}"
        else
            echo -e "${GREEN}✅ Nenhum erro detectado!${NC}"
        fi
    fi
}

# Abrir relatório HTML
open_report() {
    echo ""
    echo -e "${GREEN}🎉 Teste concluído!${NC}"
    echo ""
    echo -e "${BLUE}📁 Arquivos gerados:${NC}"
    echo -e "  - Resultados: ${RESULTS_FILE}"
    echo -e "  - Relatório HTML: ${HTML_REPORT}/index.html"
    echo -e "  - Log: ${LOG_FILE}"
    echo ""
    
    read -p "Deseja abrir o relatório HTML? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open ${HTML_REPORT}/index.html
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open ${HTML_REPORT}/index.html 2>/dev/null || \
            sensible-browser ${HTML_REPORT}/index.html 2>/dev/null || \
            echo -e "${YELLOW}Abra manualmente: ${HTML_REPORT}/index.html${NC}"
        else
            echo -e "${YELLOW}Abra manualmente: ${HTML_REPORT}/index.html${NC}"
        fi
    fi
}

# Main
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║         JMeter Stress Test - LGPD Middleware         ║"
    echo "║           Teste de Requisições de Privacidade        ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_jmeter
    check_middleware
    create_results_dir
    cleanup_old_results
    show_test_info
    
    echo ""
    read -p "Deseja continuar com o teste? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}Teste cancelado pelo usuário.${NC}"
        exit 0
    fi
    
    run_test
    generate_summary
    open_report
    
    echo ""
    echo -e "${GREEN}✅ Processo concluído!${NC}"
}

# Executar
main
