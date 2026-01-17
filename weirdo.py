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
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =======================
# CONFIG
# =======================
TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "bot.db")
DEFAULT_TZ = os.getenv("BOT_TZ", "Europe/Moscow")

# Триггеры 💩 (словоформы)
RE_TRIGGER = re.compile(
    r"(?<!\w)(пар(а|ы|е|у|ой|ам|ами|ах)?|долг(и|а|у|ом|ов|ам|ами|ах)?)(?!\w)",
    re.IGNORECASE | re.UNICODE,
)

RE_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+", re.UNICODE)

# Вероятности
EASTER_PROB = 0.005
ECHO_PROB = 0.005
AUTO_HYPE_PROB = 0.005

# Ограничения
DAILY_TRIGGER_LIMIT = 5
POOP_AFTER_DAILY_LIMIT_PROB = 0.25
MIN_EASTER_EVERY_MIN = 20
MIN_AUTOHYPE_EVERY_HOURS = 6

# Репутация
REP_COOLDOWN_MIN = 10
ALLOW_NEGATIVE_REP = True

# Дуэли
DUEL_ACCEPT_MIN = 2
DUEL_MOVE_MIN = 2 # сколько минут на ход после старта/после раунда
DUEL_HP = 4
DUEL_AMMO_MAX = 3
DUEL_BASE_ACC = 0.35
DUEL_AIM_BONUS = 0.2 # за действие "прицел"
DUEL_DODGE_PENALTY = 0.3 # за действие "уклон" (уменьшает шанс попадания по уклоняющемуся)
DUEL_MAX_ACC = 0.85
DUEL_HEAL_AMOUNT = 1
DUEL_REP_REWARD = 3
DUEL_ROUND_SECONDS_START = 30
DUEL_ROUND_SECONDS_MIN = 10
DUEL_ROUND_SECONDS_DEC = 3


# =======================
# TIME
# =======================
def now_tz(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))

def date_key(dt: datetime) -> str:
    return dt.date().isoformat()

def in_window(dt: datetime, start_h: int, end_h: int) -> bool:
    return start_h <= dt.hour < end_h

# =======================
# TEXT
# =======================
def tokenize(text: str):
    return [w.lower() for w in RE_WORD.findall(text or "")]

