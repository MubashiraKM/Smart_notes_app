import os
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

app.secret_key = app.config['SECRET_KEY']

os.makedirs(app.config['LOCAL_STORAGE_PATH'], exist_ok=True)
os.makedirs(app.config['DATABASE_PATH'], exist_ok=True)

AWS_AVAILABLE = False
try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    pass


def init_db():
    if app.config['APP_MODE'] == 'LOCAL':
        conn = sqlite3.connect(app.config['SQLITE_DB_PATH'])
        cursor = conn.cursor()
        # notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                file_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                pinned INTEGER DEFAULT 0,
                user_id TEXT NOT NULL
            )
        ''')
        
        # users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

with app.app_context():
    init_db()

def get_sqlite_connection():
    conn = sqlite3.connect(app.config['SQLITE_DB_PATH'])
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)

def register_user_cloud(username, email, password):
    try:
        table = get_users_table()

        response = table.scan(
            FilterExpression='username = :u OR email = :e',
            ExpressionAttributeValues={
                ':u': username,
                ':e': email
            }
        )

        if response.get('Items'):
            return {
                'success': False,
                'message': 'Username or email already exists'
            }

        user_id = str(uuid.uuid4())

        table.put_item(
            Item={
                'user_id': user_id,
                'username': username,
                'email': email,
                'password_hash': hash_password(password),
                'created_at': datetime.now().isoformat()
            }
        )

        return {
            'success': True,
            'user_id': user_id
        }

    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }
    
def login_user_cloud(username, password):
    try:
        table = get_users_table()

        response = table.scan(
            FilterExpression='username = :u',
            ExpressionAttributeValues={
                ':u': username
            }
        )

        items = response.get('Items', [])

        if not items:
            return None

        user = items[0]

        if not verify_password(password, user['password_hash']):
            return None

        return user

    except Exception:
        return None

def is_logged_in():
    return 'user_id' in session

def get_current_user_id():
    return session.get('user_id')



@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()

        if not username or not email or not password or not confirm_password:
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username must be at least 3 characters'
            }), 400

        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400

        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match'
            }), 400

        if '@' not in email:
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        # LOCAL MODE
        if app.config['APP_MODE'] == 'LOCAL':

            conn = get_sqlite_connection()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT user_id FROM users WHERE username = ? OR email = ?',
                (username, email)
            )

            if cursor.fetchone():
                conn.close()

                return jsonify({
                    'success': False,
                    'message': 'Username or email already exists'
                }), 400

            user_id = str(uuid.uuid4())

            password_hash = hash_password(password)

            now = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO users (
                    user_id,
                    username,
                    email,
                    password_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                username,
                email,
                password_hash,
                now
            ))

            conn.commit()
            conn.close()

        # CLOUD MODE
        else:

            result = register_user_cloud(
                username,
                email,
                password
            )

            if not result['success']:
                return jsonify(result), 400

            user_id = result['user_id']

        return jsonify({
            'success': True,
            'message': 'Registration successful! Please login.',
            'user_id': user_id
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/register', methods=['POST'])
# def register():
#     try:
#         data = request.get_json()
#         username = data.get('username', '').strip()
#         email = data.get('email', '').strip()
#         password = data.get('password', '').strip()
#         confirm_password = data.get('confirm_password', '').strip()

#         if not username or not email or not password or not confirm_password:
#             return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
#         if len(username) < 3:
#             return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400
        
#         if len(password) < 6:
#             return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
#         if password != confirm_password:
#             return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
#         if '@' not in email:
#             return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
#         conn = get_sqlite_connection()
#         cursor = conn.cursor()
        
#         cursor.execute('SELECT user_id FROM users WHERE username = ? OR email = ?', (username, email))
#         if cursor.fetchone():
#             conn.close()
#             return jsonify({'success': False, 'message': 'Username or email already exists'}), 400
        
#         user_id = str(uuid.uuid4())
#         password_hash = hash_password(password)
#         now = datetime.now().isoformat()
        
#         cursor.execute('''
#             INSERT INTO users (user_id, username, email, password_hash, created_at)
#             VALUES (?, ?, ?, ?, ?)
#         ''', (user_id, username, email, password_hash, now))
        
