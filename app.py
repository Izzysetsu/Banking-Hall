from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import os
import time
from werkzeug.utils import secure_filename
from database import init_db, get_playlist, add_media, update_media, delete_media, is_supabase_enabled, get_supabase_client

app = Flask(__name__)

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'mp4', 'webm', 'ogg'}:
        return 'video'
    return 'image'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# API Endpoints
@app.route('/api/playlist', methods=['GET'])
def api_get_playlist():
    playlist = get_playlist()
    return jsonify(playlist)

@app.route('/api/playlist/update', methods=['POST'])
def api_update_playlist():
    data = request.json
    for item in data:
        update_media(item['id'], item['duration'], item['animation'], item['order_index'])
    return jsonify({"status": "success"})

@app.route('/api/playlist/delete/<int:item_id>', methods=['DELETE'])
def api_delete_media(item_id):
    item = delete_media(item_id)
    if item:
        filename = item.get('filename') if isinstance(item, dict) else item
        if is_supabase_enabled():
            try:
                bucket = os.environ.get('SUPABASE_BUCKET', 'playlist-media')
                supabase = get_supabase_client()
                supabase.storage.from_(bucket).remove([filename])
            except Exception as e:
                app.logger.error(f"Error removing file from Supabase storage: {e}")
        else:
            if filename:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
    return jsonify({"status": "success"})

@app.route('/api/upload', methods=['POST'])
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
                bucket = os.environ.get('SUPABASE_BUCKET', 'playlist-media')
                file_bytes = file.read()
                content_type = file.content_type or ('video/mp4' if media_type == 'video' else 'image/jpeg')
                supabase = get_supabase_client()
                
                # Upload to Supabase Storage Bucket
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
    
    return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