def normalize_phrase(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t

def has_trigger(text: str) -> bool:
    return bool(RE_TRIGGER.search(text or ""))

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

    # Логи для "последние 24ч / 7д"
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

    # Кэш отображаемых имён
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_cache (
        chat_id INTEGER,
        user_id INTEGER,
        display TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")

    # Репутация
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

    # Дуэли: state=pending/active/done/cancel
    # data: JSON со всем состоянием боя
    cur.execute("""
    CREATE TABLE IF NOT EXISTS duels (
        chat_id INTEGER,
        duel_id TEXT PRIMARY KEY,
        a_id INTEGER NOT NULL,
        b_id INTEGER NOT NULL,
        state TEXT NOT NULL,
        created_at TEXT NOT NULL,
        accept_deadline TEXT NOT NULL,
        play_deadline TEXT,
        arena_msg_id INTEGER,
        data TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_duels_chat_state ON duels(chat_id, state)")

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

# =======================
# STATS LOGGING
# =======================
def add_msg_log(chat_id: int, ts: datetime, user_id: int):
    db_exec("INSERT INTO msg_log(chat_id, ts, user_id) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), user_id))

def add_words(chat_id: int, ts: datetime, words):
    for w in words:
        if len(w) < 3:
            continue
        db_exec("INSERT INTO word_log(chat_id, ts, word) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), w))

def add_phrase(chat_id: int, ts: datetime, phrase: str):
    if not phrase or len(phrase) > 300:
        return
    db_exec("INSERT INTO phrase_log(chat_id, ts, phrase) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), phrase))

def prune_logs(chat_id: int, cutoff: datetime):
    cutoff_s = cutoff.isoformat()
    db_exec("DELETE FROM msg_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))
    db_exec("DELETE FROM word_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))
    db_exec("DELETE FROM phrase_log WHERE chat_id=? AND ts < ?", (chat_id, cutoff_s))

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
    rows = db_all("""
    SELECT word, COUNT(*) as c
    FROM word_log
    WHERE chat_id=? AND ts>=?
    GROUP BY word
    ORDER BY c DESC
    LIMIT ?
    """, (chat_id, since.isoformat(), limit))
    return rows

def get_user_counts(chat_id: int, since: datetime):
    rows = db_all("""
    SELECT user_id, COUNT(*) as c
    FROM msg_log
    WHERE chat_id=? AND ts>=?
    GROUP BY user_id
    ORDER BY c DESC
    """, (chat_id, since.isoformat()))
    return rows

# =======================
# USER DISPLAY CACHE
# =======================
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
# POOP COUNTER
# =======================
def inc_daily_trigger(chat_id: int, day: str) -> int:
    row = db_one("SELECT cnt FROM daily_trigger_count WHERE chat_id=? AND day=?", (chat_id, day))
    if row is None:
        db_exec("INSERT INTO daily_trigger_count(chat_id, day, cnt) VALUES(?, ?, 1)", (chat_id, day))
        return 1
    cnt = row[0] + 1
    db_exec("UPDATE daily_trigger_count SET cnt=? WHERE chat_id=? AND day=?", (cnt, chat_id, day))
    return cnt

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
# DUELS (GUNFIGHT)
# =======================
ACTION_ALIASES = {
    "стрелять": "shoot",
    "выстрел": "shoot",
    "шут": "shoot",
    "shoot": "shoot",
    "прицел": "aim",
    "целюсь": "aim",
    "aim": "aim",
    "уклон": "dodge",
    "уклониться": "dodge",
    "dodge": "dodge",
    "перезарядка": "reload",
    "перезаряд": "reload",
    "reload": "reload",
    "перевязка": "heal",
    "лечиться": "heal",
    "heal": "heal",
}

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

def duel_new_data(a_id: int, b_id: int) -> dict:
    return {
        "round": 1,
        "round_seconds": DUEL_ROUND_SECONDS_START,
        "deadline": None,
        "players": {
            str(a_id): {
                "hp": DUEL_HP,
                "ammo": DUEL_AMMO_MAX,
                "acc": DUEL_BASE_ACC,
                "heal_used": False,
                "last_action": None
            },
            str(b_id): {
                "hp": DUEL_HP,
                "ammo": DUEL_AMMO_MAX,
                "acc": DUEL_BASE_ACC,
                "heal_used": False,
                "last_action": None
            }
        },
        "moves": {str(a_id): None, str(b_id): None},
        "bot_msgs": []  # сюда будем пушить message_id всех сообщений арены/результата
    }

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
    row = db_one("""
    SELECT duel_id, a_id, b_id, state, accept_deadline, play_deadline, arena_msg_id, data
    FROM duels WHERE chat_id=? AND duel_id=?
    """, (chat_id, duel_id))
    return row

def duel_get_pending_for_b(chat_id: int, b_id: int):
    row = db_one("""
    SELECT duel_id, a_id, b_id, accept_deadline
    FROM duels
    WHERE chat_id=? AND b_id=? AND state='pending'
    ORDER BY created_at DESC
    LIMIT 1
    """, (chat_id, b_id))
    return row

def duel_set_state(chat_id: int, duel_id: str, state: str):
    db_exec("UPDATE duels SET state=? WHERE chat_id=? AND duel_id=?", (state, chat_id, duel_id))

def duel_set_arena(chat_id: int, duel_id: str, arena_msg_id: int):
    db_exec("""
    UPDATE duels
    SET arena_msg_id=?
    WHERE chat_id=? AND duel_id=?
    """, (arena_msg_id, chat_id, duel_id))

def duel_activate(chat_id: int, duel_id: str, now: datetime, arena_msg_id: int):
    play_deadline = now + timedelta(minutes=DUEL_MOVE_MIN)
    db_exec("""
    UPDATE duels
    SET state='active', play_deadline=?, arena_msg_id=?
    WHERE chat_id=? AND duel_id=?
    """, (play_deadline.isoformat(), arena_msg_id, chat_id, duel_id))

def duel_extend_deadline(chat_id: int, duel_id: str, now: datetime):
    play_deadline = now + timedelta(minutes=DUEL_MOVE_MIN)
    db_exec("UPDATE duels SET play_deadline=? WHERE chat_id=? AND duel_id=?", (play_deadline.isoformat(), chat_id, duel_id))

def duel_get_active_by_arena(chat_id: int, arena_msg_id: int):
    row = db_one("""
    SELECT duel_id, a_id, b_id, play_deadline, data
    FROM duels
    WHERE chat_id=? AND arena_msg_id=? AND state='active'
    """, (chat_id, arena_msg_id))
    return row

def duel_get_done_by_arena(chat_id: int, arena_msg_id: int):
    row = db_one("""
    SELECT duel_id, a_id, b_id, data
    FROM duels
    WHERE chat_id=? AND arena_msg_id=? AND state='done'
    """, (chat_id, arena_msg_id))
    return row

def duel_start_round(data: dict, now_dt: datetime, a_id: int, b_id: int):
    data["moves"][str(a_id)] = None
    data["moves"][str(b_id)] = None
    data["deadline"] = (now_dt + timedelta(seconds=int(data["round_seconds"]))).isoformat()

def duel_update_data(chat_id: int, duel_id: str, data: dict):
    db_exec("UPDATE duels SET data=? WHERE chat_id=? AND duel_id=?", (json.dumps(data, ensure_ascii=False), chat_id, duel_id))

def parse_duel_target_username(text: str) -> str | None:
    m = re.search(r"дуэль\s+@([A-Za-z0-9_]+)", text, re.IGNORECASE)
    return m.group(1) if m else None

def parse_action(text: str) -> str | None:
    t = (text or "").strip().lower()
    return ACTION_ALIASES.get(t)

def duel_status_text(chat_id: int, a_id: int, b_id: int, data: dict) -> str:
    a = data["players"][str(a_id)]
    b = data["players"][str(b_id)]
    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)

    def moved(uid: int) -> str:
        return "✅ походил" if data["moves"].get(str(uid)) else "⏳ ждёт"

    deadline_str = ""
    if data.get("deadline"):
        try:
            dl = datetime.fromisoformat(data["deadline"])
            deadline_str = dl.strftime("%H:%M:%S")
        except Exception:
            deadline_str = str(data["deadline"])

    def p_line(name, p, uid):
        acc = int(p["acc"] * 100)
        return f"{name}: ❤{p['hp']} | 🔫{p['ammo']} | 🎯{acc}% | 🩹{'да' if p['heal_used'] else 'нет'} | {moved(uid)}"

    return (
        f"Раунд {data['round']}\n"
        f"Время на ход: {data.get('round_seconds', DUEL_ROUND_SECONDS_START)}s"
        + (f" (до {deadline_str})" if deadline_str else "")
        + "\n\n"
        f"{p_line(a_name, a, a_id)}\n"
        f"{p_line(b_name, b, b_id)}\n\n"
        "Жми кнопки ниже 👇"
    )


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def duel_resolve_round(chat_id: int, duel_id: str, a_id: int, b_id: int, data: dict) -> tuple[str, bool]:
    """
    Возвращает (result_text, finished)
    """
    pA = data["players"][str(a_id)]
    pB = data["players"][str(b_id)]
    mA = data["moves"][str(a_id)]
    mB = data["moves"][str(b_id)]

    a_name = get_user_display(chat_id, a_id)
    b_name = get_user_display(chat_id, b_id)

    # Нормализация "не выбрал" — считаем как уклон (чтобы игра не стопорилась)
    if mA is None:
        mA = "dodge"
    if mB is None:
        mB = "dodge"

    # Применяем небоевые действия сначала
    log = []

    def apply_action(pid, action, me, opp_name):
        nonlocal log
        if action == "aim":
            me["acc"] = clamp(me["acc"] + DUEL_AIM_BONUS, DUEL_BASE_ACC, DUEL_MAX_ACC)
            log.append(f"{opp_name}: прицеливается.")
        elif action == "reload":
            me["ammo"] = DUEL_AMMO_MAX
            log.append(f"{opp_name}: перезаряжается.")
        elif action == "heal":
            if me["heal_used"]:
                log.append(f"{opp_name}: пытался перевязаться, но уже использовал.")
            else:
                me["heal_used"] = True
                me["hp"] = clamp(me["hp"] + DUEL_HEAL_AMOUNT, 0, DUEL_HP)
                log.append(f"{opp_name}: перевязка (+{DUEL_HEAL_AMOUNT}❤).")
        elif action == "dodge":
            log.append(f"{opp_name}: уходит в уклон.")
        elif action == "shoot":
            # стрельбу отдельно
            pass

    # Сначала применяем всем aim/reload/heal/dodge (shoot позже)
    apply_action(a_id, mA, pA, a_name)
    apply_action(b_id, mB, pB, b_name)

    # Затем стрельба
    def shoot(shooter_name, shooter, target_name, target, target_action):
        nonlocal log
        if shooter["ammo"] <= 0:
            log.append(f"{shooter_name}: щёлк — патроны кончились.")
            return False
        shooter["ammo"] -= 1

        chance = shooter["acc"]
        if target_action == "dodge":
            chance = clamp(chance - DUEL_DODGE_PENALTY, 0.05, 0.95)

        hit = random.random() < chance
        if hit:
            target["hp"] = max(0, target["hp"] - 1)
            log.append(f"{shooter_name}: попал по {target_name}. (-1❤)")
        else:
            log.append(f"{shooter_name}: промахнулся.")
        return hit

    # Оба могут стрелять в одном раунде
    if mA == "shoot":
        shoot(a_name, pA, b_name, pB, mB)
    if mB == "shoot":
        shoot(b_name, pB, a_name, pA, mA)

    # Проверка победы
    finished = False
    result = ""

    if pA["hp"] <= 0 and pB["hp"] <= 0:
        finished = True
        result = "Оба падают. Ничья."
    elif pA["hp"] <= 0:
        finished = True
        rep_add(chat_id, b_id, DUEL_REP_REWARD)
        score = rep_get(chat_id, b_id)
        result = f"Победа {b_name}. +{DUEL_REP_REWARD} репутации (итого {score})."
    elif pB["hp"] <= 0:
        finished = True
        rep_add(chat_id, a_id, DUEL_REP_REWARD)
        score = rep_get(chat_id, a_id)
        result = f"Победа {a_name}. +{DUEL_REP_REWARD} репутации (итого {score})."
    else:
        # следующий раунд
        data["round"] += 1
        data["moves"][str(a_id)] = None
        data["moves"][str(b_id)] = None

    # Собираем текст
    body = "\n".join(log) if log else "Тишина."
    if finished:
        text = f"{body}\n\n{result}"
        return text, True

    # промежуточный статус
    status = duel_status_text(chat_id, a_id, b_id, data)
    text = f"{body}\n\n{status}"
    return text, False

# =======================
# SILENCE WATCHER
# =======================
async def background_silence_watcher(bot: Bot):
    while True:
        try:
            chats = db_all("SELECT chat_id FROM chat_settings WHERE enabled=1")
            for (chat_id,) in chats:
                s = get_settings(chat_id)
                tz = s["tz"]
                now = now_tz(tz)

                quiet_until = s["quiet_until"]
                if quiet_until and now < quiet_until:
                    continue

                last_msg = s["last_message_at"]

                # 03:00-12:00: если с 03:00 не было сообщений → в 12:00 пишем
                if now.hour == 12 and now.minute <= 5:
                    marker = now.replace(hour=3, minute=0, second=0, microsecond=0)
                    already = s["last_interesting_at"]
                    if (already is None) or (already.date() != now.date()):
                        if (last_msg is None) or (last_msg < marker):
                            await bot.send_message(chat_id, "интересный сегодня чат")
                            set_field(chat_id, "last_interesting_at", now)

                # 10:00-24:00: если тишина 5 часов → "где все?"
                if in_window(now, 10, 24) and last_msg is not None:
                    if now - last_msg >= timedelta(hours=5):
                        last_where = s["last_where_all_at"]
                        if (last_where is None) or (now - last_where >= timedelta(hours=5)):
                            await bot.send_message(chat_id, "где все?")
                            set_field(chat_id, "last_where_all_at", now)

                # чистка логов
                prune_logs(chat_id, now - timedelta(days=7))

                # таймаут активных дуэлей (если зависли)
                # Если deadline прошёл — отменяем
                active_duels = db_all("""
                    SELECT duel_id, play_deadline
                    FROM duels
                    WHERE chat_id=? AND state='active'
                """, (chat_id,))
                for duel_id, play_deadline in active_duels:
                    if play_deadline:
                        dl = datetime.fromisoformat(play_deadline)
                        if now > dl:
                            duel_set_state(chat_id, duel_id, "cancel")
                            # можно не спамить сообщением, но если хочешь — раскомментируй:
                            # await bot.send_message(chat_id, "Дуэль истекла по времени.")
        except Exception:
            pass

        await asyncio.sleep(60)

# =======================
# MAIN
# =======================
async def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN env var")

    init_db()
    bot = Bot(TOKEN)
    dp = Dispatcher()

    # -------- Commands: on/off/quiet/hype/stat --------
    @dp.message(Command("on"))
    async def cmd_on(message: Message):
        ensure_chat(message.chat.id)
        set_field(message.chat.id, "enabled", 1)
        set_null(message.chat.id, "quiet_until") # важный фикс: /on снимает quiet
        await message.answer("Ок. Включен.")

    @dp.message(Command("off"))
    async def cmd_off(message: Message):
        ensure_chat(message.chat.id)
        set_field(message.chat.id, "enabled", 0)
        await message.answer("Ок. Выключен.")

    @dp.message(Command("quiet"))
    async def cmd_quiet(message: Message):
        ensure_chat(message.chat.id)
        s = get_settings(message.chat.id)
        tz = s["tz"]
        parts = (message.text or "").split()
        if len(parts) < 2 or not re.fullmatch(r"-?\d+", parts[1] or ""):
            await message.answer("Формат: /quiet N (часов). Для снятия: /quiet 0")
            return
        hours = int(parts[1])
        if hours <= 0:
            set_null(message.chat.id, "quiet_until")
            await message.answer("Ок. Снова говорю.")
            return
        until = now_tz(tz) + timedelta(hours=hours)
        set_field(message.chat.id, "quiet_until", until)
        await message.answer(f"Ок. Молчу до {until.strftime('%Y-%m-%d %H:%M')}")

    @dp.message(Command("hype"))
    async def cmd_hype(message: Message):
        s = get_settings(message.chat.id)
        tz = s["tz"]
        now = now_tz(tz)
        since = now - timedelta(days=2)
        top = get_top_phrase(message.chat.id, since)
        if not top:
            await message.answer("За последние 2 дня нечего хайпить.")
            return
        phrase, c = top
        await message.answer(f"ХАЙП (2 дня):\n«{phrase}»\nПовторов: {c}")

    @dp.message(Command("stat"))
    async def cmd_stat(message: Message):
        s = get_settings(message.chat.id)
        tz = s["tz"]
        now = now_tz(tz)

        since24 = now - timedelta(hours=24)
        since7d = now - timedelta(days=7)

        top24 = get_top_words(message.chat.id, since24, limit=3)
        top7 = get_top_words(message.chat.id, since7d, limit=3)

        users24 = get_user_counts(message.chat.id, since24)
        users7 = get_user_counts(message.chat.id, since7d)

        def fmt_top(rows):
            return "—" if not rows else "\n".join([f"- {w}: {c}" for w, c in rows])

        def fmt_users(rows, limit=20):
            if not rows:
                return "—"
            out = []
            for uid, c in rows[:limit]:
                name = get_user_display(message.chat.id, int(uid))
                out.append(f"- {name}: {c}")
            return "\n".join(out)

        await message.answer(
            "СТАТИСТИКА\n\n"
            "Топ слова (24ч):\n" + fmt_top(top24) + "\n\n"
            "Топ слова (7д):\n" + fmt_top(top7) + "\n\n"
            "Сообщения по юзерам (24ч):\n" + fmt_users(users24) + "\n\n"
            "Сообщения по юзерам (7д):\n" + fmt_users(users7)
        )
    @dp.message(Command("rep"))
    async def cmd_rep(message: Message):
        chat_id = message.chat.id

        # 1) /rep reply -> один
        if message.reply_to_message and message.reply_to_message.from_user:
            uid = message.reply_to_message.from_user.id
            name = get_user_display(chat_id, uid)
            score = rep_get(chat_id, uid)
            await message.answer(f"Репутация {name}: {score}")
            return

        parts = (message.text or "").split()

        # 2) /rep @username -> один
        if len(parts) >= 2 and parts[1].startswith("@"):
            uname = parts[1][1:]
            uid = find_user_id_by_username(chat_id, uname)
            if not uid:
                await message.answer("Не знаю этого @username (пусть он хоть раз напишет в чат после запуска бота).")
                return
            name = get_user_display(chat_id, uid)
            score = rep_get(chat_id, uid)
            await message.answer(f"Репутация {name}: {score}")
            return

        # 3) /rep -> все
        rows = rep_all(chat_id)
        if not rows:
            await message.answer("Репутации пока нет.")
            return

        lines = ["Репутация в чате:"]
        for i, (uid, score) in enumerate(rows, start=1):
            name = get_user_display(chat_id, int(uid))
            lines.append(f"{i}. {name} — {score}")

        # Telegram лимит на длину сообщения, режем пачками
        chunk = []
        size = 0
        for line in lines:
            if size + len(line) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = []
                size = 0
            chunk.append(line)
            size += len(line) + 1

        if chunk:
            await message.answer("\n".join(chunk))

    @dp.callback_query(F.data.startswith("duel:act:"))
    async def cb_duel_act(q: CallbackQuery):
    # duel:act:<duel_id>:<action>
    _, _, duel_id, action = q.data.split(":", 3)
    chat_id = q.message.chat.id

    active = duel_get_active_by_arena(chat_id, q.message.message_id)
    if not active:
        await q.answer("Неактуально", show_alert=True)
        return

    duel_id_db, a_id, b_id, play_deadline, data_json = active
    if duel_id_db != duel_id:
        await q.answer("Не тот бой", show_alert=True)
        return
    if user_id not in (a_id, b_id):
        await q.answer("Ты не участник", show_alert=True)
        return

    s = get_settings(chat_id)
    now_dt = now_tz(s["tz"])
    data = json.loads(data_json) if data_json else duel_new_data(a_id, b_id)

    # дедлайн раунда
    if data.get("deadline"):
        dl = datetime.fromisoformat(data["deadline"])
        if now_dt > dl:
            duel_set_state(chat_id, duel_id, "done")
            await q.message.edit_text("ДУЭЛЬ\n\nВремя вышло. Дуэль завершена.", reply_markup=None)
            await q.answer("Время вышло", show_alert=True)
            return

    # surrender
    if action == "surrender":
        winner = b_id if user_id == a_id else a_id
        rep_add(chat_id, winner, DUEL_REP_REWARD)
        score = rep_get(chat_id, winner)
        winner_name = get_user_display(chat_id, winner)
        loser_name = get_user_display(chat_id, user_id)

        duel_set_state(chat_id, duel_id, "done")
        await q.message.edit_text(
            f"ДУЭЛЬ\n\n{loser_name} сдался. Победа {winner_name}. +{DUEL_REP_REWARD} репутации (итого {score}).",
            reply_markup=None
        )
        await q.answer("Ок")
        return

    # уже походил
    if data["moves"].get(str(user_id)) is not None:
        await q.answer("Ты уже походил")
        return

    me = data["players"][str(user_id)]
    if action == "shoot" and me["ammo"] <= 0:
        await q.answer("Патроны кончились")
        return
    if action == "heal" and me["heal_used"]:
        await q.answer("Перевязка уже была")
        return

    # записать ход
    data["moves"][str(user_id)] = action
    duel_update_data(chat_id, duel_id, data)

    # обновить арену, чтобы видно ✅/⏳
    arena_text = duel_status_text(chat_id, a_id, b_id, data)
    await q.message.edit_text("ДУЭЛЬ\n\n" + arena_text, reply_markup=kb_duel_actions(duel_id))

    # если оба походили — резолв
    if data["moves"][str(a_id)] is not None and data["moves"][str(b_id)] is not None:
        result_text, finished = duel_resolve_round(chat_id, duel_id, a_id, b_id, data)
        duel_update_data(chat_id, duel_id, data)

        if finished:
            duel_set_state(chat_id, duel_id, "done")
            await q.message.edit_text("ДУЭЛЬ\n\n" + result_text, reply_markup=None)
        else:
            # уменьшаем время
            data["round_seconds"] = max(DUEL_ROUND_SECONDS_MIN, int(data["round_seconds"]) - DUEL_ROUND_SECONDS_DEC)
            duel_start_round(data, now_dt, a_id, b_id)
            duel_update_data(chat_id, duel_id, data)

            arena_text = duel_status_text(chat_id, a_id, b_id, data)
            await q.message.edit_text("ДУЭЛЬ\n\n" + arena_text, reply_markup=kb_duel_actions(duel_id))

    await q.answer("Ок")

    # -------- Main message handler --------
    @dp.message(F.text)
    async def on_text(message: Message):
        chat_id = message.chat.id
        ensure_chat(chat_id)
        s = get_settings(chat_id)
        tz = s["tz"]
        now = now_tz(tz)

        # фиксируем последнее сообщение
        set_field(chat_id, "last_message_at", now)

        # кешируем имя
        u = message.from_user
        display = ""
        if u.username:
            display = f"@{u.username}"
        else:
            display = " ".join([x for x in [u.first_name, u.last_name] if x]).strip()
        upsert_user_display(chat_id, u.id, display, now)

        text = message.text or ""
        tlow = text.strip().lower()

        # команды не логируем
        if text.startswith("/"):
            return

        # логируем статистику/хайп всегда (даже в quiet/off)
        add_msg_log(chat_id, now, u.id)
        add_words(chat_id, now, tokenize(text))
        add_phrase(chat_id, now, normalize_phrase(text))
        prune_logs(chat_id, now - timedelta(days=7))

        # если bot выключен или quiet — не делает реакций/пасхалок/эхо/дуэлей
        quiet_until = s["quiet_until"]
        if (not s["enabled"]) or (quiet_until and now < quiet_until):
            return

        # =======================
        # 1) REPUTATION via reply "+" or "-"
        # =======================
        if message.reply_to_message and tlow in ("+", "-"):
            if tlow == "-" and not ALLOW_NEGATIVE_REP:
                return
            target_user = message.reply_to_message.from_user
            if not target_user:
                return

            # нельзя себе
            if target_user.id == message.from_user.id:
                return

            delta = 1 if tlow == "+" else -1

            if not rep_can_vote(chat_id, message.from_user.id, target_user.id, now):
                return

            rep_add(chat_id, target_user.id, delta)
            rep_mark_vote(chat_id, message.from_user.id, target_user.id, now)

            score = rep_get(chat_id, target_user.id)
            name = get_user_display(chat_id, target_user.id)

            sign = "+1" if delta > 0 else "-1"
            await message.answer(f"{sign} репутация {name}\nРепутация: {score}")
            return

        # =======================
        # 2) DUEL: start
        # =======================
        if tlow.startswith("дуэль"):
            target_id = None

            # reply target
            if message.reply_to_message and message.reply_to_message.from_user:
                target_id = message.reply_to_message.from_user.id
            else:
                # duel @username
                uname = parse_duel_target_username(text)
                if uname:
                    target_id = find_user_id_by_username(chat_id, uname)

            if not target_id:
                await message.answer("Кого в дуэль? Ответь на сообщение или: дуэль @username")
                return
            if target_id == u.id:
                return

            duel_id = duel_create(chat_id, u.id, target_id, now)
            a_name = get_user_display(chat_id, u.id)
            b_name = get_user_display(chat_id, target_id)

            await message.answer(
                f"{a_name} вызывает {b_name} на дуэль.\n"
                f"{b_name}, напиши: принял / отказ"
            )
            return

        # =======================
        # 3) DUEL: accept/decline
        # =======================
        if tlow in ("принял", "принято", "го", "ок", "да"):
            pend = duel_get_pending_for_b(chat_id, u.id)
            if pend:
                duel_id, a_id, b_id, accept_deadline = pend
                if now > datetime.fromisoformat(accept_deadline):
                    duel_set_state(chat_id, duel_id, "cancel")
                    return

                # создаём "арену"
                data_row = duel_get(chat_id, duel_id)
                duel_id_db, a_id2, b_id2, state, accept_dl, play_dl, arena_id, data_json = data_row

                data = json.loads(data_json) if data_json else duel_new_data(a_id2, b_id2)

                duel_start_round(data, now, a_id2, b_id2)
                duel_update_data(chat_id, duel_id, data)

                arena_text = duel_status_text(chat_id, a_id2, b_id2, data)
                arena_msg = await message.answer(
                    "ДУЭЛЬ\n\n" + arena_text,
                    reply_markup=kb_duel_actions(duel_id)
                )

                duel_activate(chat_id, duel_id, now, arena_msg.message_id)

                data["bot_msgs"].append(arena_msg.message_id)
                duel_update_data(chat_id, duel_id, data)

                return


        if tlow in ("отказ", "нет", "пас", "не"):
            pend = duel_get_pending_for_b(chat_id, u.id)
            if pend:
                duel_id, *_ = pend
                duel_set_state(chat_id, duel_id, "cancel")
                await message.answer("Дуэль отменена.")
            return

        # =======================
        # 4) Пасхалка (кулдаун)
        # =======================
        if random.random() < EASTER_PROB:
            last_e = s["last_easter_at"]
            if (last_e is None) or (now - last_e >= timedelta(minutes=MIN_EASTER_EVERY_MIN)):
                await message.answer("Я запомнил это сообщение навсегда...")
                set_field(chat_id, "last_easter_at", now)

        # =======================
        # 5) Эхо 
        # =======================
        if random.random() < ECHO_PROB:
            if text and not text.strip().endswith("..."):
                await message.reply(text.strip() + "...")

        # =======================
        # 6) 💩 по триггерам (после 5/день -> 25%)
        # =======================
        if has_trigger(text):
            day = date_key(now)
            cnt = inc_daily_trigger(chat_id, day)
            prob = 1.0 if cnt <= DAILY_TRIGGER_LIMIT else POOP_AFTER_DAILY_LIMIT_PROB
            if random.random() < prob:
                try:
                    await bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=message.message_id,
                        reaction=[ReactionTypeEmoji(emoji="💩")]
                    )
                except Exception:
                    pass

        # =======================
        # 7) Авто-hype (кулдаун 6ч)
        # =======================
        if random.random() < AUTO_HYPE_PROB:
            last_h = s["last_autohype_at"]
            if (last_h is None) or (now - last_h >= timedelta(hours=MIN_AUTOHYPE_EVERY_HOURS)):
                top = get_top_phrase(chat_id, now - timedelta(days=2))
                if top:
                    phrase, c = top
                    await bot.send_message(chat_id, f"ХАЙП (2 дня):\n«{phrase}»\nПовторов: {c}")
                    set_field(chat_id, "last_autohype_at", now)
                    
        # --- prepare arena: delete intermediate bot messages ---
        if message.reply_to_message and tlow == "подготовить арену":
            done = duel_get_done_by_arena(chat_id, message.reply_to_message.message_id)
            if not done:
                return

            duel_id, a_id, b_id, data_json = done
            data = json.loads(data_json) if data_json else {}
            ids = data.get("bot_msgs", [])

            # если нечего чистить
            if len(ids) <= 2:
                await message.answer("Тут и так чисто.")
                return

            # удаляем все кроме первого и последнего
            to_delete = ids[1:-1]
            deleted = 0
            for mid in to_delete:
                try:
                    await bot.delete_message(chat_id, mid)
                    deleted += 1
                except Exception:
                    pass

            await message.answer(f"Подготовлено. Удалено сообщений: {deleted}")
            return

    asyncio.create_task(background_silence_watcher(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())