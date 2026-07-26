"""add role name check constraint

Revision ID: 598c1b53ccb8
Revises: 630b8660218e
Create Date: 2026-07-26 17:53:20.358784

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '598c1b53ccb8'
down_revision = '630b8660218e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_roles_name_valid", "name IN ('admin', 'manager', 'employee')"
        )


def downgrade():
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.drop_constraint("ck_roles_name_valid", type_="check")
