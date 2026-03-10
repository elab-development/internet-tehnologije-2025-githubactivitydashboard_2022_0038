from flask import Blueprint, request, jsonify
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import case
from models import db, User, Repository, Activity, TrackedRepository, DashboardView, UserRole, ActivityType, Branch
from datetime import datetime, timedelta
from functools import wraps
import logging
import re
from dateutil.parser import parse  # otpornije parsiranje datuma
import github_api  # ovo moraš imati za sync

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

# ------------------ Helper functions ------------------
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def require_role(required_roles):
    """Dekorator za proveru korisničke role"""
    if not isinstance(required_roles, list):
        required_roles = [required_roles]

    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404

            if user.role.value not in required_roles and user.role not in required_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator

# ------------------ AUTH ROUTES ------------------
@api.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400

        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 409

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Default role
        role = UserRole.VIEWER

        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            role=role  # ovo je Python enum
        )

        db.session.add(user)
        db.session.commit()

        # Napravi access token - osiguravamo da je enum
        role_enum = user.role if isinstance(user.role, UserRole) else UserRole(user.role)

        access_token = create_access_token(
            identity=str(user.id),  # <--- obavezno string
            expires_delta=timedelta(hours=24),
            additional_claims={'role': role_enum.value}
        )

        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500


@api.route('/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=data['username']).first()
        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Osiguravamo da je user.role enum
        role_enum = user.role if isinstance(user.role, UserRole) else UserRole(user.role)

        access_token = create_access_token(
            identity=str(user.id),  # <--- obavezno string
            expires_delta=timedelta(hours=24),
            additional_claims={'role': role_enum.value}
        )

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500

@api.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200

# ------------------ REPOSITORY ROUTES ------------------
@api.route('/repositories', methods=['GET'])
@jwt_required()
def get_all_repositories():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')

        query = Repository.query
        if search:
            query = query.filter(
                db.or_(
                    Repository.name.ilike(f'%{search}%'),
                    Repository.owner.ilike(f'%{search}%'),
                    Repository.full_name.ilike(f'%{search}%')
                )
            )

        # Ako last_updated može biti NULL, stavimo fallback
        pagination = query.order_by(
            case(
                (Repository.last_updated != None, Repository.last_updated),  # <--- bez liste
            else_=datetime.utcnow()
            ).desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'repositories': [repo.to_dict() for repo in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200

    except Exception as e:
        logger.error(f"Get repositories error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch repositories'}), 500

@api.route('/repositories/<int:repo_id>', methods=['GET'])
@jwt_required()
def get_single_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    return jsonify(repository.to_dict()), 200

@api.route('/repositories', methods=['POST'])
@require_role(['ADMIN', 'MODERATOR'])
def create_repository():
    data = request.get_json()
    if not data or not data.get('full_name') or not data.get('name') or not data.get('owner'):
        return jsonify({'error': 'Missing required fields'}), 400

    existing = Repository.query.filter_by(full_name=data['full_name']).first()
    if existing:
        return jsonify({'message': 'Repository already exists', 'repository': existing.to_dict()}), 200

    repository = Repository(
        github_id=data.get('github_id', 0),
        name=data['name'],
        full_name=data['full_name'],
        owner=data['owner'],
        url=data.get('url', f'https://github.com/{data["full_name"]}'),
        description=data.get('description', ''),
        stars=data.get('stars', 0),
        forks=data.get('forks', 0),
        language=data.get('language', 'Unknown'),
        last_updated=datetime.utcnow()
    )
    db.session.add(repository)
    db.session.commit()
    return jsonify({'message': 'Repository created successfully', 'repository': repository.to_dict()}), 201

@api.route('/repositories/<int:repo_id>', methods=['PUT'])
@require_role(['ADMIN', 'MODERATOR'])
def update_repository(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    data = request.get_json()
    if data.get('description'):
        repository.description = data['description']
    repository.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Repository updated successfully', 'repository': repository.to_dict()}), 200

@api.route('/repositories/<int:repo_id>', methods=['DELETE'])
@require_role('ADMIN')
def delete_repository_by_id(repo_id):
    repository = Repository.query.get_or_404(repo_id)
    db.session.delete(repository)
    db.session.commit()
    return jsonify({'message': 'Repository deleted successfully'}), 200

@api.route('/stats/overview', methods=['GET'])
@jwt_required()
def stats_overview():
    try:
        total_repos = Repository.query.count()
        total_commits = Activity.query.filter_by(activity_type=ActivityType.commit.value).count()
        total_prs = Activity.query.filter_by(activity_type=ActivityType.pull_request.value).count()
        total_issues = Activity.query.filter_by(activity_type=ActivityType.issue.value).count()
        active_contributors = len(set(a.actor for a in Activity.query.all()))

        return jsonify({
            "counts": {
                "repositories": total_repos,
                "commits": total_commits,
                "pull_requests": total_prs,
                "issues": total_issues
            },
            "active_contributors": active_contributors
        }), 200

    except Exception as e:
        logger.error(f"Stats overview error: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch overview stats"}), 500

# ------------------ ACTIVITY ROUTES ------------------
@api.route('/activities', methods=['GET'])
@jwt_required()
def get_all_activities():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    repository_id = request.args.get('repository_id', type=int)
    activity_type = request.args.get('type')
    actor = request.args.get('actor')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Activity.query
    if repository_id:
        query = query.filter_by(repository_id=repository_id)
    if activity_type:
        try:
            query = query.filter_by(activity_type=ActivityType(activity_type))
        except ValueError:
            pass
    if actor:
        query = query.filter(Activity.actor.ilike(f'%{actor}%'))
    if start_date:
        try:
            start = parse(start_date)
            query = query.filter(Activity.timestamp >= start)
        except Exception:
            pass
    if end_date:
        try:
            end = parse(end_date)
            query = query.filter(Activity.timestamp <= end)
        except Exception:
            pass

    pagination = query.order_by(Activity.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    activities_with_repo = []
    for activity in pagination.items:
        d = activity.to_dict()
        d['repository'] = activity.repository.to_dict() if activity.repository else None
        activities_with_repo.append(d)

    return jsonify({
        'activities': activities_with_repo,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

# ------------------ TRACKED REPOS & DASHBOARD & STATS ROUTES ------------------
# Ostale rute ostaju iste kao što si imao, samo obrati pažnju na:
# 1) Parsiranje datuma sa dateutil
# 2) Koristi user.id kao JWT identity
# 3) Role provera preko .value ili enum

# ------------------ ERROR HANDLERS ------------------
@api.errorhandler(404)
def handle_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api.errorhandler(400)
def handle_bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api.errorhandler(500)
def handle_internal_error(error):
    logger.error(f'Server Error: {error}', exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

@api.errorhandler(NoAuthorizationError)
def handle_auth_error(e):
    return jsonify({
        "error": "Authorization Required",
        "message": "Missing Authorization Header"
    }), 401
@api.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.error(f'Unexpected error: {error}', exc_info=True)
    return jsonify({'error': 'Unexpected server error'}), 500
