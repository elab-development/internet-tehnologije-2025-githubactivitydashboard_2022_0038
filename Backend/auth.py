from flask import jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from models import db, User, UserRole
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(data):
    """Register a new user"""
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return {'error': 'Missing required fields'}, 400
    
    if not validate_email(data['email']):
        return {'error': 'Invalid email format'}, 400
    
    if User.query.filter_by(username=data['username']).first():
        return {'error': 'Username already exists'}, 409
    
    if User.query.filter_by(email=data['email']).first():
        return {'error': 'Email already registered'}, 409
    
    # Set role - default is VIEWER, but allow admin creation for first user
    user_count = User.query.count()
    role = UserRole.ADMIN if user_count == 0 else UserRole.VIEWER
    
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role=role
    )
    
    db.session.add(user)
    db.session.commit()
    
    return {
        'message': 'User created successfully',
        'user': user.to_dict()
    }, 201

def login_user(data):
    """Authenticate user and return JWT token"""
    if not data.get('username') or not data.get('password'):
        return {'error': 'Missing username or password'}, 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return {'error': 'Invalid credentials'}, 401
    
    # Create access token
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=24),
        additional_claims={'role': user.role.value}
    )
    
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'user': user.to_dict()
    }, 200

def get_current_user():
    """Get current user from JWT token"""
    user_id = get_jwt_identity()
    return User.query.get(int(user_id))

def require_role(role):
    """Decorator to require specific role"""
    def decorator(fn):
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user = get_current_user()
            if not current_user:
                return {'error': 'User not found'}, 404
            
            required_roles = [UserRole[r] for r in role] if isinstance(role, list) else [UserRole[role]]
            
            if current_user.role not in required_roles:
                return {'error': 'Insufficient permissions'}, 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator