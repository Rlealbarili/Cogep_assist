#!/bin/bash

# Script de Configuração Automática - Cogep Assist
# Este script automatiza a configuração inicial do ambiente

set -e  # Sair em caso de erro

echo "================================================"
echo "   Cogep Assist - Setup Automático"
echo "================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Verificar pré-requisitos
echo "1. Verificando pré-requisitos..."
if ! command_exists docker; then
    echo -e "${RED}✗ Docker não encontrado. Instale o Docker antes de continuar.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker instalado${NC}"

if ! command_exists docker-compose; then
    echo -e "${RED}✗ Docker Compose não encontrado. Instale o Docker Compose antes de continuar.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose instalado${NC}"
echo ""

# 2. Verificar arquivo .env
echo "2. Verificando arquivo .env..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ Arquivo .env não encontrado. Criando a partir do .env.example...${NC}"

    if [ ! -f .env.example ]; then
        echo -e "${RED}✗ Arquivo .env.example não encontrado!${NC}"
        exit 1
    fi

    cp .env.example .env
    echo -e "${YELLOW}⚠ ATENÇÃO: Edite o arquivo .env e substitua as senhas placeholder!${NC}"
    echo -e "${YELLOW}   Use: nano .env ou vim .env${NC}"
    echo ""

    # Gerar senhas sugeridas
    echo -e "${GREEN}Sugestões de senhas seguras:${NC}"
    echo "POSTGRES_PASSWORD=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")"
    echo "TIMESCALE_PASSWORD=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")"
    echo ""

    read -p "Pressione ENTER depois de editar o arquivo .env..."
else
    echo -e "${GREEN}✓ Arquivo .env encontrado${NC}"
fi
echo ""

# 3. Verificar se as senhas foram alteradas
echo "3. Verificando configuração de senhas..."
if grep -q "sua_senha_segura_aqui\|trading_password_segura" .env; then
    echo -e "${RED}✗ ERRO: Você ainda está usando senhas placeholder!${NC}"
    echo -e "${YELLOW}   Edite o arquivo .env e substitua as senhas antes de continuar.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Senhas configuradas${NC}"
echo ""

# 4. Parar containers existentes (se houver)
echo "4. Parando containers existentes (se houver)..."
docker-compose down 2>/dev/null || true
echo -e "${GREEN}✓ Containers parados${NC}"
echo ""

# 5. Subir containers
echo "5. Iniciando containers Docker..."
docker-compose up -d
echo -e "${GREEN}✓ Containers iniciados${NC}"
echo ""

# 6. Aguardar containers ficarem saudáveis
echo "6. Aguardando containers ficarem saudáveis..."
sleep 5

MAX_WAIT=30
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    HEALTHY=$(docker-compose ps | grep -c "healthy" || echo "0")
    if [ "$HEALTHY" -ge 3 ]; then
        echo -e "${GREEN}✓ Todos os containers estão saudáveis${NC}"
        break
    fi
    echo -n "."
    sleep 2
    WAIT_TIME=$((WAIT_TIME + 2))
done
echo ""

# 7. Verificar status
echo "7. Status dos containers:"
docker-compose ps
echo ""

# 8. Teste de conectividade
echo "8. Testando conectividade..."

# Teste PostgreSQL
if docker exec cogep_assist_postgres pg_isready -U cogep_admin -d cogep_assist >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL: Conectado${NC}"
else
    echo -e "${RED}✗ PostgreSQL: Falha na conexão${NC}"
fi

# Teste TimescaleDB
if docker exec cogep_assist_timescale pg_isready -U trading_admin -d trading_timeseries >/dev/null 2>&1; then
    echo -e "${GREEN}✓ TimescaleDB: Conectado${NC}"
else
    echo -e "${RED}✗ TimescaleDB: Falha na conexão${NC}"
fi

# Teste Redis
if docker exec cogep_assist_redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis: Conectado${NC}"
else
    echo -e "${RED}✗ Redis: Falha na conexão${NC}"
fi
echo ""

# 9. Aplicar migrações (se Python estiver disponível)
if command_exists python3; then
    echo "9. Verificando migrações do banco de dados..."

    if [ -f requirements.txt ]; then
        echo -e "${YELLOW}⚠ Execute: pip install -r requirements.txt${NC}"
        echo -e "${YELLOW}⚠ Depois execute: alembic upgrade head${NC}"
    fi
else
    echo "9. Python não encontrado. Pule as migrações por enquanto."
fi
echo ""

# Conclusão
echo "================================================"
echo -e "${GREEN}✓ Setup concluído com sucesso!${NC}"
echo "================================================"
echo ""
echo "Próximos passos:"
echo "  1. pip install -r requirements.txt"
echo "  2. alembic upgrade head"
echo "  3. Configure OPENAI_API_KEY no .env (se necessário)"
echo "  4. Configure Ollama para Qwen 2.5:14b"
echo ""
echo "Para parar os containers: docker-compose stop"
echo "Para ver logs: docker-compose logs -f"
echo ""
