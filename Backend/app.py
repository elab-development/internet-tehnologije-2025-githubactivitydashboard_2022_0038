from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
import logging
import pymysql
pymysql.install_as_MySQLdb()
# Kreirajte Flask aplikaciju prvo
app = Flask(__name__)
app.config.from_object(Config)

# Setup CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Setup JWT
jwt = JWTManager(app)

# Setup database
from models import db
db.init_app(app)

# Setup routes
from routes import api
app.register_blueprint(api, url_prefix='/api')

# JWT error handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'error': 'Token has expired',
        'message': 'Please log in again'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'error': 'Invalid token',
        'message': 'Token verification failed'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'error': 'Authorization required',
        'message': 'Request does not contain an access token'
    }), 401

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

# Root endpoint
@app.route('/')
def index():
    return jsonify({
        'name': 'GitHub Activity Dashboard API',
        'version': '1.0.0',
        'documentation': 'Visit /api endpoints',
        'health': '/health',
        'database': app.config['SQLALCHEMY_DATABASE_URI']
    })

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_mysql_connection():
    """Check if MySQL is running and accessible"""
    import pymysql
    from urllib.parse import urlparse
    
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    parsed = urlparse(db_url)
    
    try:
        connection = pymysql.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 3306,
            user=parsed.username or 'root',
            password=parsed.password or '',
            database=parsed.path[1:] if parsed.path else None,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        connection.close()
        return True
    except Exception as e:
        print(f"[ERROR] MySQL connection failed: {e}")
        return False

