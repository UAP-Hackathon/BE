"""VIEW_USER permission for admin and interviewer

Revision ID: ed02177a4c6f
Revises: a0e3d5045d81
Create Date: 2025-05-06 18:58:39.981562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from database import Base


# revision identifiers, used by Alembic.
revision: str = 'ed02177a4c6f'
down_revision: Union[str, None] = 'a0e3d5045d81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.sql import table, column


def upgrade() -> None:
   
    permissions_table = table('permissions',
        column('id', sa.Integer),
        column('name', sa.String),
        column('category', sa.String)
    )
    
    # Insert permissions
    op.bulk_insert(permissions_table,
        [
            {'id': 12, 'name': 'VIEW_USER', 'category': 'GET'}
        ]
    )
    
    # Create role_permissions table reference
    role_permissions_table = table('roles_permissions',
        column('id', sa.Integer),
        column('role_id', sa.Integer),
        column('permission_id', sa.Integer)
    )
    
    # Assign all permissions to ADMIN role
    
    role_permission_entries = []
    
    role_permission_entries.append({
        'id': 13,
        'role_id': 0,  # ADMIN role
        'permission_id': 12
    })
    role_permission_entries.append({
        'id': 14,
        'role_id': 1,  # INTERVIEWER role
        'permission_id': 12
    })


    
    op.bulk_insert(role_permissions_table, role_permission_entries)
    

def downgrade() -> None:
    from sqlalchemy.sql import table, column

    # Define tables and columns for deletion
    role_permissions_table = table('roles_permissions',
        column('permission_id', sa.Integer)
    )
    
    permissions_table = table('permissions',
        column('id', sa.Integer)
    )

    # Delete role-permission associations for VIEW_USER
    op.execute(
        role_permissions_table.delete().where(
            role_permissions_table.c.permission_id == 12
        )
    )

    # Delete the VIEW_USER permission itself
    op.execute(
        permissions_table.delete().where(
            permissions_table.c.id == 12
        )
    )

