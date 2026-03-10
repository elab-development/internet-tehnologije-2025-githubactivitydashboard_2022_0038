import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app as flask_app
from models import db as _db

os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def app():
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URL": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt",
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Registruje i loguje korisnika, vraća JWT token."""
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    r = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    print(r.headers)
    return r.get_json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ─── Auth testovi ──────────────────────────────────────────────────
class TestRegister:
    def test_register_success(self, client):
        import time
        unique = str(int(time.time()))
        r = client.post("/api/auth/register", json={
            "username": f"newuser_{unique}",
            "email":    f"new_{unique}@example.com",
            "password": "password123",
        })
        print("STATUS:", r.status_code)
        print("JSON:", r.get_json())
        print("HEADERS:", r.headers)
        assert r.status_code == 201
        assert "access_token" in r.get_json()


    def test_register_missing_fields(self, client):
        r = client.post("/api/auth/register", json={"username": "u"})
        print(r.headers)
        assert r.status_code == 400

    def test_register_invalid_email(self, client):
        r = client.post("/api/auth/register", json={
            "username": "user2", "email": "not-an-email", "password": "pass1234"
        })
        print(r.headers)
        assert r.status_code == 400

    def test_register_duplicate_username(self, client):
        payload = {"username": "dupuser", "email": "dup@ex.com", "password": "password123"}
        client.post("/api/auth/register", json=payload)
        payload["email"] = "dup2@ex.com"
        r = client.post("/api/auth/register", json=payload)
        print(r.headers)
        assert r.status_code == 409

    def test_register_duplicate_email(self, client):
        client.post("/api/auth/register", json={
            "username": "ua", "email": "same@ex.com", "password": "password123"
        })
        r = client.post("/api/auth/register", json={
            "username": "ub", "email": "same@ex.com", "password": "password123"
        })
        print(r.headers)
        assert r.status_code == 409


class TestLogin:
    def test_login_success(self, client, auth_token):
        assert auth_token is not None
        assert len(auth_token) > 10

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "username": "luser", "email": "l@ex.com", "password": "correct123"
        })
        r = client.post("/api/auth/login", json={
            "username": "luser", "password": "wrongpass"
        })
        print(r.headers)
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/auth/login", json={
            "username": "ghost", "password": "password123"
        })
        print(r.headers)
        assert r.status_code == 401

    def test_login_missing_fields(self, client):
        r = client.post("/api/auth/login", json={"username": "admin"})
        assert r.status_code == 400


class TestProtectedRoutes:
    def test_me_without_token(self, client):
        r = client.get("/api/auth/me")
        print(r.headers)
        assert r.status_code == 401

    def test_me_with_token(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        print(r.headers)
        assert r.status_code == 200
        assert r.get_json()["username"] == "testuser"

    def test_repos_without_token(self, client):
        r = client.get("/api/repositories")
        print(r.headers)
        assert r.status_code == 401

    def test_repos_with_token(self, client, auth_headers):
        r = client.get("/api/repositories", headers=auth_headers)
        print(r.headers)
        assert r.status_code == 200
        assert "repositories" in r.get_json()


class TestSecurity:
    def test_xss_in_username_sanitized(self, client):
        """XSS payload u username polju mora biti odbijen ili sanitizovan."""
        r = client.post("/api/auth/register", json={
            "username": "<script>alert(1)</script>",
            "email":    "xss@test.com",
            "password": "password123",
        })
        print(r.headers)
        # Mora biti odbijen (400/409) ili sanitizovan
        if r.status_code == 201:
            data = r.get_json()
            assert "<script>" not in str(data)

    def test_sql_injection_login(self, client):
        """SQL injection u login polju mora biti odbijen."""
        r = client.post("/api/auth/login", json={
            "username": "' OR '1'='1'; --",
            "password": "anything",
        })
        print(r.headers)
        assert r.status_code == 401  # Nije uspeo login

    def test_security_headers_present(self, client):
        """Sigurnosni headeri moraju biti prisutni."""
        r = client.get("/health")
        print(r.headers)
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-Content-Type-Options") == "nosniff"