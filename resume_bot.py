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

# ================= 1. SOZLAMALAR (CONFIG) =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAGvOLyfs3t3nK2eGdkzxy1Qb_6A--xhieA")
ADMIN_IDS = [356009218, 5341602920, 5777142647]
DB_FILE = "resume_bot_final.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ================= 2. MATNLAR =================
TEXTS = {
    'uz': {
        'welcome_user': "👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldirishni boshlang.",
        'welcome_admin': "👑 <b>Admin Panelga xush kelibsiz!</b>\nBoshqaruv menyusi:",
        'btn_fill': "📄 Rezyume to'ldirish",
        'btn_restart': "🔄 Qayta ishga tushirish",
        'btn_start': "🚀 Boshlash",
        'btn_quit': "❌ Bekor qilish",
        'btn_view': "📂 Rezyumelar (20)",
        'btn_stats': "📊 Statistika",
        
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
        'q15': "15. <b>Kafil (Ismi, Telefoni):</b>\n<i>Masalan: Akam Vali, +998901234567</i>",
        
        'resume_accepted': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'resume_cancelled': "⚠️ <b>Amaliyot bekor qilindi.</b>",
        'err_type': "⚠️ <b>Iltimos, matn ko'rinishida yozing!</b>",
        'err_age': "⚠️ <b>Xato!</b> Faqat raqam kiriting (Masalan: 25):",
        
        # ADMIN UCHUN TAYYOR SHABLON
        'admin_full_notification': (
            "🔔 <b>YANGI REZYUME QABUL QILINDI!</b>\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "👤 <b>{link_name}</b>\n"
            "📅 <b>Yosh:</b> {age}\n"
            "🚻 <b>Jins:</b> {gender}\n"
            "💍 <b>Oila:</b> {family}\n"
            "📞 <b>Tel:</b> {phone}\n"
            "📍 <b>Manzil:</b> {address}\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "💼 <b>Lavozim:</b> {pos}\n"
            "📝 <b>Tajriba:</b> {exp}\n"
            "🏢 <b>Eski ish:</b> {prev_job}\n"
            "⚽ <b>Qiziqishlar:</b> {hobby}\n"
            "💻 <b>Bilimlar:</b> {skills}\n"
            "🎯 <b>Maqsad:</b> {purpose}\n"
            "🤝 <b>Kafil:</b> {guarantor}\n"
            "📊 <b>Ball:</b> {score}\n"
            "🕒 <b>Topshirildi:</b> {time}"
        )
    }
}

# ================= 3. DATABASE ENGINE (ASINXRON & OPTIMAL) =================
async def db_execute(query, params=(), fetchone=False, fetchall=False, commit=False):
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
        except sqlite3.Error as e:
            logging.error(f"DB Error: {e} | Query: {query}")
            return None
    return await asyncio.to_thread(_run)

