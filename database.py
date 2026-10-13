import sqlite3
from datetime import datetime

DB_PATH = "chat_history.db"


def init_db():
    """创建表（如果不存在）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(role: str, content: str):
    """保存一条消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def load_messages():
    """加载所有历史消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]


def clear_messages():
    """清空所有消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()