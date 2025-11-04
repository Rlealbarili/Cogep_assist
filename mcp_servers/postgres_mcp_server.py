#!/usr/bin/env python3
"""
MCP Server para PostgreSQL - Cogep_assist
Versao minimalista e estavel
"""

import sys
import json
import logging
import psycopg2

# Forcar UTF-8 no Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', newline='')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', newline='')

# Configurar logging
log_file = "C:\\Cogep_assist\\mcp_servers\\postgres_mcp.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

logger.info("=== Iniciando PostgreSQL MCP Server ===")

# Configuracao do banco
DB_CONFIG = {
    "dbname": "cogep_db",
    "user": "agent_app",
    "password": "Qwe123rty456",
    "host": "localhost",
    "port": "5432"
}

conn = None

def test_connection():
    """Testa conexao com o banco"""
    global conn
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("[OK] Conectado ao PostgreSQL com sucesso!")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Erro de conexao: {e}")
        return False

def get_connection():
    """Obter conexao"""
    global conn
    try:
        if conn is None or conn.closed:
            conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar: {e}")
        return None

def list_tables():
    """Lista tabelas do banco"""
    logger.info("list_tables chamado")
    try:
        c = get_connection()
        if not c:
            return {"error": "Sem conexao"}
        
        with c.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            logger.info(f"Encontradas {len(tables)} tabelas")
            return {"tables": tables, "count": len(tables)}
    except Exception as e:
        logger.error(f"Erro em list_tables: {e}")
        return {"error": str(e)}

def get_table_schema(table_name):
    """Obtem schema de uma tabela"""
    logger.info(f"get_table_schema chamado para: {table_name}")
    try:
        c = get_connection()
        if not c:
            return {"error": "Sem conexao"}
        
        with c.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            
            columns = [
                {"name": row[0], "type": row[1], "nullable": row[2] == 'YES'}
                for row in cur.fetchall()
            ]
            logger.info(f"Schema obtido para {table_name}")
            return {"table": table_name, "columns": columns}
    except Exception as e:
        logger.error(f"Erro em get_table_schema: {e}")
        return {"error": str(e)}

def execute_query(query):
    """Executa query SELECT"""
    logger.info(f"execute_query: {query}")
    try:
        c = get_connection()
        if not c:
            return {"error": "Sem conexao"}
        
        with c.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"Query retornou {len(data)} linhas")
            return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"Erro em execute_query: {e}")
        return {"error": str(e)}

def count_rows(table_name):
    """Conta linhas em tabela"""
    logger.info(f"count_rows chamado para: {table_name}")
    try:
        c = get_connection()
        if not c:
            return {"error": "Sem conexao"}
        
        with c.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            logger.info(f"Tabela {table_name} tem {count} linhas")
            return {"table": table_name, "count": count}
    except Exception as e:
        logger.error(f"Erro em count_rows: {e}")
        return {"error": str(e)}

def get_table_data(table_name, limit=10):
    """Obtem dados de tabela"""
    logger.info(f"get_table_data para {table_name} com limit {limit}")
    try:
        c = get_connection()
        if not c:
            return {"error": "Sem conexao"}
        
        with c.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"Obtidos {len(data)} registros")
            return {"table": table_name, "limit": limit, "rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"Erro em get_table_data: {e}")
        return {"error": str(e)}

def handle_request(request):
    """Processa requisicoes MCP"""
    try:
        logger.info(f"Requisicao recebida: {request}")
        
        method = request.get("method")
        request_id = request.get("id", "unknown")
        
        if method == "initialize":
            logger.info("Inicializando servidor")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "PostgreSQL-COGEP",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            logger.info("Listando ferramentas")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_tables",
                            "description": "Lista todas as tabelas",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "get_table_schema",
                            "description": "Obtem schema de uma tabela",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"table_name": {"type": "string"}},
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "execute_query",
                            "description": "Executa query SELECT",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "count_rows",
                            "description": "Conta linhas em tabela",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"table_name": {"type": "string"}},
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "get_table_data",
                            "description": "Obtem dados de tabela",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string"},
                                    "limit": {"type": "integer", "default": 10}
                                },
                                "required": ["table_name"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            arguments = request.get("params", {}).get("arguments", {})
            
            logger.info(f"Chamando ferramenta: {tool_name}")
            
            if tool_name == "list_tables":
                result = list_tables()
            elif tool_name == "get_table_schema":
                result = get_table_schema(arguments.get("table_name", ""))
            elif tool_name == "execute_query":
                result = execute_query(arguments.get("query", ""))
            elif tool_name == "count_rows":
                result = count_rows(arguments.get("table_name", ""))
            elif tool_name == "get_table_data":
                result = get_table_data(arguments.get("table_name", ""), arguments.get("limit", 10))
            else:
                result = {"error": f"Ferramenta desconhecida: {tool_name}"}
            
            logger.info(f"Resultado: {result}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
                }
            }
        
        else:
            logger.warning(f"Metodo des
