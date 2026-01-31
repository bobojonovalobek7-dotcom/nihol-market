import asyncio
import sqlite3
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton, Message, ReplyKeyboardMarkup, 
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ================= 1. SOZLAMALAR =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAGvOLyfs3t3nK2eGdkzxy1Qb_6A--xhieA")
ADMIN_IDS = [356009218, 5341602920, 5777142647]
DB_FILE = "resume_bot_final.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ================= 2. MATNLAR =================
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Assalomu alaykum!</b>\nAnketani to'ldirishni boshlang.",
        'welcome_admin': "👑 <b>Admin Panel</b>",
        'btn_fill': "📄 Rezyume to'ldirish",
        'btn_restart': "🔄 Qayta ishga tushirish",
        'btn_cancel': "❌ Bekor qilish",
        'btn_view': "📂 Rezyumelar (20)",
        'btn_stats': "📊 Statistika",
        'q1':"1. F.I.O kiriting:", 
        'q2':"2. Tug'ilgan sana (kun.oy.yil):", 
        'q3':"3. Yosh:", 
        'q4':"4. Jins:",
        'q5':"5. Oilaviy holat:", 
        'q6':"6. Manzil:", 
        'q7':"7. Telefon raqamingizni yuboring:", 
        'q8':"8. Oldingi ish joyingiz:",
        'q9':"9. Tajriba (yil/oy):", 
        'q10':"10. Qaysi lavozimga topshiryapsiz?", 
        'q11':"11. Rasmingizni yuboring:", 
        'q12':"12. Qiziqishlar:",
        'q13':"13. Bilimlar (Til, Kompyuter):", 
        'q14':"14. Maqsad:", 
        'q15':"15. Kafil (Kim tavsiya qildi?):",
        'done': "✅ Sizning anketangiz qabul qilindi! Tez orada aloqaga chiqamiz.", 
        'cancel': "⚠️ Bekor qilindi.",
        'err_txt': "⚠️ Matn yozing!", 
        'err_num': "⚠️ Iltimos, raqam kiriting!",
        
        # ADMIN UCHUN SHABLON
        'admin_tpl': (
            "🔔 <b>YANGI REZYUME!</b>\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "👤 <b>{link}</b>\n"
            "📅 <b>Yosh:</b> {age}\n"
            "🚻 <b>Jins:</b> {gender}\n"
            "💍 <b>Oila:</b> {family}\n"
            "📞 <b>Tel:</b> {phone}\n"
            "📍 <b>Manzil:</b> {address}\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "💼 <b>Lavozim:</b> {pos}\n"
            "📝 <b>Tajriba:</b> {exp}\n"
            "🏢 <b>Eski ish:</b> {prev}\n"
            "⚽ <b>Qiziqishlar:</b> {hobby}\n"
            "💻 <b>Bilimlar:</b> {skills}\n"
            "🎯 <b>Maqsad:</b> {purpose}\n"
            "🤝 <b>Kafil:</b> {guarantor}\n"
            "📊 <b>Ball:</b> {score}\n"
            "🕒 <b>Vaqt:</b> {time}"
        )
    }
}

# ================= 3. DATABASE (ASINXRON) =================
async def db_exec(query, params=(), fetchone=False, fetchall=False, commit=False):
    def _run():
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute(query, params)
                if commit: conn.commit()
                if fetchone: return cursor.fetchone()
                if fetchall: return cursor.fetchall()
                return None
        except Exception as e:
            logging.error(f"DB Error: {e}")
            return None
    return await asyncio.to_thread(_run)

