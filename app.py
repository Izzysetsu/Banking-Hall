from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
import os
import time
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    init_db, get_playlist, add_media, update_media, delete_media,
    is_supabase_enabled, get_supabase_client,
    get_user_by_username, get_user_by_id, get_all_users,
    create_user, reset_user_password, delete_user
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'banking_hall_secret_key_2026_super_secure')

if os.environ.get('VERCEL'):
    app.config['UPLOAD_FOLDER'] = os.path.join('/tmp', 'uploads')
else:
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max limit

# Ensure upload folder exists safely
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception:
    pass

# Initialize database safely
try:
    init_db()
except Exception:
    pass

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized. Silakan login terlebih dahulu."}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v', '3gp', 'flv', 'wmv', 'ts'}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'heic', 'heif', 'tiff', 'ico'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'image'

def ensure_supabase_bucket(supabase, bucket_name):
    try:
        supabase.storage.get_bucket(bucket_name)
    except Exception:
        try:
            supabase.storage.create_bucket(bucket_name, options={'public': True})
        except Exception:
            pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'admin')
            return redirect(url_for('admin'))
        else:
            error = "Username atau password salah!"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html', current_user=session.get('username'))

# USER MANAGEMENT API ENDPOINTS
@app.route('/api/user/me', methods=['GET'])
@login_required
def api_user_me():
    return jsonify({
        "id": session.get('user_id'),
        "username": session.get('username'),
        "role": session.get('role')
    })

@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    users = get_all_users()
    return jsonify(users)

@app.route('/api/users/add', methods=['POST'])
@login_required
def api_add_user():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"error": "Username dan password wajib diisi"}), 400

    existing = get_user_by_username(username)
    if existing:
        return jsonify({"error": "Username sudah digunakan"}), 400

    password_hash = generate_password_hash(password)
    user = create_user(username, password_hash)
    if user:
        return jsonify({"status": "success", "user": {"id": user['id'], "username": user['username'], "role": user.get('role', 'admin')}})
    return jsonify({"error": "Gagal menambah user"}), 500

@app.route('/api/users/reset-password', methods=['POST'])
@login_required
def api_reset_password():
    data = request.json or {}
    user_id = data.get('user_id')
    new_password = data.get('new_password', '').strip()

    if not user_id or not new_password:
        return jsonify({"error": "User ID dan password baru wajib diisi"}), 400

    new_hash = generate_password_hash(new_password)
    reset_user_password(user_id, new_hash)
    return jsonify({"status": "success"})

@app.route('/api/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({"error": "Tidak dapat menghapus akun Anda sendiri yang sedang aktif!"}), 400

    users = get_all_users()
    if len(users) <= 1:
        return jsonify({"error": "Tidak dapat menghapus! Minimal harus ada 1 akun admin di sistem."}), 400

    delete_user(user_id)
    return jsonify({"status": "success"})

# PLAYLIST API ENDPOINTS
@app.route('/api/config', methods=['GET'])
def api_config():
    return jsonify({
        "supabase_enabled": is_supabase_enabled(),
        "supabase_url": os.environ.get('SUPABASE_URL', ''),
        "supabase_key": os.environ.get('SUPABASE_KEY', ''),
        "supabase_bucket": (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
    })

@app.route('/api/playlist', methods=['GET'])
def api_get_playlist():
    playlist = get_playlist()
    return jsonify(playlist)

@app.route('/api/playlist/update', methods=['POST'])
@login_required
def api_update_playlist():
    data = request.json
    for item in data:
        update_media(item['id'], item['duration'], item['animation'], item['order_index'])
    return jsonify({"status": "success"})

@app.route('/api/media/add', methods=['POST'])
@login_required
def api_add_media():
    data = request.json or {}
    filename = data.get('filename')
    media_type = data.get('type', 'image')
    url = data.get('url')
    if filename:
        add_media(filename, media_type, url=url)
        return jsonify({"status": "success"})
    return jsonify({"error": "Filename missing"}), 400

@app.route('/api/playlist/delete/<path:item_id>', methods=['DELETE'])
@login_required
def api_delete_media(item_id):
    try:
        numeric_id = int(item_id)
    except ValueError:
        numeric_id = None

    target_filename = None

    if numeric_id is not None:
        item = delete_media(numeric_id)
        if item and isinstance(item, dict):
            target_filename = item.get('filename')

    if not target_filename:
        current_list = get_playlist()
        for p in current_list:
            if str(p.get('id')) == str(item_id) or p.get('filename') == str(item_id):
                target_filename = p.get('filename')
                if numeric_id is not None:
                    delete_media(numeric_id)
                break

    if not target_filename and '.' in str(item_id):
        target_filename = str(item_id)

    if target_filename:
        if is_supabase_enabled():
            try:
                bucket = (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
                supabase = get_supabase_client()
                supabase.storage.from_(bucket).remove([target_filename])
            except Exception as e:
                app.logger.error(f"Error removing file from Supabase storage: {e}")
        else:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], target_filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

    return jsonify({"status": "success"})

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = f"{int(time.time())}_{secure_filename(file.filename)}"
        media_type = get_media_type(filename)
        
        if is_supabase_enabled():
            try:
                bucket = (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
                file_bytes = file.read()
                content_type = file.content_type or ('video/mp4' if media_type == 'video' else 'image/jpeg')
                supabase = get_supabase_client()
                
                ensure_supabase_bucket(supabase, bucket)
                
                supabase.storage.from_(bucket).upload(
                    path=filename,
                    file=file_bytes,
                    file_options={"content-type": content_type}
                )
                
                public_url = supabase.storage.from_(bucket).get_public_url(filename)
                add_media(filename, media_type, url=public_url)
                return jsonify({"status": "success", "filename": filename, "url": public_url})
            except Exception as e:
                app.logger.error(f"Supabase upload error: {e}")
                return jsonify({"error": f"Gagal upload ke Supabase Storage: {str(e)}"}), 500
        else:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            add_media(filename, media_type)
            return jsonify({"status": "success", "filename": filename})
    
    return jsonify({"error": "Format file tidak didukung"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
