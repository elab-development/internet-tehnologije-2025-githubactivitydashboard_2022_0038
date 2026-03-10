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
from github_api import GitHubAPI
from config import Config

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
    """
    Registracija novog korisnika.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, email, password]
          properties:
            username:
              type: string
              example: johndoe
            email:
              type: string
              example: john@example.com
            password:
              type: string
              example: password123
    responses:
      201:
        description: Korisnik uspešno kreiran
        schema:
          type: object
          properties:
            message: {type: string}
            access_token: {type: string}
      400:
        description: Nedostaju polja ili pogrešan format
      409:
        description: Username ili email već postoji
    """
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
        role = UserRole.VIEWER.value

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
    """
    Prijava korisnika i dobijanje JWT tokena.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
              example: admin
            password:
              type: string
              example: admin123
    responses:
      200:
        description: Uspešna prijava
        schema:
          type: object
          properties:
            access_token:
              type: string
            user:
              type: object
      401:
        description: Pogrešni kredencijali
    """
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
    """
    Vraća podatke trenutno prijavljenog korisnika.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Podaci o korisniku
      401:
        description: Niste prijavljeni
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200
# ─── GITHUB API RUTE ──────────────────────────────────────────────

@api.route('/github/user/<string:username>', methods=['GET'])
@jwt_required()
def get_github_user(username):
    """
    Dohvata GitHub profil korisnika direktno sa GitHub API-ja.
    ---
    tags:
      - GitHub
      - Auth
    security:
      - Bearer: []
    parameters:
      - in: path
        name: username
        type: string
        required: true
        example: torvalds
    responses:
      200:
        description: GitHub profil korisnika
      404:
        description: Korisnik nije pronađen na GitHubu
    """
    try:
        gh = GitHubAPI(token=Config.GITHUB_TOKEN)
        user = gh.gh.get_user(username)
        return jsonify({
            'login':       user.login,
            'name':        user.name,
            'avatar_url':  user.avatar_url,
            'bio':         user.bio,
            'public_repos': user.public_repos,
            'followers':   user.followers,
            'following':   user.following,
            'html_url':    user.html_url,
            'created_at':  user.created_at.isoformat() if user.created_at else None,
        }), 200
    except Exception as e:
        return jsonify({'error': f'GitHub korisnik nije pronađen: {str(e)}'}), 404


@api.route('/github/user/<string:username>/repos', methods=['GET'])
@jwt_required()
def get_github_user_repos(username):
    """
    Dohvata repozitorijume GitHub korisnika direktno sa GitHub API-ja.
    ---
    tags:
      - GitHub
    security:
      - Bearer: []
    parameters:
      - in: path
        name: username
        type: string
        required: true
        example: torvalds
      - in: query
        name: sort
        type: string
        enum: [updated, stars, forks, created]
        default: updated
      - in: query
        name: per_page
        type: integer
        default: 30
    responses:
      200:
        description: Lista repozitorijuma sa GitHub-a
    """
    try:
        sort     = request.args.get('sort', 'updated')
        per_page = min(int(request.args.get('per_page', 30)), 100)

        gh   = GitHubAPI(token=Config.GITHUB_TOKEN)
        user = gh.gh.get_user(username)
        repos = user.get_repos(sort=sort)

        result = []
        count  = 0
        for repo in repos:
            if count >= per_page:
                break
            result.append({
                'id':          repo.id,
                'name':        repo.name,
                'full_name':   repo.full_name,
                'owner':       repo.owner.login,
                'description': repo.description or '',
                'stars':       repo.stargazers_count,
                'forks':       repo.forks_count,
                'language':    repo.language or 'Unknown',
                'url':         repo.html_url,
                'updated':     repo.updated_at.strftime('%Y-%m-%d') if repo.updated_at else '',
                'private':     repo.private,
            })
            count += 1

        return jsonify({
            'username':     username,
            'repos':        result,
            'total_found':  len(result),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Greška pri dohvatanju repos: {str(e)}'}), 404


@api.route('/github/repo/<string:owner>/<string:repo_name>', methods=['GET'])
@jwt_required()
def get_github_repo_details(owner, repo_name):
    """
    Dohvata detalje repozitorijuma direktno sa GitHub API-ja.
    ---
    tags:
      - GitHub
    security:
      - Bearer: []
    parameters:
      - in: path
        name: owner
        type: string
        required: true
        example: pallets
      - in: path
        name: repo_name
        type: string
        required: true
        example: flask
    responses:
      200:
        description: Detalji repozitorijuma
      404:
        description: Repozitorijum nije pronađen
    """
    try:
        gh   = GitHubAPI(token=Config.GITHUB_TOKEN)
        repo = gh.gh.get_repo(f'{owner}/{repo_name}')

        # Dohvati grane
        branches = [{'name': b.name, 'protected': b.protected}
                    for b in list(repo.get_branches())[:10]]

        # Dohvati poslednje commitove
        commits = []
        for c in list(repo.get_commits())[:10]:
            commits.append({
                'sha':     c.sha[:7],
                'message': c.commit.message.split('\n')[0][:80],
                'author':  c.commit.author.name if c.commit.author else 'Unknown',
                'date':    c.commit.author.date.isoformat() if c.commit.author else '',
                'url':     c.html_url,
            })

        return jsonify({
            'id':            repo.id,
            'name':          repo.name,
            'full_name':     repo.full_name,
            'owner':         repo.owner.login,
            'description':   repo.description or '',
            'stars':         repo.stargazers_count,
            'forks':         repo.forks_count,
            'watchers':      repo.watchers_count,
            'open_issues':   repo.open_issues_count,
            'language':      repo.language or 'Unknown',
            'url':           repo.html_url,
            'default_branch': repo.default_branch,
            'created_at':    repo.created_at.isoformat() if repo.created_at else None,
            'updated_at':    repo.updated_at.isoformat() if repo.updated_at else None,
            'branches':      branches,
            'recent_commits': commits,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Repozitorijum nije pronađen: {str(e)}'}), 404


@api.route('/github/repo/<string:owner>/<string:repo_name>/sync', methods=['POST'])
@require_role(['ADMIN', 'MODERATOR'])
def sync_github_repo(owner, repo_name):
    """
    Sinhronizuje repozitorijum sa GitHub API-ja u lokalnu bazu.
    ---
    tags:
      - GitHub
    security:
      - Bearer: []
    parameters:
      - in: path
        name: owner
        type: string
        required: true
      - in: path
        name: repo_name
        type: string
        required: true
    responses:
      200:
        description: Repozitorijum sinhronizovan u bazu
      403:
        description: Nedovoljne privilegije
    """
    try:
        gh         = GitHubAPI(token=Config.GITHUB_TOKEN)
        repository = gh.sync_repository(f'{owner}/{repo_name}')

        if not repository:
            return jsonify({'error': 'Nije moguće sinhronizovati repozitorijum'}), 400

        return jsonify({
            'message':    'Repozitorijum uspešno sinhronizovan',
            'repository': repository.to_dict(),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Greška pri sinhronizaciji: {str(e)}'}), 500

# ------------------ REPOSITORY ROUTES ------------------
@api.route('/repositories', methods=['GET'])
@jwt_required()
def get_all_repositories():
    """
    Lista svih repozitorijuma sa paginacijom.
    ---
    tags:
      - Repositories
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 20
      - in: query
        name: search
        type: string
        description: Pretraga po imenu ili owner-u
    responses:
      200:
        description: Lista repozitorijuma
        schema:
          type: object
          properties:
            repositories:
              type: array
            total: {type: integer}
            pages: {type: integer}
            current_page: {type: integer}
    """
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
    """
    Kreira novi repozitorijum (samo Admin/Moderator).
    ---
    tags:
      - Repositories
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [full_name, name, owner]
          properties:
            full_name: {type: string, example: "pallets/flask"}
            name:      {type: string, example: "flask"}
            owner:     {type: string, example: "pallets"}
            description: {type: string}
            stars:     {type: integer}
            language:  {type: string}
    responses:
      201:
        description: Repozitorijum kreiran
      403:
        description: Nedovoljne privilegije
    """
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
    """
    Briše repozitorijum (samo Admin).
    ---
    tags:
      - Repositories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: repo_id
        type: integer
        required: true
    responses:
      200:
        description: Repozitorijum obrisan
      403:
        description: Nedovoljne privilegije
      404:
        description: Repozitorijum nije pronađen
    """
    repository = Repository.query.get_or_404(repo_id)
    db.session.delete(repository)
    db.session.commit()
    return jsonify({'message': 'Repository deleted successfully'}), 200

@api.route('/stats/overview', methods=['GET'])
@jwt_required()
def stats_overview():
    """
    Ukupne statistike dashboarda.
    ---
    tags:
      - Stats
    security:
      - Bearer: []
    responses:
      200:
        description: Statistike
        schema:
          type: object
          properties:
            counts:
              type: object
              properties:
                repositories: {type: integer}
                commits:       {type: integer}
                pull_requests: {type: integer}
                issues:        {type: integer}
            active_contributors:
              type: integer
    """
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
    """
    Lista aktivnosti sa filterima.
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 50
      - in: query
        name: repository_id
        type: integer
        description: Filtriraj po repozitorijumu
      - in: query
        name: type
        type: string
        enum: [commit, push, pull_request, issue, create, delete, fork, watch]
        description: Tip aktivnosti
      - in: query
        name: actor
        type: string
        description: GitHub korisničko ime
      - in: query
        name: start_date
        type: string
        format: date
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        example: "2024-12-31"
    responses:
      200:
        description: Lista aktivnosti
    """
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
    repo_cache = {}
    for activity in pagination.items:
      d = activity.to_dict()
      if activity.repository_id:
        if activity.repository_id not in repo_cache:
            repo = Repository.query.get(activity.repository_id)
            repo_cache[activity.repository_id] = repo.to_dict() if repo else None
        d['repository'] = repo_cache[activity.repository_id]
    else:
        d['repository'] = None
    activities_with_repo.append(d)

    return jsonify({
        'activities': activities_with_repo,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200
@api.route('/activities/repository/<int:repo_id>', methods=['GET'])
@jwt_required()
def get_repository_activities(repo_id):
    """
    Lista aktivnosti za specifičan repozitorijum.
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: repo_id
        type: integer
        required: true
        example: 1
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: per_page
        type: integer
        default: 50
      - in: query
        name: type
        type: string
        enum: [commit, push, pull_request, issue, create, delete, fork, watch]
    responses:
      200:
        description: Lista aktivnosti za repozitorijum
      404:
        description: Repozitorijum nije pronađen
    """
    # Provjeri da repozitorijum postoji
    repository = Repository.query.get_or_404(repo_id)

    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    activity_type = request.args.get('type')

    query = Activity.query.filter_by(repository_id=repo_id)

    if activity_type:
        try:
            query = query.filter_by(activity_type=ActivityType(activity_type))
        except ValueError:
            pass

    pagination = query.order_by(Activity.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    activities = []
    for activity in pagination.items:
        d = activity.to_dict()
        d['repository'] = repository.to_dict()
        activities.append(d)

    return jsonify({
        'activities':   activities,
        'total':        pagination.total,
        'pages':        pagination.pages,
        'current_page': page,
        'repository':   repository.to_dict(),
    }), 200


import requests as http_requests
import os

# ─── GITHUB OAUTH ─────────────────────────────────────────────────
GITHUB_CLIENT_ID     = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

@api.route('/auth/github', methods=['GET'])
def github_oauth_redirect():
    """
    Redirect na GitHub OAuth login stranicu.
    ---
    tags:
      - Auth
    responses:
      302:
        description: Redirect na GitHub
    """
    from flask import redirect
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email"
        f"&redirect_uri=http://localhost:5000/api/auth/github/callback"
    )
    return redirect(f"https://github.com/login/oauth/authorize?{params}")


@api.route('/auth/github/callback', methods=['GET'])
def github_oauth_callback():
    """
    GitHub OAuth callback — razmena code za token.
    ---
    tags:
      - Auth
    parameters:
      - in: query
        name: code
        type: string
        required: true
    responses:
      200:
        description: JWT token i podaci o korisniku
      400:
        description: OAuth greška
    """
    from flask import redirect
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Missing OAuth code'}), 400

    # ── Razmeni code za GitHub access token ──────────────────────
    token_resp = http_requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        json={
            "client_id":     GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code":          code,
        },
        timeout=10,
    )

    token_data = token_resp.json()
    github_token = token_data.get("access_token")
    if not github_token:
        return jsonify({'error': 'Failed to get GitHub token', 'details': token_data}), 400

    # ── Dohvati GitHub profil ─────────────────────────────────────
    user_resp = http_requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    gh_user = user_resp.json()

    # ── Dohvati email ─────────────────────────────────────────────
    email_resp = http_requests.get(
        "https://api.github.com/user/emails",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    emails    = email_resp.json()
    primary   = next((e["email"] for e in emails if e.get("primary")), None)
    email     = primary or gh_user.get("email") or f"{gh_user['login']}@github.local"

    # ── Nađi ili kreiraj korisnika u bazi ────────────────────────
    from werkzeug.security import generate_password_hash
    import secrets

    user = User.query.filter_by(username=gh_user["login"]).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            username=gh_user["login"],
            email=email,
            password_hash=generate_password_hash(secrets.token_hex(32)),
            role="viewer",
        )
        db.session.add(user)
        db.session.commit()
        logger.info(f"OAuth: novi korisnik kreiran: {user.username}")
    else:
        logger.info(f"OAuth: postojeći korisnik ulogovan: {user.username}")

    # ── Kreiraj JWT token ─────────────────────────────────────────
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=24),
        additional_claims={"role": user.role},
    )

    # ── Redirect na frontend sa tokenom ──────────────────────────
    return redirect(
        f"http://localhost:3000/oauth/callback?token={access_token}&username={user.username}"
    )


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
