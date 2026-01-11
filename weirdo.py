import asyncio
import os
import re
import random
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import ReactionTypeEmoji

# TOKEN = os.getenv("aboba")                  # --- PLACE TOKEN HERE (cmd) ---
DB_PATH = os.getenv("DB_PATH", "bot.db")
DEFAULT_TZ = os.getenv("BOT_TZ", "Europe/Moscow")

# Триггеры по словоформам (без библиотек морфологии, но ловит нормально)

RE_TRIGGER = re.compile(
    r"(?<!\w)(пар(а|ы|е|у|ой|ам|ами|ах)?|долг(и|а|у|ом|ов|ам|ами|ах)?)(?!\w)",
    re.IGNORECASE | re.UNICODE,
)

RE_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+", re.UNICODE)

# Шансы и лимиты
POOP_AFTER_DAILY_LIMIT_PROB = 0.25  # после 5 сообщений в сутки
DAILY_TRIGGER_LIMIT = 5

EASTER_PROB = 0.05
ECHO_PROB = 0.001
AUTO_HYPE_PROB = 0.02

# Кулдауны, чтобы не спамило даже при везении вероятности
MIN_EASTER_EVERY_MIN = 20
MIN_AUTOHYPE_EVERY_HOURS = 6

def now_tz(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))

def date_key(dt: datetime) -> str:
    return dt.date().isoformat()

def tokenize(text: str):
    return [w.lower() for w in RE_WORD.findall(text)]

def has_trigger(text: str) -> bool:
    return bool(RE_TRIGGER.search(text or ""))

def normalize_phrase(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t

# ---------- DB helpers ----------
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

    # Для реакции 💩 нужно "кол-во триггерных сообщений за сутки"
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_trigger_count (
        chat_id INTEGER,
        day TEXT,
        cnt INTEGER NOT NULL,
        PRIMARY KEY(chat_id, day)
    )""")

    # Логи за 7 дней (чтобы считать "за 24ч/7д")
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

    # Кэш имён
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_cache (
        chat_id INTEGER,
        user_id INTEGER,
        display TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(chat_id, user_id)
    )""")

    con.commit()
    con.close()

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

def inc_daily_trigger(chat_id: int, day: str) -> int:
    row = db_one("SELECT cnt FROM daily_trigger_count WHERE chat_id=? AND day=?", (chat_id, day))
    if row is None:
        db_exec("INSERT INTO daily_trigger_count(chat_id, day, cnt) VALUES(?, ?, 1)", (chat_id, day))
        return 1
    cnt = row[0] + 1
    db_exec("UPDATE daily_trigger_count SET cnt=? WHERE chat_id=? AND day=?", (cnt, chat_id, day))
    return cnt

def upsert_user_display(chat_id: int, user_id: int, display: str, ts: datetime):
    display = (display or "").strip()
    if not display:
        display = f"id:{user_id}"
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

