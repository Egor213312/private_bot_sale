import aiosqlite

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            tg_id INTEGER UNIQUE,
            name TEXT,
            phone TEXT,
            email TEXT,
            is_admin INTEGER DEFAULT 0
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1
        )""")
        await db.commit()

async def get_user(tg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone()

async def add_user(tg_id, name, phone, email, is_admin=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, name, phone, email, is_admin) VALUES (?, ?, ?, ?, ?)",
            (tg_id, name, phone, email, is_admin)
        )
        await db.commit()

async def update_user_email(tg_id, email):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET email = ? WHERE tg_id = ?", (email, tg_id))
        await db.commit()

async def update_user_phone(tg_id, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET phone = ? WHERE tg_id = ?", (phone, tg_id))
        await db.commit()

async def get_subscription(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM subscriptions WHERE user_id = ? AND active = 1", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_subscription(user_id, start_date, end_date):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO subscriptions (user_id, start_date, end_date, active) VALUES (?, ?, ?, 1)",
            (user_id, start_date, end_date)
        )
        await db.commit()

async def deactivate_subscriptions(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET active = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()

async def add_invite_link(user_id, invite_link):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET invite_link = ? WHERE user_id = ? AND active = 1", (invite_link, user_id))
        await db.commit()

async def get_invite_link(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT invite_link FROM subscriptions WHERE user_id = ? AND active = 1", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None 