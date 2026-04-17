"""add composite index (privacy_request_id, operation) on privacy_requests_services

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 00:00:00.000000

O COUNT query em _count_responses filtra por (privacy_request_id, operation).
O índice simples em privacy_request_id já ajuda, mas o índice composto elimina
qualquer filtragem residual e permite um index-only scan no PostgreSQL,
o que importa quando a tabela acumula dezenas de milhares de linhas ao longo
dos 80 runs do benchmark.

Também remove o índice simples em privacy_request_id que fica redundante:
o índice composto (A, B) atende consultas que filtram só por A (prefixo esquerdo).
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Índice composto cobre WHERE privacy_request_id=? AND operation=?
    # e também consultas que filtram só por privacy_request_id (prefixo esquerdo).
    op.create_index(
        'ix_prs_request_id_operation',
        'privacy_requests_services',
        ['privacy_request_id', 'operation'],
    )
    # Remove o índice simples agora redundante.
    op.drop_index(
        'ix_privacy_requests_services_privacy_request_id',
        table_name='privacy_requests_services',
    )


def downgrade() -> None:
    op.create_index(
        'ix_privacy_requests_services_privacy_request_id',
        'privacy_requests_services',
        ['privacy_request_id'],
    )
    op.drop_index(
        'ix_prs_request_id_operation',
        table_name='privacy_requests_services',
    )
