import sqlite3

from aiogram import Router, F, types

from aiogram.filters import Command

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

 

# Впишите сюда ваш числовой Telegram ID

ADMIN_ID = 6921885296

 

promo_router = Router()

waiting_promo_input = set()

 

db = sqlite3.connect("game_v2.db")

cur = db.cursor()

 

cur.execute("""

CREATE TABLE IF NOT EXISTS promocodes (

    code TEXT PRIMARY KEY,

    reward INTEGER,

    uses_left INTEGER

)

""")

 

cur.execute("""

CREATE TABLE IF NOT EXISTS promo_used (

    user_id INTEGER,

    code TEXT,

    PRIMARY KEY (user_id, code)

)

""")

db.commit()

 

 

def promo_admin_kb():

    return InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="p_create")],

        [InlineKeyboardButton(text="📋 Список активных кодов", callback_data="p_list")]

    ])

 

 

# --- ПАНЕЛЬ ПРОМОКОДОВ ДЛЯ АДМИНА (/promoadmin) ---

@promo_router.message(Command("promoadmin"))

async def cmd_promo_admin(message: types.Message):

    if message.from_user.id != ADMIN_ID:

        return

    waiting_promo_input.discard(ADMIN_ID)

    await message.answer(

        "🎟 <b>Управление промокодами</b>\n\nВыберите нужное действие:",

        parse_mode="HTML",

        reply_markup=promo_admin_kb()

    )

 

 

@promo_router.callback_query(F.data == "p_back")

async def cb_p_back(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        return

    waiting_promo_input.discard(ADMIN_ID)

    await call.message.edit_text(

        "🎟 <b>Управление промокодами</b>\n\nВыберите нужное действие:",

        parse_mode="HTML",

        reply_markup=promo_admin_kb()

    )

 

 

@promo_router.callback_query(F.data == "p_create")

async def cb_p_create(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        return

    waiting_promo_input.add(ADMIN_ID)

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="p_back")]])

    await call.message.edit_text(

        "➕ <b>Создание нового промокода</b>\n\n"

        "Отправьте следующим сообщением 3 значения через пробел:\n"

        "<code>НАЗВАНИЕ ЭНЕРГИЯ КОЛИЧЕСТВО</code>\n\n"

        "<i>Пример:</i> <code>RAMEN777 150 30</code>",

        parse_mode="HTML",

        reply_markup=kb

    )

 

 

@promo_router.message(F.from_user.id == ADMIN_ID, lambda m: m.from_user.id in waiting_promo_input)

async def process_p_create(message: types.Message):

    waiting_promo_input.discard(ADMIN_ID)

    parts = (message.text or "").split()

    if len(parts) != 3:

        return await message.reply(

            "❌ Нужно ввести ровно 3 значения через пробел.\nПример: <code>RAMEN777 150 30</code>",

            parse_mode="HTML",

            reply_markup=promo_admin_kb()

        )

 

    raw_code, reward_str, uses_str = parts

    if not reward_str.isdigit() or not uses_str.isdigit():

        return await message.reply(

            "❌ Энергия и количество активаций должны быть числами без плюсов.\nПример: <code>RAMEN777 150 30</code>",

            parse_mode="HTML",

            reply_markup=promo_admin_kb()

        )

 

    code = raw_code.strip().upper()

    reward = int(reward_str)

    uses = int(uses_str)

 

    cur.execute("INSERT OR REPLACE INTO promocodes (code, reward, uses_left) VALUES (?, ?, ?)", (code, reward, uses))

    db.commit()

 

    await message.reply(

        f"✅ <b>Промокод создан!</b>\n\n"

        f"🎟 Код: <code>{code}</code>\n"

        f"⚡ Награда: <b>+{reward}⚡</b>\n"

        f"👥 Активаций: <b>{uses} шт.</b>",

        parse_mode="HTML",

        reply_markup=promo_admin_kb()

    )

 

 

@promo_router.callback_query(F.data == "p_list")

async def cb_p_list(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:

        return

    cur.execute("SELECT code, reward, uses_left FROM promocodes WHERE uses_left > 0")

    rows = cur.fetchall()

    if not rows:

        return await call.answer("Активных промокодов сейчас нет!", show_alert=True)

 

    text = "📋 <b>Активные промокоды:</b>\n\n"

    for code, reward, uses in rows:

        text += f"∙ <code>{code}</code> — <b>+{reward}⚡</b> (осталось {uses} шт.)\n"

 

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="p_back")]])

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

 

 

# --- АКТИВАЦИЯ ПРОМОКОДА ИГРОКАМИ (/promo КОД) ---

@promo_router.message(Command("promo"))

async def cmd_use_promo(message: types.Message):

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2:

        return await message.reply("🎟 <b>Как активировать промокод:</b>\nНапиши <code>/promo ТВОЙ_КОД</code>", parse_mode="HTML")

 

    _, raw_code = parts

    code = raw_code.strip().upper()

    uid = message.from_user.id

 

    cur.execute("SELECT reward, uses_left FROM promocodes WHERE code = ?", (code,))

    promo = cur.fetchone()

    if not promo:

        return await message.reply("❌ Такого промокода не существует или он уже закончился!")

 

    reward, uses_left = promo

    if uses_left <= 0:

        return await message.reply("😢 Все активации этого промокода уже разобрали!")

 

    cur.execute("SELECT 1 FROM promo_used WHERE user_id = ? AND code = ?", (uid, code))

    if cur.fetchone():

        return await message.reply("⚠️ Ты уже активировал этот промокод ранее!")

 

    cur.execute("SELECT energy FROM users WHERE user_id = ?", (uid,))

    user_row = cur.fetchone()

    if not user_row:

        return await message.reply("Сначала запусти бота командой /start!")

 

    (current_energy,) = user_row

    new_energy = current_energy + reward

 

    cur.execute("UPDATE users SET energy = ? WHERE user_id = ?", (new_energy, uid))

    cur.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))

    cur.execute("INSERT INTO promo_used (user_id, code) VALUES (?, ?)", (uid, code))

    db.commit()

 

    await message.reply(

        f"🎉 <b>Промокод {code} активирован!</b>\n"

        f"Тебе начислено <b>+{reward}⚡</b>!\n"

        f"Проверить шкалу героя: /card",

        parse_mode="HTML"

        )