#         conn.commit()
#         conn.close()
        
#         return jsonify({
#             'success': True,
#             'message': 'Registration successful! Please login.',
#             'user_id': user_id
#         }), 201
    
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():

    try:
        data = request.get_json()

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400

        # LOCAL MODE
        if app.config['APP_MODE'] == 'LOCAL':

            conn = get_sqlite_connection()
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT user_id, username, password_hash
                FROM users
                WHERE username = ?
                ''',
                (username,)
            )

            user = cursor.fetchone()

            conn.close()

            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Invalid username or password'
                }), 401

            if not verify_password(password, user['password_hash']):
                return jsonify({
                    'success': False,
                    'message': 'Invalid username or password'
                }), 401

        # CLOUD MODE
        else:

            user = login_user_cloud(username, password)

            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Invalid username or password'
                }), 401

        session['user_id'] = user['user_id']
        session['username'] = user['username']

        session.permanent = True

        app.permanent_session_lifetime = timedelta(days=7)

        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'user_id': user['user_id'],
            'username': user['username']
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/login', methods=['POST'])
# def login():
#     """Login user"""
#     try:
#         data = request.get_json()
#         username = data.get('username', '').strip()
#         password = data.get('password', '').strip()

#         if not username or not password:
#             return jsonify({'success': False, 'message': 'Username and password are required'}), 400

#         conn = get_sqlite_connection()
#         cursor = conn.cursor()
        
#         cursor.execute('SELECT user_id, username, password_hash FROM users WHERE username = ?', (username,))
#         user = cursor.fetchone()
#         conn.close()
        
#         if not user:
#             return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
 
#         if not verify_password(password, user['password_hash']):
#             return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

#         session['user_id'] = user['user_id']
#         session['username'] = user['username']
#         session.permanent = True
#         app.permanent_session_lifetime = timedelta(days=7)
        
#         return jsonify({
#             'success': True,
#             'message': 'Login successful!',
#             'user_id': user['user_id'],
#             'username': user['username']
#         }), 200
    
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth_status', methods=['GET'])
def auth_status():
    if is_logged_in():
        return jsonify({
            'success': True,
            'is_logged_in': True,
            'user_id': get_current_user_id(),
            'username': session.get('username', '')
        }), 200
    else:
        return jsonify({
            'success': True,
            'is_logged_in': False
        }), 200


def allowed_file(filename):

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_tags(content, title, subject):

    tags = set()

    if subject:
        tags.add(subject.lower())

    keyword_map = {
        'python': ['python', 'flask', 'django', 'pandas', 'numpy'],
        'database': ['sql', 'database', 'mysql', 'postgresql', 'mongodb', 'dynamodb'],
        'ml': ['machine learning', 'deep learning', 'neural', 'tensorflow', 'pytorch', 'sklearn'],
        'web': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'http'],
        'cloud': ['aws', 'azure', 'gcp', 'cloud', 's3', 'ec2', 'lambda'],
        'devops': ['docker', 'kubernetes', 'ci/cd', 'jenkins', 'gitlab', 'devops'],
        'security': ['security', 'encryption', 'authentication', 'oauth', 'jwt'],
        'api': ['api', 'rest', 'graphql', 'json', 'endpoint'],
        'data': ['data', 'analysis', 'visualization', 'statistics', 'analytics'],
        'programming':['java','python','C','CPP','C++']
        
    }

    text = (content + " " + title).lower()

    for category, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in text:
                tags.add(category)
                break

    words = re.findall(r'\b[A-Z]{2,}\b', content + " " + title)
    for word in words[:5]:  
        tags.add(word.lower())
    
    return list(tags) if tags else ['untagged']

def mock_ai_tags(content, title, subject):
    return generate_tags(content, title, subject)


def save_file_s3(file):
    if not file or not file.filename:
        return None, "No file provided"

    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'none'
        allowed = ', '.join(sorted(app.config['ALLOWED_EXTENSIONS']))
        return None, f"File type '.{ext}' is not allowed. Allowed types: {allowed}"

    try:
        filename = secure_filename(file.filename)
        s3_key = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{filename}"

        file.stream.seek(0)

        content_type = (file.content_type or '').strip()
        if not content_type or content_type == 'application/octet-stream':
            import mimetypes
            guessed, _ = mimetypes.guess_type(filename)
            content_type = guessed or 'application/octet-stream'

        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            file.stream,
            app.config['AWS_S3_BUCKET'],
            s3_key,
            ExtraArgs={'ContentType': content_type}
        )
        app.logger.info(f"S3 upload success: {s3_key}")
        return s3_key, None

    except Exception as e:
        error_msg = f"S3 upload failed: {str(e)}"
        app.logger.error(error_msg)
        return None, error_msg


def save_file_local(file):
    if not file or not file.filename:
        return None, "No file provided"

    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'none'
        allowed = ', '.join(sorted(app.config['ALLOWED_EXTENSIONS']))
        return None, f"File type '.{ext}' is not allowed. Allowed types: {allowed}"

    try:
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{filename}"
        filepath = os.path.join(app.config['LOCAL_STORAGE_PATH'], filename)
        file.save(filepath)
        return filename, None
    except Exception as e:
        error_msg = f"Local file save failed: {str(e)}"
        app.logger.error(error_msg)
        return None, error_msg


def save_file(file):
    if app.config['APP_MODE'] == 'LOCAL':
        return save_file_local(file)
    else:
        return save_file_s3(file)


def get_s3_presigned_url(s3_key, expiry=3600):
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': app.config['AWS_S3_BUCKET'],
                'Key': s3_key
            },
            ExpiresIn=expiry
        )
        return url
    except Exception as e:
        app.logger.error(f"Pre-signed URL generation failed: {e}")
        return None


def add_note_local(title, subject, content, tags, file_url, user_id):
    try:
        note_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notes (id, title, subject, content, tags, file_url, created_at, updated_at, pinned, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (note_id, title, subject, content, json.dumps(tags), file_url, now, now, 0, user_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'id': note_id, 'message': 'Note added successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_notes_local(user_id, subject=None, search=None, sort_by='latest'):
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM notes WHERE user_id = ?'
        params = [user_id]
        
        if subject:
            query += ' AND subject = ?'
            params.append(subject)
        
        if search:
            query += ' AND (title LIKE ? OR content LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])
        
        if sort_by == 'latest':
            query += ' ORDER BY pinned DESC, created_at DESC'
        elif sort_by == 'oldest':
            query += ' ORDER BY pinned DESC, created_at ASC'
        elif sort_by == 'title_asc':
            query += ' ORDER BY pinned DESC, title ASC'
        elif sort_by == 'title_desc':
            query += ' ORDER BY pinned DESC, title DESC'
        else:
            query += ' ORDER BY pinned DESC, created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        notes = []
        for row in rows:
            note = dict(row)
            note['tags'] = json.loads(note['tags']) if note['tags'] else []
            note['pinned'] = bool(note['pinned'])
            notes.append(note)
        
        conn.close()
        return notes
    except Exception as e:
        return []

def delete_note_local(note_id, user_id):
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT file_url FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {'success': False, 'message': 'Note not found or unauthorized'}
        
        if row['file_url']:
            file_path = os.path.join(app.config['LOCAL_STORAGE_PATH'], row['file_url'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        cursor.execute('DELETE FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Note deleted successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def pin_note_local(note_id, user_id):
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT pinned FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {'success': False, 'message': 'Note not found or unauthorized'}
        
        new_pinned_status = 1 - row['pinned']
        now = datetime.now().isoformat()
        
        cursor.execute('UPDATE notes SET pinned = ?, updated_at = ? WHERE id = ? AND user_id = ?',
                      (new_pinned_status, now, note_id, user_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'pinned': bool(new_pinned_status)}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def update_note_local(note_id, user_id, title, subject, content, file_url=None):
    try:
        tags = mock_ai_tags(content, title, subject)
        now = datetime.now().isoformat()
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT file_url FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        existing = cursor.fetchone()
        
        if not existing:
            conn.close()
            return {'success': False, 'message': 'Note not found or unauthorized'}

        final_file_url = file_url if file_url else existing['file_url']
        
        cursor.execute('''
            UPDATE notes 
            SET title = ?, subject = ?, content = ?, tags = ?, file_url = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (title, subject, content, json.dumps(tags), final_file_url, now, note_id, user_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Note updated successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_note_local(note_id, user_id):
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            note = dict(row)
            note['tags'] = json.loads(note['tags']) if note['tags'] else []
            note['pinned'] = bool(note['pinned'])
            return note
        return None
    except Exception as e:
        return None

def get_all_subjects_local(user_id):
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT subject FROM notes WHERE user_id = ? ORDER BY subject', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [row['subject'] for row in rows]
    except Exception as e:
        return []

# Cloud operations

def get_dynamodb_table():
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )
    return dynamodb.Table(app.config['AWS_DYNAMODB_TABLE'])

