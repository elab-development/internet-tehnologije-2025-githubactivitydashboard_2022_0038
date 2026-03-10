from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from config import Config
import logging
import pymysql
pymysql.install_as_MySQLdb()

# ─── App inicijalizacija ───────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# ─── Swagger konfiguracija ─────────────────────────────────────────
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "swagger_ui_config": {
        "persistAuthorization": True,    # ← token ostaje sačuvan
        "displayRequestDuration": True,  # ← vidiš koliko traje request
    },
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "GitHub Activity Dashboard API",
        "description": (
            "REST API za praćenje GitHub aktivnosti.\n\n"
            "## Autentifikacija\n"
            "API koristi JWT Bearer tokene. Nakon logina, "
            "dodaj header: `Authorization: Bearer <token>`"
        ),
        "version": "1.0.0",
        "contact": {"name": "GitHub Activity Dashboard"},
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT token format: **Bearer &lt;token&gt;**",
        }
    },
    "security": [{"Bearer": []}],
    "tags": [
        {"name": "Auth",         "description": "Registracija, login, korisničke informacije"},
        {"name": "Repositories", "description": "CRUD operacije nad repozitorijumima"},
        {"name": "Activities",   "description": "Pregled GitHub aktivnosti"},
        {"name": "Stats",        "description": "Statistike i pregledi"},
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# ─── CORS ─────────────────────────────────────────────────────────
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000",
                    "http://localhost:8000", "http://localhost:80", "http://localhost",       # ← dodaj ovo
                    "http://frontend:3000", "*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,
    }
})

# ─── JWT ──────────────────────────────────────────────────────────
jwt = JWTManager(app)

# ─── Database + Migrate ───────────────────────────────────────────
from models import db
db.init_app(app)
migrate = Migrate(app, db)

# ─── Rate Limiter (zaštita od brute-force) ────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",
)

# ─── Security Headers (XSS, Clickjacking zaštita) ─────────────────
@app.after_request
def set_security_headers(response):
    # Swagger UI - preskoči CSP, inače ne radi
    if (request.path.startswith('/apidocs') or 
        request.path.startswith('/flasgger_static') or
        request.path.startswith('/apispec')):
        return response
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"]       = "1; mode=block"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://avatars.githubusercontent.com;"
    )
    return response

# ─── Blueprints ───────────────────────────────────────────────────
from routes import api
app.register_blueprint(api, url_prefix='/api')

# ─── JWT Error Handlers ───────────────────────────────────────────
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token has expired', 'message': 'Please log in again'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Invalid token', 'message': 'Token verification failed'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Authorization required', 'message': 'Missing access token'}), 401

# ─── Health Check ─────────────────────────────────────────────────
@app.route('/health')
def health_check():
    """
    Health check endpoint.
    ---
    tags:
      - Health
    responses:
      200:
        description: API je aktivan
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            version:
              type: string
              example: 1.0.0
    """
    return jsonify({'status': 'healthy', 'version': '1.0.0'}), 200

@app.route('/')
def index():
    return jsonify({
        'name': 'GitHub Activity Dashboard API',
        'version': '1.0.0',
        'docs': 'http://backend:5000/apidocs/',
        'health': '/health',
    })

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ─── Expose limiter za routes.py ──────────────────────────────────
def get_limiter():
    return limiter


import time
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from app import app, db
from models import User, Repository, Activity, Branch
def initialize_database(max_retries=10, delay=3):
    """Initialize database with tables and seed data (Docker-friendly)"""
    with app.app_context():
        # ── Retry loop za Docker MySQL ──
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        parsed = urlparse(db_url)

        for attempt in range(max_retries):
            try:
                connection = pymysql.connect(
                    host=parsed.hostname or 'db',        # 'db' = ime MySQL servisa u docker-compose
                    port=parsed.port or 3306,
                    user=parsed.username or 'root',
                    password=parsed.password or '',
                    database=parsed.path[1:] if parsed.path else None,
                    charset='utf8mb4',
                )
                connection.close()
                print("[INFO] MySQL connection OK")
                break
            except Exception as e:
                print(f"[WARN] MySQL connection failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(delay)
        else:
            print("[ERROR] Could not connect to MySQL after multiple attempts")
            return False

        # ── Kreiranje tabela ──
        db.create_all()
        print("[INFO] Tables created")

        # ── Default users ──
        if User.query.count() == 0:
            for uname, email, pwd, role in [
                ('admin',     'admin@dashboard.com',     'admin123',     'admin'),
                ('moderator', 'moderator@dashboard.com', 'moderator123', 'moderator'),
                ('viewer',    'viewer@dashboard.com',    'viewer123',    'viewer'),
            ]:
                db.session.add(User(
                    username=uname, email=email,
                    password_hash=generate_password_hash(pwd), role=role
                ))
            db.session.commit()
            print("[INFO] Default users created")

        # ── Sample repositories ──
        if Repository.query.count() == 0:
            repos = [
                Repository(github_id=28457823, name='flask',  full_name='pallets/flask',
                           owner='pallets',   url='https://github.com/pallets/flask',
                           description='Python micro framework', stars=65000, forks=16000, language='Python'),
                Repository(github_id=4164482,  name='django', full_name='django/django',
                           owner='django',    url='https://github.com/django/django',
                           description='Web framework for perfectionists', stars=75000, forks=31000, language='Python'),
                Repository(github_id=10270250, name='react',  full_name='facebook/react',
                           owner='facebook', url='https://github.com/facebook/react',
                           description='JavaScript library for UIs', stars=220000, forks=46000, language='JavaScript'),
            ]
            db.session.add_all(repos)
            db.session.commit()

            # ── Branches ──
            flask_repo  = Repository.query.filter_by(full_name='pallets/flask').first()
            django_repo = Repository.query.filter_by(full_name='django/django').first()

            branches = [
                Branch(name='main',        last_commit_sha='abc123', is_protected=True,  repository_id=flask_repo.id),
                Branch(name='development', last_commit_sha='def456', is_protected=False, repository_id=flask_repo.id),
                Branch(name='main',        last_commit_sha='ghi789', is_protected=True,  repository_id=django_repo.id),
            ]
            db.session.add_all(branches)
            db.session.commit()

            # ── Activities ──
            activities = [
                Activity(github_id='commit_abc123', activity_type='push',         actor='admin',    action='pushed',
                         ref='Fixed bug in auth',    timestamp=datetime.utcnow() - timedelta(hours=1),
                         data={'sha': 'abc123'},     repository_id=flask_repo.id,  branch_id=branches[0].id),
                Activity(github_id='pr_123',         activity_type='pull_request', actor='developer1', action='opened',
                         ref='Add new feature',      timestamp=datetime.utcnow() - timedelta(hours=2),
                         data={'number': 123},       repository_id=flask_repo.id,  branch_id=branches[1].id),
                Activity(github_id='issue_456',      activity_type='issue',        actor='admin',       action='opened',
                         ref='Bug: Crash on startup',timestamp=datetime.utcnow() - timedelta(hours=3),
                         data={'number': 456},       repository_id=django_repo.id, branch_id=branches[2].id),
            ]
            db.session.add_all(activities)
            db.session.commit()
            print("[INFO] Sample data created")

        return True
initialize_database()
# create_tables()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("GitHub Activity Dashboard API")
    print(f"Swagger UI: http://localhost:5000/apidocs/")
    print("=" * 60)

    if initialize_database():
        app.run(debug=True, port=5000, host='0.0.0.0')
    else:
        print("[ERROR] Database init failed.")