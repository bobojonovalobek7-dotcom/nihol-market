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
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ================= CONFIG (SOZLAMALAR) =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAGvOLyfs3t3nK2eGdkzxy1Qb_6A--xhieA")
ADMIN_IDS = [356009218, 5341602920, 5777142647]  
DB_FILE = "resume_bot_final.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

# ================= TEXTS (MATNLAR) =================
TEXTS = {
    'uz': {
        'welcome_user': "👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldirishni boshlang.",
        'welcome_admin': "👑 <b>Admin Panelga xush kelibsiz!</b>",
        'btn_fill': "📄 Rezyume to'ldirish",
        'btn_restart': "🔄 Qayta ishga tushirish",
        'btn_start': "🚀 Boshlash",
        'btn_quit': "❌ Bekor qilish",
        
        # Savollar
        'ask_name': "1. <b>F.I.O</b> to'liq kiriting:\n<i>Masalan: Bobojonov Alobek</i>",
        'ask_birth': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):\n<i>Masalan: 25.10.1998</i>",
        'ask_age': "3. <b>Yoshingiz</b> (faqat raqamda):\n<i>Masalan: 26</i>",
        'ask_gender': "4. <b>Jinsingizni tanlang:</b>",
        'ask_family': "5. <b>Oilaviy holatingiz:</b>\n<i>Masalan: Turmushga chiqqan, Bo'ydoq</i>",
        'ask_address': "6. <b>Manzilingizni kiriting:</b>\n<i>Masalan: Urganch shahri, Al-Xorazmiy 12</i>",
        'ask_phone': "7. <b>📞 Telefon raqamingizni yuboring:</b>",
        'ask_prev_job': "8. <b>Oldingi ish joyingiz:</b>\n<i>Masalan: 'Nihol' marketi yoki 'Yo'q'</i>",
        'ask_exp': "9. <b>Ish tajribangiz:</b>\n<i>Masalan: 2 yil sotuvchi</i>",
        'ask_position': "10. <b>Qaysi lavozimda ishlamoqchisiz?</b>",
        'ask_photo': "11. <b>🖼 Rasm (3x4) yuboring:</b>",
        'ask_interests': "12. <b>Shaxsiy qiziqishlaringiz:</b>\n<i>Masalan: Sport, Kitob</i>",
        'ask_skills': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili, Excel</i>",
        'ask_purpose': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Rivojlanish va daromad</i>",
        'ask_guarantor': "15. <b>Kafil (Ismi, Telefoni):</b>\n<i>Masalan: Akam Vali, +998901234567</i>",
        
        'resume_accepted': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'resume_cancelled': "⚠️ <b>Amaliyot bekor qilindi.</b>",
        'err_type': "⚠️ <b>Iltimos, matn ko'rinishida yozing!</b>",
        'err_age': "⚠️ <b>Xato!</b> Faqat raqam kiriting (Masalan: 25):",
        
        # --- ADMIN UCHUN TO'LIQ FORMAT (RASMDAGIDEK) ---
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

# ================= DATABASE =================
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
            logging.error(f"DB Error: {e}")
            return None
    return await asyncio.to_thread(_run)

async def setup_database():
    logging.info("Baza sozlanmoqda...")
    await db_execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT)", commit=True)
    for admin_id in ADMIN_IDS:
        await db_execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (admin_id,), commit=True)

    await db_execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)", commit=True)
    
    await db_execute("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, birth_date TEXT, 
        age INTEGER, gender TEXT, family_status TEXT, address TEXT, phone_number TEXT, previous_job TEXT, 
        experience TEXT, position TEXT, photo_id TEXT, interests TEXT, skills TEXT, 
        purpose TEXT, guarantor TEXT, score INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""", commit=True)

    await db_execute("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)", commit=True)
    
    # Vakansiyalar
    existing_vacs = await db_execute("SELECT count(*) FROM vacancies", fetchone=True)
    if existing_vacs and existing_vacs[0] == 0:
        default_vacancies = ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]
        for vac in default_vacancies:
            await db_execute("INSERT INTO vacancies (title) VALUES (?)", (vac,), commit=True)
            
    logging.info("Baza tayyor!")

# ================= KEYBOARDS =================
def get_user_kb(in_process=False):
    builder = ReplyKeyboardBuilder()
    if in_process:
        builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    else:
        builder.add(KeyboardButton(text=TEXTS['uz']['btn_fill']))
        builder.add(KeyboardButton(text=TEXTS['uz']['btn_restart'])) 
        builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📂 Rezyumelar"), KeyboardButton(text="📊 Statistika"))
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_restart'])) 
    return builder.as_markup(resize_keyboard=True)

# ================= STATES =================
class ResumeFSM(StatesGroup):
    full_name = State(); birth_date = State(); age = State(); gender = State(); family_status = State(); address = State()
    phone_number = State(); previous_job = State(); experience = State(); position = State(); photo = State()
    interests = State(); skills = State(); purpose = State(); guarantor = State()

# ================= HANDLERS =================
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
    user_id = message.from_user.id
    
    # Bazaga yozamiz (Adminga xabar BORMAYDI)
    await db_execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
                     (user_id, message.from_user.username, message.from_user.first_name), commit=True)
    
    if user_id in ADMIN_IDS:
        await message.answer(TEXTS['uz']['welcome_admin'], reply_markup=get_admin_kb())
    else:
        await message.answer(TEXTS['uz']['welcome_user'], reply_markup=get_user_kb())

# --- ADMIN PANEL ---
@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    r_c = (await db_execute("SELECT COUNT(*) FROM resumes", fetchone=True))[0]
    u_c = (await db_execute("SELECT COUNT(*) FROM users", fetchone=True))[0]
    await message.answer(f"📊 <b>Statistika:</b>\n👥 Userlar: {u_c}\n📄 Rezyumelar: {r_c}")

@dp.message(F.text == "📂 Rezyumelar")
async def admin_view_resumes(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    resumes = await db_execute("SELECT id, full_name, position FROM resumes ORDER BY id DESC LIMIT 20", fetchall=True)
    if not resumes: return await message.answer("📭 Bo'sh")
    
    kb = InlineKeyboardBuilder()
    for res in resumes:
        kb.add(InlineKeyboardButton(text=f"{res[1]} | {res[2]}", callback_data=f"view_{res[0]}"))
    kb.adjust(1)
    await message.answer("📂 So'nggi 20 ta rezyume:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("view_"))
async def view_detail(call: CallbackQuery):
    rid = call.data.split("_")[1]
    d = await db_execute("SELECT * FROM resumes WHERE id = ?", (rid,), fetchone=True)
    if d:
        link_name = f"<a href='tg://user?id={d[1]}'>{d[2]}</a>"
        cap = TEXTS['uz']['admin_full_notification'].format(
            link_name=link_name, age=d[4], gender=d[5], family=d[6], address=d[7], phone=d[8],
            prev_job=d[9], exp=d[10], pos=d[11], hobby=d[13], skills=d[14], purpose=d[15], guarantor=d[16], score=d[17], time=d[18]
        )
        chat_btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={d[1]}")]])
        try: await call.message.answer_photo(d[12], caption=cap, reply_markup=chat_btn)
        except: await call.message.answer(cap, reply_markup=chat_btn)
    await call.answer()

# --- REZYUME TO'LDIRISH ---
@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_h(message: Message, state: FSMContext):
    await state.clear()
    kb = get_admin_kb() if message.from_user.id in ADMIN_IDS else get_user_kb()
    await message.answer("⚠️ Bekor qilindi", reply_markup=kb)

@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_resume(message: Message, state: FSMContext):
    await state.set_state(ResumeFSM.full_name)
    await message.answer(TEXTS['uz']['ask_name'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeFSM.birth_date)
    await message.answer(TEXTS['uz']['ask_birth'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(birth_date=message.text)
    await state.set_state(ResumeFSM.age)
    await message.answer(TEXTS['uz']['ask_age'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        return await message.answer(TEXTS['uz']['err_age'], reply_markup=get_user_kb(True))
    await state.update_data(age=int(message.text))
    await state.set_state(ResumeFSM.gender)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol"))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_gender'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.gender)
async def s4(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(gender=message.text)
    await state.set_state(ResumeFSM.family_status)
    await message.answer(TEXTS['uz']['ask_family'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.family_status)
async def s4_new(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(family_status=message.text)
    await state.set_state(ResumeFSM.address)
    await message.answer(TEXTS['uz']['ask_address'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.address)
async def s5(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(address=message.text)
    await state.set_state(ResumeFSM.phone_number)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_phone'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.phone_number, F.contact | F.text)
async def s6(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    if not phone: return await message.answer("Iltimos, telefon raqam yuboring!")
    await state.update_data(phone=phone)
    await state.set_state(ResumeFSM.previous_job)
    await message.answer(TEXTS['uz']['ask_prev_job'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.previous_job)
async def s7(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(prev_job=message.text)
    await state.set_state(ResumeFSM.experience)
    await message.answer(TEXTS['uz']['ask_exp'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.experience)
async def s8(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(exp=message.text)
    await state.set_state(ResumeFSM.position)
    vacs = await db_execute("SELECT title FROM vacancies", fetchall=True)
    kb = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs: kb.add(KeyboardButton(text=v[0]))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_position'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.position)
async def s9(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(pos=message.text)
    await state.set_state(ResumeFSM.photo)
    await message.answer(TEXTS['uz']['ask_photo'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.photo, F.photo)
async def s10(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(ResumeFSM.interests)
    await message.answer(TEXTS['uz']['ask_interests'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.interests)
async def s11(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(interests=message.text)
    await state.set_state(ResumeFSM.skills)
    await message.answer(TEXTS['uz']['ask_skills'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.skills)
async def s12(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(skills=message.text)
    await state.set_state(ResumeFSM.purpose)
    await message.answer(TEXTS['uz']['ask_purpose'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.purpose)
async def s13(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(purpose=message.text)
    await state.set_state(ResumeFSM.guarantor)
    await message.answer(TEXTS['uz']['ask_guarantor'], reply_markup=get_user_kb(True))

@dp.message(ResumeFSM.guarantor)
async def s14(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(guarantor=message.text)
    d = await state.get_data()
    # Nomzodning o'ziga qisqa ko'rsatamiz
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {d['full_name']}\n📞 {d['phone']}\n💼 {d['pos']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="conf_final")]])
    await message.answer_photo(d['photo'], caption=cap, reply_markup=kb)

# --- FINAL (ADMIN GA TO'LIQ FORMATDA BORADI) ---
@dp.callback_query(F.data == "conf_final")
async def confirm(call: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    user_id = call.from_user.id
    
    score = 50
    if any(x in str(d.get('skills', '')).lower() for x in ['rus', 'excel']): score += 20
    now = datetime.now().strftime("%H:%M | %d.%m.%Y")
    
    await db_execute("""INSERT INTO resumes (
        user_id, full_name, birth_date, age, gender, family_status, address, phone_number, previous_job, experience, 
        position, photo_id, interests, skills, purpose, guarantor, score) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
        (user_id, d['full_name'], d['birth_date'], d['age'], d['gender'], d['family_status'], d['address'],
         d['phone'], d['prev_job'], d['exp'], d['pos'], d['photo'], d['interests'], d['skills'], 
         d['purpose'], d['guarantor'], score), commit=True)
    
    # --- ADMIN UCHUN MAXSUS XABAR (To'liq ochilgan va silka bilan) ---
    
    # Ismga silka qo'yamiz (tg://user?id=123...)
    link_name = f"<a href='tg://user?id={user_id}'>{d['full_name']}</a>"
    
    # Katta formatdagi tekst
    admin_caption = TEXTS['uz']['admin_full_notification'].format(
        link_name=link_name, # Link
        age=d['age'], gender=d['gender'], family=d['family_status'], phone=d['phone'], address=d['address'],
        pos=d['pos'], exp=d['exp'], prev_job=d['prev_job'], hobby=d['interests'], skills=d['skills'],
        purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    
    # "Nomzodga yozish" tugmasi
    chat_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={user_id}")]
    ])

    # Adminlarga yuborish
    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, "CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, d['photo'], caption=admin_caption, reply_markup=chat_btn)
        except Exception as e:
            logging.error(f"Failed to send to admin {adm}: {e}")
    
    await call.message.delete()
    kb = get_admin_kb() if user_id in ADMIN_IDS else get_user_kb()
    await call.message.answer("🎉 " + TEXTS['uz']['resume_accepted'], reply_markup=kb)
    await state.clear()

async def main():
    await setup_database()
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
