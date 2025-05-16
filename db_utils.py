import sqlite3
from config import DB_FILE


CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_path TEXT,
    photo_name TEXT,
    extracted_text TEXT,
    translated_text TEXT,
    saved_file_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
'''


def get_connection():
    """Возвращает соединение с БД, считывающее строки как словари."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализирует базу данных, создаёт таблицу при необходимости."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def insert_record(user_id, file_path, photo_name, extracted_text, translated_text, saved_file_path):
    """Вставляет новую запись о переводе."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO database
            (user_id, file_path, photo_name, extracted_text, translated_text, saved_file_path)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (user_id, file_path, photo_name, extracted_text, translated_text, saved_file_path)
    )
    conn.commit()
    conn.close()


def record_exists(user_id, photo_name):
    """Проверяет, существует ли запись с заданным именем для пользователя."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT COUNT(*) FROM database WHERE user_id = ? AND photo_name = ?',
        (user_id, photo_name)
    )
    exists = cur.fetchone()[0] > 0
    conn.close()
    return exists


def fetch_history(user_id):
    """Возвращает список всех записей пользователя в порядке убывания времени."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, file_path, photo_name, extracted_text, translated_text, saved_file_path, timestamp
        FROM database
        WHERE user_id = ?
        ORDER BY timestamp DESC
        ''',
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    # Преобразовать sqlite3.Row в обычный dict
    return [dict(row) for row in rows]


def fetch_record_by_id(record_id):
    """Возвращает одну запись по её ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, user_id, file_path, photo_name, extracted_text, translated_text, saved_file_path, timestamp
        FROM database
        WHERE id = ?
        ''',
        (record_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_record(user_id, record_id=None):
    """Удаляет одну запись по ID или все записи пользователя, если record_id is None."""
    conn = get_connection()
    cur = conn.cursor()
    if record_id:
        cur.execute('DELETE FROM database WHERE id = ?', (record_id,))
    else:
        cur.execute('DELETE FROM database WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
