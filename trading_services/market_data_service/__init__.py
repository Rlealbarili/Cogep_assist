"""
Market Data Service
===================

Responsável por:
- Conectar aos WebSockets de exchanges (Alpaca, OANDA)
- Ingerir ticks de mercado em tempo real
- Publicar dados no Redis Pub/Sub (canal: market:ticks:<SYMBOL>)
- Armazenar OHLCV no TimescaleDB
"""
