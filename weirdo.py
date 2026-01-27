import asyncio
import os
import re
import random
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


# =======================
# CONFIG
# =======================
TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
DEFAULT_TZ = os.getenv("BOT_TZ", "Europe/Moscow")

# Триггеры 💩
RE_TRIGGER = re.compile(
    r"(?<!\w)(пар(а|ы|е|у|ой|ам|ами|ах)?|долг(и|а|у|ом|ов|ам|ами|ах)?)(?!\w)",
    re.IGNORECASE | re.UNICODE,
)
RE_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+", re.UNICODE)

EASTER_PROB = 0.005
ECHO_PROB = 0.005
AUTO_HYPE_PROB = 0.005

DAILY_TRIGGER_LIMIT = 5
POOP_AFTER_DAILY_LIMIT_PROB = 0.25
MIN_EASTER_EVERY_MIN = 20
MIN_AUTOHYPE_EVERY_HOURS = 6

# Репутация
REP_COOLDOWN_MIN = 10
ALLOW_NEGATIVE_REP = True

# Дуэли
DUEL_ACCEPT_MIN = 2
DUEL_ROUND_SECONDS = 60
DUEL_HP = 4
DUEL_AMMO_MAX = 3
DUEL_BASE_ACC = 0.35
DUEL_AIM_BONUS = 0.20
DUEL_DODGE_PENALTY = 0.30
DUEL_MAX_ACC = 0.85
DUEL_HEAL_AMOUNT = 1
DUEL_REP_REWARD = 3

DUEL_CRIT_BASE = 0.10
DUEL_CRIT_AFTER_AIM = 0.22
DUEL_CRIT_DMG = 2
DUEL_FUMBLE_PROB = 0.04

SHOP_ITEMS = {
    "title_neon": {"price": 250, "type": "title", "value": "⚡ NEON"},
    "title_void": {"price": 400, "type": "title", "value": "🕳️ VOID"},
    "duel_kit":   {"price": 150, "type": "consumable", "value": {"hp": 1, "ammo": 1}},  # одноразовый
    "slot_charm": {"price": 200, "type": "consumable", "value": {"refund_pct": 30}},   # одноразовый “страховка”
}

RANKS = [
    (0,    "🪨 Новичок"),
    (200,  "🔧 Стажёр"),
    (600,  "⚙️ Мастерок"),
    (1500, "🧠 Архитектор"),
    (3000, "👑 Легенда"),
]
REP_RANKS = [
    (0,   "😶 no-name"),
    (50,  "🙂 заметный"),
    (200,  "😎 уважаемый"),
    (500,  "🧠 авторитет"),
    (1000, "👑 легенда чата"),
]

WIN_RANKS = [
    (0,    "🪙 новичок"),
    (300,  "💰 копилка"),
    (1000, "🏦 игрок"),
    (2500, "💎 богач"),
    (6000, "👑 магнат"),
]

CHAT_RANKS = [
    (0,    "🫥 молчун"),
    (50,   "💬 в теме"),
    (500,  "🗣️ активист"),
    (1500,  "📣 голос чата"),
    (5000, "🔥 двигатель"),
]


# Эпики
EPIC_ONE_HP = [
    "☠️ {name} едва держится. Следующий выстрел решит всё.",
    "🩸 {name} на последнем дыхании.",
    "🕯️ {name} балансирует между жизнью и поражением.",
]
EPIC_BOTH_ONE_HP = [
    "⚡ Оба на 1❤. Тишина перед развязкой.",
    "🔥 У обоих по 1❤. Следующий ход — финал.",
]
EPIC_NEAR_MISS = [
    "🫣 Пуля прошла в миллиметре.",
    "💨 Настолько близко, что воздух дрогнул.",
    "😬 Это должно было попасть.",
]
EPIC_DOUBLE_MISS = [
    "🥶 Нервы не выдержали. Оба промахнулись.",
    "😶 Слишком много напряжения — ни одного попадания.",
]
EPIC_CRIT = [
    "💥 КРИТ! Это было слишком точно.",
    "⚡ Критический выстрел — больно.",
    "🔥 В яблочко. Критическое попадание!",
]

# /luck
LUCK_COOLDOWN_MIN = 120
LUCK_REP_MIN = 1
LUCK_REP_MAX = 5

# Баффы на следующую дуэль
LUCK_BUFFS = [
    ("acc", 0.10, "🎯 Бафф: +10% точности в следующей дуэли"),
    ("hp", 1, "❤️ Бафф: +1 HP в следующей дуэли"),
    ("ammo", 1, "🔫 Бафф: +1 патрон в начале следующей дуэли"),
    ("crit", 0.12, "💥 Бафф: +12% шанс крита в следующей дуэли"),
]

# Команды статистики (антиспам)
WHEREALL_COOLDOWN_MIN = 1
INTERESTING_COOLDOWN_MIN = 1

# Храним “последнюю реплику” чата (для echo)
_last_chat_text = {}  # chat_id -> str


# =======================
# TIME / TEXT
# =======================
def now_tz(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))

def date_key(dt: datetime) -> str:
    return dt.date().isoformat()

def tokenize(text: str):
    return [w.lower() for w in RE_WORD.findall(text or "")]

