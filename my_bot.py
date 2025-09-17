# my_bot.py
import datetime
import sqlite3
from typing import Optional, Dict
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "СЮДА_ВАШ_ТОКЕН"
DB_FILE = "works.db"

# Conversation states
EDIT_AMOUNT, EDIT_WHO, EDIT_FOR = range(3)

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL UNIQUE,
            name TEXT,
            group_id INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            who_did TEXT NOT NULL,
            for_whom TEXT NOT NULL,
            work TEXT,
            amount REAL NOT NULL,
            group_id INTEGER NOT NULL,
            creator_tg INTEGER,
            creator_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def ensure_user(tg_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (tg_id) VALUES (?)", (tg_id,))
    conn.commit()
    conn.close()

def get_user(tg_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, tg_id, name, group_id FROM users WHERE tg_id=?", (tg_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {"id": r[0], "tg_id": r[1], "name": r[2], "group_id": r[3]}

def set_user_name(tg_id: int, name: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=? WHERE tg_id=?", (name, tg_id))
    conn.commit()
    conn.close()

def get_group(group_id: int) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM groups WHERE id=?", (group_id,))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else None

def add_record(who: str, whom: str, work: str, amount: float, group_id: int, creator_tg: int, creator_name: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO records (date, who_did, for_whom, work, amount, group_id, creator_tg, creator_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.date.today().isoformat(), who, whom, work, amount, group_id, creator_tg, creator_name))
    conn.commit()
    conn.close()

def get_records_group_month(group_id: int, ym: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, who_did, for_whom, work, amount, creator_tg, creator_name
        FROM records
        WHERE group_id=? AND strftime('%Y-%m', date)=?
        ORDER BY date
    """, (group_id, ym))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_record_by_id(rec_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, who_did, for_whom, work, amount, group_id, creator_tg FROM records WHERE id=?", (rec_id,))
    r = cur.fetchone()
    conn.close()
    return r

def update_record(rec_id: int, amount: Optional[float], who: Optional[str], whom: Optional[str]):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if amount is not None:
        cur.execute("UPDATE records SET amount=? WHERE id=?", (amount, rec_id))
    if who is not None:
        cur.execute("UPDATE records SET who_did=? WHERE id=?", (who, rec_id))
    if whom is not None:
        cur.execute("UPDATE records SET for_whom=? WHERE id=?", (whom, rec_id))
    conn.commit()
    conn.close()

def delete_record(rec_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM records WHERE id=?", (rec_id,))
    conn.commit()
    conn.close()

# ---------------- Utils ----------------
def reply_menu():
    return ReplyKeyboardMarkup([[KeyboardButton("Меню")]], resize_keyboard=True)

def main_menu() -> InlineKeyboardMarkup:
    ym = datetime.date.today().strftime("%Y-%m")
    buttons = [
        [InlineKeyboardButton("➕ Добавить запись", callback_data="menu_add")],
        [InlineKeyboardButton("📄 Записи (этот мес.)", callback_data=f"records|{ym}")],
        [InlineKeyboardButton("📊 Баланс", callback_data=f"menu_balance|{ym}")],
        [InlineKeyboardButton("⚙️ Установить имя", callback_data="menu_name")],
    ]
    return InlineKeyboardMarkup(buttons)

def calc_balance(rows, period):
    balance = {}
    for who, whom, work, amount, *_ in rows:
        balance[whom] = balance.get(whom, 0) + amount
        balance[who] = balance.get(who, 0) - amount
    text = [f"Баланс за {period}:"]
    for person, val in balance.items():
        if val > 0:
            text.append(f"{person} должен {abs(val)}")
    if len(text) == 1:
        text.append("Никто никому не должен.")
    return "\n".join(text)

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)
    user = get_user(update.effective_user.id)
    name = user["name"] if user and user["name"] else None
    group_name = get_group(user["group_id"]) if user and user["group_id"] else None

    if not name:
        msg = "Привет! У тебя пока не задано имя. Укажи его командой /set_name Иван"
    elif not group_name:
        msg = f"Привет, {name}! Ты пока не в группе. Создай или подключись."
    else:
        msg = f"Привет, {name}! Ты в группе \"{group_name}\""

    await update.message.reply_text(msg, reply_markup=reply_menu())
    await update.message.reply_text("Главное меню:", reply_markup=main_menu())

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_name = context.args[0]
    except IndexError:
        await update.message.reply_text("Используй: /set_name Иван")
        return
    set_user_name(update.effective_user.id, new_name)
    await update.message.reply_text(f"Имя установлено: {new_name}")

async def records_show(update: Update, context: ContextTypes.DEFAULT_TYPE, ym: Optional[str] = None):
    if not ym:
        try:
            ym = context.args[0]
        except Exception:
            await update.message.reply_text("Используй: /records YYYY-MM")
            return
    user = get_user(update.effective_user.id)
    if not user or not user["group_id"]:
        await update.message.reply_text("Вы не в группе.")
        return
    rows = get_records_group_month(user["group_id"], ym)
    if not rows:
        await update.message.reply_text("Записей за этот месяц нет.")
        return
    for r in rows:
        text = f"ID {r[0]} | {r[1]} | {r[2]} сделал {r[4]} → {r[3]} | {r[5]:.2f}"
        kb = []
        if r[6] == update.effective_user.id:
            kb = [[
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit|{r[0]}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete|{r[0]}")
            ]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

# ---- Callback router ----
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "menu_add":
        await q.message.reply_text("Чтобы добавить запись, напиши: Иван сделал сайт для Ольги за 5000")
    elif q.data.startswith("records|"):
        ym = q.data.split("|")[1]
        await records_show(update, context, ym)  # фикс
    elif q.data.startswith("menu_balance"):
        ym = q.data.split("|")[1]
        user = get_user(update.effective_user.id)
        if not user or not user["group_id"]:
            await q.message.reply_text("Вы не в группе.")
            return
        rows = get_records_group_month(user["group_id"], ym)
        if not rows:
            await q.message.reply_text("Записей нет.")
            return
        await q.message.reply_text(calc_balance(rows, ym))
    elif q.data == "menu_name":
        await q.message.reply_text("Установить имя: /set_name Иван")

# ---------------- Main ----------------
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_name", set_name))
    app.add_handler(CommandHandler("records", records_show))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.Regex("^Меню$"), start))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
