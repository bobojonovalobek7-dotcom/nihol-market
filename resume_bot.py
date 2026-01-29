import asyncio
import sqlite3
import logging
import os
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

# ================= SOZLAMALAR =================
# Serverda BOT_TOKEN ni Environment Variable qilib berish tavsiya etiladi, yoki shu yerga yozing
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAGvOLyfs3t3nK2eGdkzxy1Qb_6A--xhieA")
ADMIN_IDS = [356009218, 5341602920]  # Super Adminlar
DB_FILE = "resume_bot_final.db"

# ================= TEXTS (MATNLAR) =================
TEXTS = {
    'uz': {
        'welcome_user': "👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldirishni boshlang.",
        'welcome_admin': "👑 <b>Admin Panelga xush kelibsiz!</b>\nQuyidagi menyu orqali boshqaring:",
        'btn_fill': "📄 Rezyume to'ldirish",
        'btn_restart_user': "🔄 Qayta ishga tushirish",
        'btn_start': "🚀 Boshidan boshlash",
        'btn_quit': "❌ Bekor qilish",
        # Admin tugmalari
        'btn_view_resumes': "📂 Rezyumelar (Ro'yxat)",
        'btn_stats': "📊 Statistika",
        # Savollar
        'ask_name': "1. <b>F.I.O</b> to'liq kiriting:\n<i>Masalan: Bobojonov Alobek</i>",
        'ask_birth': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):\n<i>Masalan: 25.10.1998</i>",
        'ask_age': "3. <b>Yoshingiz</b> (faqat raqamda):\n<i>Masalan: 26</i>",
        'ask_gender': "4. <b>Jinsingizni tanlang:</b>",
        'ask_address': "5. <b>Manzilingizni kiriting:</b>\n<i>Masalan: Urganch shahri, Al-Xorazmiy ko'chasi 12-uy</i>",
        'ask_location': "6. <b>📍 Lokatsiyangizni yuboring:</b> (Pastdagi tugmani bosing)",
        'ask_phone': "7. <b>📞 Telefon raqamingizni yuboring:</b>",
        'ask_prev_job': "8. <b>Oldingi ish joyingiz:</b>\n<i>Masalan: 'Nihol' marketi yoki 'Yo'q'</i>",
        'ask_exp': "9. <b>Ish tajribangiz:</b>\n<i>Masalan: 2 yil sotuvchi bo'lib ishlaganman</i>",
        'ask_position': "10. <b>Lavozimni tanlang:</b>",
        'ask_photo': "11. <b>🖼 Rasm (3x4) yuboring:</b>",
        'ask_hobby': "12. <b>Qiziqishlaringiz (hobbi):</b>\n<i>Masalan: Kitob o'qish, Futbol</i>",
        'ask_skills': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili (a'lo), Excel</i>",
        'ask_purpose': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Jamoaga foyda keltirish va rivojlanish</i>",
        'ask_guarantor': "15. <b>Kafil (Ism, Tel):</b>\n<i>Masalan: Alimov Vali, +998901234567</i>",
        'resume_accepted': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'resume_cancelled': "⚠️ <b>Amaliyot bekor qilindi.</b>",
        'err_age': "⚠️ <b>Xato!</b> Iltimos, yoshingizni faqat raqamda kiriting (Masalan: 25):",
        # Admin xabarnomasi (Yangi User)
        'new_user_alert': "👤 <b>Yangi foydalanuvchi qo'shildi!</b>\n\n🆔 ID: <code>{id}</code>\n🔗 Username: @{user}\nIsmi: {name}",
        # Admin xabarnomasi (Yangi Rezyume)
        'new_resume_admin': (
            "🔔 <b>DIQQAT: YANGI NOMZOD QO'SHILDI!</b> 🔔\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Nomzod:</b> <code>{name}</code>\n"
            "📞 <b>Tel:</b> <code>{phone}</code>\n"
            "💼 <b>Lavozim:</b> <code>{pos}</code>\n"
            "📊 <b>Ball:</b> 🔥 <b>{score} ball</b> 🔥\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🕒 <b>Vaqt:</b> <i>{time}</i>\n"
            "📥 <i>Ma'lumotlar bazaga saqlandi.</i>"
        )
    }
}

