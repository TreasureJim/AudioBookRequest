"""Add qbittorrent and moving support

Revision ID: 8b4b238dee89
Revises: d0fac85afd0f
Create Date: 2026-03-13 21:44:36.493654

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '8b4b238dee89'
down_revision: Union[str, None] = 'd0fac85afd0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('author',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asin', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('save_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('asin'),
    sa.UniqueConstraint('name')
    )
    op.create_table('series',
    sa.Column('asin', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('save_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.PrimaryKeyConstraint('asin')
    )
    op.create_table('audiobookauthorlink',
    sa.Column('audiobook_asin', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('author_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['audiobook_asin'], ['audiobook.asin'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['author_id'], ['author.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('audiobook_asin', 'author_id')
    )
    op.create_table('audiobookserieslink',
    sa.Column('audiobook_asin', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('series_asin', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sequence', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.ForeignKeyConstraint(['audiobook_asin'], ['audiobook.asin'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['series_asin'], ['series.asin'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('audiobook_asin', 'series_asin')
    )
    with op.batch_alter_table('audiobook', schema=None) as batch_op:
        batch_op.add_column(sa.Column('download_progress', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('download_client_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column('moved', sa.Boolean(), nullable=False))
        batch_op.drop_column('authors')


def downgrade() -> None:
    with op.batch_alter_table('audiobook', schema=None) as batch_op:
        batch_op.add_column(sa.Column('authors', sqlite.JSON(), nullable=True))
        batch_op.drop_column('moved')
        batch_op.drop_column('download_client_hash')
        batch_op.drop_column('download_progress')

    op.drop_table('audiobookserieslink')
    op.drop_table('audiobookauthorlink')
    op.drop_table('series')
    op.drop_table('author')
