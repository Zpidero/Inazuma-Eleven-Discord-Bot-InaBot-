import aiosqlite

DB = "InaBot/data/cards.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                user_id TEXT,
                card_id TEXT,
                card_name TEXT,
                card_image TEXT,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_claims (
                user_id TEXT PRIMARY KEY,
                last_claim TIMESTAMP
            )
        """)
        await db.commit()

async def claim_card(user_id, card_id, card_name, card_image):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO collections (user_id, card_id, card_name, card_image) VALUES (?, ?, ?, ?)",
            (user_id, card_id, card_name, card_image)
        )
        await db.execute(
            "INSERT OR REPLACE INTO daily_claims (user_id, last_claim) VALUES (?, CURRENT_TIMESTAMP)",
            (user_id,)
        )
        await db.commit()

async def can_claim(user_id):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT last_claim FROM daily_claims WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return True
            from datetime import datetime, timezone
            last = datetime.fromisoformat(row[0])
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            return (now - last).total_seconds() >= 86400  # 24h

async def get_collection(user_id):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT card_id, card_name, card_image, obtained_at FROM collections WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()