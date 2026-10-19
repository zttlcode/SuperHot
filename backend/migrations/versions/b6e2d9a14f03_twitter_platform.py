"""Platform-aware monitors and typed Twitter content; preserve existing TikTok data."""
from alembic import op
import sqlalchemy as sa

revision = 'b6e2d9a14f03'
down_revision = 'aca275d2faf0'
branch_labels = None
depends_on = None


def upgrade():
    convention = {'uq': 'uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s'}
    with op.batch_alter_table('monitors', naming_convention=convention) as batch:
        batch.add_column(sa.Column('platform', sa.String(20), nullable=False, server_default='tiktok'))
        batch.add_column(sa.Column('provider_data', sa.JSON(), nullable=False, server_default='{}'))
        batch.alter_column('sec_uid', existing_type=sa.String(256), nullable=True)
        batch.alter_column('backfill_cursor', existing_type=sa.String(100), type_=sa.Text())
        batch.drop_constraint('uq_monitors_owner_id_author_id', type_='unique')
        batch.create_unique_constraint('uq_monitors_owner_platform_author', ['owner_id', 'platform', 'author_id'])
    # sec_uid remains available for legacy rows; the TikTok adapter reads it as fallback.
    with op.batch_alter_table('posts') as batch:
        batch.add_column(sa.Column('post_type', sa.String(20), nullable=False, server_default='original'))
        batch.add_column(sa.Column('references', sa.JSON(), nullable=False, server_default='[]'))


def downgrade():
    # Removing platform identity while Twitter monitors exist would corrupt identity.
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM monitors WHERE platform <> 'tiktok'")).scalar()
    if count:
        raise RuntimeError('Remove Twitter monitors before downgrading this schema.')
    with op.batch_alter_table('posts') as batch:
        batch.drop_column('references')
        batch.drop_column('post_type')
    with op.batch_alter_table('monitors') as batch:
        batch.drop_constraint('uq_monitors_owner_platform_author', type_='unique')
        batch.create_unique_constraint('uq_monitors_owner_id_author_id', ['owner_id', 'author_id'])
        batch.alter_column('sec_uid', existing_type=sa.String(256), nullable=False)
        batch.alter_column('backfill_cursor', existing_type=sa.Text(), type_=sa.String(100))
        batch.drop_column('provider_data')
        batch.drop_column('platform')
