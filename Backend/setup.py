#!/usr/bin/env python3
"""
Setup script for GitHub Activity Dashboard
"""

import subprocess
import sys

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def create_database():
    """Create MySQL database"""
    print("\nCreating MySQL database...")
    
    # Instructions for MySQL
    print("="*60)
    print("MySQL DATABASE SETUP")
    print("="*60)
    print("\nPlease run these commands in MySQL:")
    print("""
-- Connect to MySQL
mysql -u root -p

-- Create database
CREATE DATABASE github_dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (optional)
CREATE USER 'dashboard_user'@'localhost' IDENTIFIED BY 'yourpassword';
GRANT ALL PRIVILEGES ON github_dashboard.* TO 'dashboard_user'@'localhost';
FLUSH PRIVILEGES;

-- Exit MySQL
EXIT;
""")
    print("="*60)

def setup_environment():
    """Create .env file if it doesn't exist"""
    import os
    
    env_file = '.env'
    if not os.path.exists(env_file):
        print("\nCreating .env file...")
        with open(env_file, 'w') as f:
            f.write("""# MySQL database
DATABASE_URL=mysql://root:yourpassword@localhost:3306/github_dashboard

# Secret keys
SECRET_KEY=your-super-secret-key-12345-change-in-production
JWT_SECRET_KEY=jwt-super-secret-key-12345-change-in-production

# GitHub token (optional for basic functionality)
GITHUB_TOKEN=your_github_token_here_optional
""")
        print(f"[SUCCESS] Created {env_file}")
        print("[INFO] Please edit .env file with your MySQL credentials")

if __name__ == '__main__':
    print("GitHub Activity Dashboard Setup")
    print("="*60)
    
    install_requirements()
    create_database()
    setup_environment()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Edit .env file with your MySQL credentials")
    print("2. Start MySQL server if not running")
    print("3. Run: python app.py")
    print("\nFor help:")
    print("  - Windows: Start XAMPP/WAMP MySQL")
    print("  - Linux: sudo service mysql start")
    print("  - Mac: brew services start mysql")