import aiosqlite
import json
from datetime import datetime
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                mode TEXT DEFAULT 'hard',
                hard_step TEXT,
                hard_vars TEXT,
                return_to TEXT,
                soft_history TEXT,
                attempts TEXT,
                last_activity TEXT
            )
        """)
        await db.commit()


def _default_state():
    return {
        "mode": "hard",
        "hard_step": "greeting",
        "hard_vars": {},
        "return_to": None,
        "soft_history": [],
        "attempts": {},
    }


async def get_state(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
    if not row:
        return _default_state()
    return {
        "mode": row[1] or "hard",
        "hard_step": row[2] or "greeting",
        "hard_vars": json.loads(row[3] or "{}"),
        "return_to": row[4],
        "soft_history": json.loads(row[5] or "[]"),
        "attempts": json.loads(row[6] or "{}"),
    }


async def set_state(user_id: int, **fields):
    current = await get_state(user_id)
    current.update(fields)
    current["last_activity"] = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users
            (user_id, mode, hard_step, hard_vars, return_to, soft_history, attempts, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            current["mode"],
            current["hard_step"],
            json.dumps(current["hard_vars"], ensure_ascii=False),
            current["return_to"],
            json.dumps(current["soft_history"][-10:], ensure_ascii=False),
            json.dumps(current["attempts"], ensure_ascii=False),
            current["last_activity"],
        ))
        await db.commit()
