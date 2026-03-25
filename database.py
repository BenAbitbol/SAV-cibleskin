"""SAV Assistant CibleSkin - Base de donnees SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "sav_data.db"


def get_db():
    """Retourne une connexion a la base de donnees."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialise les tables de la base de donnees."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT,
            price REAL,
            description TEXT,
            category TEXT,
            in_stock INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_email TEXT,
            channel TEXT NOT NULL,
            category TEXT,
            customer_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            context TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channel TEXT NOT NULL,
            category TEXT,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# --- Settings ---

def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value),
    )
    conn.commit()
    conn.close()


# --- Knowledge Base ---

def get_kb_articles(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT * FROM knowledge_base WHERE category = ? ORDER BY updated_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM knowledge_base ORDER BY category, updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_kb_article(article_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_base WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_kb_article(title, content, category, article_id=None):
    conn = get_db()
    if article_id:
        conn.execute(
            "UPDATE knowledge_base SET title=?, content=?, category=?, updated_at=datetime('now') WHERE id=?",
            (title, content, category, article_id),
        )
    else:
        conn.execute(
            "INSERT INTO knowledge_base (title, content, category) VALUES (?, ?, ?)",
            (title, content, category),
        )
    conn.commit()
    conn.close()


def delete_kb_article(article_id):
    conn = get_db()
    conn.execute("DELETE FROM knowledge_base WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()


# --- Products ---

def get_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_product(name, sku, price, description, category, in_stock, product_id=None):
    conn = get_db()
    if product_id:
        conn.execute(
            "UPDATE products SET name=?, sku=?, price=?, description=?, category=?, in_stock=? WHERE id=?",
            (name, sku, price, description, category, in_stock, product_id),
        )
    else:
        conn.execute(
            "INSERT INTO products (name, sku, price, description, category, in_stock) VALUES (?, ?, ?, ?, ?, ?)",
            (name, sku, price, description, category, in_stock),
        )
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


# --- Conversations ---

def save_conversation(customer_name, customer_email, channel, category, customer_message, ai_response, context, status="draft"):
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (customer_name, customer_email, channel, category, customer_message, ai_response, context, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (customer_name, customer_email, channel, category, customer_message, ai_response, context, status),
    )
    conn.commit()
    conn.close()


def get_conversations(limit=50, status=None, channel=None):
    conn = get_db()
    query = "SELECT * FROM conversations WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_conversation_status(conv_id, status):
    conn = get_db()
    conn.execute("UPDATE conversations SET status = ? WHERE id = ?", (status, conv_id))
    conn.commit()
    conn.close()


def get_conversation(conv_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_conversation(conv_id):
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()


# --- Templates ---

def get_templates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM templates ORDER BY channel, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_template(name, channel, category, content, template_id=None):
    conn = get_db()
    if template_id:
        conn.execute(
            "UPDATE templates SET name=?, channel=?, category=?, content=? WHERE id=?",
            (name, channel, category, content, template_id),
        )
    else:
        conn.execute(
            "INSERT INTO templates (name, channel, category, content) VALUES (?, ?, ?, ?)",
            (name, channel, category, content),
        )
    conn.commit()
    conn.close()


def delete_template(template_id):
    conn = get_db()
    conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()


# --- Stats ---

def get_stats():
    conn = get_db()
    stats = {}
    stats["total_conversations"] = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
    stats["by_channel"] = {
        r["channel"]: r["c"]
        for r in conn.execute("SELECT channel, COUNT(*) as c FROM conversations GROUP BY channel").fetchall()
    }
    stats["by_status"] = {
        r["status"]: r["c"]
        for r in conn.execute("SELECT status, COUNT(*) as c FROM conversations GROUP BY status").fetchall()
    }
    stats["by_category"] = {
        r["category"]: r["c"]
        for r in conn.execute(
            "SELECT category, COUNT(*) as c FROM conversations WHERE category IS NOT NULL GROUP BY category"
        ).fetchall()
    }
    stats["total_products"] = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    stats["total_kb_articles"] = conn.execute("SELECT COUNT(*) as c FROM knowledge_base").fetchone()["c"]
    conn.close()
    return stats