# Funkcija za inicijalizaciju baze
def initialize_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        try:
            # Proveri MySQL konekciju
            print("[INFO] Checking MySQL connection...")
            if not check_mysql_connection():
                print("[ERROR] MySQL is not running or connection failed!")
                print("[INFO] Please start MySQL server:")
                print("  - Windows: Open XAMPP/WAMP and start MySQL")
                print("  - Linux: sudo service mysql start")
                print("  - Mac: brew services start mysql")
                return False
            
            # Kreiraj tabele ako ne postoje
            print("[INFO] Creating database tables...")
            db.create_all()
            print("[SUCCESS] Database tables created successfully")
            
            # Create default admin user if no users exist
            from werkzeug.security import generate_password_hash
            from models import User, Repository, Activity, Branch
            
            if User.query.count() == 0:
                print("[INFO] Creating default users...")
                
                admin = User(
                    username='admin',
                    email='admin@githubdashboard.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin'
                )
                db.session.add(admin)
                
                moderator = User(
                    username='moderator',
                    email='moderator@githubdashboard.com',
                    password_hash=generate_password_hash('moderator123'),
                    role='moderator'
                )
                db.session.add(moderator)
                
                viewer = User(
                    username='viewer',
                    email='viewer@githubdashboard.com',
                    password_hash=generate_password_hash('viewer123'),
                    role='viewer'
                )
                db.session.add(viewer)
                
                db.session.commit()
                print("[SUCCESS] Default users created")
                print("  - admin (admin123)")
                print("  - moderator (moderator123)")
                print("  - viewer (viewer123)")
            
            # Create sample repositories if none exist
            if Repository.query.count() == 0:
                print("[INFO] Creating sample repositories...")
                
                sample_repos = [
                    Repository(
                        github_id=28457823,
                        name='flask',
                        full_name='pallets/flask',
                        owner='pallets',
                        url='https://github.com/pallets/flask',
                        description='The Python micro framework for building web applications.',
                        stars=65000,
                        forks=16000,
                        language='Python'
                    ),
                    Repository(
                        github_id=4164482,
                        name='django',
                        full_name='django/django',
                        owner='django',
                        url='https://github.com/django/django',
                        description='The Web framework for perfectionists with deadlines.',
                        stars=75000,
                        forks=31000,
                        language='Python'
                    ),
                    Repository(
                        github_id=10270250,
                        name='react',
                        full_name='facebook/react',
                        owner='facebook',
                        url='https://github.com/facebook/react',
                        description='A declarative, efficient, and flexible JavaScript library for building user interfaces.',
                        stars=220000,
                        forks=46000,
                        language='JavaScript'
                    )
                ]
                
                for repo in sample_repos:
                    db.session.add(repo)
                
                db.session.commit()
                print("[SUCCESS] Sample repositories created")
                
                # Create sample branches
                print("[INFO] Creating sample branches...")
                flask_repo = Repository.query.filter_by(full_name='pallets/flask').first()
                django_repo = Repository.query.filter_by(full_name='django/django').first()
                
                branches = [
                    Branch(
                        name='main',
                        last_commit_sha='abc123def456',
                        is_protected=True,
                        repository_id=flask_repo.id
                    ),
                    Branch(
                        name='development',
                        last_commit_sha='def456ghi789',
                        is_protected=False,
                        repository_id=flask_repo.id
                    ),
                    Branch(
                        name='main',
                        last_commit_sha='ghi789jkl012',
                        is_protected=True,
                        repository_id=django_repo.id
                    )
                ]
                
                for branch in branches:
                    db.session.add(branch)
                
                db.session.commit()
                print("[SUCCESS] Sample branches created")
                
                # Create sample activities
                print("[INFO] Creating sample activities...")
                from datetime import datetime, timedelta
                
                activities = [
                    Activity(
                        github_id='commit_abc123',
                        activity_type='push',
                        actor='octocat',
                        action='pushed',
                        ref='Fixed bug in authentication',
                        timestamp=datetime.utcnow() - timedelta(hours=1),
                        data={'sha': 'abc123', 'message': 'Fixed bug', 'url': 'https://github.com/pallets/flask/commit/abc123'},
                        repository_id=flask_repo.id,
                        branch_id=branches[0].id
                    ),
                    Activity(
                        github_id='pr_123',
                        activity_type='pull_request',
                        actor='developer1',
                        action='opened',
                        ref='Add new feature',
                        timestamp=datetime.utcnow() - timedelta(hours=2),
                        data={'number': 123, 'title': 'Add new feature', 'state': 'open'},
                        repository_id=flask_repo.id,
                        branch_id=branches[1].id
                    ),
                    Activity(
                        github_id='issue_456',
                        activity_type='issue',
                        actor='user2',
                        action='opened',
                        ref='Bug report: Crash on startup',
                        timestamp=datetime.utcnow() - timedelta(hours=3),
                        data={'number': 456, 'title': 'Crash on startup', 'state': 'open'},
                        repository_id=django_repo.id,
                        branch_id=branches[2].id
                    )
                ]
                
                for activity in activities:
                    db.session.add(activity)
                
                db.session.commit()
                print("[SUCCESS] Sample activities created")
            
            # Count existing data
            user_count = User.query.count()
            repo_count = Repository.query.count()
            activity_count = Activity.query.count()
            branch_count = Branch.query.count()
            
            print(f"[INFO] Database initialized successfully!")
            print(f"[INFO] Total records:")
            print(f"  - Users: {user_count}")
            print(f"  - Repositories: {repo_count}")
            print(f"  - Branches: {branch_count}")
            print(f"  - Activities: {activity_count}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error initializing database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GitHub Activity Dashboard API - MySQL Edition")
    print("="*60)
    
    # Inicijaliziraj bazu prije pokretanja servera
    if initialize_database():
        print("\n" + "="*60)
        print("Server Information")
        print("="*60)
        print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        print("Server: http://localhost:5000")
        print("\nAPI Endpoints:")
        print("  GET  /health                    - Health check")
        print("  POST /api/auth/register         - Register user")
        print("  POST /api/auth/login            - Login")
        print("  GET  /api/auth/me               - Get current user")
        print("  GET  /api/repositories          - List repositories")
        print("  POST /api/repositories          - Create repository (Admin/Mod)")
        print("  GET  /api/activities            - List activities")
        print("\nDefault Users:")
        print("  admin     - admin123")
        print("  moderator - moderator123")
        print("  viewer    - viewer123")
        print("="*60)
        print("\nPress Ctrl+C to stop the server\n")
        
        app.run(debug=True, port=5000, host='0.0.0.0')
    else:
        print("\n[ERROR] Failed to initialize database. Please check MySQL connection.")
        print("[INFO] Make sure MySQL is running and the database exists.")