async def setup_db():
    # Adminlar jadvali
    await db_exec("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)", commit=True)
    for admin_id in ADMIN_IDS:
        await db_exec("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,), commit=True)

    # Foydalanuvchilar jadvali
    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)", commit=True)
    
    # Rezyumelar jadvali
    await db_exec("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, birth TEXT, age INTEGER, gender TEXT, family TEXT,
        address TEXT, phone TEXT, prev TEXT, exp TEXT, pos TEXT, photo TEXT, hobby TEXT,
        skills TEXT, purpose TEXT, guarantor TEXT, score INTEGER, date TEXT)""", commit=True)

    # Vakansiyalar jadvali
    await db_exec("CREATE TABLE IF NOT EXISTS vacancies (title TEXT PRIMARY KEY)", commit=True)
    for v in ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]:
        await db_exec("INSERT OR IGNORE INTO vacancies (title) VALUES (?)", (v,), commit=True)

# ================= 4. KLAVIATURALAR =================
def kb_user(in_process=False):
    b = ReplyKeyboardBuilder()
    if in_process:
        b.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    else:
        b.add(KeyboardButton(text=TEXTS['uz']['btn_fill'])).add(KeyboardButton(text=TEXTS['uz']['btn_restart']))
        b.adjust(1)
    return b.as_markup(resize_keyboard=True)

def kb_admin():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=TEXTS['uz']['btn_view']), KeyboardButton(text=TEXTS['uz']['btn_stats']))
    b.row(KeyboardButton(text=TEXTS['uz']['btn_restart']))
    return b.as_markup(resize_keyboard=True)

# ================= 5. STATES (TO'LIQ) =================
class Form(StatesGroup):
    name = State()
    birth = State()
    age = State()
    gender = State()
    family = State()
    address = State()
    phone = State()
    prev = State()
    exp = State()
    pos = State()
    photo = State()
    hobby = State()
    skills = State()
    purpose = State()
    guarantor = State()

# ================= 6. LOGIKA =================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

@dp.message(CommandStart())
@dp.message(F.text.in_([TEXTS['uz']['btn_restart']]))
async def start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    await db_exec("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,), commit=True)
    
    kb = kb_admin() if uid in ADMIN_IDS else kb_user()
    txt = TEXTS['uz']['welcome_admin'] if uid in ADMIN_IDS else TEXTS['uz']['welcome']
    await m.answer(txt, reply_markup=kb)

# --- ADMIN PANEL ---
@dp.message(F.text == TEXTS['uz']['btn_stats'])
async def stats(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    rc = (await db_exec("SELECT COUNT(*) FROM resumes", fetchone=True))[0]
    uc = (await db_exec("SELECT COUNT(*) FROM users", fetchone=True))[0]
    await m.answer(f"📊 <b>Statistika:</b>\n👥 Userlar: {uc}\n📄 Rezyumelar: {rc}")

@dp.message(F.text == TEXTS['uz']['btn_view'])
async def view_resumes(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    res = await db_exec("SELECT id, name, pos FROM resumes ORDER BY id DESC LIMIT 20", fetchall=True)
    if not res: return await m.answer("📭 Hozircha rezyumelar yo'q")
    
    kb = ReplyKeyboardBuilder()
    for r in res: kb.add(KeyboardButton(text=f"{r[1]} | {r[2]}"))
    kb.adjust(1)
    await m.answer("📂 So'nggi 20 ta:", reply_markup=kb.as_markup(resize_keyboard=True))

# --- REZYUME TO'LDIRISH ---
@dp.message(F.text == TEXTS['uz']['btn_cancel'])
async def quit_proc(m: Message, state: FSMContext):
    await state.clear()
    kb = kb_admin() if m.from_user.id in ADMIN_IDS else kb_user()
    await m.answer(TEXTS['uz']['cancel'], reply_markup=kb)

@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_form(m: Message, state: FSMContext):
    await state.set_state(Form.name)
    await m.answer(TEXTS['uz']['q1'], reply_markup=kb_user(True))

@dp.message(Form.name)
async def p_name(m: Message, s: FSMContext):
    await s.update_data(name=m.text)
    await s.set_state(Form.birth)
    await m.answer(TEXTS['uz']['q2'])

@dp.message(Form.birth)
async def p_birth(m: Message, s: FSMContext):
    await s.update_data(birth=m.text)
    await s.set_state(Form.age)
    await m.answer(TEXTS['uz']['q3'])

@dp.message(Form.age)
async def p_age(m: Message, s: FSMContext):
    if not m.text.isdigit(): 
        return await m.answer(TEXTS['uz']['err_num'])
    await s.update_data(age=m.text)
    await s.set_state(Form.gender)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol"))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q4'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.gender)
async def p_gender(m: Message, s: FSMContext):
    await s.update_data(gender=m.text)
    await s.set_state(Form.family)
    await m.answer(TEXTS['uz']['q5'], reply_markup=kb_user(True))

@dp.message(Form.family)
async def p_family(m: Message, s: FSMContext):
    await s.update_data(family=m.text)
    await s.set_state(Form.address)
    await m.answer(TEXTS['uz']['q6'])

@dp.message(Form.address)
async def p_addr(m: Message, s: FSMContext):
    await s.update_data(address=m.text)
    await s.set_state(Form.phone)
    # INDENTATION FIXED HERE
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q7'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.phone, F.contact | F.text)
async def p_phone(m: Message, s: FSMContext):
    phone = m.contact.phone_number if m.contact else m.text
    await s.update_data(phone=phone)
    await s.set_state(Form.prev)
    await m.answer(TEXTS['uz']['q8'], reply_markup=kb_user(True))

@dp.message(Form.prev)
async def p_prev(m: Message, s: FSMContext):
    await s.update_data(prev=m.text)
    await s.set_state(Form.exp)
    await m.answer(TEXTS['uz']['q9'])

@dp.message(Form.exp)
async def p_exp(m: Message, s: FSMContext):
    await s.update_data(exp=m.text)
    await s.set_state(Form.pos)
    # INDENTATION FIXED HERE
    vacs = await db_exec("SELECT title FROM vacancies", fetchall=True)
    kb = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs:
            kb.add(KeyboardButton(text=v[0]))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q10'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.pos)
async def p_pos(m: Message, s: FSMContext):
    await s.update_data(pos=m.text)
    await s.set_state(Form.photo)
    await m.answer(TEXTS['uz']['q11'], reply_markup=kb_user(True))

@dp.message(Form.photo, F.photo)
async def p_photo(m: Message, s: FSMContext):
    await s.update_data(photo=m.photo[-1].file_id)
    await s.set_state(Form.hobby)
    await m.answer(TEXTS['uz']['q12'])

@dp.message(Form.hobby)
async def p_hobby(m: Message, s: FSMContext):
    await s.update_data(hobby=m.text)
    await s.set_state(Form.skills)
    await m.answer(TEXTS['uz']['q13'])

@dp.message(Form.skills)
async def p_skills(m: Message, s: FSMContext):
    await s.update_data(skills=m.text)
    await s.set_state(Form.purpose)
    await m.answer(TEXTS['uz']['q14'])

@dp.message(Form.purpose)
async def p_purp(m: Message, s: FSMContext):
    await s.update_data(purpose=m.text)
    await s.set_state(Form.guarantor)
    await m.answer(TEXTS['uz']['q15'])

@dp.message(Form.guarantor)
async def p_guar(m: Message, s: FSMContext):
    await s.update_data(guarantor=m.text)
    d = await s.get_data()
    
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 <b>Ism:</b> {d['name']}\n📞 <b>Tel:</b> {d['phone']}\n💼 <b>Lavozim:</b> {d['pos']}\n\n<i>Ma'lumotlar to'g'rimi?</i>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ HA, TASDIQLASH", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ BEKOR QILISH", callback_data="cancel_final")]
    ])
    
    await m.answer_photo(photo=d['photo'], caption=cap, reply_markup=kb)

# --- FINAL ---
@dp.callback_query(F.data == "cancel_final")
async def cancel_final(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("❌ Anketani bekor qildingiz.", reply_markup=kb_user())
    await state.clear()

@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    await call.answer("Yuborilmoqda...", show_alert=True)
    # Xabarni o'chirish yoki tahrirlash (tugmani olib tashlash)
    await call.message.edit_reply_markup(reply_markup=None)
    
    d = await state.get_data()
    uid = call.from_user.id
    
    # Ball hisoblash (oddiy mantiq)
    score = 50 
    skills_text = str(d.get('skills', '')).lower()
    if 'rus' in skills_text: score += 10
    if 'ingliz' in skills_text: score += 10
    if 'excel' in skills_text or 'word' in skills_text: score += 10
    
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # BAZAGA YOZISH
    try:
        await db_exec("""INSERT INTO resumes (
            user_id, name, birth, age, gender, family, address, phone, prev, exp, 
            pos, photo, hobby, skills, purpose, guarantor, score, date) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
            (uid, d['name'], d['birth'], d['age'], d['gender'], d['family'], d['address'],
             d['phone'], d['prev'], d['exp'], d['pos'], d['photo'], d['hobby'], d['skills'], 
             d['purpose'], d['guarantor'], score, now), commit=True)
        logging.info(f"Yangi rezyume saqlandi: {uid}")
    except Exception as e:
        logging.error(f"Bazaga yozishda xato: {e}")
    
    # ADMINGA YUBORISH
    link = f"<a href='tg://user?id={uid}'>{d['name']}</a>"
    cap = TEXTS['uz']['admin_tpl'].format(
        link=link, age=d['age'], gender=d['gender'], family=d['family'], phone=d['phone'],
        address=d['address'], pos=d['pos'], exp=d['exp'], prev=d['prev'], hobby=d['hobby'],
        skills=d['skills'], purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={uid}")]
    ])

    sent_count = 0
    for adm in ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=adm, photo=d['photo'], caption=cap, reply_markup=btn)
            sent_count += 1
        except Exception as e:
            logging.warning(f"Admin {adm} ga bormadi: {e}")
    
    # USERGA JAVOB
    kb = kb_admin() if uid in ADMIN_IDS else kb_user()
    await call.message.answer(TEXTS['uz']['done'], reply_markup=kb)
    await state.clear()

async def main():
    await setup_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