def add_msg_log(chat_id: int, ts: datetime, user_id: int):
    db_exec("INSERT INTO msg_log(chat_id, ts, user_id) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), user_id))

def add_words(chat_id: int, ts: datetime, words):
    # ограничим шум: слова длиной 1–2 символа можно скипнуть
    for w in words:
        if len(w) < 3:
            continue
        db_exec("INSERT INTO word_log(chat_id, ts, word) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), w))

def add_phrase(chat_id: int, ts: datetime, phrase: str):
    if not phrase or len(phrase) > 300:
        return
    db_exec("INSERT INTO phrase_log(chat_id, ts, phrase) VALUES(?, ?, ?)", (chat_id, ts.isoformat(), phrase))

def prune_logs(chat_id: int, cutoff: datetime):
    # держим только последние 7 дней
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

def in_window(dt: datetime, start_h: int, end_h: int) -> bool:
    return start_h <= dt.hour < end_h

# ---------- Background watcher (тишина) ----------
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

                # 03:00-12:00: если до 12:00 не писали (с 03:00)
                if now.hour == 12 and now.minute <= 5:
                    marker = now.replace(hour=3, minute=0, second=0, microsecond=0)
                    already = s["last_interesting_at"]
                    if (already is None) or (already.date() != now.date()):
                        if (last_msg is None) or (last_msg < marker):
                            await bot.send_message(chat_id, "интересный сегодня чат")
                            set_field(chat_id, "last_interesting_at", now)

                # 10:00-24:00: если тишина 5 часов
                if in_window(now, 10, 24) and last_msg is not None:
                    if now - last_msg >= timedelta(hours=5):
                        last_where = s["last_where_all_at"]
                        if (last_where is None) or (now - last_where >= timedelta(hours=5)):
                            await bot.send_message(chat_id, "где все?")
                            set_field(chat_id, "last_where_all_at", now)

                # чистка логов (раз в минуту — норм, объёмы маленькие)
                prune_logs(chat_id, now - timedelta(days=7))

        except Exception:
            pass

        await asyncio.sleep(60)

# ---------- Main ----------
async def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN env var")

    init_db()
    bot = Bot(token)
    dp = Dispatcher()

    @dp.message(Command("on"))
    async def cmd_on(message: Message):
        ensure_chat(message.chat.id)
        set_field(message.chat.id, "enabled", 1)
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
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Формат: /quiet N (часов)")
            return
        hours = int(parts[1])
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
                name = get_user_display(message.chat.id, uid)
                out.append(f"- {name}: {c}")
            return "\n".join(out)

        await message.answer(
            "СТАТИСТИКА\n\n"
            "Топ слова (24ч):\n" + fmt_top(top24) + "\n\n"
            "Топ слова (7д):\n" + fmt_top(top7) + "\n\n"
            "Сообщения по юзерам (24ч):\n" + fmt_users(users24) + "\n\n"
            "Сообщения по юзерам (7д):\n" + fmt_users(users7)
        )

    @dp.message(F.text)
    async def on_text(message: Message):
        chat_id = message.chat.id
        ensure_chat(chat_id)
        s = get_settings(chat_id)
        tz = s["tz"]
        now = now_tz(tz)

        # фиксируем последнее сообщение
        set_field(chat_id, "last_message_at", now)

        # кэш имени
        u = message.from_user
        display = u.username or " ".join([x for x in [u.first_name, u.last_name] if x]).strip() or f"id:{u.id}"
        if u.username:
            display = f"@{u.username}"
        upsert_user_display(chat_id, u.id, display, now)

        text = message.text or ""

        # не учитываем команды в логи/статы
        if text.startswith("/"):
            return

        # логи для статистики/хайпа
        add_msg_log(chat_id, now, u.id)
        add_words(chat_id, now, tokenize(text))
        add_phrase(chat_id, now, normalize_phrase(text))

        # если бот выключен или quiet — не делает действий, но статистику собирает
        quiet_until = s["quiet_until"]
        if (not s["enabled"]) or (quiet_until and now < quiet_until):
            return

        # пасхалка 1% (с кулдауном)
        if random.random() < EASTER_PROB:
            last_e = s["last_easter_at"]
            if (last_e is None) or (now - last_e >= timedelta(minutes=MIN_EASTER_EVERY_MIN)):
                await message.answer("Я запомнил это сообщение навсегда...")
                set_field(chat_id, "last_easter_at", now)

        # эхо 0.5%
        if random.random() < ECHO_PROB:
            if text and not text.endswith("..."):
                await message.reply(text.strip() + "...")

        # 💩 по триггерам
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
                    # если в группе реакции запрещены / у бота нет прав — просто молчим
                    pass

        # авто-hype 1% (с кулдауном)
        if random.random() < AUTO_HYPE_PROB:
            last_h = s["last_autohype_at"]
            if (last_h is None) or (now - last_h >= timedelta(hours=MIN_AUTOHYPE_EVERY_HOURS)):
                top = get_top_phrase(chat_id, now - timedelta(days=2))
                if top:
                    phrase, c = top
                    await bot.send_message(chat_id, f"ХАЙП (2 дня):\n«{phrase}»\nПовторов: {c}")
                    set_field(chat_id, "last_autohype_at", now)

    asyncio.create_task(background_silence_watcher(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