def normalize_phrase(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t

def has_trigger(text: str) -> bool:
    return bool(RE_TRIGGER.search(text or ""))

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def epic_fmt(t: str, **kw) -> str:
    return t.format(**kw)

def fmt_dt(dt: datetime, tz: str) -> str:
    # коротко, но понятно
    try:
        loc = dt.astimezone(ZoneInfo(tz))
    except Exception:
        loc = dt
    return loc.strftime("%Y-%m-%d %H:%M:%S")

def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


# =======================
# DB HELPERS
# =======================
def db_exec(sql, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    con.close()

def db_one(sql, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    con.close()
    return row

def db_all(sql, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 1,
        tz TEXT NOT NULL DEFAULT '',
        quiet_until TEXT,
        last_message_at TEXT,
        last_easter_at TEXT,
        last_autohype_at TEXT,
        last_where_all_at TEXT,
        last_interesting_at TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_trigger_count (
        chat_id INTEGER,
        day TEXT,
        cnt INTEGER NOT NULL,
        PRIMARY KEY(chat_id, day)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS msg_log (
        chat_id INTEGER,
        ts TEXT,
        user_id INTEGER
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_msg_log_chat_ts ON msg_log(chat_id, ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_msg_log_chat_user_ts ON msg_log(chat_id, user_id, ts)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS word_log (
        chat_id INTEGER,
        ts TEXT,
        word TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_word_log_chat_ts ON word_log(chat_id, ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_word_log_chat_word_ts ON word_log(chat_id, word, ts)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS phrase_log (
        chat_id INTEGER,
        ts TEXT,
        phrase TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_phrase_log_chat_ts ON phrase_log(chat_id, ts)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_cache (
        chat_id INTEGER,
        user_id INTEGER,
        display TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rep (
        chat_id INTEGER,
        user_id INTEGER,
        score INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rep_votes (
        chat_id INTEGER,
        from_user_id INTEGER,
        to_user_id INTEGER,
        ts TEXT NOT NULL,
        PRIMARY KEY(chat_id, from_user_id, to_user_id)
    )""")

    # duels
    cur.execute("""
    CREATE TABLE IF NOT EXISTS duels (
        chat_id INTEGER,
        duel_id TEXT PRIMARY KEY,
        a_id INTEGER NOT NULL,
        b_id INTEGER NOT NULL,
        state TEXT NOT NULL,
        created_at TEXT NOT NULL,
        accept_deadline TEXT NOT NULL,
        arena_msg_id INTEGER,
        data TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_duels_chat_state ON duels(chat_id, state)")

    # luck
    cur.execute("""
    CREATE TABLE IF NOT EXISTS luck_cooldown (
        chat_id INTEGER,
        user_id INTEGER,
        ts TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS luck_buff (
        chat_id INTEGER,
        user_id INTEGER,
        buff_json TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")
    # скрытая удача
    cur.execute("""
    CREATE TABLE IF NOT EXISTS luck_score (
        chat_id INTEGER,
        user_id INTEGER,
        score INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(chat_id, user_id)
    )""")

        # =======================
    # TOKENS ECONOMY
    # =======================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wallet (
        chat_id INTEGER,
        user_id INTEGER,
        balance INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS token_tx (
        chat_id INTEGER,
        ts TEXT NOT NULL,
        from_user_id INTEGER,
        to_user_id INTEGER,
        amount INTEGER NOT NULL,
        kind TEXT NOT NULL,
        meta TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_token_tx_chat_ts ON token_tx(chat_id, ts)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS slot_cooldown (
        chat_id INTEGER,
        user_id INTEGER,
        ts TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jackpot_pool (
        chat_id INTEGER PRIMARY KEY,
        amount INTEGER NOT NULL DEFAULT 0
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS treasury (
        chat_id INTEGER PRIMARY KEY,
        amount INTEGER NOT NULL DEFAULT 0
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_claim (
        chat_id INTEGER,
        user_id INTEGER,
        day TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id, day)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_streak (
        chat_id INTEGER,
        user_id INTEGER,
        last_claim_at TEXT,
        streak INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS duel_bets (
        duel_id TEXT PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        bet INTEGER NOT NULL DEFAULT 0,
        a_paid INTEGER NOT NULL DEFAULT 0,
        b_paid INTEGER NOT NULL DEFAULT 0
    )""")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_duel_bets_chat ON duel_bets(chat_id)")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(chat_id, user_id, item)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    title TEXT DEFAULT NULL,
    PRIMARY KEY(chat_id, user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_stats (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,

        msg_count INTEGER NOT NULL DEFAULT 0,

        tokens_earned INTEGER NOT NULL DEFAULT 0,  -- всего получено токенов (daily, выигрыши, банк дуэли)
        tokens_spent  INTEGER NOT NULL DEFAULT 0,  -- всего потрачено (ставки, покупки)

        slot_spent INTEGER NOT NULL DEFAULT 0,
        slot_won   INTEGER NOT NULL DEFAULT 0,     -- выплаты по слотам (включая джекпот)

        duel_wins   INTEGER NOT NULL DEFAULT 0,
        duel_losses INTEGER NOT NULL DEFAULT 0,
        duel_bank_won INTEGER NOT NULL DEFAULT 0,  -- сколько токенов выиграно банками дуэлей

        updated_at TEXT,

        PRIMARY KEY(chat_id, user_id)
    )""")

    con.commit()
    con.close()

def ensure_chat(chat_id: int):
    row = db_one("SELECT chat_id FROM chat_settings WHERE chat_id=?", (chat_id,))
    if row is None:
        db_exec("INSERT INTO chat_settings(chat_id, tz) VALUES(?, ?)", (chat_id, DEFAULT_TZ))

def get_settings(chat_id: int):
    ensure_chat(chat_id)
    row = db_one("""
    SELECT enabled, tz, quiet_until, last_message_at, last_easter_at, last_autohype_at,
           last_where_all_at, last_interesting_at
    FROM chat_settings WHERE chat_id=?
    """, (chat_id,))
    enabled, tz, quiet_until, last_msg, last_easter, last_autohype, last_where, last_interesting = row
    tz = tz if tz else DEFAULT_TZ

    def parse_dt(s):
        return datetime.fromisoformat(s) if s else None

    return {
        "enabled": bool(enabled),
        "tz": tz,
        "quiet_until": parse_dt(quiet_until),
        "last_message_at": parse_dt(last_msg),
        "last_easter_at": parse_dt(last_easter),
        "last_autohype_at": parse_dt(last_autohype),
        "last_where_all_at": parse_dt(last_where),
        "last_interesting_at": parse_dt(last_interesting),
    }

def set_field(chat_id: int, field: str, value):
    ensure_chat(chat_id)
    if isinstance(value, datetime):
        value = value.isoformat()
    db_exec(f"UPDATE chat_settings SET {field}=? WHERE chat_id=?", (value, chat_id))

def set_null(chat_id: int, field: str):
    ensure_chat(chat_id)
    db_exec(f"UPDATE chat_settings SET {field}=NULL WHERE chat_id=?", (chat_id,))

def inc_daily_trigger(chat_id: int, day: str) -> int:
    row = db_one("SELECT cnt FROM daily_trigger_count WHERE chat_id=? AND day=?", (chat_id, day))
    if row is None:
        db_exec("INSERT INTO daily_trigger_count(chat_id, day, cnt) VALUES(?, ?, 1)", (chat_id, day, 1))
        return 1
    cnt = row[0] + 1
    db_exec("UPDATE daily_trigger_count SET cnt=? WHERE chat_id=? AND day=?", (cnt, chat_id, day))
    return cnt

def add_msg_log(chat_id: int, ts: datetime, user_id: int):
    db_exec("INSERT INTO msg_log(chat_id, ts, user_id) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), user_id))

def add_words(chat_id: int, ts: datetime, words):
    rows = []
    for w in words:
        w = w.lower()
        if len(w) < 3:
            continue
        rows.append((chat_id, ts.isoformat(), w))
    if not rows:
        return
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executemany("INSERT INTO word_log(chat_id, ts, word) VALUES(?, ?, ?)", rows)
    con.commit()
    con.close()

def add_phrase(chat_id: int, ts: datetime, phrase: str):
    if not phrase:
        return
    phrase = normalize_phrase(phrase)
    if not phrase or len(phrase) > 300:
        return
    db_exec("INSERT INTO phrase_log(chat_id, ts, phrase) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), phrase))

def prune_logs(chat_id: int, cutoff: datetime):
    cutoff_s = cutoff.isoformat()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM msg_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))
    cur.execute("DELETE FROM word_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))
    cur.execute("DELETE FROM phrase_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))
    con.commit()
    con.close()

def get_top_phrase(chat_id: int, since: datetime):
    rows = db_all("""
    SELECT phrase, COUNT(*) as c
    FROM phrase_log
    WHERE chat_id=? AND ts>=?
    GROUP BY phrase
    ORDER BY c DESC
    LIMIT 1
    """, (chat_id, since.isoformat()))
    return rows[0] if rows else None

def get_top_words(chat_id: int, since: datetime, limit=3):
    return db_all("""
    SELECT word, COUNT(*) as c
    FROM word_log
    WHERE chat_id=? AND ts>=?
    GROUP BY word
    ORDER BY c DESC
    LIMIT ?
    """, (chat_id, since.isoformat(), limit))

def get_user_counts(chat_id: int, since: datetime):
    return db_all("""
    SELECT user_id, COUNT(*) as c
    FROM msg_log
    WHERE chat_id=? AND ts>=?
    GROUP BY user_id
    ORDER BY c DESC
    """, (chat_id, since.isoformat()))

def upsert_user_display(chat_id: int, user_id: int, display: str, ts: datetime):
    display = (display or "").strip() or f"id:{user_id}"
    db_exec("""
    INSERT INTO user_cache(chat_id, user_id, display, updated_at)
    VALUES(?, ?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET
      display=excluded.display,
      updated_at=excluded.updated_at
    """, (chat_id, user_id, display, ts.isoformat()))

def get_user_display(chat_id: int, user_id: int) -> str:
    row = db_one("SELECT display FROM user_cache WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return row[0] if row else f"id:{user_id}"

def find_user_id_by_username(chat_id: int, username: str) -> int | None:
    row = db_one("SELECT user_id FROM user_cache WHERE chat_id=? AND display=?", (chat_id, f"@{username}"))
    return int(row[0]) if row else None


# =======================
# REPUTATION
# =======================
def rep_get(chat_id: int, user_id: int) -> int:
    row = db_one("SELECT score FROM rep WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return int(row[0]) if row else 0

def rep_add(chat_id: int, user_id: int, delta: int):
    db_exec("""
    INSERT INTO rep(chat_id, user_id, score) VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET score = score + ?
    """, (chat_id, user_id, delta, delta))

def rep_all(chat_id: int):
    return db_all("""
        SELECT user_id, score
        FROM rep
        WHERE chat_id=?
        ORDER BY score DESC, user_id ASC
    """, (chat_id,))

def rep_can_vote(chat_id: int, from_id: int, to_id: int, now: datetime, cooldown_min: int = REP_COOLDOWN_MIN) -> bool:
    row = db_one("""
    SELECT ts FROM rep_votes WHERE chat_id=? AND from_user_id=? AND to_user_id=?
    """, (chat_id, from_id, to_id))
    if not row:
        return True
    last = datetime.fromisoformat(row[0])
    return (now - last) >= timedelta(minutes=cooldown_min)

def rep_mark_vote(chat_id: int, from_id: int, to_id: int, now: datetime):
    db_exec("""
    INSERT INTO rep_votes(chat_id, from_user_id, to_user_id, ts)
    VALUES(?, ?, ?, ?)
    ON CONFLICT(chat_id, from_user_id, to_user_id) DO UPDATE SET ts=excluded.ts
    """, (chat_id, from_id, to_id, now.isoformat()))

# =======================
# TOKENS WALLET
# =======================
MAX_BET = 200
SLOT_COOLDOWN_MIN = 10
PAY_FEE_PCT = 3  # комиссия на переводы, %

def wallet_get(chat_id: int, user_id: int) -> int:
    row = db_one("SELECT balance FROM wallet WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return int(row[0]) if row else 0

def wallet_add(chat_id: int, user_id: int, delta: int):
    db_exec("""
    INSERT INTO wallet(chat_id, user_id, balance) VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET balance = balance + ?
    """, (chat_id, user_id, delta, delta))

def wallet_set(chat_id: int, user_id: int, value: int):
    value = max(0, int(value))
    db_exec("""
    INSERT INTO wallet(chat_id, user_id, balance) VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET balance = excluded.balance
    """, (chat_id, user_id, value))

def tx_log(chat_id: int, ts: datetime, from_uid: int | None, to_uid: int | None, amount: int, kind: str, meta: str | None = None):
    db_exec(
        "INSERT INTO token_tx(chat_id, ts, from_user_id, to_user_id, amount, kind, meta) VALUES(?, ?, ?, ?, ?, ?, ?)",
        (chat_id, ts.isoformat(), from_uid, to_uid, int(amount), kind, meta),
    )

def pool_get(chat_id: int, table: str) -> int:
    row = db_one(f"SELECT amount FROM {table} WHERE chat_id=?", (chat_id,))
    return int(row[0]) if row else 0

def pool_add(chat_id: int, table: str, delta: int):
    db_exec(f"""
    INSERT INTO {table}(chat_id, amount) VALUES(?, ?)
    ON CONFLICT(chat_id) DO UPDATE SET amount = amount + ?
    """, (chat_id, int(delta), int(delta)))

def econ_snapshot(chat_id: int) -> dict:
    total_wallet = db_one("SELECT COALESCE(SUM(balance),0) FROM wallet WHERE chat_id=?", (chat_id,))
    total_wallet = int(total_wallet[0]) if total_wallet else 0

    holders = db_one("SELECT COUNT(*) FROM wallet WHERE chat_id=? AND balance>0", (chat_id,))
    holders = int(holders[0]) if holders else 0

    treasury = pool_get(chat_id, "treasury")
    jackpot = pool_get(chat_id, "jackpot_pool")

    return {
        "total_wallet": total_wallet,
        "holders": holders,
        "treasury": int(treasury),
        "jackpot": int(jackpot),
    }

def pool_set(chat_id: int, table: str, value: int):
    value = max(0, int(value))
    db_exec(f"""
    INSERT INTO {table}(chat_id, amount) VALUES(?, ?)
    ON CONFLICT(chat_id) DO UPDATE SET amount = excluded.amount
    """, (chat_id, value))

def slot_can_spin(chat_id: int, user_id: int, now: datetime) -> bool:
    row = db_one("SELECT ts FROM slot_cooldown WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    if not row:
        return True
    last = datetime.fromisoformat(row[0])
    return (now - last) >= timedelta(minutes=SLOT_COOLDOWN_MIN)

def slot_mark_spin(chat_id: int, user_id: int, now: datetime):
    db_exec("""
    INSERT INTO slot_cooldown(chat_id, user_id, ts)
    VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET ts=excluded.ts
    """, (chat_id, user_id, now.isoformat()))

def daily_claimed(chat_id: int, user_id: int, day: str) -> bool:
    row = db_one(
        "SELECT 1 FROM daily_claim WHERE chat_id=? AND user_id=? AND day=?",
        (chat_id, user_id, day),
    )
    return bool(row)

def daily_mark_claim(chat_id: int, user_id: int, day: str):
    db_exec(
        "INSERT OR IGNORE INTO daily_claim(chat_id, user_id, day) VALUES(?, ?, ?)",
        (chat_id, user_id, day),
    )

def daily_streak_get(chat_id: int, user_id: int):
    return db_one(
        "SELECT last_claim_at, streak FROM daily_streak WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )

def daily_streak_set(chat_id: int, user_id: int, last_claim_at: datetime, streak: int):
    db_exec("""
    INSERT INTO daily_streak(chat_id, user_id, last_claim_at, streak)
    VALUES(?, ?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET
      last_claim_at=excluded.last_claim_at,
      streak=excluded.streak
    """, (chat_id, user_id, last_claim_at.isoformat(), int(streak)))

def duel_bet_create(chat_id: int, duel_id: str, bet: int):
    db_exec(
        "INSERT INTO duel_bets(duel_id, chat_id, bet, a_paid, b_paid) VALUES(?, ?, ?, 0, 0)",
        (duel_id, chat_id, int(bet)),
    )

def duel_bet_get(duel_id: str):
    return db_one("SELECT chat_id, bet, a_paid, b_paid FROM duel_bets WHERE duel_id=?", (duel_id,))

def duel_bet_set_paid(duel_id: str, a_paid: int | None = None, b_paid: int | None = None):
    row = duel_bet_get(duel_id)
    if not row:
        return
    chat_id, bet, ap, bp = row
    ap = ap if a_paid is None else int(a_paid)
    bp = bp if b_paid is None else int(b_paid)
    db_exec("UPDATE duel_bets SET a_paid=?, b_paid=? WHERE duel_id=?", (ap, bp, duel_id))

def duel_bet_delete(duel_id: str):
    db_exec("DELETE FROM duel_bets WHERE duel_id=?", (duel_id,))

def duel_mark_loss(chat_id: int, duel_id: str, loser_id: int, now: datetime):
    # проигрыш учитываем один раз: если дуэль уже удалена из ставок, всё равно можно писать loss
    stats_inc(chat_id, loser_id, "duel_losses", 1, now)

def duel_bet_payout(chat_id: int, duel_id: str, winner_id: int, now: datetime):
    row = duel_bet_get(duel_id)
    if not row:
        return 0
    _chat, bet, a_paid, b_paid = row
    bet = int(bet)
    if bet <= 0:
        duel_bet_delete(duel_id)
        return 0

    bank = bet * 2
    wallet_add(chat_id, winner_id, bank)

    # победителю начислили банк — это "выигрыш общий"
    stats_inc(chat_id, winner_id, "tokens_earned", bank, now)
    stats_inc(chat_id, winner_id, "duel_bank_won", bank, now)
    stats_inc(chat_id, winner_id, "duel_wins", 1, now)

    tx_log(chat_id, now, None, winner_id, bank, "duel_bet_payout", meta=f"duel_id={duel_id},bet={bet}")
    duel_bet_delete(duel_id)
    return bank

# =======================
# SLOTS (TOKENS) — режимы риска + джекпот
# =======================
# доли ставки
JACKPOT_PCT = 8   # % в джекпот
TREASURY_PCT = 2  # % в казну

# таблицы выплат: (multiplier, weight)
SLOT_TABLES = {
    # почти безопасно, около нуля/чуть в плюс
    "low":  [(0.0, 14), (0.5, 16), (1.0, 45), (1.5, 16), (2.0, 6), (3.0, 2), (5.0, 1)],

    # в среднем около нуля
    "mid":  [(0.0, 18), (0.5, 15), (1.0, 40), (1.5, 15), (2.0, 8), (3.0, 3), (5.0, 1)],

    # риск выше (можно оставить около нуля/слегка минус, но с шансом больших x)
    "high": [(0.0, 28), (0.5, 12), (1.0, 28), (2.0, 18), (4.0, 10), (8.0, 4)],
}


JACKPOT_CHANCE = {  # шанс “сорвать банк”
    "low":  0.002,
    "mid":  0.003,
    "high": 0.005,
}

def weighted_choice(pairs):
    total = sum(w for _, w in pairs)
    r = random.randint(1, total)
    s = 0
    for val, w in pairs:
        s += w
        if r <= s:
            return val
    return pairs[-1][0]

def parse_slot_args(args: str | None) -> tuple[str, int] | None:
    """
    /slot 50
    /slot 50 high
    /slot high 50
    """
    if not args:
        return None
    parts = [p for p in (args or "").split() if p.strip()]
    if not parts:
        return None

    mode = "mid"
    bet = None

    for p in parts:
        pl = p.lower()
        if pl in ("low", "mid", "high"):
            mode = pl
        elif p.isdigit():
            bet = int(p)

    if bet is None:
        return None

    bet = max(1, min(MAX_BET, bet))
    return mode, bet

def slot_spin(mode: str) -> tuple[str, float, bool]:
    """
    returns: (emoji_line, multiplier, jackpot_hit)
    """
    mode = mode if mode in SLOT_TABLES else "mid"

    # шанс сорвать джекпот
    if random.random() < JACKPOT_CHANCE[mode]:
        return "👑 | 👑 | 👑", 0.0, True

    mult = float(weighted_choice(SLOT_TABLES[mode]))
    # просто визуал, не влияет на математику
    if mult >= 8:
        line = "💎 | 💎 | 💎"
    elif mult >= 4:
        line = "🔥 | 🔥 | 🔥"
    elif mult >= 2:
        line = "🍀 | 🍀 | 🍀"
    elif mult >= 1:
        line = "🍋 | 🍋 | 🍋"
    elif mult > 0:
        line = "🍒 | 🍒 | 🍒"
    else:
        line = "💀 | 💀 | 💀"

    return line, mult, False

# =======================
# SAFE EDIT (ANTI FLOOD)
# =======================
_last_edit_at = {}
_last_edit_text = {}

async def safe_edit_text(msg: Message, text: str, reply_markup=None, *, min_interval=1.2):
    if msg is None:
        return

    now = datetime.utcnow()
    key = (msg.chat.id, msg.message_id)

    if _last_edit_text.get(key) == text:
        return

    last_at = _last_edit_at.get(key)
    if last_at and (now - last_at).total_seconds() < min_interval:
        return

    try:
        await msg.edit_text(text, reply_markup=reply_markup)
        _last_edit_at[key] = now
        _last_edit_text[key] = text
    except Exception:
        # не шумим, Telegram/aiogram сам иногда ругается на слишком частые edits
        pass


# =======================
# LUCK / SLOTS
# =======================
def luck_can_spin(chat_id: int, user_id: int, now: datetime) -> bool:
    row = db_one("SELECT ts FROM luck_cooldown WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    if not row:
        return True
    last = datetime.fromisoformat(row[0])
    return (now - last) >= timedelta(minutes=LUCK_COOLDOWN_MIN)

def luck_mark_spin(chat_id: int, user_id: int, now: datetime):
    db_exec("""
    INSERT INTO luck_cooldown(chat_id, user_id, ts)
    VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET ts=excluded.ts
    """, (chat_id, user_id, now.isoformat()))

def luck_set_buff(chat_id: int, user_id: int, buff: dict):
    db_exec("""
    INSERT INTO luck_buff(chat_id, user_id, buff_json)
    VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET buff_json=excluded.buff_json
    """, (chat_id, user_id, json.dumps(buff, ensure_ascii=False)))

def luck_pop_buff(chat_id: int, user_id: int) -> dict | None:
    row = db_one("SELECT buff_json FROM luck_buff WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    if not row:
        return None
    try:
        buff = json.loads(row[0])
    except Exception:
        buff = None
    db_exec("DELETE FROM luck_buff WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return buff

def spin_slots(luck_score: int) -> tuple[str, dict | None, int]:
    reels = ["🍒", "🍋", "💎", "🍀", "💥", "🧠", "👑"]
    r1, r2, r3 = random.choice(reels), random.choice(reels), random.choice(reels)
    rep_win = random.randint(LUCK_REP_MIN, LUCK_REP_MAX)

    # luck_score даёт небольшой бонус/штраф к репе (-1..+1)
    rep_win += int(round(luck_score / 100.0))
    rep_win = max(0, rep_win)

    buff = None
    if r1 == r2 == r3:
        rep_win += 3
        kind, val, _ = random.choice(LUCK_BUFFS)
        buff = {"kind": kind, "value": val}
    else:
        # чем выше luck_score, тем выше шанс баффа (пример: от 15% до 45%)
        base_p = 0.25
        p = clamp(base_p + (luck_score / 100.0) * 0.20, 0.15, 0.45)

        if random.random() < p:
            kind, val, _ = random.choice(LUCK_BUFFS)
            buff = {"kind": kind, "value": val}

    text = f"{r1} | {r2} | {r3}"
    return text, buff, rep_win

def buff_desc(buff: dict) -> str:
    kind = buff.get("kind")
    val = buff.get("value")
    if kind == "acc":
        return f"🎯 Бафф: +{int(float(val)*100)}% точности в следующей дуэли"
    if kind == "hp":
        return f"❤️ Бафф: +{val} HP в следующей дуэли"
    if kind == "ammo":
        return f"🔫 Бафф: +{val} патрон(а) в начале следующей дуэли"
    if kind == "crit":
        return f"💥 Бафф: +{int(float(val)*100)}% шанс крита в следующей дуэли"
    return "🎲 Бафф удачи"

def luckscore_get(chat_id: int, user_id: int) -> int:
    row = db_one("SELECT score FROM luck_score WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return int(row[0]) if row else 0

def luckscore_add(chat_id: int, user_id: int, delta: int):
    # ограничим диапазон, чтобы не улетало в космос
    cur = luckscore_get(chat_id, user_id) + int(delta)
    cur = clamp(cur, -100, 100)
    db_exec("""
    INSERT INTO luck_score(chat_id, user_id, score) VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET score=excluded.score
    """, (chat_id, user_id, cur))

def luck_aura(luck_score: int) -> str:
    if luck_score >= 60:
        return "🍀 аура: очень везёт"
    if luck_score >= 25:
        return "✨ аура: везёт"
    if luck_score <= -60:
        return "💀 аура: чёрная полоса"
    if luck_score <= -25:
        return "🌧️ аура: не везёт"
    return "🫥 аура: ровно"

# =======================
# DUELS
# =======================
ACTION_ALIASES = {
    "стрелять": "shoot", "выстрел": "shoot", "shoot": "shoot",
    "прицел": "aim", "целюсь": "aim", "aim": "aim",
    "уклон": "dodge", "уклониться": "dodge", "dodge": "dodge",
    "перезарядка": "reload", "перезаряд": "reload", "reload": "reload",
    "перевязка": "heal", "лечиться": "heal", "heal": "heal",
}

def act_name(action: str) -> str:
    return {
        "aim": "🎯 прицел",
        "reload": "🔄 перезарядка",
        "heal": "🩹 перевязка",
        "dodge": "🕺 уклон",
        "shoot": "🔫 выстрел",
        "surrender": "🏳️ сдача",
    }.get(action, action)

def kb_duel_actions(duel_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔫 Стрелять", callback_data=f"duel:act:{duel_id}:shoot")
    kb.button(text="🎯 Прицел", callback_data=f"duel:act:{duel_id}:aim")
    kb.button(text="🕺 Уклон", callback_data=f"duel:act:{duel_id}:dodge")
    kb.button(text="🔄 Перезарядка", callback_data=f"duel:act:{duel_id}:reload")
    kb.button(text="🩹 Перевязка", callback_data=f"duel:act:{duel_id}:heal")
    kb.button(text="🏳️ Сдаться", callback_data=f"duel:act:{duel_id}:surrender")
    kb.adjust(2, 2, 2)
    return kb.as_markup()

def kb_duel_accept(duel_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принять", callback_data=f"duel:accept:{duel_id}")
    kb.button(text="❌ Отказ", callback_data=f"duel:decline:{duel_id}")
    kb.adjust(2)
    return kb.as_markup()

def duel_new_data(a_id: int, b_id: int) -> dict:
    return {
        "round": 1,
        "round_seconds": DUEL_ROUND_SECONDS,
        "deadline": None,
        "players": {
            str(a_id): {"hp": DUEL_HP, "ammo": DUEL_AMMO_MAX, "acc": DUEL_BASE_ACC, "heal_used": False, "aimed": False, "crit_bonus": 0.0},
            str(b_id): {"hp": DUEL_HP, "ammo": DUEL_AMMO_MAX, "acc": DUEL_BASE_ACC, "heal_used": False, "aimed": False, "crit_bonus": 0.0},
        },
        "turn": str(a_id),
        "moves": {str(a_id): None, str(b_id): None},
        "last_round_lines": [],
    }

def duel_apply_luck_buff(chat_id: int, user_id: int, p: dict) -> str | None:
    buff = luck_pop_buff(chat_id, user_id)
    if not buff:
        return None

    kind = buff.get("kind")
    val = buff.get("value")
    if kind == "acc":
        p["acc"] = clamp(float(p["acc"]) + float(val), 0.05, DUEL_MAX_ACC)
        return "🎲 Бафф удачи применён: +точность"
    if kind == "hp":
        p["hp"] = int(p["hp"]) + int(val)
        return "🎲 Бафф удачи применён: +HP"
    if kind == "ammo":
        p["ammo"] = int(p["ammo"]) + int(val)
        return "🎲 Бафф удачи применён: +патроны"
    if kind == "crit":
        p["crit_bonus"] = float(p.get("crit_bonus", 0.0)) + float(val)
        return "🎲 Бафф удачи применён: +шанс крита"
    return None

def duel_create(chat_id: int, a_id: int, b_id: int, now: datetime) -> str:
    duel_id = str(uuid.uuid4())
    accept_deadline = now + timedelta(minutes=DUEL_ACCEPT_MIN)
    data = duel_new_data(a_id, b_id)
    db_exec("""
    INSERT INTO duels(chat_id, duel_id, a_id, b_id, state, created_at, accept_deadline, data)
    VALUES(?, ?, ?, ?, 'pending', ?, ?, ?)
    """, (chat_id, duel_id, a_id, b_id, now.isoformat(), accept_deadline.isoformat(), json.dumps(data, ensure_ascii=False)))
    return duel_id

def duel_get(chat_id: int, duel_id: str):
    return db_one("""
    SELECT duel_id, a_id, b_id, state, accept_deadline, arena_msg_id, data
    FROM duels WHERE chat_id=? AND duel_id=?
    """, (chat_id, duel_id))

def duel_get_pending_for_b(chat_id: int, b_id: int):
    return db_one("""
    SELECT duel_id, a_id, b_id, accept_deadline
    FROM duels
    WHERE chat_id=? AND b_id=? AND state='pending'
    ORDER BY created_at DESC
    LIMIT 1
    """, (chat_id, b_id))

def duel_get_active_by_arena(chat_id: int, arena_msg_id: int):
    return db_one("""
    SELECT duel_id, a_id, b_id, data
    FROM duels
    WHERE chat_id=? AND arena_msg_id=? AND state='active'
    """, (chat_id, arena_msg_id))

def duel_set_state(chat_id: int, duel_id: str, state: str):
    db_exec("UPDATE duels SET state=? WHERE chat_id=? AND duel_id=?", (state, chat_id, duel_id))

def duel_set_arena(chat_id: int, duel_id: str, arena_msg_id: int):
    db_exec("UPDATE duels SET arena_msg_id=? WHERE chat_id=? AND duel_id=?", (arena_msg_id, chat_id, duel_id))

def duel_update_data(chat_id: int, duel_id: str, data: dict):
    db_exec("UPDATE duels SET data=? WHERE chat_id=? AND duel_id=?", (json.dumps(data, ensure_ascii=False), chat_id, duel_id))

def duel_activate(chat_id: int, duel_id: str, arena_msg_id: int):
    db_exec("UPDATE duels SET state='active', arena_msg_id=? WHERE chat_id=? AND duel_id=?", (arena_msg_id, chat_id, duel_id))

def duel_start_round(data: dict, now_dt: datetime, a_id: int, b_id: int):
    data["last_epic"] = None
    data["moves"][str(a_id)] = None
    data["moves"][str(b_id)] = None
    data["turn"] = str(a_id)
    data["deadline"] = (now_dt + timedelta(seconds=int(data.get("round_seconds", DUEL_ROUND_SECONDS)))).isoformat()

def duel_status_text(chat_id: int, a_id: int, b_id: int, data: dict) -> str:
    a = data["players"][str(a_id)]
    b = data["players"][str(b_id)]
    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)

    def moved(uid: int) -> str:
        return "✅ походил" if data["moves"].get(str(uid)) else "⏳ ждёт"

    def hp_bar(hp: int, max_hp: int) -> str:
        hp = max(0, min(hp, max_hp))
        return "█" * hp + "░" * (max_hp - hp)

    def ammo_bar(ammo: int, max_ammo: int) -> str:
        ammo = max(0, min(ammo, max_ammo))
        return "●" * ammo + "○" * (max_ammo - ammo)

    deadline_str = ""
    if data.get("deadline"):
        try:
            dl = datetime.fromisoformat(data["deadline"])
            remain_s = int((dl - datetime.now(dl.tzinfo)).total_seconds())
            if remain_s < 0:
                remain_s = 0
            deadline_str = f"{remain_s}s"
        except Exception:
            deadline_str = ""

    round_s = int(data.get("round_seconds", DUEL_ROUND_SECONDS))

    def p_block(name: str, p: dict, uid: int) -> str:
        acc = int(float(p["acc"]) * 100)
        hp = int(p["hp"])
        ammo = int(p["ammo"])
        heal_left = 0 if p.get("heal_used") else 1

        # базовые лимиты
        base_hp_max = DUEL_HP
        base_ammo_max = DUEL_AMMO_MAX

        # сколько сверху базы (от баффов)
        extra_hp = max(0, hp - base_hp_max)
        extra_ammo = max(0, ammo - base_ammo_max)

        def hp_bar(hp_val: int, max_hp: int) -> str:
            hp_val = max(0, min(hp_val, max_hp))
            return "█" * hp_val + "░" * (max_hp - hp_val)

        def ammo_bar(ammo_val: int, max_ammo: int) -> str:
            ammo_val = max(0, min(ammo_val, max_ammo))
            return "●" * ammo_val + "○" * (max_ammo - ammo_val)

        hp_line = f"❤️ {hp}/{base_hp_max}  {hp_bar(hp, base_hp_max)}"
        if extra_hp > 0:
            hp_line += f" (+{extra_hp})"

        ammo_line = f"🔫 {ammo_bar(ammo, base_ammo_max)}"
        if extra_ammo > 0:
            ammo_line += f" (+{extra_ammo})"

        return (
            f"👤 {name}\n"
            f"{hp_line}\n"
            f"{ammo_line}   🎯 {acc}%   🩹{heal_left}\n"
            f"{moved(uid)}"
        )

    last_lines = []
    for line in (data.get("last_round_lines") or []):
        line = (line or "").strip()
        if line:
            last_lines.append("— " + line)

    last_block = ""
    if last_lines:
        last_block = "\n\n🧾 Прошлый раунд:\n" + "\n".join(last_lines)

    epic = (data.get("last_epic") or "").strip()
    if epic:
        last_block += "\n\n⚡ Эпик момент:\n" + epic

    header = f"🤠 ДУЭЛЬ • Раунд {data.get('round', 1)}"
    timer = f"⏱️ Осталось: {deadline_str} (раунд {round_s}s)" if deadline_str else f"⏱️ Раунд: {round_s}s"
    
    turn_id = safe_int(data.get("turn"), 0)
    turn_name = get_user_display(chat_id, turn_id) if turn_id else "?"
    
    return (
        f"{header}\n"
        f"▶️ Ходит: {turn_name}\n"
        f"{timer}\n\n"
        f"{p_block(a_name, a, a_id)}\n\n"
        f"{p_block(b_name, b, b_id)}"
        f"{last_block}\n\n"
        f"Жми кнопки ниже 👇"
    )

def duel_resolve_round(chat_id: int, duel_id: str, a_id: int, b_id: int, data: dict) -> tuple[str, bool]:
    pA = data["players"][str(a_id)]
    pB = data["players"][str(b_id)]
    mA = data["moves"].get(str(a_id))
    mB = data["moves"].get(str(b_id))

    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)

    if mA is None:
        mA = "dodge"
    if mB is None:
        mB = "dodge"

    a_hp_before = int(pA["hp"])
    b_hp_before = int(pB["hp"])

    log = []

    def apply_action(action: str, me: dict, actor_name: str):
        if action == "aim":
            me["acc"] = clamp(float(me["acc"]) + DUEL_AIM_BONUS, DUEL_BASE_ACC, DUEL_MAX_ACC)
            me["aimed"] = True
            log.append(f"{actor_name}: 🎯 прицел.")
        elif action == "reload":
            me["ammo"] = DUEL_AMMO_MAX
            log.append(f"{actor_name}: 🔄 перезарядка.")
        elif action == "heal":
            if me.get("heal_used"):
                log.append(f"{actor_name}: 🩹 перевязка не удалась (уже была).")
            else:
                me["heal_used"] = True
                before = int(me["hp"])
                me["hp"] = clamp(int(me["hp"]) + DUEL_HEAL_AMOUNT, 0, 99)
                log.append(f"{actor_name}: 🩹 перевязка ({before}→{int(me['hp'])}❤).")
        elif action == "dodge":
            log.append(f"{actor_name}: 🕺 уклон.")

    def shoot(shooter_name: str, shooter: dict, target_name: str, target: dict, target_action: str):
        if DUEL_FUMBLE_PROB > 0 and random.random() < DUEL_FUMBLE_PROB:
            log.append(f"{shooter_name}: 🔫 осечка!")
            shooter["aimed"] = False
            return {"shot": True, "hit": False, "crit": False, "near": False}

        if int(shooter["ammo"]) <= 0:
            log.append(f"{shooter_name}: 🔫 щёлк — патронов нет.")
            shooter["aimed"] = False
            return {"shot": False, "hit": False, "crit": False, "near": False}

        shooter["ammo"] = int(shooter["ammo"]) - 1

        chance = float(shooter["acc"])
        if target_action == "dodge":
            chance = clamp(chance - DUEL_DODGE_PENALTY, 0.05, 0.95)

        roll = random.random()
        hit = roll < chance
        near = (not hit) and abs(roll - chance) <= 0.07

        if hit:
            base_crit = DUEL_CRIT_AFTER_AIM if shooter.get("aimed") else DUEL_CRIT_BASE
            crit_bonus = float(shooter.get("crit_bonus", 0.0))
            crit = random.random() < clamp(base_crit + crit_bonus, 0.0, 0.95)

            dmg = DUEL_CRIT_DMG if crit else 1
            target["hp"] = max(0, int(target["hp"]) - dmg)

            if crit:
                log.append(f"{shooter_name}: 💥 КРИТ по {target_name}! (-{dmg}❤)")
            else:
                log.append(f"{shooter_name}: 🔫 попадание по {target_name}. (-1❤)")
        else:
            miss_lines = ["💨 МИМО!", "🫥 промах.", "🧱 пуля в стену.", "🌪️ мимо цели."]
            log.append(f"{shooter_name}: 🔫 {random.choice(miss_lines)}")

        shooter["aimed"] = False
        return {"shot": True, "hit": hit, "crit": crit if hit else False, "near": near}

    # 1) небоевые
    if mA != "shoot":
        apply_action(mA, pA, a_name)
    if mB != "shoot":
        apply_action(mB, pB, b_name)

    # 2) стрельба
    sA = sB = None
    if mA == "shoot":
        sA = shoot(a_name, pA, b_name, pB, mB)
    if mB == "shoot":
        sB = shoot(b_name, pB, a_name, pA, mA)

    a_hp_after = int(pA["hp"])
    b_hp_after = int(pB["hp"])

    def short_line(name: str, action: str, before: int, after: int) -> str:
        if action == "heal":
            return f"{name}: {act_name(action)} ({before}→{after}❤️)"
        return f"{name}: {act_name(action)}"

    data["last_round_lines"] = [
        short_line(a_name, mA, a_hp_before, a_hp_after),
        short_line(b_name, mB, b_hp_before, b_hp_after),
    ]

    epic = None
    if a_hp_after == 1 and b_hp_after == 1:
        epic = epic_fmt(random.choice(EPIC_BOTH_ONE_HP))
    elif a_hp_after == 1:
        epic = epic_fmt(random.choice(EPIC_ONE_HP), name=a_name)
    elif b_hp_after == 1:
        epic = epic_fmt(random.choice(EPIC_ONE_HP), name=b_name)
    else:
        if (sA and sA.get("near")) or (sB and sB.get("near")):
            epic = random.choice(EPIC_NEAR_MISS)
        elif (sA and sB and sA.get("shot") and sB.get("shot") and (not sA.get("hit")) and (not sB.get("hit"))):
            epic = random.choice(EPIC_DOUBLE_MISS)

    if (sA and sA.get("crit")) or (sB and sB.get("crit")):
        log.append(random.choice(EPIC_CRIT))

    if epic:
        log.append(epic)

    # сохраним эпик отдельно, чтобы показать в статусе
    data["last_epic"] = epic  # будет None если не было

    body = "\n".join([x for x in log if x.strip()]) if log else "Тишина."
    # сохраним лог раунда (чтобы показать в статусе)
    data["last_round_log"] = [x for x in log if (x or "").strip()][-2:]  # последние 2 строк

    finished = False
    result = ""

    if int(pA["hp"]) <= 0 and int(pB["hp"]) <= 0:
        finished = True
        result = "Оба падают. Ничья."
    elif int(pA["hp"]) <= 0:
        finished = True
        rep_add(chat_id, b_id, DUEL_REP_REWARD)
        score = rep_get(chat_id, b_id)
        result = f"Победа {b_name}. +{DUEL_REP_REWARD} репутации (итого {score})."
    elif int(pB["hp"]) <= 0:
        finished = True
        rep_add(chat_id, a_id, DUEL_REP_REWARD)
        score = rep_get(chat_id, a_id)
        result = f"Победа {a_name}. +{DUEL_REP_REWARD} репутации (итого {score})."

    if finished:
        return f"{body}\n\n{result}", True

    data["round"] = int(data.get("round", 1)) + 1
    data["moves"][str(a_id)] = None
    data["moves"][str(b_id)] = None
    return body, False

# =======================
# STATS HELPERS
# =======================
def stats_ensure(chat_id: int, user_id: int, now: datetime | None = None):
    ts = now.isoformat() if isinstance(now, datetime) else None
    db_exec("""
    INSERT INTO user_stats(chat_id, user_id, updated_at)
    VALUES(?, ?, ?)
    ON CONFLICT(chat_id, user_id) DO UPDATE SET updated_at=COALESCE(excluded.updated_at, updated_at)
    """, (chat_id, user_id, ts))

def stats_inc(chat_id: int, user_id: int, field: str, delta: int, now: datetime | None = None):
    # защита от кривого field
    allowed = {
        "msg_count",
        "tokens_earned", "tokens_spent",
        "slot_spent", "slot_won",
        "duel_wins", "duel_losses", "duel_bank_won",
    }
    if field not in allowed:
        return
    stats_ensure(chat_id, user_id, now)
    ts = now.isoformat() if isinstance(now, datetime) else None
    db_exec(f"""
    UPDATE user_stats
    SET {field} = {field} + ?,
        updated_at = COALESCE(?, updated_at)
    WHERE chat_id=? AND user_id=?
    """, (int(delta), ts, chat_id, user_id))

def stats_get(chat_id: int, user_id: int) -> dict:
    row = db_one("""
    SELECT msg_count, tokens_earned, tokens_spent,
           slot_spent, slot_won,
           duel_wins, duel_losses, duel_bank_won
    FROM user_stats
    WHERE chat_id=? AND user_id=?
    """, (chat_id, user_id))

    if not row:
        return {
            "msg_count": 0,
            "tokens_earned": 0,
            "tokens_spent": 0,
            "slot_spent": 0,
            "slot_won": 0,
            "duel_wins": 0,
            "duel_losses": 0,
            "duel_bank_won": 0,
        }

    return {
        "msg_count": int(row[0]),
        "tokens_earned": int(row[1]),
        "tokens_spent": int(row[2]),
        "slot_spent": int(row[3]),
        "slot_won": int(row[4]),
        "duel_wins": int(row[5]),
        "duel_losses": int(row[6]),
        "duel_bank_won": int(row[7]),
    }

def _rank_by(value: int, table: list[tuple[int, str]]) -> str:
    cur = table[0][1]
    for need, name in table:
        if value >= need:
            cur = name
        else:
            break
    return cur

def rep_rank(chat_id: int, user_id: int) -> str:
    return _rank_by(rep_get(chat_id, user_id), REP_RANKS)

def win_rank(chat_id: int, user_id: int) -> str:
    st = stats_get(chat_id, user_id)
    # "выигрыши общие" — считаю как ВСЕ полученные токены (daily + выигрыши + банки дуэлей)
    earned = st["tokens_earned"]
    return _rank_by(earned, WIN_RANKS)

def chat_rank(chat_id: int, user_id: int) -> str:
    st = stats_get(chat_id, user_id)
    return _rank_by(st["msg_count"], CHAT_RANKS)

def overall_rank(chat_id: int, user_id: int) -> str:
    st = stats_get(chat_id, user_id)
    rep = rep_get(chat_id, user_id)
    earned = st["tokens_earned"]
    profit = earned - st["tokens_spent"]
    msgs = st["msg_count"]
    duel_wins = st["duel_wins"]

    # общий рейтинг (простая формула, потом настроим)
    score = rep * 10 + duel_wins * 50 + max(0, profit) // 20 + msgs // 50

    OVERALL = [
        (0,    "🪨 нуб"),
        (200,  "🔧 стажёр"),
        (600,  "⚙️ игрок"),
        (1500, "🧠 олд"),
        (3000, "👑 босс"),
    ]
    return _rank_by(score, OVERALL)

# =======================
# CHAT MODERATION HELPERS
# =======================
def chat_is_quiet(s: dict, now: datetime) -> bool:
    qu = s.get("quiet_until")
    return bool(qu and now < qu)

def can_easter(s: dict, now: datetime) -> bool:
    last = s.get("last_easter_at")
    if not last:
        return True
    return (now - last) >= timedelta(minutes=MIN_EASTER_EVERY_MIN)

def can_autohype(s: dict, now: datetime) -> bool:
    last = s.get("last_autohype_at")
    if not last:
        return True
    return (now - last) >= timedelta(hours=MIN_AUTOHYPE_EVERY_HOURS)

def cooldown_ok(last_dt: datetime | None, now: datetime, min_minutes: int) -> bool:
    if not last_dt:
        return True
    return (now - last_dt) >= timedelta(minutes=min_minutes)

async def maybe_set_poop_reaction(bot: Bot, msg: Message):
    # Реакции бот может ставить не везде/не всегда — поэтому try/except
    try:
        await bot.set_message_reaction(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            reaction=[{"type": "emoji", "emoji": "💩"}],
            is_big=False,
        )
    except Exception:
        pass


# =======================
# DUEL WATCHER (timer)
# =======================
async def background_duel_watcher(bot: Bot):
    """
    Каждые 2 секунды:
    - закрываем просроченные pending-дуэли
    - закрываем/двигаем активные дуэли по истечению раунда
    """
    while True:
        try:
            chats = db_all("SELECT chat_id FROM chat_settings WHERE enabled=1")
            for (chat_id,) in chats:
                s = get_settings(chat_id)
                tz = s["tz"]
                now = now_tz(tz)

                # 1) pending: истёк дедлайн принятия
                pending = db_all("""
                    SELECT duel_id, a_id, b_id, accept_deadline
                    FROM duels
                    WHERE chat_id=? AND state='pending'
                """, (chat_id,))
                for duel_id, a_id, b_id, accept_deadline in pending:
                    try:
                        dl = datetime.fromisoformat(accept_deadline)
                    except Exception:
                        dl = None
                    if dl and now > dl:
                        bet_row = duel_bet_get(duel_id)
                        if bet_row:
                            _chat, bet, a_paid, b_paid = bet_row
                            bet = int(bet)
                            if bet > 0 and int(a_paid) == 1:
                                wallet_add(chat_id, a_id, +bet)
                                tx_log(chat_id, now, None, a_id, bet, "duel_bet_refund", meta=f"duel_id={duel_id},reason=expired")
                            
                            duel_bet_delete(duel_id)

                        duel_set_state(chat_id, duel_id, "done")

                # 2) active: истёк раунд
                active = db_all("""
                    SELECT duel_id, a_id, b_id, arena_msg_id, data
                    FROM duels
                    WHERE chat_id=? AND state='active' AND arena_msg_id IS NOT NULL
                """, (chat_id,))

                for duel_id, a_id, b_id, arena_msg_id, data_json in active:
                    if not data_json:
                        continue
                    try:
                        data = json.loads(data_json)
                    except Exception:
                        continue

                    dl_s = data.get("deadline")
                    if not dl_s:
                        continue
                    try:
                        dl = datetime.fromisoformat(dl_s)
                    except Exception:
                        continue

                    if now > dl:
                        # если кто-то не походил — dodge
                        if data["moves"].get(str(a_id)) is None:
                            data["moves"][str(a_id)] = "dodge"
                        if data["moves"].get(str(b_id)) is None:
                            data["moves"][str(b_id)] = "dodge"

                        body, finished = duel_resolve_round(chat_id, duel_id, a_id, b_id, data)

                        if finished:
                            duel_set_state(chat_id, duel_id, "done")
                            
                            # определяем победителя по hp
                            a_hp = int(data["players"][str(a_id)]["hp"])
                            b_hp = int(data["players"][str(b_id)]["hp"])
                            winner = None
                            if a_hp > 0 and b_hp <= 0:
                                winner = a_id
                            elif b_hp > 0 and a_hp <= 0:
                                winner = b_id

                            if winner:
                                loser = b_id if winner == a_id else a_id
                                duel_mark_loss(chat_id, duel_id, loser, now)

                                bank = duel_bet_payout(chat_id, duel_id, winner, now)
                                if bank > 0:
                                    body += f"\n\n💰 Банк: +{bank} tokens победителю."

                            duel_update_data(chat_id, duel_id, data)
                            try:
                                await bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=arena_msg_id,
                                    text="🤠 ДУЭЛЬ • ЗАВЕРШЕНО\n\n" + body,
                                )
                            except Exception:
                                pass
                        else:
                            duel_start_round(data, now, a_id, b_id)
                            duel_update_data(chat_id, duel_id, data)
                            try:
                                arena_text = duel_status_text(chat_id, a_id, b_id, data)
                                await bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=arena_msg_id,
                                    text=arena_text,
                                    reply_markup=kb_duel_actions(duel_id),
                                )
                            except Exception:
                                pass

        except Exception as e:
            log_error("background_duel_watcher", e)

        await asyncio.sleep(2)


# =======================
# COMMANDS / HANDLERS HELPERS
# =======================
def resolve_target_user_id(chat_id: int, msg: Message, arg: str | None) -> int | None:
    # 1) reply
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id

    if not arg:
        return None

    arg = arg.strip()

    # 2) @username
    if arg.startswith("@") and len(arg) > 1:
        uid = find_user_id_by_username(chat_id, arg[1:])
        return uid

    # 3) numeric id
    if arg.isdigit():
        return int(arg)

    return None

def update_user_cache_from_message(chat_id: int, msg: Message, now: datetime):
    u = msg.from_user
    if not u:
        return
    display = None
    if u.username:
        display = f"@{u.username}"
    else:
        name = " ".join([x for x in [u.first_name, u.last_name] if x]).strip()
        display = name if name else f"id:{u.id}"
    upsert_user_display(chat_id, u.id, display, now)

async def reply_help(msg: Message):
    text = (
        "Команды:\n\n"

        "⚙️ Управление\n"
        "• /on — включить бота в чате\n"
        "• /off — выключить бота в чате\n"
        "• /tz Europe/Moscow — часовой пояс чата\n"
        "• /quiet 30m | 2h | 1d | off — тихий режим\n\n"

        "⭐ Репутация\n"
        "• /rep @user + | /rep @user - — репа (или reply)\n"
        "• + / - (в ответ на сообщение) — быстрый плюс/минус\n"
        "• /repme — моя репа\n"
        "• /toprep — топ репы\n\n"

        "🤠 Дуэли\n"
        "• /duel @user [ставка] — вызов на дуэль (макс 200)\n"
        "• /betinfo — (reply на арену) статус ставки\n\n"

        "📊 Статистика\n"
        "• /me или /profile — игровой профиль (ранги/стата)\n"
        "• /whereall [day|week|month] — активность за период (по умолчанию 24ч)\n"
        "• /interesting — интересное за 24ч\n"
        "• /wordweek — слово недели\n\n"

        "💰 Tokens-экономика\n"
        "• /balance — баланс tokens + jackpot\n"
        "• /pay @user <amount> — перевод tokens (комиссия в казну)\n"
        "• /slot <bet> [low|mid|high] — слоты (КД 10 минут, макс ставка 200)\n"
        "• /daily — ежедневный дроп tokens + стрик\n"
        "• /shop — магазин\n"
        "• /buy <item> — купить предмет\n"
        "• /inv — инвентарь\n"
        "• /rank — ранг по потраченному в магазине\n"
        "• /econ — сводка экономики чата (сколько в кошельках, казне, джекпоте)"
    )
    await msg.reply(text)


def parse_duration_to_until(now: datetime, arg: str) -> datetime | None:
    a = (arg or "").strip().lower()
    if a in ("off", "0", "нет"):
        return None
    m = re.fullmatch(r"(\d{1,4})(s|sec|m|min|h|d)", a)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit in ("s", "sec"):
        return now + timedelta(seconds=n)
    if unit in ("m", "min"):
        return now + timedelta(minutes=n)
    if unit == "h":
        return now + timedelta(hours=n)
    if unit == "d":
        return now + timedelta(days=n)
    return None

def parse_period_arg(arg: str | None) -> tuple[str, timedelta]:
    """
    Периоды для статистики:
    - default: 24 часа
    - week: 7 дней
    - month: 30 дней
    """
    a = (arg or "").strip().lower()

    if a in ("", "day", "24h", "d"):
        return ("24h", timedelta(hours=24))

    if a in ("week", "7d", "w"):
        return ("7d", timedelta(days=7))

    if a in ("month", "30d", "m"):
        return ("30d", timedelta(days=30))

    # неизвестное — по умолчанию 24ч
    return ("24h", timedelta(hours=24))

def build_whereall_text(chat_id: int, tz: str, now: datetime, delta: timedelta, label: str) -> str:
    since = now - delta
    rows = get_user_counts(chat_id, since)
    if not rows:
        return f"За период {label} сообщений нет."

    title = {
        "24h": "📊 Активность за 24ч",
        "7d": "📊 Активность за 7 дней",
        "30d": "📊 Активность за 30 дней",
    }.get(label, "📊 Активность")

    lines = [f"{title} (с {fmt_dt(since, tz)}):"]
    for uid, c in rows[:15]:
        name = get_user_display(chat_id, int(uid))
        lines.append(f"• {name}: {c}")
    if len(rows) > 15:
        lines.append(f"… и ещё {len(rows)-15} участников.")
    return "\n".join(lines)

def build_interesting_text(chat_id: int, tz: str, now: datetime) -> str:
    since = now - timedelta(hours=24)
    topw = get_top_words(chat_id, since, limit=5)
    topp = get_top_phrase(chat_id, since)
    parts = [f"🧠 Интересное за 24ч (с {fmt_dt(since, tz)}):"]

    if topw:
        parts.append("Топ-слова:")
        for w, c in topw:
            parts.append(f"• {w} — {c}")
    else:
        parts.append("Топ-слова: пусто")

    if topp:
        phrase, c = topp
        parts.append("")
        parts.append(f"Топ-фраза ({c}):")
        parts.append(f"«{phrase}»")
    else:
        parts.append("")
        parts.append("Топ-фраза: пусто")

    return "\n".join(parts)

def build_word_of_period(chat_id: int, tz: str, now: datetime, delta: timedelta, title: str) -> str:
    since = now - delta
    topw = get_top_words(chat_id, since, limit=1)
    if not topw:
        return f"{title}: нет данных за период."

    w, c = topw[0]
    return (
        f"{title}\n"
        f"🗓️ Период: с {fmt_dt(since, tz)}\n"
        f"🏆 Слово: **{w}**\n"
        f"🔁 Встречалось: {c}"
    )

async def handle_autohype(msg: Message, chat_id: int, tz: str, now: datetime):
    since = now - timedelta(hours=24)
    topw = get_top_words(chat_id, since, limit=3)
    if not topw:
        return
    words = ", ".join([w for w, _ in topw])
    hype = random.choice([
        f"⚡ Я вижу, тут сегодня крутятся темы: {words}.",
        f"🔥 Главные слова дня: {words}.",
        f"🧠 Чат живёт на: {words}.",
    ])
    await msg.reply(hype)
    set_field(chat_id, "last_autohype_at", now)

async def handle_easter(msg: Message, chat_id: int, now: datetime):
    egg = random.choice([
        "💩",
        "👁️ я всё вижу.",
        "⚠️ не будите бота.",
        "🗿.",
        "🥷 тень прошла.",
    ])
    await msg.reply(egg)
    set_field(chat_id, "last_easter_at", now)

def log_error(where: str, e: Exception):
    # минимальный лог в консоль
    try:
        print(f"[ERROR] {where}: {type(e).__name__}: {e}")
    except Exception:
        pass

def inv_add(chat_id: int, user_id: int, item: str, delta: int):
    db_exec("""
    INSERT INTO inventory(chat_id, user_id, item, qty) VALUES(?, ?, ?, ?)
    ON CONFLICT(chat_id, user_id, item) DO UPDATE SET qty = qty + ?
    """, (chat_id, user_id, item, int(delta), int(delta)))

def inv_get(chat_id: int, user_id: int, item: str) -> int:
    row = db_one("SELECT qty FROM inventory WHERE chat_id=? AND user_id=? AND item=?", (chat_id, user_id, item))
    return int(row[0]) if row else 0

# =======================
# DISPATCHER
# =======================
dp = Dispatcher()


# =======================
# BASIC COMMANDS
# =======================
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    await reply_help(msg)

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    await reply_help(msg)

@dp.message(Command("on"))
async def cmd_on(msg: Message):
    chat_id = msg.chat.id
    ensure_chat(chat_id)
    set_field(chat_id, "enabled", 1)
    await msg.reply("✅ Бот включён в этом чате.")

@dp.message(Command("off"))
async def cmd_off(msg: Message):
    chat_id = msg.chat.id
    ensure_chat(chat_id)
    set_field(chat_id, "enabled", 0)
    await msg.reply("⛔ Бот выключён в этом чате.")


@dp.message(Command("tz"))
async def cmd_tz(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    ensure_chat(chat_id)
    arg = (command.args or "").strip()
    if not arg:
        s = get_settings(chat_id)
        await msg.reply(f"Текущий TZ: {s['tz']}")
        return
    try:
        ZoneInfo(arg)
    except Exception:
        await msg.reply("Не понимаю TZ. Пример: /tz Europe/Moscow или /tz Europe/Amsterdam")
        return
    set_field(chat_id, "tz", arg)
    await msg.reply(f"✅ TZ установлен: {arg}")


@dp.message(Command("quiet"))
async def cmd_quiet(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    tz = s["tz"]
    now = now_tz(tz)

    arg = (command.args or "").strip().lower()
    if not arg:
        qu = s.get("quiet_until")
        if qu and now < qu:
            await msg.reply(f"🤫 Quiet включен до {fmt_dt(qu, tz)}")
        else:
            await msg.reply("Quiet сейчас выключен. Пример: /quiet 30m, /quiet 2h, /quiet off")
        return

    until = parse_duration_to_until(now, arg)
    if until is None:
        # off
        if arg in ("off", "0", "нет"):
            set_null(chat_id, "quiet_until")
            await msg.reply("✅ Quiet выключен.")
            return
        await msg.reply("Формат: /quiet 30m | 2h | 1d | off")
        return

    set_field(chat_id, "quiet_until", until)
    await msg.reply(f"🤫 Quiet включен до {fmt_dt(until, tz)}")

@dp.message(Command("betinfo"))
async def cmd_betinfo(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    if not msg.reply_to_message:
        await msg.reply("Ответь на арену дуэли командой /betinfo")
        return

    arena_msg_id = msg.reply_to_message.message_id
    active = duel_get_active_by_arena(chat_id, arena_msg_id)
    if not active:
        await msg.reply("Не вижу активную дуэль в этом сообщении.")
        return

    duel_id, a_id, b_id, _ = active
    row = duel_bet_get(duel_id)
    if not row:
        await msg.reply("Ставок нет.")
        return
    _chat, bet, a_paid, b_paid = row
    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)
    await msg.reply(f"💰 Ставка: {bet}\n{a_name} внес: {'✅' if a_paid else '❌'}\n{b_name} внес: {'✅' if b_paid else '❌'}")

# =======================
# REPUTATION
# =======================
@dp.message(Command("repme"))
async def cmd_repme(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    update_user_cache_from_message(chat_id, msg, now)
    score = rep_get(chat_id, msg.from_user.id)
    await msg.reply(f"Твоя репутация: {score}")

@dp.message(Command("toprep"))
async def cmd_toprep(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    rows = rep_all(chat_id)
    if not rows:
        await msg.reply("Пока репутации нет.")
        return

    lines = ["🏆 Топ репутации:"]
    for i, (uid, score) in enumerate(rows[:15], start=1):
        name = get_user_display(chat_id, int(uid))
        lines.append(f"{i}. {name} — {score}")
    await msg.reply("\n".join(lines))

@dp.message(Command("rep"))
async def cmd_rep(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    args = (command.args or "").strip()
    if not args:
        await msg.reply("Пример: /rep @user +  |  /rep (в ответ на сообщение) +")
        return

    parts = args.split()
    if len(parts) == 1:
        sign = parts[0]
        target = resolve_target_user_id(chat_id, msg, None)
    else:
        target = resolve_target_user_id(chat_id, msg, parts[0])
        sign = parts[1] if len(parts) >= 2 else "+"

    if not target:
        await msg.reply("Не понял, кому. Используй reply или @username.")
        return
    if not msg.from_user:
        return
    if target == msg.from_user.id:
        await msg.reply("Себе нельзя 😄")
        return

    if sign in ("+", "++", "plus"):
        delta = 1
    elif sign in ("-", "--", "minus"):
        if not ALLOW_NEGATIVE_REP:
            await msg.reply("Минус-репа отключена.")
            return
        delta = -1
    else:
        await msg.reply("Знак: + или -")
        return

    if not rep_can_vote(chat_id, msg.from_user.id, target, now, REP_COOLDOWN_MIN):
        await msg.reply(f"КД на репутацию: {REP_COOLDOWN_MIN} минут.")
        return

    rep_add(chat_id, target, delta)
    rep_mark_vote(chat_id, msg.from_user.id, target, now)
    score = rep_get(chat_id, target)
    name = get_user_display(chat_id, target)
    await msg.reply(f"{name}: {'+' if delta>0 else ''}{delta} репутации. Итог: {score}")


# =======================
# LUCK
# =======================
@dp.message(Command("luck"))
async def cmd_luck(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    update_user_cache_from_message(chat_id, msg, now)
    uid = msg.from_user.id

    if not luck_can_spin(chat_id, uid, now):
        row = db_one("SELECT ts FROM luck_cooldown WHERE chat_id=? AND user_id=?", (chat_id, uid))
        last = datetime.fromisoformat(row[0]) if row else now
        left = (last + timedelta(minutes=LUCK_COOLDOWN_MIN)) - now
        mins = max(0, int(left.total_seconds() // 60))
        secs = max(0, int(left.total_seconds() % 60))
        await msg.reply(f"⏳ Слоты на кд. Осталось ~{mins}m {secs}s.")
        return

    ls = luckscore_get(chat_id, uid)
    slots, buff, rep_win = spin_slots(ls)

    rep_add(chat_id, uid, rep_win)
    luck_mark_spin(chat_id, uid, now)

    if buff:
        luckscore_add(chat_id, uid, +3)
    else:
        luckscore_add(chat_id, uid, +1)

    text = [f"🎰 {slots}", f"+{rep_win} репутации. Теперь: {rep_get(chat_id, uid)}"]
    if buff:
        luck_set_buff(chat_id, uid, buff)
        text.append(buff_desc(buff))

    text.append(luck_aura(luckscore_get(chat_id, uid)))

    await msg.reply("\n".join(text))

@dp.message(Command("balance"))
async def cmd_balance(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)

    update_user_cache_from_message(chat_id, msg, now)
    uid = msg.from_user.id
    bal = wallet_get(chat_id, uid)
    jp = pool_get(chat_id, "jackpot_pool")
    await msg.reply(f"💰 Tokens: {bal}\n👑 Jackpot: {jp}")

@dp.message(Command("econ"))
async def cmd_econ(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    snap = econ_snapshot(chat_id)

    await msg.reply(
        "📉 Экономика чата (tokens)\n"
        f"👛 В кошельках всего: {snap['total_wallet']}\n"
        f"👥 У кого баланс > 0: {snap['holders']}\n"
        f"🏦 Казна: {snap['treasury']}\n"
        f"👑 Джекпот: {snap['jackpot']}\n"
        f"🧾 Всего в системе: {snap['total_wallet'] + snap['treasury'] + snap['jackpot']}"
    )

@dp.message(Command("pay"))
async def cmd_pay(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)

    update_user_cache_from_message(chat_id, msg, now)

    args = (command.args or "").strip()
    if not args:
        await msg.reply("Пример: /pay @user 50 (или reply) 50")
        return

    parts = args.split()
    amount = None

    # вариант: /pay 50 (reply)
    if len(parts) == 1 and parts[0].isdigit():
        amount = int(parts[0])
        target = resolve_target_user_id(chat_id, msg, None)
    else:
        # /pay @user 50
        target = resolve_target_user_id(chat_id, msg, parts[0])
        if len(parts) >= 2 and parts[1].isdigit():
            amount = int(parts[1])

    if not target or amount is None:
        await msg.reply("Формат: /pay @user 50  (или reply) /pay 50")
        return

    if target == msg.from_user.id:
        await msg.reply("Себе нельзя.")
        return

    amount = max(1, amount)
    fee = max(1, (amount * PAY_FEE_PCT) // 100)
    total = amount + fee

    bal = wallet_get(chat_id, msg.from_user.id)
    if bal < total:
        await msg.reply(f"Не хватает tokens. Нужно {total} (включая комиссию {fee}). У тебя {bal}.")
        return

    wallet_add(chat_id, msg.from_user.id, -total)
    wallet_add(chat_id, target, +amount)
    pool_add(chat_id, "treasury", +fee)

    tx_log(chat_id, now, msg.from_user.id, target, amount, "pay", meta=f"fee={fee}")

    to_name = get_user_display(chat_id, target)
    await msg.reply(f"✅ Перевод: {to_name} +{amount} tokens\nКомиссия: {fee} → казна")

@dp.message(Command("slot"))
async def cmd_slot(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    update_user_cache_from_message(chat_id, msg, now)
    uid = msg.from_user.id

    parsed = parse_slot_args(command.args)
    if not parsed:
        await msg.reply("Пример: /slot 50  |  /slot 50 high  |  /slot low 20\nМакс ставка 200.")
        return

    mode, bet = parsed

    if not slot_can_spin(chat_id, uid, now):
        row = db_one("SELECT ts FROM slot_cooldown WHERE chat_id=? AND user_id=?", (chat_id, uid))
        last = datetime.fromisoformat(row[0]) if row else now
        left = (last + timedelta(minutes=SLOT_COOLDOWN_MIN)) - now
        mins = max(0, int(left.total_seconds() // 60))
        secs = max(0, int(left.total_seconds() % 60))
        await msg.reply(f"⏳ Слот на кд. Осталось ~{mins}m {secs}s.")
        return

    bal = wallet_get(chat_id, uid)
    if bal < bet:
        await msg.reply(f"Не хватает tokens. Ставка {bet}, у тебя {bal}.")
        return

    # списали ставку
    wallet_add(chat_id, uid, -bet)

    stats_inc(chat_id, uid, "tokens_spent", bet, now)
    stats_inc(chat_id, uid, "slot_spent", bet, now)

    # распределили проценты
    jp_add = (bet * JACKPOT_PCT) // 100
    tr_add = (bet * TREASURY_PCT) // 100
    pool_add(chat_id, "jackpot_pool", +jp_add)
    pool_add(chat_id, "treasury", +tr_add)

    # крутим
    line, mult, jackpot_hit = slot_spin(mode)

    win = 0
    extra = []

    if jackpot_hit:
        jp = pool_get(chat_id, "jackpot_pool")
        win = jp
        pool_set(chat_id, "jackpot_pool", 0)
        extra.append(f"👑 ДЖЕКПОТ: +{jp} tokens")
    else:
        win = int(round(bet * mult))

    if win > 0:
        wallet_add(chat_id, uid, +win)

        stats_inc(chat_id, uid, "tokens_earned", win, now)
        stats_inc(chat_id, uid, "slot_won", win, now)

    slot_mark_spin(chat_id, uid, now)
    tx_log(chat_id, now, uid, None, bet, "slot_bet", meta=f"mode={mode}")
    if win > 0:
        tx_log(chat_id, now, None, uid, win, "slot_win", meta=f"mode={mode},mult={mult}")

    new_bal = wallet_get(chat_id, uid)
    jp_now = pool_get(chat_id, "jackpot_pool")

    res = [
        f"🎰 {line}",
        f"Режим: {mode} • Ставка: {bet}",
    ]

    if jackpot_hit:
        res.append("Сорвал банк.")
    else:
        if win <= 0:
            res.append("💀 Мимо.")
        else:
            res.append(f"✅ Выигрыш: +{win} tokens (x{mult:g})")

    if extra:
        res.extend(extra)

    res.append(f"💰 Баланс: {new_bal}")
    res.append(f"👑 Jackpot: {jp_now}")

    await msg.reply("\n".join(res))

@dp.message(Command("daily"))
async def cmd_daily(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)

    update_user_cache_from_message(chat_id, msg, now)
    uid = msg.from_user.id

    day = date_key(now)
    if daily_claimed(chat_id, uid, day):
        await msg.reply("⏳ Ты уже забирал daily сегодня.")
        return

    # --- streak ---
    row = daily_streak_get(chat_id, uid)
    last = datetime.fromisoformat(row[0]) if row and row[0] else None
    streak = int(row[1]) if row else 0

    yesterday = (now - timedelta(days=1)).date().isoformat()
    if last and last.date().isoformat() == yesterday:
        streak += 1
    else:
        streak = 1

    # базовый дроп
    base = random.randint(25, 50)

    # бонус за активность за 24ч: +0..+10
    since = now - timedelta(hours=24)
    row2 = db_one(
        "SELECT COUNT(*) FROM msg_log WHERE chat_id=? AND user_id=? AND ts>=?",
        (chat_id, uid, since.isoformat()),
    )
    c = int(row2[0]) if row2 else 0
    bonus = min(10, c // 5)

    # бонус за стрик
    streak_bonus = min(20, (streak - 1) * 2)

    amount = base + bonus + streak_bonus

    wallet_add(chat_id, uid, amount)
    stats_inc(chat_id, uid, "tokens_earned", amount, now)
    daily_mark_claim(chat_id, uid, day)
    daily_streak_set(chat_id, uid, now, streak)
    tx_log(chat_id, now, None, uid, amount, "daily", meta=f"base={base},bonus={bonus},streak={streak},msg24h={c}")

    bal = wallet_get(chat_id, uid)

    await msg.reply(
        f"🎁 Daily: +{amount} tokens (база {base} + активность {bonus} + стрик {streak_bonus})\n"
        f"🔥 Стрик: {streak}\n"
        f"💰 Баланс: {bal}"
    )

@dp.message(Command("shop"))
async def cmd_shop(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    lines = ["🛒 Магазин:"]
    for k, v in SHOP_ITEMS.items():
        lines.append(f"• {k} — {v['price']} tokens")
    lines.append("\nКупить: /buy <item>")
    await msg.reply("\n".join(lines))

@dp.message(Command("buy"))
async def cmd_buy(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)

    uid = msg.from_user.id
    item = (command.args or "").strip()
    if item not in SHOP_ITEMS:
        await msg.reply("Нет такого предмета. Смотри /shop")
        return

    price = int(SHOP_ITEMS[item]["price"])
    bal = wallet_get(chat_id, uid)
    if bal < price:
        await msg.reply(f"Не хватает tokens. Нужно {price}, у тебя {bal}.")
        return

    wallet_add(chat_id, uid, -price)
    stats_inc(chat_id, uid, "tokens_spent", price, now)
    pool_add(chat_id, "treasury", +price)
    tx_log(chat_id, now, uid, None, price, "buy", meta=f"item={item}")

    it = SHOP_ITEMS[item]
    if it["type"] == "title":
        db_exec("""
        INSERT INTO user_profile(chat_id, user_id, title) VALUES(?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET title=excluded.title
        """, (chat_id, uid, it["value"]))
        await msg.reply(f"✅ Куплено. Титул установлен: {it['value']}")
    else:
        inv_add(chat_id, uid, item, 1)
        await msg.reply(f"✅ Куплено: {item} x1")

@dp.message(Command("inv"))
async def cmd_inv(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    uid = msg.from_user.id
    rows = db_all("SELECT item, qty FROM inventory WHERE chat_id=? AND user_id=? AND qty>0", (chat_id, uid))
    if not rows:
        await msg.reply("🎒 Инвентарь пуст.")
        return
    lines = ["🎒 Инвентарь:"]
    for it, q in rows:
        lines.append(f"• {it} x{q}")
    await msg.reply("\n".join(lines))

# =======================
# STATS
# =======================
@dp.message(Command("whereall"))
async def cmd_whereall(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return

    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    if not cooldown_ok(s.get("last_where_all_at"), now, WHEREALL_COOLDOWN_MIN):
        await msg.reply(f"⏳ КД {WHEREALL_COOLDOWN_MIN} минут.")
        return

    label, delta = parse_period_arg(command.args)

    set_field(chat_id, "last_where_all_at", now)
    await msg.reply(build_whereall_text(chat_id, tz, now, delta, label))

@dp.message(Command("interesting"))
async def cmd_interesting(msg: Message):
    # алиас на /wordweek
    await cmd_wordweek(msg)


@dp.message(Command("wordweek"))
async def cmd_wordweek(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return

    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    if not cooldown_ok(s.get("last_interesting_at"), now, INTERESTING_COOLDOWN_MIN):
        await msg.reply(f"⏳ КД {INTERESTING_COOLDOWN_MIN} минут.")
        return

    set_field(chat_id, "last_interesting_at", now)
    await msg.reply(build_word_of_period(chat_id, tz, now, timedelta(days=7), "🧠 Слово недели"))

#для вывода ранка
def spent_in_shop(chat_id: int, user_id: int) -> int:
    row = db_one("""
        SELECT COALESCE(SUM(amount),0)
        FROM token_tx
        WHERE chat_id=? AND from_user_id=? AND kind='buy'
    """, (chat_id, user_id))
    return int(row[0]) if row else 0

def rank_name(spent: int) -> str:
    cur = RANKS[0][1]
    for need, name in RANKS:
        if spent >= need:
            cur = name
        else:
            break
    return cur

@dp.message(Command("rank"))
async def cmd_rank(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    uid = msg.from_user.id
    sp = spent_in_shop(chat_id, uid)
    r = rank_name(sp)
    await msg.reply(f"🏷️ Ранг: {r}\n💸 Потрачено в магазине: {sp} tokens")

@dp.message(Command("profile"))
@dp.message(Command("me"))
async def cmd_profile(msg: Message):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    update_user_cache_from_message(chat_id, msg, now)

    uid = msg.from_user.id
    name = get_user_display(chat_id, uid)

    st = stats_get(chat_id, uid)
    rep = rep_get(chat_id, uid)

    earned = st["tokens_earned"]
    spent = st["tokens_spent"]
    profit = earned - spent

    bal = wallet_get(chat_id, uid)

    await msg.reply(
        f"🎮 Профиль: {name}\n\n"
        f"🏷️ Общий ранг: {overall_rank(chat_id, uid)}\n"
        f"⭐ Ранг по репе: {rep_rank(chat_id, uid)} (репа {rep})\n"
        f"💰 Ранг по выигрышам: {win_rank(chat_id, uid)} (получено {earned})\n"
        f"💬 Ранг по активности: {chat_rank(chat_id, uid)} (сообщений {st['msg_count']})\n\n"
        f"⚔️ Дуэли: ✅ {st['duel_wins']} / ❌ {st['duel_losses']}  | банк выигран: {st['duel_bank_won']}\n"
        f"🎰 Слоты: потрачено {st['slot_spent']} / выиграно {st['slot_won']}\n"
        f"📈 Профит (получено-потрачено): {profit}\n"
        f"👛 Баланс сейчас: {bal}"
    )

# =======================
# DUEL FLOW (invite / accept / decline / actions)
# =======================
def kb_duel_invite(duel_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принять", callback_data=f"duel:accept:{duel_id}")
    kb.button(text="❌ Отказ", callback_data=f"duel:decline:{duel_id}")
    kb.adjust(2)
    return kb.as_markup()

@dp.message(Command("duel"))
async def cmd_duel(msg: Message, command: CommandObject):
    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        return

    update_user_cache_from_message(chat_id, msg, now)
    a_id = msg.from_user.id

    raw = (command.args or "").strip()
    parts = raw.split()

    bet = 0
    target_arg = None

    # /duel @user 50  или /duel 50 @user (разрешим оба)
    for p in parts:
        if p.isdigit():
            bet = int(p)
        else:
            target_arg = p

    b_id = resolve_target_user_id(chat_id, msg, target_arg)


    if not b_id:
        await msg.reply("Кого дуэлить? Пример: /duel @user (или reply на сообщение)")
        return
    if b_id == a_id:
        await msg.reply("Сам с собой — нет 😄")
        return

    if bet < 0:
        bet = 0
    if bet > MAX_BET:
        await msg.reply(f"Макс ставка: {MAX_BET} tokens.")
        return

    # цель уже имеет pending?
    pending = duel_get_pending_for_b(chat_id, b_id)
    if pending:
        await msg.reply("У этого игрока уже висит приглашение. Пусть примет/откажет.")
        return

    if bet > 0:
        bal = wallet_get(chat_id, a_id)
        if bal < bet:
            await msg.reply(f"Не хватает tokens на ставку {bet}. У тебя {bal}.")
            return
        wallet_add(chat_id, a_id, -bet)

    duel_id = duel_create(chat_id, a_id, b_id, now)

    duel_bet_create(chat_id, duel_id, bet)
    if bet > 0:
        duel_bet_set_paid(duel_id, a_paid=1)
        tx_log(chat_id, now, a_id, None, bet, "duel_bet_lock", meta=f"duel_id={duel_id}")

    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)
    accept_deadline = now + timedelta(minutes=DUEL_ACCEPT_MIN)

    text = (
        f"🤠 Дуэль!\n"
        f"{a_name} вызывает {b_name}.\n\n"
        f"⏳ Принять до: {fmt_dt(accept_deadline, tz)}\n"
        f"Правила: 1 минута на раунд, HP={DUEL_HP}, патроны={DUEL_AMMO_MAX}.\n"
    )
    if bet > 0:
        text += f"\n💰 Ставка: {bet} tokens (банк {bet*2})"

    await msg.reply(text, reply_markup=kb_duel_invite(duel_id))

@dp.callback_query(F.data.startswith("duel:accept:"))
async def cb_duel_accept(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        await cb.answer("Бот выключен.", show_alert=True)
        return
    tz = s["tz"]
    now = now_tz(tz)

    duel_id = cb.data.split(":")[-1]
    row = duel_get(chat_id, duel_id)
    if not row:
        await cb.answer("Дуэль не найдена.", show_alert=True)
        return

    _duel_id, a_id, b_id, state, accept_deadline, arena_msg_id, data_json = row

    if state != "pending":
        await cb.answer("Это приглашение уже не активно.", show_alert=True)
        return

    if not cb.from_user:
        return

    if cb.from_user.id != b_id:
        await cb.answer("Принять может только вызванный игрок.", show_alert=True)
        return

    try:
        dl = datetime.fromisoformat(accept_deadline)
    except Exception:
        dl = None
    if dl and now > dl:
        duel_set_state(chat_id, duel_id, "done")
        await cb.answer("Поздно. Приглашение истекло.", show_alert=True)
        return

    bet_row = duel_bet_get(duel_id)
    bet = int(bet_row[1]) if bet_row else 0

    if bet > 0:
        bal = wallet_get(chat_id, b_id)
        if bal < bet:
            await cb.answer("Не хватает tokens на ставку.", show_alert=True)
            return
        wallet_add(chat_id, b_id, -bet)
        duel_bet_set_paid(duel_id, b_paid=1)
        tx_log(chat_id, now, b_id, None, bet, "duel_bet_lock", meta=f"duel_id={duel_id}")

    # активируем дуэль и создаём арену (новое сообщение)
    try:
        data = json.loads(data_json) if data_json else duel_new_data(a_id, b_id)
    except Exception:
        data = duel_new_data(a_id, b_id)

    # применяем баффы удачи (если есть) — на старте
    a_note = duel_apply_luck_buff(chat_id, a_id, data["players"][str(a_id)])
    b_note = duel_apply_luck_buff(chat_id, b_id, data["players"][str(b_id)])

    duel_start_round(data, now, a_id, b_id)

    arena_text = duel_status_text(chat_id, a_id, b_id, data)
    arena = await cb.message.answer(arena_text, reply_markup=kb_duel_actions(duel_id))

    duel_activate(chat_id, duel_id, arena.message_id)
    duel_update_data(chat_id, duel_id, data)

    notes = []
    if a_note:
        notes.append(f"{get_user_display(chat_id, a_id)}: {a_note}")
    if b_note:
        notes.append(f"{get_user_display(chat_id, b_id)}: {b_note}")
    if notes:
        await cb.message.answer("\n".join(notes))

    await cb.answer("Принято!")

    # обновим приглашение, уберём кнопки
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

@dp.callback_query(F.data.startswith("duel:decline:"))
async def cb_duel_decline(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        await cb.answer("Бот выключен.", show_alert=True)
        return

    duel_id = cb.data.split(":")[-1]
    row = duel_get(chat_id, duel_id)
    if not row:
        await cb.answer("Дуэль не найдена.", show_alert=True)
        return

    _duel_id, a_id, b_id, state, accept_deadline, arena_msg_id, data_json = row
    if state != "pending":
        await cb.answer("Уже не актуально.", show_alert=True)
        return

    if not cb.from_user:
        return

    if cb.from_user.id != b_id:
        await cb.answer("Отказаться может только вызванный игрок.", show_alert=True)
        return

    bet_row = duel_bet_get(duel_id)
    if bet_row:
        _chat, bet, a_paid, b_paid = bet_row
        bet = int(bet)
        if bet > 0 and int(a_paid) == 1:
            wallet_add(chat_id, a_id, +bet)
            tz = get_settings(chat_id)["tz"]
            now = now_tz(tz)
            tx_log(chat_id, now, None, a_id, bet, "duel_bet_refund", meta=f"duel_id={duel_id}")
        duel_bet_delete(duel_id)

    duel_set_state(chat_id, duel_id, "done")
    await cb.answer("Отказ.")
    try:
        await cb.message.edit_text("❌ Дуэль отклонена.")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("duel:act:"))
async def cb_duel_action(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        await cb.answer("Бот выключен.", show_alert=True)
        return
    tz = s["tz"]
    now = now_tz(tz)
    if chat_is_quiet(s, now):
        await cb.answer("Quiet режим.", show_alert=True)
        return

    # duel:act:<duel_id>:<action>
    parts = cb.data.split(":")
    if len(parts) < 4:
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return
    duel_id = parts[2]
    action = parts[3]

    row = duel_get(chat_id, duel_id)
    if not row:
        await cb.answer("Дуэль не найдена.", show_alert=True)
        return

    _duel_id, a_id, b_id, state, accept_deadline, arena_msg_id, data_json = row
    if state != "active":
        await cb.answer("Дуэль уже не активна.", show_alert=True)
        return

    if not cb.from_user:
        return
    uid = cb.from_user.id
    if uid not in (a_id, b_id):
        await cb.answer("Ты не участник этой дуэли.", show_alert=True)
        return

    if not data_json:
        await cb.answer("Ошибка данных дуэли.", show_alert=True)
        return

    try:
        data = json.loads(data_json)
    except Exception as e:
        log_error("cb_duel_action json.loads", e)
        await cb.answer("Ошибка данных дуэли.", show_alert=True)
        return
    
    if str(uid) != data.get("turn"):
        await cb.answer("Сейчас ход другого игрока.", show_alert=True)
        return

    # дедлайн текущего раунда
    if data.get("deadline"):
        try:
            dl = datetime.fromisoformat(data["deadline"])
        except Exception:
            dl = None
        if dl and now > dl:
            await cb.answer("Раунд уже закончился. Жди обновления.", show_alert=True)
            return

    # сдача
    if action == "surrender":
        other = b_id if uid == a_id else a_id
        other_name = get_user_display(chat_id, other)
        me_name = get_user_display(chat_id, uid)

        bank = duel_bet_payout(chat_id, duel_id, other, now)
        rep_add(chat_id, other, DUEL_REP_REWARD)
        score = rep_get(chat_id, other)

        duel_set_state(chat_id, duel_id, "done")
        try:
            text = (
                f"🤠 ДУЭЛЬ • ЗАВЕРШЕНО\n\n"
                f"{me_name} позорно покидает арену.\n"
                f"Победа {other_name}. +{DUEL_REP_REWARD} репутации (итого {score})."
            )
            if bank > 0:
                text += f"\n\n💰 Банк: +{bank} tokens победителю."
            await cb.message.edit_text(text)
        except Exception:
            pass

        await cb.answer("Ты сдался.")
        return


    # если уже ходил
    if data["moves"].get(str(uid)) is not None:
        await cb.answer("Ты уже сделал ход в этом раунде.", show_alert=True)
        return

    # нормализуем алиасы (вдруг)
    action_norm = ACTION_ALIASES.get(action, action)
    if action_norm not in ("shoot", "aim", "dodge", "reload", "heal"):
        await cb.answer("Неизвестное действие.", show_alert=True)
        return

    data["moves"][str(uid)] = action_norm

    # --- переключаем ход на другого игрока ---
    other = b_id if uid == a_id else a_id
    data["turn"] = str(other)

    duel_update_data(chat_id, duel_id, data)

    # если второй уже походил — резолвим раунд
    if data["moves"].get(str(a_id)) and data["moves"].get(str(b_id)):
        body, finished = duel_resolve_round(chat_id, duel_id, a_id, b_id, data)
        if finished:
            duel_set_state(chat_id, duel_id, "done")

            # определяем победителя по hp
            a_hp = int(data["players"][str(a_id)]["hp"])
            b_hp = int(data["players"][str(b_id)]["hp"])
            winner = None
            if a_hp > 0 and b_hp <= 0:
                winner = a_id
            elif b_hp > 0 and a_hp <= 0:
                winner = b_id

            if winner:
                bank = duel_bet_payout(chat_id, duel_id, winner, now)
                if bank > 0:
                    body += f"\n\n💰 Банк: +{bank} tokens победителю."

            duel_update_data(chat_id, duel_id, data)
            try:
                await cb.message.edit_text("🤠 ДУЭЛЬ • ЗАВЕРШЕНО\n\n" + body)
            except Exception:
                pass
        else:
            duel_start_round(data, now, a_id, b_id)
            duel_update_data(chat_id, duel_id, data)
            try:
                arena_text = duel_status_text(chat_id, a_id, b_id, data)
                await cb.message.edit_text(arena_text, reply_markup=kb_duel_actions(duel_id))
            except Exception:
                pass

        await cb.answer("Раунд завершён.")
        return

    # иначе просто обновим статус арены, чтобы было видно "походил"
    try:
        arena_text = duel_status_text(chat_id, a_id, b_id, data)
        await cb.message.edit_text(arena_text, reply_markup=kb_duel_actions(duel_id))
    except Exception:
        pass

    await cb.answer("Ход принят.")


# =======================
# MESSAGE PIPELINE (logs + triggers)
# =======================

@dp.message(F.text.in_({"+", "++", "+++", "-", "--", "---"}))
async def rep_by_reply(msg: Message):
    if not msg.text:
        return

    text = msg.text.strip()
    if text not in ("+", "++", "+++", "-", "--", "---"):
        return

    # обязательно ответ
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        return

    chat_id = msg.chat.id
    s = get_settings(chat_id)
    if not s["enabled"]:
        return

    voter = msg.from_user
    target = msg.reply_to_message.from_user

    if not voter or voter.id == target.id:
        return

    delta = 1 if text.startswith("+") else -1
    if delta < 0 and not ALLOW_NEGATIVE_REP:
        return

    tz = s["tz"]
    now = now_tz(tz)

    if not rep_can_vote(chat_id, voter.id, target.id, now):
        return

    rep_add(chat_id, target.id, delta)
    rep_mark_vote(chat_id, voter.id, target.id, now)

    score = rep_get(chat_id, target.id)
    name = get_user_display(chat_id, target.id)

    await msg.reply(f"{name}: {'+' if delta>0 else ''}{delta} репутации (итого {score})")

@dp.message()
async def any_message(msg: Message, bot: Bot):
    # логирование, триггеры, авто-приколы
    if not msg.chat:
        return
    
    # не логируем ботов (включая самого бота и других ботов в чате)
    if not msg.from_user or msg.from_user.is_bot:
        return

    chat_id = msg.chat.id

    s = get_settings(chat_id)
    if not s["enabled"]:
        return

    tz = s["tz"]
    now = now_tz(tz)

    # user cache
    update_user_cache_from_message(chat_id, msg, now)

    # базовые логи
    if msg.from_user:
        add_msg_log(chat_id, now, msg.from_user.id)

    # слова/фразы
    text = msg.text or msg.caption or ""

    # --- логируем только обычные сообщения с текстом ---
    if not text:
        return

    # --- не логируем команды ---
    # /rep, /duel, /luck и т.п.
    if text.lstrip().startswith("/"):
        return

    print(f"[MSG] chat={msg.chat.id} from={msg.from_user.id} text={(msg.text or msg.caption or '')[:50]!r}")

    if text:
        add_words(chat_id, now, tokenize(text))
        # как фразу логируем "нормализованную строку" (без огромных полотен)
        phr = normalize_phrase(text)
        if 0 < len(phr) <= 120:
            add_phrase(chat_id, now, phr)

    # чистка логов (храним 7 дней)
    prune_logs(chat_id, now - timedelta(days=7))

    set_field(chat_id, "last_message_at", now)

    if chat_is_quiet(s, now):
        return

    # 💩 триггер
    if text and has_trigger(text):
        cnt = inc_daily_trigger(chat_id, date_key(now))

        # лимит в день, дальше — редко
        if cnt <= DAILY_TRIGGER_LIMIT:
            await maybe_set_poop_reaction(bot, msg)
        else:
            if random.random() < POOP_AFTER_DAILY_LIMIT_PROB:
                await maybe_set_poop_reaction(bot, msg)

    # пасхалка
    if can_easter(s, now) and random.random() < EASTER_PROB:
        await handle_easter(msg, chat_id, now)

    # авто-хайп
    if can_autohype(s, now) and random.random() < AUTO_HYPE_PROB:
        await handle_autohype(msg, chat_id, tz, now)

# =======================
# MAIN
# =======================
async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in environment.")

    init_db()

    bot = Bot(TOKEN)
    # Запускаем watcher
    asyncio.create_task(background_duel_watcher(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())