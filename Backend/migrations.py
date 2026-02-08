from flask_migrate import Migrate
from models import db

migrate = Migrate()

# Ovo će biti korišćeno u app.py
# Migracije se generišu komandama:
# flask db init
# flask db migrate -m "Initial migration"
# flask db upgrade

# Primeri migracionih fajlova koje će Flask-Migrate generisati:

# 1. Initial migration (kreiranje svih tabela)
"""
# migrations/versions/initial_migration.py
def upgrade():
    # Kreiranje tabela
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'MODERATOR', 'VIEWER', name='userrole'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    op.create_table('repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('owner', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stars', sa.Integer(), nullable=True),
        sa.Column('forks', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_id')
    )
    
    op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_id', sa.String(length=100), nullable=False),
        sa.Column('activity_type', sa.Enum('PUSH', 'PULL_REQUEST', 'ISSUE', 'CREATE', 'DELETE', 'FORK', 'WATCH', name='activitytype'), nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('ref', sa.String(length=200), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_id')
    )
    
    op.create_table('dashboard_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('tracked_repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'repository_id', name='unique_user_repo')
    )
"""

# 2. Dodavanje nove kolone (dodajemo language kolonu Repository modelu)
"""
# migrations/versions/add_language_to_repositories.py
def upgrade():
    # Dodavanje nove kolone
    op.add_column('repositories', sa.Column('language', sa.String(length=50), nullable=True))
    
    # Postavljanje default vrednosti za postojeće redove
    op.execute("UPDATE repositories SET language = 'Unknown' WHERE language IS NULL")
"""

# 3. Dodavanje spoljnog ključa i indeksa (poboljšanje performansi)
"""
# migrations/versions/add_indexes_for_performance.py
def upgrade():
    # Dodavanje indeksa za često korišćene upite
    op.create_index('ix_activities_repository_timestamp', 'activities', ['repository_id', 'timestamp'])
    op.create_index('ix_activities_actor', 'activities', ['actor'])
    op.create_index('ix_activities_type', 'activities', ['activity_type'])
    
    # Dodavanje indeksa za repositories
    op.create_index('ix_repositories_owner', 'repositories', ['owner'])
    op.create_index('ix_repositories_stars', 'repositories', ['stars'])
"""

# 4. Izmena postojeće kolone (proširivanje dužine username polja)
"""
# migrations/versions/increase_username_length.py
def upgrade():
    # Menjamo dužinu username polja sa 80 na 100 karaktera
    op.alter_column('users', 'username',
               existing_type=sa.VARCHAR(length=80),
               type_=sa.String(length=100),
               existing_nullable=False)
"""