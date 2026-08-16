import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT,
                last_visit TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                photo_id TEXT,
                stock_count INTEGER DEFAULT 0,
                is_sale INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                buys_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_title TEXT NOT NULL,
                product_price REAL NOT NULL,
                delivery_method TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                delivery_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await db.commit()

async def add_or_update_user(user_id: int, username: str | None, first_name: str | None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, created_at, last_visit)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_visit = excluded.last_visit
        """, (user_id, username, first_name, now, now))
        await db.commit()

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# --- ТОВАРЫ ---

async def add_product(title: str, description: str, price: float, photo_id: str | None, stock_count: int, is_sale: int = 0, is_new: int = 0) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO products (title, description, price, photo_id, stock_count, is_sale, is_new, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, price, photo_id, stock_count, is_sale, is_new, now))
        await db.commit()
        return cursor.lastrowid

async def get_all_products() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_products_in_stock() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE stock_count > 0 ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_new_products() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE is_new = 1 ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_sale_products() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE is_sale = 1 ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_product(product_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_product_field(product_id: int, field: str, value):
    allowed_fields = {"title", "description", "price", "photo_id", "stock_count", "is_sale", "is_new"}
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
        await db.commit()

async def decrease_stock(product_id: int, count: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE products 
            SET stock_count = MAX(0, stock_count - ?) 
            WHERE id = ?
        """, (count, product_id))
        await db.commit()

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()

async def increment_view(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE products SET views_count = views_count + 1 WHERE id = ?", (product_id,))
        await db.commit()

async def increment_buy(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE products SET buys_count = buys_count + 1 WHERE id = ?", (product_id,))
        await db.commit()

# --- ЗАКАЗЫ ---

async def create_order(user_id: int, product_id: int, product_title: str, product_price: float, delivery_method: str, full_name: str, phone: str, address: str) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, product_id, product_title, product_price, delivery_method, full_name, phone, address, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
        """, (user_id, product_id, product_title, product_price, delivery_method, full_name, phone, address, now, now))
        await db.commit()
        return cursor.lastrowid

async def get_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_orders(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_order_status(order_id: int, status: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders 
            SET status = ?, updated_at = ? 
            WHERE id = ?
        """, (status, now, order_id))
        await db.commit()

async def update_order_delivery_date(order_id: int, delivery_date: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders 
            SET delivery_date = ?, status = 'date_assigned', updated_at = ? 
            WHERE id = ?
        """, (delivery_date, now, order_id))
        await db.commit()

# --- СТАТИСТИКА ---

async def get_bot_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) as total_users FROM users") as cursor:
            user_row = await cursor.fetchone()
            total_users = user_row["total_users"] if user_row else 0
        
        async with db.execute("SELECT COUNT(*) as total_orders FROM orders") as cursor:
            order_row = await cursor.fetchone()
            total_orders = order_row["total_orders"] if order_row else 0

        async with db.execute("SELECT * FROM products ORDER BY views_count DESC, buys_count DESC") as cursor:
            products = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "products": products
        }