async def setup_database():
    logging.info("Baza tekshirilmoqda...")
    await db_execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT)", commit=True)
    for admin_id in ADMIN_IDS:
        await db_execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (admin_id,), commit=True)

    await db_execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)", commit=True)
    
    await db_execute("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, birth_date TEXT, 
        age INTEGER, gender TEXT, address TEXT, phone_number TEXT, previous_job TEXT, 
        experience TEXT, position TEXT, photo_id TEXT, interests TEXT, skills TEXT, 
        purpose TEXT, guarantor TEXT, score INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""", commit=True)

    # --- MIGRATION (Eski bazada ustun yo'q bo'lsa qo'shamiz) ---
    try:
        await db_execute("ALTER TABLE resumes ADD COLUMN family_status TEXT DEFAULT 'Kiritilmagan'", commit=True)
        logging.info("Migratsiya: 'family_status' ustuni qo'shildi.")
    except:
        pass # Ustun bor bo'lsa indamaymiz

    await db_execute("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)", commit=True)
    
    existing = await db_execute("SELECT count(*) FROM vacancies", fetchone=True)
    if existing and existing[0] == 0:
        default_vacancies = ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]
        for vac in default_vacancies:
            await db_execute("INSERT INTO vacancies (title) VALUES (?)", (vac,), commit=True)
            
    logging.info("Baza tayyor!")

# ================= 4. KLAVIATURALAR =================
def get_user_kb(in_process=False):
    b = ReplyKeyboardBuilder()
    if in_process:
        b.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    else:
        b.add(KeyboardButton(text=TEXTS['uz']['btn_fill']))
        b.add(KeyboardButton(text=TEXTS['uz']['btn_restart'])) 
        b.adjust(1)
    return b.as_markup(resize_keyboard=True)

def get_admin_kb():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=TEXTS['uz']['btn_view']), KeyboardButton(text=TEXTS['uz']['btn_stats']))
    b.row(KeyboardButton(text=TEXTS['uz']['btn_restart'])) 
    return b.as_markup(resize_keyboard=True)

# ================= 5. STATES =================
class ResumeFSM(StatesGroup):
    full_name=s(); birth=s(); age=s(); gender=s(); family=s(); address=s(); phone=s(); prev_job=s(); exp=s()
    position=s(); photo=s(); interests=s(); skills=s(); purpose=s(); guarantor=s()

# ================= 6. BOT LOGIKASI =================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

async def validate_text(message: Message):
    if not message.text:
        await message.answer(TEXTS['uz']['err_type'])
        return False
    return True

# --- START ---
@dp.message(CommandStart())
@dp.message(F.text == TEXTS['uz']['btn_start'])
@dp.message(F.text == TEXTS['uz']['btn_restart'])
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await db_execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)", 
                     (uid, message.from_user.username, message.from_user.first_name), commit=True)
    
    kb = get_admin_kb() if uid in ADMIN_IDS else get_user_kb()
    txt = TEXTS['uz']['welcome_admin'] if uid in ADMIN_IDS else TEXTS['uz']['welcome_user']
    await message.answer(txt, reply_markup=kb)

# --- ADMIN PANEL ---
@dp.message(F.text == TEXTS['uz']['btn_stats'])
async def stats(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    r_c = (await db_execute("SELECT COUNT(*) FROM resumes", fetchone=True))[0]
    u_c = (await db_execute("SELECT COUNT(*) FROM users", fetchone=True))[0]
    await m.answer(f"📊 <b>Statistika:</b>\n👥 Userlar: {u_c}\n📄 Rezyumelar: {r_c}")

@dp.message(F.text == TEXTS['uz']['btn_view'])
async def view_resumes(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    res = await db_execute("SELECT id, full_name, position FROM resumes ORDER BY id DESC LIMIT 20", fetchall=True)
    if not res: return await m.answer("📭 Bo'sh")
    
    kb = InlineKeyboardBuilder()
    for r in res: kb.add(InlineKeyboardButton(text=f"{r[1]} | {r[2]}", callback_data=f"view_{r[0]}"))
    kb.adjust(1)
    await m.answer("📂 So'nggi 20 ta:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("view_"))
async def view_detail(call: CallbackQuery):
    rid = call.data.split("_")[1]
    d = await db_execute("SELECT * FROM resumes WHERE id=?", (rid,), fetchone=True)
    if d:
        try:
            link = f"<a href='tg://user?id={d[1]}'>{d[2]}</a>"
            cap = TEXTS['uz']['admin_full_notification'].format(
                link_name=link, age=d[4], gender=d[5], family=d[6], address=d[7], phone=d[8],
                prev_job=d[9], exp=d[10], pos=d[11], hobby=d[13], skills=d[14], purpose=d[15],
                guarantor=d[16], score=d[17], time=d[18]
            )
            btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Yozish", url=f"tg://user?id={d[1]}")]])
            await call.message.answer_photo(d[12], caption=cap, reply_markup=btn)
        except: await call.message.answer("Eski formatdagi ma'lumot.")
    await call.answer()

# --- REZYUME TO'LDIRISH ---
@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_h(m: Message, state: FSMContext):
    await state.clear()
    kb = get_admin_kb() if m.from_user.id in ADMIN_IDS else get_user_kb()
    await m.answer(TEXTS['uz']['resume_cancelled'], reply_markup=kb)

@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_form(m: Message, state: FSMContext):
    await state.set_state(ResumeFSM.full_name)
    await m.answer(TEXTS['uz']['q1'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.full_name)
async def p_name(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(full_name=m.text); await state.set_state(ResumeFSM.birth_date)
    await m.answer(TEXTS['uz']['q2'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.birth_date)
async def p_birth(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(birth_date=m.text); await state.set_state(ResumeFSM.age)
    await m.answer(TEXTS['uz']['q3'])

@dp.message(ResumeFSM.age)
async def p_age(m: Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer(TEXTS['uz']['err_age'])
    await state.update_data(age=m.text); await state.set_state(ResumeFSM.gender)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol"))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q4'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.gender)
async def p_gender(m: Message, state: FSMContext):
    if m.text not in ["Erkak", "Ayol"]: return await m.answer(TEXTS['uz']['err_txt'])
    await state.update_data(gender=m.text); await state.set_state(ResumeFSM.family_status)
    await m.answer(TEXTS['uz']['q5'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.family_status)
async def p_family(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(family_status=m.text); await state.set_state(ResumeFSM.address)
    await m.answer(TEXTS['uz']['q6'])

@dp.message(ResumeFSM.address)
async def p_addr(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(address=m.text); await state.set_state(ResumeFSM.phone_number)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q7'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.phone_number, F.contact | F.text)
async def p_phone(m: Message, state: FSMContext):
    phone = m.contact.phone_number if m.contact else m.text
    if not phone: return await m.answer("Tel raqam yozing!")
    await state.update_data(phone=phone); await state.set_state(ResumeFSM.previous_job)
    await m.answer(TEXTS['uz']['q8'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.previous_job)
async def p_prev(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(prev_job=m.text); await state.set_state(ResumeFSM.experience)
    await m.answer(TEXTS['uz']['q9'])

@dp.message(ResumeFSM.experience)
async def p_exp(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(exp=m.text); await state.set_state(ResumeFSM.position)
    vacs = await db_execute("SELECT title FROM vacancies", fetchall=True)
    kb = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs: kb.add(KeyboardButton(text=v[0]))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q10'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.position)
async def p_pos(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(pos=m.text); await state.set_state(ResumeFSM.photo)
    await m.answer(TEXTS['uz']['q11'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.photo, F.photo)
async def p_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id); await state.set_state(ResumeFSM.interests)
    await m.answer(TEXTS['uz']['q12'])

@dp.message(ResumeFSM.interests)
async def p_hobby(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(interests=m.text); await state.set_state(ResumeFSM.skills)
    await m.answer(TEXTS['uz']['q13'])

@dp.message(ResumeFSM.skills)
async def p_skills(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(skills=m.text); await state.set_state(ResumeFSM.purpose)
    await m.answer(TEXTS['uz']['q14'])

@dp.message(ResumeFSM.purpose)
async def p_purp(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(purpose=m.text); await state.set_state(ResumeFSM.guarantor)
    await m.answer(TEXTS['uz']['q15'])

@dp.message(ResumeFSM.guarantor)
async def p_guar(m: Message, state: FSMContext):
    if not await validate_text(m): return
    await state.update_data(guarantor=m.text)
    d = await state.get_data()
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {d['full_name']}\n📞 {d['phone']}\n💼 {d['pos']}\n💍 {d['family_status']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await m.answer_photo(d['photo'], caption=cap, reply_markup=kb)

# --- FINAL (TASDIQLASH VA ADMINLARGA JO'NATISH) ---
@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    # Foydalanuvchiga jarayon boshlanganini bildiramiz
    await call.answer("Yuborilmoqda, iltimos kuting...", show_alert=True)
    await call.message.delete()
    
    d = await state.get_data()
    uid = call.from_user.id
    
    score = 50
    if any(x in str(d.get('skills', '')).lower() for x in ['rus', 'excel']): score += 20
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # BAZAGA YOZISH
    await db_execute("""INSERT INTO resumes (
        user_id, full_name, birth_date, age, gender, family_status, address, phone_number, previous_job, experience, 
        position, photo_id, interests, skills, purpose, guarantor, score, created_at) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
        (uid, d['full_name'], d['birth_date'], d['age'], d['gender'], d['family_status'], d['address'],
         d['phone'], d['prev_job'], d['exp'], d['pos'], d['photo'], d['interests'], d['skills'], 
         d['purpose'], d['guarantor'], score, now), commit=True)
    
    # 15 SONIYA KUTISH
    logging.info("15 soniya kutish boshlandi...")
    await asyncio.sleep(15)
    logging.info("Kutish yakunlandi, adminlarga yuborilmoqda.")
    
    # ADMINGA YUBORISH
    link = f"<a href='tg://user?id={uid}'>{d['full_name']}</a>"
    cap = TEXTS['uz']['admin_full_notification'].format(
        link_name=link, age=d['age'], gender=d['gender'], family=d['family_status'], 
        phone=d['phone'], address=d['address'], pos=d['pos'], exp=d['exp'], 
        prev_job=d['prev_job'], hobby=d['interests'], skills=d['skills'],
        purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={uid}")]])

    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, "CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, d['photo'], caption=cap, reply_markup=btn)
        except Exception as e:
            logging.warning(f"Admin {adm} ga bormadi: {e}")
    
    # Userga yakuniy javob
    kb = get_admin_kb() if uid in ADMIN_IDS else get_user_kb()
    await call.message.answer(TEXTS['uz']['done'], reply_markup=kb)
    await state.clear()

async def main():
    await setup_database()
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot, skip_updates=True) # Bot o'chib yonganda eski xabarlarni o'qimasligi uchun

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
