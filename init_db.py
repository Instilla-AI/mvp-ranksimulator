#!/usr/bin/env python3
"""
Database initialization script for Railway deployment
"""
import os
from app import app, db
from models import User

def init_database():
    """Initialize database and create admin user"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created!")
        
        # Check if admin exists
        admin = User.query.filter_by(email='ciccioragusa@gmail.com').first()
        
        if not admin:
            print("Creating admin user...")
            admin = User(
                email='ciccioragusa@gmail.com',
                name='Admin',
                role='admin'
            )
            admin.set_password('12345Aa!')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created!")
            print("   Email: ciccioragusa@gmail.com")
            print("   Password: 12345Aa!")
        else:
            print("ℹ️  Admin user already exists")
        
        print("\n✅ Database initialization complete!")

if __name__ == '__main__':
    init_database()
