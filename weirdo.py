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
LUCK_COOLDOWN_MIN = 30
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
WHEREALL_COOLDOWN_MIN = 20
INTERESTING_COOLDOWN_MIN = 20

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
    data["moves"][str(a_id)] = None
    data["moves"][str(b_id)] = None
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
        return (
            f"👤 {name}\n"
            f"❤️ {hp}/{DUEL_HP}  {hp_bar(hp, DUEL_HP)}\n"
            f"🔫 {ammo_bar(ammo, DUEL_AMMO_MAX)}   🎯 {acc}%   🩹{heal_left}\n"
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

    header = f"🤠 ДУЭЛЬ • Раунд {data.get('round', 1)}"
    timer = f"⏱️ Осталось: {deadline_str} (раунд {round_s}s)" if deadline_str else f"⏱️ Раунд: {round_s}s"

    return (
        f"{header}\n"
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

    body = "\n".join([x for x in log if x.strip()]) if log else "Тишина."

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
        "Команды:\n"
        "• /on, /off — включить/выключить бота в чате\n"
        "• /tz Europe/Moscow — часовой пояс чата\n"
        "• /quiet 30m | 2h | 1d | off — тихий режим\n"
        "• /rep @user + | /rep @user - | /repme — репа\n"
        "• /toprep — топ по репутации\n"
        "• /luck — слоты (раз в 30 минут)\n"
        "• /duel @user — вызвать на дуэль\n"
        "• /whereall — кто сколько писал за 24ч\n"
        "• /interesting — топ-слова/фразы за 24ч\n"
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
    Возвращает (label, delta)
    label: "24h" | "7d" | "30d"
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

    arg = (command.args or "").strip()
    b_id = resolve_target_user_id(chat_id, msg, arg)

    if not b_id:
        await msg.reply("Кого дуэлить? Пример: /duel @user (или reply на сообщение)")
        return
    if b_id == a_id:
        await msg.reply("Сам с собой — нет 😄")
        return

    # цель уже имеет pending?
    pending = duel_get_pending_for_b(chat_id, b_id)
    if pending:
        await msg.reply("У этого игрока уже висит приглашение. Пусть примет/откажет.")
        return

    duel_id = duel_create(chat_id, a_id, b_id, now)
    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)
    accept_deadline = now + timedelta(minutes=DUEL_ACCEPT_MIN)

    text = (
        f"🤠 Дуэль!\n"
        f"{a_name} вызывает {b_name}.\n\n"
        f"⏳ Принять до: {fmt_dt(accept_deadline, tz)}\n"
        f"Правила: 1 минута на раунд, HP={DUEL_HP}, патроны={DUEL_AMMO_MAX}.\n"
    )
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
        # второй победил
        other = b_id if uid == a_id else a_id
        rep_add(chat_id, other, DUEL_REP_REWARD)
        score = rep_get(chat_id, other)
        other_name = get_user_display(chat_id, other)
        me_name = get_user_display(chat_id, uid)
        duel_set_state(chat_id, duel_id, "done")
        try:
            await cb.message.edit_text(
                f"🤠 ДУЭЛЬ • ЗАВЕРШЕНО\n\n"
                f"{me_name} сдаётся.\n"
                f"Победа {other_name}. +{DUEL_REP_REWARD} репутации (итого {score})."
            )
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
    duel_update_data(chat_id, duel_id, data)

    # если второй уже походил — резолвим раунд
    if data["moves"].get(str(a_id)) and data["moves"].get(str(b_id)):
        body, finished = duel_resolve_round(chat_id, duel_id, a_id, b_id, data)
        if finished:
            duel_set_state(chat_id, duel_id, "done")
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
@dp.message()
@dp.message()
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