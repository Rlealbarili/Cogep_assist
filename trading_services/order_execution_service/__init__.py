"""
Order Execution Service
========================

Responsável por:
- Subscrever ao canal orders:execute do Redis
- Executar ordens via API da exchange (Alpaca/OANDA)
- Implementar retry logic com exponential backoff
- Logar resultados (sucesso/falha) no PostgreSQL
- ÚNICO componente com credenciais de API write
"""
