"""add indexes privacy_request_id and service_id

Revision ID: a1b2c3d4e5f6
Revises: dcae4810489c
Create Date: 2026-04-15 00:00:00.000000

Sem índice em privacy_request_id, cada verificação do 2PC (should_publish_execute,
should_finished_request) fazia full table scan em privacy_requests_services.
Com 360k registros acumulados ao final dos 80 runs, a latência por requisição
subia de ~1s para ~120s. Índices eliminam a degradação.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dcae4810489c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_privacy_requests_services_privacy_request_id',
        'privacy_requests_services',
        ['privacy_request_id'],
    )
    op.create_index(
        'ix_privacy_requests_services_service_id',
        'privacy_requests_services',
        ['service_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_privacy_requests_services_service_id',
                  table_name='privacy_requests_services')
    op.drop_index('ix_privacy_requests_services_privacy_request_id',
                  table_name='privacy_requests_services')
