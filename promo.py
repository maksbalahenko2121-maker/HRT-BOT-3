import sqlite3

from aiogram import Router, types

from aiogram.filters import Command

 

promo_router = Router()

 

# Подключаемся к той же базе данных

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

 

 

# --- КОМАНДА ДЛЯ ИГРОКОВ: /promo КОД ---

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

        return await message.reply("😢 Увы, все активации этого промокода уже разобрали!")

 

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

        f"Теперь у твоего героя: <b>{new_energy}⚡</b> (проверить в /card).",

        parse_mode="HTML"

    )

 

 

# --- КОМАНДЫ ДЛЯ АДМИНА: СОЗДАНИЕ И СПИСОК ---

# Формат: /addpromo КОД ЭНЕРГИЯ КОЛИЧЕСТВО

# Пример: /addpromo RAMEN2026 150 30

@promo_router.message(Command("addpromo"))

async def cmd_add_promo(message: types.Message):

    from bot import ADMIN_ID

    if message.from_user.id != ADMIN_ID:

        return

 

    parts = (message.text or "").split()

    if len(parts) != 4:

        return await message.reply(

            "🛠 <b>Создание промокода:</b>\n"

            "<code>/addpromo КОД ЭНЕРГИЯ АКТИВАЦИИ</code>\n\n"

            "<i>Пример:</i> <code>/addpromo ANIME777 200 50</code>\n"

            "(создаст код ANIME777 на +200⚡ для первых 50 человек)",

            parse_mode="HTML"

        )

 

    _, raw_code, reward_str, uses_str = parts

    if not reward_str.isdigit() or not uses_str.isdigit():

        return await message.reply("❌ Энергия и количество активаций должны быть числами!")

 

    code = raw_code.strip().upper()

    reward = int(reward_str)

    uses = int(uses_str)

 

    cur.execute("INSERT OR REPLACE INTO promocodes (code, reward, uses_left) VALUES (?, ?, ?)", (code, reward, uses))

    db.commit()

 

    await message.reply(

        f"✅ <b>Промокод создан!</b>\n"

        f"🎟 Код: <code>{code}</code>\n"

        f"⚡ Награда: <b>+{reward}⚡</b>\n"

        f"👥 Осталось активаций: <b>{uses} шт.</b>",

        parse_mode="HTML"

    )

 

 

@promo_router.message(Command("promolist"))

async def cmd_promo_list(message: types.Message):

    from bot import ADMIN_ID

    if message.from_user.id != ADMIN_ID:

        return

 

    cur.execute("SELECT code, reward, uses_left FROM promocodes WHERE uses_left > 0")

    rows = cur.fetchall()

    if not rows:

        return await message.reply("📭 Активных промокодов сейчас нет.")

 

    text = "🎟 <b>Активные промокоды:</b>\n\n"

    for code, reward, uses in rows:

        text += f"∙ <code>{code}</code> — <b>+{reward}⚡</b> (осталось {uses} шт.)\n"

    await message.reply(text, parse_mode="HTML")

