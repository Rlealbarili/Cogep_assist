"""
Technical Signal Service
========================

Responsável por:
- Subscrever canais market:ticks:* do Redis
- Agregar ticks em velas OHLCV
- Calcular indicadores técnicos (RSI, MACD, Bollinger Bands)
- Publicar sinais técnicos no Redis (canal: signals:tech:<SYMBOL>)
"""