def get_s3_client():
    return boto3.client(
        's3',
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )

def add_note_cloud(title, subject, content, tags, file_url, user_id):
    try:
        note_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        table = get_dynamodb_table()
        
        table.put_item(Item={
            'id': note_id,
            'title': title,
            'subject': subject,
            'content': content,
            'tags': tags,
            'file_url': file_url or '',
            'created_at': now,
            'updated_at': now,
            'pinned': False,
            'user_id': user_id
        })
        
        return {'success': True, 'id': note_id, 'message': 'Note added to cloud successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}



def get_users_table():
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )

    return dynamodb.Table(app.config['AWS_USERS_TABLE'])




def get_notes_cloud(user_id, subject=None, search=None, sort_by='latest'):
    try:
        table = get_dynamodb_table()
        response = table.scan(FilterExpression='user_id = :uid',
                             ExpressionAttributeValues={':uid': user_id})
        
        notes = response.get('Items', [])

        if subject:
            notes = [n for n in notes if n.get('subject') == subject]

        if search:
            search_lower = search.lower()
            notes = [n for n in notes if 
                    search_lower in n.get('title', '').lower() or 
                    search_lower in n.get('content', '').lower()]
        
        if sort_by == 'latest':
            notes.sort(key=lambda x: (-x.get('pinned', False), -datetime.fromisoformat(x.get('created_at', '')).timestamp()))
        elif sort_by == 'oldest':
            notes.sort(key=lambda x: (-x.get('pinned', False), datetime.fromisoformat(x.get('created_at', '')).timestamp()))
        elif sort_by == 'title_asc':
            notes.sort(key=lambda x: (-x.get('pinned', False), x.get('title', '').lower()))
        elif sort_by == 'title_desc':
            pinned_notes   = [n for n in notes if n.get('pinned', False)]
            unpinned_notes = [n for n in notes if not n.get('pinned', False)]
            pinned_notes.sort(key=lambda x: x.get('title', '').lower(), reverse=True)
            unpinned_notes.sort(key=lambda x: x.get('title', '').lower(), reverse=True)
            notes = pinned_notes + unpinned_notes
        
        return notes
    except Exception as e:
        return []

