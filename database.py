import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = 'database.sqlite'
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

def is_supabase_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY and 'your-project-id' not in SUPABASE_URL and '...' not in SUPABASE_KEY)

def get_supabase_client():
    if is_supabase_enabled():
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if is_supabase_enabled():
        # Using Supabase Cloud DB
        return

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

def get_playlist():
    if is_supabase_enabled():
        supabase = get_supabase_client()
        try:
            res = supabase.table('playlist').select('*').order('order_index', desc=False).order('id', desc=False).execute()
            return res.data if res.data else []
        except Exception as e:
            print(f"Supabase warning (bisa terjadi jika tabel/kolom belum dibuat): {e}")
            return []

    conn = get_db_connection()
    items = conn.execute('SELECT * FROM playlist ORDER BY order_index ASC, id ASC').fetchall()
    conn.close()
    return [dict(ix) for ix in items]

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
