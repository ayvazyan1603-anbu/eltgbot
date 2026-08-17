import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT,
                last_visit TEXT
            )
        """)
        
        # Таблица типов продуктов (категорий)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Таблица брендов / подкатегорий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_type TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(category_type, name)
            )
        """)

        # Таблица товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                photo_id TEXT,
                stock_count INTEGER DEFAULT 0,
                category_type TEXT DEFAULT 'Обувь',
                brand TEXT DEFAULT 'Другое',
                article TEXT DEFAULT '',
                size TEXT DEFAULT '',
                color TEXT DEFAULT '',
                season TEXT DEFAULT '',
                is_sale INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                buys_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Таблица заказов
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
                status TEXT DEFAULT 'pending_payment',
                delivery_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Таблица корзины
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                created_at TEXT,
                UNIQUE(user_id, product_id)
            )
        """)

        await db.commit()

        # Добавляем стандартные категории если их нет
        default_categories = ["Обувь", "Одежда", "Аксессуары", "Электроника"]
        for cat in default_categories:
            await db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
        
        # Миграция колонок на случай если таблица products уже существовала без новых полей
        existing_cols = []
        async with db.execute("PRAGMA table_info(products)") as cursor:
            rows = await cursor.fetchall()
            existing_cols = [row[1] for row in rows]
        
        new_cols = {
            "category_type": "TEXT DEFAULT 'Обувь'",
            "brand": "TEXT DEFAULT 'Другое'",
            "article": "TEXT DEFAULT ''",
            "size": "TEXT DEFAULT ''",
            "color": "TEXT DEFAULT ''",
            "season": "TEXT DEFAULT ''"
        }
        for col, col_type in new_cols.items():
            if col not in existing_cols:
                try:
                    await db.execute(f"ALTER TABLE products ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

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

# --- КАТЕГОРИИ И БРЕНДЫ ---

async def get_all_category_types() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM categories ORDER BY id ASC") as cursor:
            cats = [row[0] for row in await cursor.fetchall()]
        
        # Также достаем уникальные типы из товаров
        async with db.execute("SELECT DISTINCT category_type FROM products WHERE category_type IS NOT NULL AND category_type != ''") as cursor:
            prod_cats = [row[0] for row in await cursor.fetchall()]

        for c in prod_cats:
            if c not in cats:
                cats.append(c)
        return cats or ["Обувь", "Одежда", "Аксессуары", "Электроника"]

async def add_category_type(name: str):
    name = name.strip()
    if not name:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        await db.commit()

async def get_brands_by_category(category_type: str) -> list[dict]:
    """
    Возвращает список словарей: [{'name': 'Adidas', 'count': 5}, ...]
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Бренды из базы брендов
        async with db.execute("SELECT name FROM brands WHERE category_type = ?", (category_type,)) as cursor:
            saved_brands = [row[0] for row in await cursor.fetchall()]
        
        # Подсчет количества товаров для каждого бренда
        async with db.execute("""
            SELECT brand, COUNT(*) as count 
            FROM products 
            WHERE category_type = ? AND brand IS NOT NULL AND brand != '' AND stock_count > 0
            GROUP BY brand
        """, (category_type,)) as cursor:
            brand_counts = {row[0]: row[1] for row in await cursor.fetchall()}

        # Собираем общий список
        all_brand_names = list(saved_brands)
        for b in brand_counts.keys():
            if b not in all_brand_names:
                all_brand_names.append(b)

        result = []
        for b in sorted(all_brand_names):
            result.append({
                "name": b,
                "count": brand_counts.get(b, 0)
            })
        return result

async def add_brand(category_type: str, brand_name: str):
    category_type = category_type.strip()
    brand_name = brand_name.strip()
    if not brand_name or not category_type:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO brands (category_type, name) VALUES (?, ?)", (category_type, brand_name))
        await db.commit()

# --- ТОВАРЫ ---

