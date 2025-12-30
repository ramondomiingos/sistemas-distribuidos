# Dockerfile

# 1. Imagem base oficial do Python
FROM python:3.11-slim

# 2. Define o diretório de trabalho
WORKDIR /app

# 3. Copia os arquivos de dependências
COPY requirements.txt .

# 4. Instala as dependências do sistema e do Python
RUN apt-get update && \
    apt-get install -y gcc libpq-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apt-get remove -y gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# 5. Copia o restante do código da aplicação
COPY . .

# 6. Expõe a porta padrão do FastAPI/Uvicorn
EXPOSE 8000

# 7. Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]