import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    APP_MODE = os.getenv('APP_MODE', 'LOCAL') 
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_DYNAMODB_TABLE = os.getenv('AWS_DYNAMODB_TABLE', 'smart-notes-table')
    AWS_USERS_TABLE = os.getenv('AWS_USERS_TABLE', 'smart-users-table')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'smart-notes-bucket')

    LOCAL_STORAGE_PATH = os.path.join(os.getcwd(), 'local_storage')
    DATABASE_PATH = os.path.join(os.getcwd(), 'database')
    SQLITE_DB_PATH = os.path.join(DATABASE_PATH, 'notes.db')

    UPLOAD_FOLDER = LOCAL_STORAGE_PATH
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'doc'}

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = DevelopmentConfig if os.getenv('FLASK_ENV') == 'development' else ProductionConfig