async def add_product(
    title: str,
    description: str,
    price: float,
    photo_id: str | None,
    stock_count: int,
    category_type: str = "Обувь",
    brand: str = "Другое",
    article: str = "",
    size: str = "",
    color: str = "",
    season: str = "",
    is_sale: int = 0,
    is_new: int = 0
) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Автоматически сохраняем категорию и бренд в справочники
    await add_category_type(category_type)
    await add_brand(category_type, brand)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO products (
                title, description, price, photo_id, stock_count,
                category_type, brand, article, size, color, season,
                is_sale, is_new, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, price, photo_id, stock_count,
            category_type, brand, article, size, color, season,
            is_sale, is_new, now
        ))
        await db.commit()
        return cursor.lastrowid

async def get_all_products() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_products_by_filter(
    category_type: str | None = None,
    brand: str | None = None,
    is_sale: int | None = None,
    is_new: int | None = None,
    article: str | None = None,
    size: str | None = None,
    color: str | None = None,
    season: str | None = None,
    search_query: str | None = None,
    in_stock_only: bool = True
) -> list[dict]:
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if in_stock_only:
        query += " AND stock_count > 0"
    if category_type:
        query += " AND category_type = ?"
        params.append(category_type)
    if brand:
        query += " AND brand = ?"
        params.append(brand)
    if is_sale is not None:
        query += " AND is_sale = ?"
        params.append(is_sale)
    if is_new is not None:
        query += " AND is_new = ?"
        params.append(is_new)
    if article:
        query += " AND (article LIKE ? OR title LIKE ?)"
        params.append(f"%{article}%")
        params.append(f"%{article}%")
    if size:
        query += " AND size LIKE ?"
        params.append(f"%{size}%")
    if color:
        query += " AND color LIKE ?"
        params.append(f"%{color}%")
    if season:
        query += " AND season LIKE ?"
        params.append(f"%{season}%")
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ? OR brand LIKE ?)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")

    query += " ORDER BY id DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_product(product_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_product_field(product_id: int, field: str, value):
    allowed_fields = {
        "title", "description", "price", "photo_id", "stock_count",
        "category_type", "brand", "article", "size", "color", "season",
        "is_sale", "is_new"
    }
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")
    
    if field == "category_type":
        await add_category_type(str(value))
    
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

# --- КОРЗИНА ---

async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cart (user_id, product_id, quantity, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, product_id) DO UPDATE SET
                quantity = quantity + excluded.quantity
        """, (user_id, product_id, quantity, now))
        await db.commit()

async def get_cart(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.id as cart_id, c.quantity, p.* 
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def remove_from_cart(user_id: int, product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        await db.commit()

async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

# --- ЗАКАЗЫ ---

async def create_order(user_id: int, product_id: int, product_title: str, product_price: float, delivery_method: str, full_name: str, phone: str, address: str, status: str = "pending_payment") -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, product_id, product_title, product_price, delivery_method, full_name, phone, address, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, product_id, product_title, product_price, delivery_method, full_name, phone, address, status, now, now))
        await db.commit()
        return cursor.lastrowid

async def get_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_user_orders(user_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def mark_order_as_paid(order_id: int) -> dict | None:
    order = await get_order(order_id)
    if not order:
        return None

    if order["status"] == "pending_payment" or order["status"] == "new":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE orders 
                SET status = 'paid', updated_at = ? 
                WHERE id = ?
            """, (now, order_id))
            await db.commit()
        
        await decrease_stock(order["product_id"], 1)
        await increment_buy(order["product_id"])
        
        return await get_order(order_id)
    
    return order

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

        async with db.execute("SELECT COUNT(*) as paid_orders FROM orders WHERE status != 'pending_payment'") as cursor:
            paid_row = await cursor.fetchone()
            paid_orders = paid_row["paid_orders"] if paid_row else 0

        async with db.execute("SELECT * FROM products ORDER BY views_count DESC, buys_count DESC") as cursor:
            products = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "products": products
        }
