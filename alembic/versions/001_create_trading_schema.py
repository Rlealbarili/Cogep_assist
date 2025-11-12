"""Create trading schema and tables

Revision ID: 001_trading_schema
Revises: 8c18d11615bb
Create Date: 2025-01-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_trading_schema'
down_revision = '8c18d11615bb'  # Última migration do Cogep_assist
branch_labels = None
depends_on = None


def upgrade():
    # Criar schema trading
    op.execute('CREATE SCHEMA IF NOT EXISTS trading')

    # Criar ENUMS no schema trading
    op.execute("""
        CREATE TYPE trading.orderside AS ENUM ('BUY', 'SELL')
    """)

    op.execute("""
        CREATE TYPE trading.orderstatus AS ENUM (
            'PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED'
        )
    """)

    op.execute("""
        CREATE TYPE trading.signaltype AS ENUM ('TECHNICAL', 'SENTIMENT')
    """)

    # Criar tabela market_signals
    op.create_table(
        'market_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('signal_type', postgresql.ENUM('TECHNICAL', 'SENTIMENT', name='signaltype', schema='trading'), nullable=False),
        sa.Column('signal_data', sa.JSON(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=5), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='trading'
    )
    op.create_index(op.f('ix_trading_market_signals_symbol'), 'market_signals', ['symbol'], unique=False, schema='trading')
    op.create_index(op.f('ix_trading_market_signals_timestamp'), 'market_signals', ['timestamp'], unique=False, schema='trading')

    # Criar tabela trading_orders
    op.create_table(
        'trading_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', postgresql.ENUM('BUY', 'SELL', name='orderside', schema='trading'), nullable=False),
        sa.Column('size', sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=5), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED', name='orderstatus', schema='trading'), nullable=False),
        sa.Column('strategy', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('paper_trading', sa.Boolean(), nullable=True),
        sa.Column('execution_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
        schema='trading'
    )
    op.create_index(op.f('ix_trading_trading_orders_order_id'), 'trading_orders', ['order_id'], unique=True, schema='trading')
    op.create_index(op.f('ix_trading_trading_orders_symbol'), 'trading_orders', ['symbol'], unique=False, schema='trading')

    # Criar tabela performance_metrics
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('metric_date', sa.DateTime(), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('avg_latency_ms', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('avg_slippage', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('profitable_trades', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='trading'
    )
    op.create_index(op.f('ix_trading_performance_metrics_symbol'), 'performance_metrics', ['symbol'], unique=False, schema='trading')
    op.create_index(op.f('ix_trading_performance_metrics_metric_date'), 'performance_metrics', ['metric_date'], unique=False, schema='trading')


def downgrade():
    # Remover tabelas
    op.drop_index(op.f('ix_trading_performance_metrics_metric_date'), table_name='performance_metrics', schema='trading')
    op.drop_index(op.f('ix_trading_performance_metrics_symbol'), table_name='performance_metrics', schema='trading')
    op.drop_table('performance_metrics', schema='trading')

    op.drop_index(op.f('ix_trading_trading_orders_symbol'), table_name='trading_orders', schema='trading')
    op.drop_index(op.f('ix_trading_trading_orders_order_id'), table_name='trading_orders', schema='trading')
    op.drop_table('trading_orders', schema='trading')

    op.drop_index(op.f('ix_trading_market_signals_timestamp'), table_name='market_signals', schema='trading')
    op.drop_index(op.f('ix_trading_market_signals_symbol'), table_name='market_signals', schema='trading')
    op.drop_table('market_signals', schema='trading')

    # Remover ENUMs
    op.execute('DROP TYPE trading.signaltype')
    op.execute('DROP TYPE trading.orderstatus')
    op.execute('DROP TYPE trading.orderside')

    # Remover schema
    op.execute('DROP SCHEMA IF EXISTS trading CASCADE')
