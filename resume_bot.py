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

# Loglarni to'g'ri sozlash
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ================= 2. MATNLAR =================
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldirishni boshlang.",
        'welcome_admin': "👑 <b>Admin Panel</b>",
        'btn_fill': "📄 Rezyume to'ldirish",
        'btn_restart': "🔄 Qayta ishga tushirish",
        'btn_start': "🚀 Boshlash",
        'btn_quit': "❌ Bekor qilish",
        'btn_view': "📂 Rezyumelar (20)",
        'btn_stats': "📊 Statistika",
        
        # Savollar
        'q1': "1. <b>F.I.O</b> to'liq kiriting:\n<i>Masalan: Bobojonov Alobek</i>",
        'q2': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):\n<i>Masalan: 25.10.1998</i>",
        'q3': "3. <b>Yoshingiz</b> (faqat raqamda):\n<i>Masalan: 26</i>",
        'q4': "4. <b>Jinsingizni tanlang:</b>",
        'q5': "5. <b>Oilaviy holatingiz:</b>\n<i>Masalan: Turmushga chiqqan, Bo'ydoq</i>",
        'q6': "6. <b>Manzilingizni kiriting:</b>\n<i>Masalan: Urganch shahri, Al-Xorazmiy 12</i>",
        'q7': "7. <b>📞 Telefon raqamingizni yuboring:</b>",
        'q8': "8. <b>Oldingi ish joyingiz:</b>\n<i>Masalan: 'Nihol' marketi yoki 'Yo'q'</i>",
        'q9': "9. <b>Ish tajribangiz:</b>\n<i>Masalan: 2 yil sotuvchi</i>",
        'q10': "10. <b>Qaysi lavozimda ishlamoqchisiz?</b>",
        'q11': "11. <b>🖼 Rasm (3x4) yuboring:</b>",
        'q12': "12. <b>Shaxsiy qiziqishlaringiz:</b>\n<i>Masalan: Sport, Kitob</i>",
        'q13': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili, Excel</i>",
        'q14': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Rivojlanish va daromad</i>",
        'q15': "15. <b>Sizga kafil bo'la oladigan odam bormi?</b>\n(Ismi, Telefoni):\n<i>Masalan: Akam Vali, +998901234567</i>",
        
        'done': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'cancel': "⚠️ <b>Bekor qilindi.</b>",
        'err_txt': "⚠️ <b>Iltimos, matn yozing!</b>",
        'err_num': "⚠️ <b>Faqat raqam kiriting!</b>",
        
        # ADMIN UCHUN TAYYOR SHABLON
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

