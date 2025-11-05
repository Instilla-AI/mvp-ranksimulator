from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = db.relationship('Analysis', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Analysis(db.Model):
    """Analysis history model"""
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    entity = db.Column(db.String(200))
    language = db.Column(db.String(10))
    ai_visibility_score = db.Column(db.Float)
    total_queries = db.Column(db.Integer)
    covered_queries = db.Column(db.Integer)
    result_data = db.Column(db.JSON)  # Store full analysis result
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert analysis to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'url': self.url,
            'entity': self.entity,
            'language': self.language,
            'ai_visibility_score': self.ai_visibility_score,
            'total_queries': self.total_queries,
            'covered_queries': self.covered_queries,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_dict_full(self):
        """Convert analysis to dictionary with full result data"""
        data = self.to_dict()
        data['result_data'] = self.result_data
        return data