# ================= DATABASE (BAZA) =================
def db_query(query, params=(), commit=False, fetchall=False, fetchone=False):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit: conn.commit()
            if fetchall: return cursor.fetchall()
            if fetchone: return cursor.fetchone()
    except Exception as e:
        logging.error(f"Database Error: {e}")
        return None

def setup_database():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # 1. Adminlar jadvali
            cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT)")
            # Adminlarni bittalab qo'shamiz (Serverdagi xatolikni oldini olish uchun)
            for admin_id in ADMIN_IDS:
                cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (admin_id,))
            
            # 2. Foydalanuvchilar
            cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)")
            
            # 3. Rezyumelar
            cursor.execute("""CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, birth_date TEXT, 
                age INTEGER, gender TEXT, address TEXT, latitude REAL, longitude REAL, phone_number TEXT, 
                previous_job TEXT, experience TEXT, position TEXT, photo_id TEXT, hobby TEXT, skills TEXT, 
                purpose TEXT, guarantor TEXT, score INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
            
            # 4. Vakansiyalar
            cursor.execute("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
            
            conn.commit()
    except Exception as e:
        logging.critical(f"Baza yaratishda xatolik: {e}")

# ================= KEYBOARDS (MENYULAR) =================
# Oddiy foydalanuvchi menyusi
def get_user_kb(in_process=False):
    builder = ReplyKeyboardBuilder()
    if in_process:
        builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    else:
        builder.add(KeyboardButton(text=TEXTS['uz']['btn_fill']))
        builder.add(KeyboardButton(text=TEXTS['uz']['btn_restart_user'])) 
        builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# ADMIN menyusi (YANGILANDI: Qayta ishga tushirish qo'shildi)
def get_admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_view_resumes']), KeyboardButton(text=TEXTS['uz']['btn_stats']))
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_restart_user'])) # <-- Admin uchun ham qo'shildi
    return builder.as_markup(resize_keyboard=True)

# ================= STATES =================
class ResumeFSM(StatesGroup):
    full_name = State(); birth_date = State(); age = State(); gender = State(); address = State()
    location = State(); phone_number = State(); previous_job = State(); experience = State()
    position = State(); photo = State(); hobby = State(); skills = State(); purpose = State(); guarantor = State()

# ================= HANDLERS =================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# --- START (YANGI FOYDALANUVCHINI ANIQLASH) ---
@dp.message(CommandStart())
@dp.message(F.text == TEXTS['uz']['btn_start'])
@dp.message(F.text == TEXTS['uz']['btn_restart_user'])
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "NoUsername"
    full_name = message.from_user.first_name
    
    # 1. Foydalanuvchi avval bormi, tekshiramiz?
    user_exist = db_query("SELECT user_id FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    # 2. Agar YO'Q bo'lsa -> Bazaga qo'shamiz va Adminga xabar beramiz
    if not user_exist:
        db_query("INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
                 (user_id, username, full_name), commit=True)
        
        # Yangi foydalanuvchi haqida Adminlarga xabar
        alert_msg = TEXTS['uz']['new_user_alert'].format(id=user_id, user=username, name=full_name)
        for adm in ADMIN_IDS:
            try:
                await bot.send_message(adm, alert_msg)
            except: pass
    
    # 3. Menyularni ajratish
    if user_id in ADMIN_IDS:
        await message.answer(TEXTS['uz']['welcome_admin'], reply_markup=get_admin_kb())
    else:
        await message.answer(TEXTS['uz']['welcome_user'], reply_markup=get_user_kb())

# --- ADMIN PANEL FUNKSIYALARI ---
@dp.message(F.text == TEXTS['uz']['btn_stats'])
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    
    res_count = db_query("SELECT COUNT(*) FROM resumes", fetchone=True)
    usr_count = db_query("SELECT COUNT(*) FROM users", fetchone=True)
    
    r_c = res_count[0] if res_count else 0
    u_c = usr_count[0] if usr_count else 0
    
    await message.answer(f"📊 <b>STATISTIKA</b>\n\n👥 Jami foydalanuvchilar: {u_c}\n📄 Topshirilgan rezyumelar: {r_c}")

@dp.message(F.text == TEXTS['uz']['btn_view_resumes'])
async def admin_view_resumes(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    
    resumes = db_query("SELECT id, full_name, position FROM resumes ORDER BY id DESC LIMIT 10", fetchall=True)
    
    if not resumes:
        await message.answer("📭 Hozircha rezyumelar yo'q.")
        return
    
    kb = InlineKeyboardBuilder()
    for res in resumes:
        kb.add(InlineKeyboardButton(text=f"{res[1]} | {res[2]}", callback_data=f"view_{res[0]}"))
    kb.adjust(1)
    await message.answer("📂 <b>So'nggi 10 ta rezyume:</b>", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("view_"))
async def view_resume_detail(call: CallbackQuery):
    resume_id = call.data.split("_")[1]
    data = db_query("SELECT * FROM resumes WHERE id = ?", (resume_id,), fetchone=True)
    
    if data:
        caption = (
            f"👤 <b>NOMZOD:</b> {data[2]}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Yosh:</b> {data[4]}  |  <b>Jins:</b> {data[5]}\n"
            f"🎂 <b>Tug'ilgan sana:</b> {data[3]}\n"
            f"📍 <b>Manzil:</b> {data[6]}\n"
            f"📞 <b>Tel:</b> {data[9]}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 <b>Lavozim:</b> {data[12]}\n"
            f"📝 <b>Tajriba:</b> {data[11]}\n"
            f"🏢 <b>Oldingi ish:</b> {data[10]}\n"
            f"💻 <b>Bilimlari:</b> {data[15]}\n"
            f"🎨 <b>Hobbi:</b> {data[14]}\n"
            f"🎯 <b>Maqsad:</b> {data[16]}\n"
            f"🤝 <b>Kafil:</b> {data[17]}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Ball:</b> {data[18]}\n"
            f"🕒 <b>Vaqt:</b> {data[19]}"
        )
        try: await call.message.answer_photo(photo=data[13], caption=caption)
        except: await call.message.answer(caption)
    await call.answer()

# --- REZYUME TO'LDIRISH JARAYONI ---
@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_handler(message: Message, state: FSMContext):
    await state.clear()
    kb = get_admin_kb() if message.from_user.id in ADMIN_IDS else get_user_kb()
    await message.answer("⚠️ " + TEXTS['uz']['resume_cancelled'], reply_markup=kb)

@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_resume(message: Message, state: FSMContext):
    await state.set_state(ResumeFSM.full_name)
    await message.answer(TEXTS['uz']['ask_name'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text); await state.set_state(ResumeFSM.birth_date)
    await message.answer(TEXTS['uz']['ask_birth'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    await state.update_data(birth_date=message.text); await state.set_state(ResumeFSM.age)
    await message.answer(TEXTS['uz']['ask_age'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer(TEXTS['uz']['err_age'], reply_markup=get_user_kb(in_process=True))
    await state.update_data(age=int(message.text)); await state.set_state(ResumeFSM.gender)
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol"))
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_gender'], reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.gender)
async def s4(message: Message, state: FSMContext):
    await state.update_data(gender=message.text); await state.set_state(ResumeFSM.address)
    await message.answer(TEXTS['uz']['ask_address'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.address)
async def s5(message: Message, state: FSMContext):
    await state.update_data(address=message.text); await state.set_state(ResumeFSM.location)
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📍 Lokatsiya", request_location=True))
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_location'], reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.location, F.location)
async def s6(message: Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude); await state.set_state(ResumeFSM.phone_number)
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_phone'], reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.phone_number, F.contact | F.text)
async def s7(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone); await state.set_state(ResumeFSM.previous_job)
    await message.answer(TEXTS['uz']['ask_prev_job'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.previous_job)
async def s8(message: Message, state: FSMContext):
    await state.update_data(prev_job=message.text); await state.set_state(ResumeFSM.experience)
    await message.answer(TEXTS['uz']['ask_exp'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.experience)
async def s9(message: Message, state: FSMContext):
    await state.update_data(exp=message.text); await state.set_state(ResumeFSM.position)
    vacs = db_query("SELECT title FROM vacancies", fetchall=True)
    builder = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs: builder.add(KeyboardButton(text=v[0]))
    else:
        builder.add(KeyboardButton(text="Sotuvchi"), KeyboardButton(text="Kassir"))
    builder.adjust(2)
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_position'], reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.position)
async def s10(message: Message, state: FSMContext):
    await state.update_data(pos=message.text); await state.set_state(ResumeFSM.photo)
    await message.answer(TEXTS['uz']['ask_photo'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.photo, F.photo)
async def s11(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id); await state.set_state(ResumeFSM.hobby)
    await message.answer(TEXTS['uz']['ask_hobby'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.hobby)
async def s12(message: Message, state: FSMContext):
    await state.update_data(hobby=message.text); await state.set_state(ResumeFSM.skills)
    await message.answer(TEXTS['uz']['ask_skills'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.skills)
async def s13(message: Message, state: FSMContext):
    await state.update_data(skills=message.text); await state.set_state(ResumeFSM.purpose)
    await message.answer(TEXTS['uz']['ask_purpose'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.purpose)
async def s14(message: Message, state: FSMContext):
    await state.update_data(purpose=message.text); await state.set_state(ResumeFSM.guarantor)
    await message.answer(TEXTS['uz']['ask_guarantor'], reply_markup=get_user_kb(in_process=True))

@dp.message(ResumeFSM.guarantor)
async def s15(message: Message, state: FSMContext):
    await state.update_data(guarantor=message.text)
    data = await state.get_data()
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {data['full_name']}\n📞 {data['phone']}\n💼 {data['pos']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="conf_final")]])
    await message.answer_photo(data['photo'], caption=cap, reply_markup=kb)

# --- TASDIQLASH VA ADMINNI XABARDOR QILISH ---
@dp.callback_query(F.data == "conf_final")
async def process_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = 50 
    if any(w in str(data.get('skills', '')).lower() for w in ["rus", "excel"]): score += 20
    now = datetime.now().strftime("%H:%M | %d.%m.%Y")
    
    db_query("""INSERT INTO resumes 
             (user_id, full_name, birth_date, age, gender, address, latitude, longitude,
              phone_number, previous_job, experience, position, photo_id, hobby, skills, purpose, guarantor, score)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
             (call.from_user.id, data['full_name'], data['birth_date'], data['age'], data['gender'], data['address'],
              data.get('lat', 0), data.get('lon', 0), data['phone'], data['prev_job'], data['exp'], 
              data['pos'], data['photo'], data['hobby'], data['skills'], data['purpose'], data['guarantor'], score), commit=True)

    msg = TEXTS['uz']['new_resume_admin'].format(name=data['full_name'], phone=data['phone'], pos=data['pos'], score=score, time=now)

    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, sticker="CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, photo=data['photo'], caption=msg)
        except: pass

    await call.message.delete()
    # Foydalanuvchi Admin bo'lsa -> Admin menyu, bo'lmasa -> User menyu qaytaramiz
    kb = get_admin_kb() if call.from_user.id in ADMIN_IDS else get_user_kb()
    await call.message.answer("🎉 " + TEXTS['uz']['resume_accepted'], reply_markup=kb)
    await state.clear()

async def main():
    setup_database()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