# ================= 3. DATABASE ENGINE (ASINXRON) =================
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
    await db_exec("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT)", commit=True)
    for admin_id in ADMIN_IDS:
        await db_exec("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (admin_id,), commit=True)

    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)", commit=True)
    
    await db_exec("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, birth_date TEXT, 
        age INTEGER, gender TEXT, family_status TEXT, address TEXT, phone_number TEXT, previous_job TEXT, 
        experience TEXT, position TEXT, photo_id TEXT, interests TEXT, skills TEXT, 
        purpose TEXT, guarantor TEXT, score INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""", commit=True)

    # Migratsiya (Eski bazani buzmaslik uchun)
    try: await db_exec("ALTER TABLE resumes ADD COLUMN family_status TEXT DEFAULT 'None'", commit=True)
    except: pass

    await db_exec("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)", commit=True)
    exist = await db_exec("SELECT count(*) FROM vacancies", fetchone=True)
    if exist and exist[0] == 0:
        for v in ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]:
            await db_exec("INSERT INTO vacancies (title) VALUES (?)", (v,), commit=True)

# ================= 4. KLAVIATURALAR =================
def kb_user(in_process=False):
    b = ReplyKeyboardBuilder()
    if in_process:
        b.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    else:
        b.add(KeyboardButton(text=TEXTS['uz']['btn_fill']))
        b.add(KeyboardButton(text=TEXTS['uz']['btn_restart']))
        b.adjust(1)
    return b.as_markup(resize_keyboard=True)

def kb_admin():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=TEXTS['uz']['btn_view']), KeyboardButton(text=TEXTS['uz']['btn_stats']))
    b.row(KeyboardButton(text=TEXTS['uz']['btn_restart']))
    return b.as_markup(resize_keyboard=True)

# ================= 5. STATES =================
class Form(StatesGroup):
    name = State(); birth = State(); age = State(); gender = State(); family = State(); address = State()
    phone = State(); prev = State(); exp = State(); pos = State(); photo = State()
    hobby = State(); skills = State(); purpose = State(); guarantor = State()

# ================= 6. LOGIKA =================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

async def valid_txt(m: Message):
    if not m.text: 
        await m.answer(TEXTS['uz']['err_txt'])
        return False
    return True

@dp.message(CommandStart())
@dp.message(F.text == TEXTS['uz']['btn_start'])
@dp.message(F.text == TEXTS['uz']['btn_restart'])
async def start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    await db_exec("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)", 
                  (uid, m.from_user.username, m.from_user.first_name), commit=True)
    
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
    res = await db_exec("SELECT id, full_name, position FROM resumes ORDER BY id DESC LIMIT 20", fetchall=True)
    if not res: return await m.answer("📭 Bo'sh")
    
    kb = InlineKeyboardBuilder()
    for r in res:
        kb.add(InlineKeyboardButton(text=f"{r[1]} | {r[2]}", callback_data=f"v_{r[0]}"))
    kb.adjust(1)
    await m.answer("📂 So'nggi 20 ta:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("v_"))
async def view_one(call: CallbackQuery):
    rid = call.data.split("_")[1]
    d = await db_exec("SELECT * FROM resumes WHERE id=?", (rid,), fetchone=True)
    if d:
        try:
            # Indexlar o'zgarishi mumkin, shuning uchun ehtiyot bo'lamiz
            # Bazadan o'qish tartibi: id, uid, name, birth, age, gender, family, addr, phone, prev, exp, pos, photo, int, skill, purp, guar, score, date
            link = f"<a href='tg://user?id={d[1]}'>{d[2]}</a>"
            cap = TEXTS['uz']['admin_tpl'].format(
                link=link, age=d[4], gender=d[5], family=d[6], address=d[7], phone=d[8],
                prev=d[9], exp=d[10], pos=d[11], hobby=d[13], skills=d[14], purpose=d[15],
                guarantor=d[16], score=d[17], time=d[18]
            )
            btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Yozish", url=f"tg://user?id={d[1]}")]])
            await call.message.answer_photo(d[12], caption=cap, reply_markup=btn)
        except: await call.message.answer("Eski formatdagi ma'lumot.")
    await call.answer()

# --- FORM ---
@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_proc(m: Message, state: FSMContext):
    await state.clear()
    kb = kb_admin() if m.from_user.id in ADMIN_IDS else kb_user()
    await m.answer(TEXTS['uz']['cancel'], reply_markup=kb)

@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_form(m: Message, state: FSMContext):
    await state.set_state(Form.name)
    await m.answer(TEXTS['uz']['q1'], reply_markup=kb_user(True))

@dp.message(Form.name)
async def s1(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(name=m.text); await state.set_state(Form.birth)
    await m.answer(TEXTS['uz']['q2'], reply_markup=kb_user(True))

@dp.message(Form.birth)
async def s2(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(birth=m.text); await state.set_state(Form.age)
    await m.answer(TEXTS['uz']['q3'], reply_markup=kb_user(True))

@dp.message(Form.age)
async def s3(m: Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer(TEXTS['uz']['err_num'], reply_markup=kb_user(True))
    await state.update_data(age=m.text); await state.set_state(Form.gender)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol"))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await m.answer(TEXTS['uz']['q4'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.gender)
async def s4(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(gender=m.text); await state.set_state(Form.family)
    await m.answer(TEXTS['uz']['q5'], reply_markup=kb_user(True))

@dp.message(Form.family)
async def s5(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(family=m.text); await state.set_state(Form.address)
    await m.answer(TEXTS['uz']['q6'], reply_markup=kb_user(True))

@dp.message(Form.address)
async def s6(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(address=m.text); await state.set_state(Form.phone)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await m.answer(TEXTS['uz']['q7'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.phone, F.contact | F.text)
async def s7(m: Message, state: FSMContext):
    p = m.contact.phone_number if m.contact else m.text
    if not p: return await m.answer("Tel raqam yozing!")
    await state.update_data(phone=p); await state.set_state(Form.prev)
    await m.answer(TEXTS['uz']['q8'], reply_markup=kb_user(True))

@dp.message(Form.prev)
async def s8(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(prev=m.text); await state.set_state(Form.exp)
    await m.answer(TEXTS['uz']['q9'], reply_markup=kb_user(True))

@dp.message(Form.exp)
async def s9(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(exp=m.text); await state.set_state(Form.pos)
    vacs = await db_exec("SELECT title FROM vacancies", fetchall=True)
    kb = ReplyKeyboardBuilder()
    if vacs: 
        for v in vacs: kb.add(KeyboardButton(text=v[0]))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await m.answer(TEXTS['uz']['q10'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.pos)
async def s10(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(pos=m.text); await state.set_state(Form.photo)
    await m.answer(TEXTS['uz']['q11'], reply_markup=kb_user(True))

@dp.message(Form.photo, F.photo)
async def s11(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id); await state.set_state(Form.hobby)
    await m.answer(TEXTS['uz']['q12'], reply_markup=kb_user(True))

@dp.message(Form.hobby)
async def s12(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(hobby=m.text); await state.set_state(Form.skills)
    await m.answer(TEXTS['uz']['q13'], reply_markup=kb_user(True))

@dp.message(Form.skills)
async def s13(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(skills=m.text); await state.set_state(Form.purpose)
    await m.answer(TEXTS['uz']['q14'], reply_markup=kb_user(True))

@dp.message(Form.purpose)
async def s14(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(purpose=m.text); await state.set_state(Form.guarantor)
    await m.answer(TEXTS['uz']['q15'], reply_markup=kb_user(True))

@dp.message(Form.guarantor)
async def s15(m: Message, state: FSMContext):
    if not await valid_txt(m): return
    await state.update_data(guarantor=m.text)
    d = await state.get_data()
    
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {d['name']}\n📞 {d['phone']}\n💼 {d['pos']}\n💍 {d['family']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await m.answer_photo(d['photo'], caption=cap, reply_markup=kb)

# --- FINAL ---
@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    uid = call.from_user.id
    
    score = 50
    if any(x in str(d.get('skills', '')).lower() for x in ['rus', 'excel']): score += 20
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # 1. Bazaga yozish (Async)
    await db_exec("""INSERT INTO resumes (
        user_id, full_name, birth_date, age, gender, family_status, address, phone_number, previous_job, experience, 
        position, photo_id, interests, skills, purpose, guarantor, score) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
        (uid, d['name'], d['birth'], d['age'], d['gender'], d['family'], d['address'],
         d['phone'], d['prev'], d['exp'], d['pos'], d['photo'], d['hobby'], d['skills'], 
         d['purpose'], d['guarantor'], score), commit=True)
    
    # 2. ADMINGA YUBORISH
    link = f"<a href='tg://user?id={uid}'>{d['name']}</a>"
    cap = TEXTS['uz']['admin_tpl'].format(
        link=link, age=d['age'], gender=d['gender'], family=d['family'], 
        phone=d['phone'], address=d['address'], pos=d['pos'], exp=d['exp'], 
        prev=d['prev'], hobby=d['hobby'], skills=d['skills'],
        purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Yozish", url=f"tg://user?id={uid}")]])

    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, "CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, d['photo'], caption=cap, reply_markup=btn)
        except: pass
    
    await call.message.delete()
    kb = kb_admin() if uid in ADMIN_IDS else kb_user()
    await call.message.answer(TEXTS['uz']['done'], reply_markup=kb)
    await state.clear()

async def main():
    await setup_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
