from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    VIEWER = "viewer"

class ActivityType(enum.Enum):
    commit = "commit"
    push = "push"
    pull_request = "pull_request"
    issue = "issue"
    create = "create"
    delete = "delete"
    fork = "fork"
    watch = "watch"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum('admin', 'moderator', 'viewer', name='user_role'), default='viewer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracked_repos = db.relationship('TrackedRepository', backref='tracking_user', lazy=True, cascade="all, delete-orphan")
    dashboard_views = db.relationship('DashboardView', backref='view_user', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_moderator(self):
        return self.role == 'moderator'
    
    def is_viewer(self):
        return self.role == 'viewer'

class Repository(db.Model):
    __tablename__ = 'repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), nullable=False, index=True)
    owner = db.Column(db.String(100), nullable=False, index=True)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    language = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    activities = db.relationship('Activity', backref='activity_repository', lazy=True, cascade="all, delete-orphan")
    tracked_by = db.relationship('TrackedRepository', backref='tracked_repository', lazy=True, cascade="all, delete-orphan")
    branches = db.relationship('Branch', backref='branch_repository', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'github_id': self.github_id,
            'name': self.name,
            'full_name': self.full_name,
            'owner': self.owner,
            'url': self.url,
            'description': self.description,
            'stars': self.stars,
            'forks': self.forks,
            'language': self.language,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_recent_activities(self, limit=10):
        return Activity.query.filter_by(repository_id=self.id)\
            .order_by(Activity.timestamp.desc())\
            .limit(limit)\
            .all()
    
    def get_activity_count(self):
        return Activity.query.filter_by(repository_id=self.id).count()

class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    last_commit_sha = db.Column(db.String(100))
    is_protected = db.Column(db.Boolean, default=False)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    activities = db.relationship('Activity', backref='activity_branch', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'last_commit_sha': self.last_commit_sha,
            'is_protected': self.is_protected,
            'repository_id': self.repository_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    activity_type = db.Column(db.Enum('commit','push', 'pull_request', 'issue', 'create', 'delete', 'fork', 'watch', name='activity_type'), nullable=False)
    #activity_type = db.Column(db.Enum(ActivityType), nullable=False)
    actor = db.Column(db.String(100), nullable=False, index=True)
    action = db.Column(db.String(100))
    ref = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    data = db.Column(db.JSON)  # MySQL 5.7+ podržava JSON
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'github_id': self.github_id,
            'activity_type': self.activity_type,
            'actor': self.actor,
            'action': self.action,
            'ref': self.ref,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'data': self.data,
            'repository_id': self.repository_id,
            'branch_id': self.branch_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_type(cls, activity_type):
        return cls.query.filter_by(activity_type=activity_type)\
            .order_by(cls.timestamp.desc())\
            .all()
    
    @classmethod
    def get_by_actor(cls, actor_name):
        return cls.query.filter(Activity.actor.ilike(f'%{actor_name}%'))\
            .order_by(cls.timestamp.desc())\
            .all()

class TrackedRepository(db.Model):
    __tablename__ = 'tracked_repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False, index=True)
    ownership_type = db.Column(db.String(50), default='TRACKING')  # TRACKING, OWNER, COLLABORATOR
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'repository_id', name='unique_user_repo'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'repository_id': self.repository_id,
            'ownership_type': self.ownership_type,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }

class DashboardView(db.Model):
    __tablename__ = 'dashboard_views'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    filters = db.Column(db.JSON)  # MySQL 5.7+ podržava JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'filters': self.filters,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }