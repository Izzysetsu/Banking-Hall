import sqlite3
import os
from dotenv import load_dotenv

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
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite init error: {e}")

def get_playlist():
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('playlist').select('*').order('order_index', desc=False).order('id', desc=False).execute()
            return res.data if res.data else []
        except Exception as e:
            print(f"Supabase warning: {e}")
            return []

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

        supabase.table('playlist').insert(payload).execute()
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

def update_media(item_id, duration, animation, order_index):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        supabase.table('playlist').update({
            'duration': duration,
            'animation': animation,
            'order_index': order_index
        }).eq('id', item_id).execute()
        return

    conn = get_db_connection()
    conn.execute(
        'UPDATE playlist SET duration = ?, animation = ?, order_index = ? WHERE id = ?',
        (duration, animation, order_index, item_id)
    )
    conn.commit()
    conn.close()

def delete_media(item_id):
    if is_supabase_enabled():
        supabase = get_supabase_client()
        res = supabase.table('playlist').select('*').eq('id', item_id).execute()
        if res.data and len(res.data) > 0:
            item = res.data[0]
            supabase.table('playlist').delete().eq('id', item_id).execute()
            return item
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
