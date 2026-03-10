# 🐙 GitHub Activity Dashboard

Open-source platforma za praćenje i vizualizaciju GitHub aktivnosti repozitorijuma i korisnika u realnom vremenu.

## 🛠️ Tech Stack

| Sloj       | Tehnologija                                  |
|------------|----------------------------------------------|
| Backend    | Python 3.11 / Flask 3.0                      |
| Frontend   | Python / Reflex                              |
| Baza       | MySQL 8.0                                    |
| Auth       | JWT (flask-jwt-extended)                     |
| API docs   | Swagger UI (Flasgger)                        |
| Container  | Docker + Docker Compose                      |
| Proxy      | Nginx                                        |

## 🌐 Eksterni API-ji

- **GitHub REST API** (PyGithub) — repozitorijumi, grane, aktivnosti, commitovi
- **GitHub OAuth** — Integracija za OAuth 2.0 login

## 👥 Tipovi korisnika

| Uloga       | Prava                                              |
|-------------|----------------------------------------------------|
| `admin`     | Sve operacije: CREATE, UPDATE, DELETE, READ        |
| `moderator` | CREATE i UPDATE repozitorijuma, READ               |
| `viewer`    | Samo READ operacije                                |

## 🚀 Pokretanje aplikacije

### Preduslov: Docker i Docker Compose

### 1. Kloniraj repozitorijum
```bash
git clone https://github.com/elab-development/internet-tehnologije-2025-githubactivitydashboard_2022_0038.git
cd github-activity-dashboard
```

### 2. Kreiraj `.env` fajl
```bash
cp .env.example .env
# Uredi .env sa svojim vrednostima
```

### 3. Pokreni aplikaciju
```bash
docker compose up --build
```

### 4. Pristup aplikaciji

| Servis       | URL                               |
|--------------|-----------------------------------|
| Frontend     | http://localhost:3000             |
| Backend API  | http://localhost:5000/api         |
| Swagger UI   | http://localhost:5000/apidocs/    |

## 🔑 Environment varijable (`.env`)
```env
# MySQL
MYSQL_DATABASE=github_dashboard
MYSQL_USER=ghuser
MYSQL_PASSWORD=ghpassword
MYSQL_ROOT_PASSWORD=rootpassword

# Flask
DATABASE_URL=mysql+pymysql://ghuser:ghpassword@db:3306/github_dashboard
SECRET_KEY=your-super-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
FLASK_ENV=production

# GitHub API
GITHUB_TOKEN=ghp_your_personal_access_token
```

## 🔒 Bezbednosne mere

- ✅ **JWT autentifikacija** — sve zaštićene rute zahtevaju token
- ✅ **XSS zaštita** — Content-Security-Policy + X-XSS-Protection header
- ✅ **SQL Injection** — SQLAlchemy ORM sa parametrizovanim upitima
- ✅ **Clickjacking** — X-Frame-Options: DENY header
- ✅ **Brute-force zaštita** — Rate limiting (flask-limiter + Nginx)
- ✅ **CORS whitelist** — dozvoljeni samo poznati origini

## 🌿 Git grane
```
main          ← stabilna produkcija
develop       ← integracija feature-a  
feature/auth              ← autentifikacija i JWT
feature/github-api        ← GitHub API integracija
feature/docker            ← Docker konfiguracija
feature/swagger-ci        ← Swagger + CI/CD
```

## 🧪 Testovi
```bash
cd Backend
pytest tests/ -v
```

## 📊 API dokumentacija

Swagger UI dostupan na: `http://localhost:5000/apidocs/`

Dokumentovane rute:
- `POST /api/auth/register` — Registracija
- `POST /api/auth/login` — Login
- `GET  /api/auth/me` — Trenutni korisnik
- `GET  /api/repositories` — Lista repozitorijuma
- `POST /api/repositories` — Kreiraj repozitorijum
- `GET  /api/activities` — Lista aktivnosti
- `GET  /api/stats/overview` — Statistike