"""add_initial_data

Revision ID: a0e3d5045d81
Revises: 4b46dd944c71
Create Date: 2025-03-11 00:11:00.879896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import datetime
import sys
import os

# Add the parent directory to sys.path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import hash


# revision identifiers, used by Alembic.
revision: str = 'a0e3d5045d81'
down_revision: Union[str, None] = '4b46dd944c71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create role table reference
    roles_table = table('roles',
        column('id', sa.Integer),
        column('name', sa.String)
    )
    
    # Insert roles
    op.bulk_insert(roles_table,
        [
            {'id': 0, 'name': 'ADMIN'},
            {'id': 1, 'name': 'INTERVIEWER'},
            {'id': 2, 'name': 'JOB_SEEKER'}
        ]
    )
    
    # Create permissions table reference
    permissions_table = table('permissions',
        column('id', sa.Integer),
        column('name', sa.String),
        column('category', sa.String)
    )
    
    # Insert permissions
    op.bulk_insert(permissions_table,
        [
            # User endpoints
            {'id': 1, 'name': 'CREATE_USER', 'category': 'POST'},
            {'id': 2, 'name': 'UPDATE_USER', 'category': 'PUT'},
            {'id': 3, 'name': 'DELETE_USER', 'category': 'POST'},
            {'id': 4, 'name': 'LIST_ALL_USERS', 'category': 'GET'},
            
            # Role endpoints
            {'id': 5, 'name': 'CREATE_ROLE', 'category': 'POST'},
            {'id': 6, 'name': 'UPDATE_ROLE', 'category': 'PUT'},
            {'id': 7, 'name': 'DELETE_ROLE', 'category': 'POST'},
            {'id': 8, 'name': 'LIST_ALL_ROLES', 'category': 'GET'},
            
            # Permission endpoints
            {'id': 9, 'name': 'CREATE_PERMISSION', 'category': 'POST'},
            {'id': 10, 'name': 'ASSIGN_ROLE_PERMISSION', 'category': 'POST'},
            {'id': 11, 'name': 'LIST_ALL_PERMISSIONS', 'category': 'GET'}
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
    for i in range(1, 12):  # For all 11 permissions
        role_permission_entries.append({
            'id': i,
            'role_id': 0,  # ADMIN role
            'permission_id': i
        })
    
    op.bulk_insert(role_permissions_table, role_permission_entries)
    
    # Create users table reference
    users_table = table('users',
        column('id', sa.Integer),
        column('name', sa.String),
        column('email', sa.String),
        column('password', sa.String),
        column('role_id', sa.Integer),
        column('username', sa.String),
        column('contact', sa.String),
        column('created_at', sa.DateTime)
    )
    
    # Hash password for admin user
    hashed_password = hash("1234")
    
    # Insert admin user
    op.bulk_insert(users_table,
        [
            {
                'id': 1,
                'name': 'Dibbyo Roy',
                'email': 'dibbyoroy7@gmail.com',
                'password': hashed_password,
                'role_id': 0,  # ADMIN role
                'username': 'dibbyoroy',
                'contact': '01763157183',
                'created_at': datetime.datetime.utcnow()
            }
        ]
    )


def downgrade() -> None:
    # Delete the admin user
    op.execute("DELETE FROM users WHERE id = 1")
    
    # Delete role-permission assignments
    op.execute("DELETE FROM roles_permissions WHERE role_id = 0")
    
    # Delete permissions
    op.execute("DELETE FROM permissions WHERE id BETWEEN 1 AND 11")
    
    # Delete roles
    op.execute("DELETE FROM roles WHERE id IN (0, 1, 2)")
