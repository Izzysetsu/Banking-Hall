import sqlite3
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

def is_supabase_enabled():
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_KEY', '')
    return bool(url and key and 'your-project-id' not in url and '...' not in key)

def get_supabase_client():
    if is_supabase_enabled():
        from supabase import create_client
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_KEY')
        return create_client(url, key)
    return None

def get_db_path():
    if os.environ.get('VERCEL'):
        return '/tmp/database.sqlite'
    return 'database.sqlite'

def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if is_supabase_enabled():
        ensure_default_users_supabase()
        return

    try:
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS playlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                type TEXT NOT NULL,
                url TEXT,
                duration INTEGER DEFAULT 10,
                animation TEXT DEFAULT 'fade',
                order_index INTEGER DEFAULT 0
            )
        ''')
        try:
            conn.execute('ALTER TABLE playlist ADD COLUMN url TEXT')
        except sqlite3.OperationalError:
            pass

        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

        ensure_default_users_sqlite()
    except Exception as e:
        print(f"SQLite init error: {e}")

def ensure_default_users_sqlite():
    try:
        conn = get_db_connection()
        count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        if count == 0:
            default_pass = generate_password_hash('admin123')
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', ('admin1', default_pass, 'admin'))
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', ('admin2', default_pass, 'admin'))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ensuring default users in SQLite: {e}")

def ensure_default_users_supabase():
    try:
        supabase = get_supabase_client()
        res = supabase.table('users').select('id').limit(1).execute()
        if not res.data:
            default_pass = generate_password_hash('admin123')
            supabase.table('users').insert([
                {'username': 'admin1', 'password_hash': default_pass, 'role': 'admin'},
                {'username': 'admin2', 'password_hash': default_pass, 'role': 'admin'}
            ]).execute()
    except Exception as e:
        print(f"Error ensuring default users in Supabase: {e}")

# USER CRUD FUNCTIONS
def get_user_by_username(username):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('users').select('*').eq('username', username).execute()
            return res.data[0] if res.data and len(res.data) > 0 else None
        except Exception as e:
            print(f"Supabase get_user_by_username error: {e}")
            return None

    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        print(f"SQLite get_user_by_username error: {e}")
        return None

def get_user_by_id(user_id):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('users').select('*').eq('id', user_id).execute()
            return res.data[0] if res.data and len(res.data) > 0 else None
        except Exception as e:
            print(f"Supabase get_user_by_id error: {e}")
            return None

    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        print(f"SQLite get_user_by_id error: {e}")
        return None

def get_all_users():
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('users').select('id, username, role, created_at').order('id', desc=False).execute()
            return res.data if res.data else []
        except Exception as e:
            print(f"Supabase get_all_users error: {e}")
            return []

    try:
        conn = get_db_connection()
        users = conn.execute('SELECT id, username, role, created_at FROM users ORDER BY id ASC').fetchall()
        conn.close()
        return [dict(u) for u in users]
    except Exception as e:
        print(f"SQLite get_all_users error: {e}")
        return []

def create_user(username, password_hash, role='admin'):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        res = supabase.table('users').insert({
            'username': username,
            'password_hash': password_hash,
            'role': role
        }).execute()
        return res.data[0] if res.data else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, password_hash, role))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return get_user_by_id(new_id)

def reset_user_password(user_id, new_password_hash):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        supabase.table('users').update({'password_hash': new_password_hash}).eq('id', user_id).execute()
        return True

    conn = get_db_connection()
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
    conn.commit()
    conn.close()
    return True

def delete_user(user_id):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        supabase.table('users').delete().eq('id', user_id).execute()
        return True

    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

# PLAYLIST FUNCTIONS
def get_playlist_from_storage(supabase):
    try:
        bucket = (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
        files = supabase.storage.from_(bucket).list()
        if not files:
            return []

        video_exts = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v', '3gp', 'flv', 'wmv', 'ts'}
        items = []

        for idx, f in enumerate(files):
            fname = f.get('name') if isinstance(f, dict) else getattr(f, 'name', None)
            if fname and fname != '.emptyFolderPlaceholder':
                ext = fname.rsplit('.', 1)[1].lower() if '.' in fname else ''
                m_type = 'video' if ext in video_exts else 'image'
                public_url = supabase.storage.from_(bucket).get_public_url(fname)

                items.append({
                    'id': idx + 1,
                    'filename': fname,
                    'type': m_type,
                    'url': public_url,
                    'duration': 10,
                    'animation': 'fade',
                    'order_index': idx + 1
                })
        return items
    except Exception as e:
        print(f"Storage fallback error: {e}")
        return []

def sync_storage_to_db(supabase):
    try:
        bucket = (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
        files = supabase.storage.from_(bucket).list()
        if not files:
            return

        try:
            res = supabase.table('playlist').select('filename').execute()
            existing_filenames = {item['filename'] for item in res.data} if res.data else set()
        except Exception:
            existing_filenames = set()

        video_exts = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v', '3gp', 'flv', 'wmv', 'ts'}

        for idx, f in enumerate(files):
            fname = f.get('name') if isinstance(f, dict) else getattr(f, 'name', None)
            if fname and fname not in existing_filenames and fname != '.emptyFolderPlaceholder':
                ext = fname.rsplit('.', 1)[1].lower() if '.' in fname else ''
                m_type = 'video' if ext in video_exts else 'image'
                public_url = supabase.storage.from_(bucket).get_public_url(fname)

                payload = {
                    'filename': fname,
                    'type': m_type,
                    'url': public_url,
                    'duration': 10,
                    'animation': 'fade',
                    'order_index': idx + 1
                }
                try:
                    supabase.table('playlist').insert(payload).execute()
                except Exception as insert_err:
                    print(f"Sync insert warning: {insert_err}")
    except Exception as e:
        print(f"Auto-sync warning: {e}")

def get_playlist():
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            sync_storage_to_db(supabase)
            res = supabase.table('playlist').select('*').order('order_index', desc=False).order('id', desc=False).execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception as e:
            print(f"Supabase DB query error: {e}")

        return get_playlist_from_storage(supabase)

    try:
        conn = get_db_connection()
        items = conn.execute('SELECT * FROM playlist ORDER BY order_index ASC, id ASC').fetchall()
        conn.close()
        return [dict(ix) for ix in items]
    except Exception as e:
        print(f"SQLite get_playlist error: {e}")
        return []

def add_media(filename, media_type, url=None):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('playlist').select('order_index').order('order_index', desc=True).limit(1).execute()
            max_order = res.data[0]['order_index'] if (res.data and len(res.data) > 0 and res.data[0].get('order_index') is not None) else 0
        except Exception:
            max_order = 0

        payload = {
            'filename': filename,
            'type': media_type,
            'duration': 10,
            'animation': 'fade',
            'order_index': max_order + 1
        }
        if url:
            payload['url'] = url

        try:
            supabase.table('playlist').insert(payload).execute()
        except Exception as e:
            print(f"Database insert warning: {e}")
        return

    conn = get_db_connection()
    result = conn.execute('SELECT MAX(order_index) as max_order FROM playlist').fetchone()
    max_order = result['max_order'] if result and result['max_order'] is not None else 0

    conn.execute(
        'INSERT INTO playlist (filename, type, url, duration, animation, order_index) VALUES (?, ?, ?, ?, ?, ?)',
        (filename, media_type, url, 10, 'fade', max_order + 1)
    )
    conn.commit()
    conn.close()

def update_media(item_id, duration, animation, order_index, filename=None):
    try:
        duration_val = int(duration) if (duration is not None and str(duration).strip().isdigit()) else 10
    except (ValueError, TypeError):
        duration_val = 10

    try:
        order_val = int(order_index) if (order_index is not None and str(order_index).strip().isdigit()) else 0
    except (ValueError, TypeError):
        order_val = 0

    if is_supabase_enabled():
        supabase = get_supabase_client()
        payload = {
            'duration': duration_val,
            'animation': animation or 'fade',
            'order_index': order_val
        }

        # 1. Try matching by filename first if provided
        if filename:
            res = supabase.table('playlist').select('id').eq('filename', filename).execute()
            if res.data and len(res.data) > 0:
                real_id = res.data[0]['id']
                supabase.table('playlist').update(payload).eq('id', real_id).execute()
                return True
            else:
                video_exts = {'mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v', '3gp', 'flv', 'wmv', 'ts'}
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                payload['filename'] = filename
                payload['type'] = 'video' if ext in video_exts else 'image'
                bucket = (os.environ.get('SUPABASE_BUCKET') or 'playlist-media').strip()
                payload['url'] = supabase.storage.from_(bucket).get_public_url(filename)
                supabase.table('playlist').insert(payload).execute()
                return True

        # 2. Try updating by item_id
        if item_id:
            supabase.table('playlist').update(payload).eq('id', item_id).execute()
            return True

        return False

    conn = get_db_connection()
    conn.execute(
        'UPDATE playlist SET duration = ?, animation = ?, order_index = ? WHERE id = ? OR filename = ?',
        (duration_val, animation, order_val, item_id, filename)
    )
    conn.commit()
    conn.close()
    return True

def delete_media(item_id):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('playlist').select('*').eq('id', item_id).execute()
            if res.data and len(res.data) > 0:
                item = res.data[0]
                supabase.table('playlist').delete().eq('id', item_id).execute()
                return item
        except Exception as e:
            print(f"Delete media DB warning: {e}")
        return None

    conn = get_db_connection()
    item = conn.execute('SELECT * FROM playlist WHERE id = ?', (item_id,)).fetchone()
    if item:
        conn.execute('DELETE FROM playlist WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return dict(item)
    conn.close()
    return None
