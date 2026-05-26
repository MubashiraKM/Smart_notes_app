"""
Configuration Management for Smart Notes Application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # App Mode
    APP_MODE = os.getenv('APP_MODE', 'LOCAL')  # CLOUD or LOCAL
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_DYNAMODB_TABLE = os.getenv('AWS_DYNAMODB_TABLE', 'smart-notes-table')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'smart-notes-bucket')
    
    # Local Storage
    LOCAL_STORAGE_PATH = os.path.join(os.getcwd(), 'local_storage')
    DATABASE_PATH = os.path.join(os.getcwd(), 'database')
    SQLITE_DB_PATH = os.path.join(DATABASE_PATH, 'notes.db')
    
    # File Upload
    UPLOAD_FOLDER = LOCAL_STORAGE_PATH
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'doc'}

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

# Select configuration based on environment
config = DevelopmentConfig if os.getenv('FLASK_ENV') == 'development' else ProductionConfig