def delete_note_cloud(note_id, user_id):
    try:
        table = get_dynamodb_table()

        response = table.get_item(Key={'id': note_id})
        item = response.get('Item', {})
        
        if item.get('user_id') != user_id:
            return {'success': False, 'message': 'Unauthorized'}
  
        if item.get('file_url'):
            try:
                s3_client = get_s3_client()
                s3_client.delete_object(
                    Bucket=app.config['AWS_S3_BUCKET'],
                    Key=item['file_url'] 
                    
                )
            except Exception as e:
                app.logger.warning(f"S3 delete failed (non-fatal): {e}")
        
        table.delete_item(Key={'id': note_id})
        
        return {'success': True, 'message': 'Note deleted from cloud successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def pin_note_cloud(note_id, user_id):
    try:
        table = get_dynamodb_table()
 
        response = table.get_item(Key={'id': note_id})
        item = response.get('Item', {})
        
        if not item or item.get('user_id') != user_id:
            return {'success': False, 'message': 'Note not found or unauthorized'}
        
        new_pinned_status = not item.get('pinned', False)
        now = datetime.now().isoformat()
        
        table.update_item(
            Key={'id': note_id},
            UpdateExpression='SET pinned = :p, updated_at = :u',
            ExpressionAttributeValues={':p': new_pinned_status, ':u': now}
        )
        
        return {'success': True, 'pinned': new_pinned_status}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def update_note_cloud(note_id, user_id, title, subject, content, file_url=None):
    try:
        tags = mock_ai_tags(content, title, subject)
        now = datetime.now().isoformat()
        
        table = get_dynamodb_table()

        response = table.get_item(Key={'id': note_id})
        existing = response.get('Item')
        
        if not existing or existing.get('user_id') != user_id:
            return {'success': False, 'message': 'Note not found or unauthorized'}
  
        old_file_url = existing.get('file_url', '')
        if file_url and old_file_url and old_file_url != file_url:
            try:
                s3_client = get_s3_client()
                s3_client.delete_object(
                    Bucket=app.config['AWS_S3_BUCKET'],
                    Key=old_file_url
                )
            except Exception as e:
                app.logger.warning(f"Old S3 file delete failed (non-fatal): {e}")

        final_file_url = file_url if file_url else old_file_url
        
        update_expr = 'SET title = :t, subject = :s, content = :c, tags = :tg, file_url = :f, updated_at = :u'
        expr_values = {
            ':t': title,
            ':s': subject,
            ':c': content,
            ':tg': tags,
            ':f': final_file_url,
            ':u': now
        }
        
        table.update_item(
            Key={'id': note_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
        
        return {'success': True, 'message': 'Note updated in cloud successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_note_cloud(note_id, user_id):
    try:
        table = get_dynamodb_table()
        response = table.get_item(Key={'id': note_id})
        item = response.get('Item')
        
        if item and item.get('user_id') == user_id:
            return item
        return None
    except Exception as e:
        return None

def get_all_subjects_cloud(user_id):
    try:
        table = get_dynamodb_table()
        response = table.scan(ProjectionExpression='subject, user_id',
                             FilterExpression='user_id = :uid',
                             ExpressionAttributeValues={':uid': user_id})
        
        subjects = set()
        for item in response.get('Items', []):
            if item.get('subject'):
                subjects.add(item['subject'])
        
        return sorted(list(subjects))
    except Exception as e:
        return []


@app.route('/')
def index():
    return render_template('index.html', app_mode=app.config['APP_MODE'])

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'app_mode': app.config['APP_MODE'],
        'max_file_size': app.config['MAX_CONTENT_LENGTH'],
        'allowed_extensions': list(app.config['ALLOWED_EXTENSIONS'])
    })

@app.route('/api/add_note', methods=['POST'])
def add_note():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        data = request.form
        title = data.get('title', '').strip()
        subject = data.get('subject', '').strip()
        content = data.get('content', '').strip()
        file = request.files.get('file')

        if not title or not subject or not content:
            return jsonify({'success': False, 'message': 'Title, subject, and content are required'}), 400
        file_url = None
        if file and file.filename:
            file_url, file_error = save_file(file)
            if file_error:
                return jsonify({'success': False, 'message': file_error}), 400

        tags = mock_ai_tags(content, title, subject)

        if app.config['APP_MODE'] == 'LOCAL':
            result = add_note_local(title, subject, content, tags, file_url, user_id)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            result = add_note_cloud(title, subject, content, tags, file_url, user_id)
        
        return jsonify(result), 201 if result['success'] else 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/get_notes', methods=['GET'])
def get_notes():
    """Get all notes"""
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        subject = request.args.get('subject')
        search = request.args.get('search')
        sort_by = request.args.get('sort', 'latest')
        
        if app.config['APP_MODE'] == 'LOCAL':
            notes = get_notes_local(user_id, subject, search, sort_by)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            notes = get_notes_cloud(user_id, subject, search, sort_by)
        
        return jsonify({
            'success': True,
            'count': len(notes),
            'notes': notes
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/get_note/<note_id>', methods=['GET'])
def get_note(note_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        if app.config['APP_MODE'] == 'LOCAL':
            note = get_note_local(note_id, user_id)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            note = get_note_cloud(note_id, user_id)
        
        if note:
            return jsonify({'success': True, 'note': note}), 200
        else:
            return jsonify({'success': False, 'message': 'Note not found'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/delete_note/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        if app.config['APP_MODE'] == 'LOCAL':
            result = delete_note_local(note_id, user_id)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            result = delete_note_cloud(note_id, user_id)
        
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pin_note/<note_id>', methods=['PUT'])
def pin_note(note_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        if app.config['APP_MODE'] == 'LOCAL':
            result = pin_note_local(note_id, user_id)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            result = pin_note_cloud(note_id, user_id)
        
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/update_note/<note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        data = request.form
        title = data.get('title', '').strip()
        subject = data.get('subject', '').strip()
        content = data.get('content', '').strip()
        file = request.files.get('file')

        if not title or not subject or not content:
            return jsonify({'success': False, 'message': 'Title, subject, and content are required'}), 400
        
        file_url = None
        if file and file.filename:
            file_url, file_error = save_file(file)
            if file_error:
                return jsonify({'success': False, 'message': file_error}), 400

        if app.config['APP_MODE'] == 'LOCAL':
            result = update_note_local(note_id, user_id, title, subject, content, file_url)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            result = update_note_cloud(note_id, user_id, title, subject, content, file_url)
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_id = get_current_user_id()
        
        if app.config['APP_MODE'] == 'LOCAL':
            subjects = get_all_subjects_local(user_id)
        else:
            if not AWS_AVAILABLE:
                return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500
            subjects = get_all_subjects_cloud(user_id)
        
        return jsonify({
            'success': True,
            'subjects': subjects
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/uploads/<filename>')
def download_file(filename):
    if app.config['APP_MODE'] == 'LOCAL':
        from flask import send_from_directory
        try:
            return send_from_directory(app.config['LOCAL_STORAGE_PATH'], filename)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 404
    else:
        return jsonify({
            'success': False,
            'message': 'Use /api/file_url?key=<s3_key> to access cloud files'
        }), 400


@app.route('/api/file_url', methods=['GET'])
def get_file_url():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    if app.config['APP_MODE'] == 'LOCAL':
        return jsonify({'success': False, 'message': 'Not applicable in LOCAL mode'}), 400

    if not AWS_AVAILABLE:
        return jsonify({'success': False, 'message': 'AWS SDK not available'}), 500

    s3_key = request.args.get('key', '').strip()
    if not s3_key:
        return jsonify({'success': False, 'message': 'key parameter is required'}), 400

    url = get_s3_presigned_url(s3_key)
    if url:
        return jsonify({'success': True, 'url': url}), 200
    else:
        return jsonify({'success': False, 'message': 'Could not generate file URL'}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500



if __name__ == '__main__':
    print(f"\n{'='*70}")
    print(f"Smart Notes Application Starting")
    print(f"{'='*70}")
    print(f"Mode: {app.config['APP_MODE']}")
    print(f"URL: http://127.0.0.1:5000")
    print(f"{'='*70}\n")
    
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
