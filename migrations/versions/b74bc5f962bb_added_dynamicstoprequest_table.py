"""Added DynamicStopRequest table

Revision ID: b74bc5f962bb
Revises: 
Create Date: 2025-03-19 17:52:02.664837

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b74bc5f962bb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('route')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('route',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('route_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('start_point', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('end_point', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='route_pkey')
    )
    # ### end Alembic commands ###
