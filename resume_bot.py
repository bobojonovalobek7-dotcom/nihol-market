import asyncio
import sqlite3
import logging
import re
import os
import sys
import time
from datetime import datetime

# --- RENDER UCHUN MUHIM QISM (BUNI ALBATTA QO'SHISH KERAK) ---
from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot ishlab turibdi! (Render uchun)")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render PORTni o'zi beradi, agar bermasa 8080 ni oladi
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"==> Veb server {port}-portda ishga tushdi! <==")
# -------------------------------------------------------------

# Word uchun
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    CallbackQuery
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ---------------------------------------------------------
# SOZLAMALAR
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8593426346:AAG9mRz-mYs79vTalBK-twGcQFTu7JbGAFo")
SUPER_ADMIN_ID = 5341602920 
DB_FILE = "resume_bot_final.db"
TIMEOUT_SECONDS = 300 

# --- MIDDLEWARE (Vaqt nazorati) ---
class TimeoutMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_activity = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if user_id:
            current_time = time.time()
            if user_id in self.last_activity:
                elapsed = current_time - self.last_activity[user_id]
                state: FSMContext = data.get('state')
                if state:
                    current_state = await state.get_state()
                    if elapsed > TIMEOUT_SECONDS and current_state is not None:
                        await state.clear()
                        self.last_activity[user_id] = current_time
                        msg_text = "⚠️ <b>Vaqt tugadi.</b>\nIltimos, /start ni bosing."
                        try:
                            if isinstance(event, Message):
                                await event.answer(msg_text)
                            elif isinstance(event, CallbackQuery):
                                await event.message.answer(msg_text)
                        except: pass
                        return
            self.last_activity[user_id] = current_time
        return await handler(event, data)

# --- MA'LUMOTLAR BAZASI ---
def setup_database():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT DEFAULT 'admin', added_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (SUPER_ADMIN_ID,))
        cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, language TEXT DEFAULT 'uz')")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                birth_date TEXT,
                age INTEGER,
                gender TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL,
                phone_number TEXT,
                previous_job TEXT,
                experience TEXT,
                position TEXT,
                photo_id TEXT,
                hobby TEXT,
                skills TEXT,
                purpose TEXT,
                guarantor TEXT,
                status TEXT DEFAULT 'pending',
                score INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )""")
        cursor.execute("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '')")
        cursor.execute("SELECT count(*) FROM vacancies")
        if cursor.fetchone()[0] == 0:
            default_jobs = [("Sotuvchi", ""), ("Kassir", ""), ("Oshpaz", ""), ("Gruzchik", "")]
            cursor.executemany("INSERT INTO vacancies (title, description) VALUES (?, ?)", default_jobs)
        conn.commit()

# --- YORDAMCHI FUNKSIYALAR ---
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit(); return
        if fetchone: return cursor.fetchone()
        if fetchall: return cursor.fetchall()

def is_admin(user_id):
    res = db_query("SELECT user_id FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
    return res is not None

def calculate_score(age, experience_text, skills_text):
    score = 0
    try:
        if 18 <= int(age) <= 35: score += 20
        elif int(age) < 18: score += 5
        else: score += 10
    except: pass
    try:
        nums = re.findall(r'\d+', str(experience_text))
        if nums and int(nums[0]) >= 1: score += 20
    except: pass
    keywords = ["sotuv", "kassir", "oshpaz", "gruzchik", "rus", "ingliz", "word", "excel"]
    if skills_text:
        count = sum(1 for word in keywords if word in str(skills_text).lower())
        score += (count * 5)
    return score

def generate_word_file(admin_id):
    filename = f"resumes_{admin_id}_{int(time.time())}.docx"
    doc = Document()
    doc.add_heading('Nomzodlar Ro\'yxati', 0).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    resumes = db_query("SELECT * FROM resumes ORDER BY created_at DESC", fetchall=True)
    if not resumes:
        doc.add_paragraph("Ma'lumot yo'q.")
        doc.save(filename)
        return filename

    for r in resumes:
        try:
            r_id = r[0]
            full_name = r[2]
            phone = r[9] if len(r) > 9 else "Yo'q"
            position = r[12] if len(r) > 12 else "Yo'q"
            age = r[4] if len(r) > 4 else "0"
            exp = r[11] if len(r) > 11 else "Yo'q"
            skills = r[14] if len(r) > 14 else "Yo'q"
            score = r[19] if len(r) > 19 else 0
            created_at = r[20] if len(r) > 20 else ""

            p = doc.add_paragraph()
            runner = p.add_run(f"ID: {r_id} | {full_name} ({score} ball)")
            runner.bold = True
            runner.font.size = Pt(14)

            details = (
                f"Lavozim: {position}\n"
                f"Tel: {phone}\n"
                f"Yosh: {age}\n"
                f"Tajriba: {exp}\n"
                f"Ko'nikmalar: {skills}\n"
                f"Sana: {created_at}\n"
                "---------------------------------------------------"
            )
            doc.add_paragraph(details)
        except Exception as e:
            doc.add_paragraph(f"Xatolik (ID {r[0]}): {e}")

    doc.save(filename)
    return filename

# --- TEXTS ---
TEXTS = {
    'uz': {
        'admin_panel': "⚙️ <b>Admin panel</b>\nQuyidagi bo'limlardan birini tanlang:",
        'view_resumes': "📂 Rezyumelarni ko'rish",
        'download_word': "📥 Word yuklash",
        'manage_vacancies': "💼 Vakansiyalar",
        'fill_resume': "📄 Rezyume to'ldirish",
        'ask_name': "1. <b>F.I.O</b> to'liq kiriting:",
        'ask_birth': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):",
        'ask_age': "3. <b>Yoshingiz</b> (raqam):",
        'ask_gender': "4. <b>Jinsingiz:</b>",
        'ask_address': "5. <b>Manzilingiz:</b>",
        'ask_location': "6. <b>Lokatsiya</b> yuboring:",
        'ask_phone': "7. <b>Telefon raqam:</b>",
        'ask_prev_job': "8. <b>Oldingi ish joyi:</b>",
        'ask_exp': "9. <b>Tajribangiz:</b>",
        'ask_position': "10. <b>Lavozimni tanlang:</b>",
        'ask_photo': "11. <b>Rasm</b> (3x4) yuboring:",
        'ask_hobby': "12. <b>Hobbi:</b>",
        'ask_skills': "13. <b>Til va Kompyuter bilimlari:</b>",
        'ask_purpose': "14. <b>Maqsad:</b>",
        'ask_guarantor': "15. <b>Kafil</b> (FIO, Tel):",
        'err_age': "❗️ Faqat raqam kiriting!",
        'err_phone': "❗️ Noto'g'ri raqam!",
        'vacancies_title': "💼 <b>Vakansiyalar bo'limi</b>\n\nYangi vakansiya qo'shish uchun shunchaki nomini yozing (masalan: Menejer).\nO'chirish uchun: /del_vac ID\n\n<b>Mavjud vakansiyalar:</b>",
        'vac_added': "✅ Vakansiya qo'shildi: ",
        'no_resumes': "📭 Yangi rezyumelar yo'q.",
        'super_admin_help': "👨‍💻 <b>Super Admin Buyruqlari:</b>\n\n/add_admin ID - Admin qo'shish\n/del_admin ID - Adminni o'chirish\n/admins - Ro'yxat"
    },
    'ru': {
        'admin_panel': "⚙️ Админ панель",
        'view_resumes': "📂 Смотреть резюме",
        'download_word': "📥 Скачать Word",
        'manage_vacancies': "💼 Вакансии",
        'fill_resume': "📄 Заполнить резюме",
        'ask_position': "10. <b>Выберите должность:</b>",
        'vacancies_title': "💼 <b>Вакансии</b>\n\nНапишите название, чтобы добавить.\nУдалить: /del_vac ID\n\nСписок:",
        'vac_added': "✅ Вакансия добавлена: ",
        'no_resumes': "📭 Нет новых резюме.",
        'super_admin_help': "👨‍💻 <b>Super Admin:</b>\n/add_admin ID\n/del_admin ID\n/admins"
    }
}

def get_text(key, lang='uz'):
    return TEXTS.get(lang, TEXTS['uz']).get(key, key)

async def get_state_lang(user_id):
    res = db_query("SELECT language FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return res[0] if res else 'uz'

# --- SETUP ---
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

dp.message.middleware(TimeoutMiddleware())
dp.callback_query.middleware(TimeoutMiddleware())

# --- STATES ---
class ResumeFSM(StatesGroup):
    full_name = State()
    birth_date = State()
    age = State()
    gender = State()
    address = State()
    location = State()
    phone_number = State()
    previous_job = State()
    experience = State()
    position = State()
    photo = State()
    hobby = State()
    skills = State()
    purpose = State()
    guarantor = State()

class AdminFSM(StatesGroup):
    add_vacancy = State()

# --- HANDLERS ---
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    db_query("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username), commit=True)
    
    if is_admin(user_id):
        db_query("UPDATE users SET language='uz' WHERE user_id=?", (user_id,), commit=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")]])
    await message.answer("Assalomu alaykum! Tilni tanlang / Выберите язык:", reply_markup=kb)

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    db_query("UPDATE users SET language = ? WHERE user_id = ?", (lang, callback.from_user.id), commit=True)
    user_id = callback.from_user.id

    if is_admin(user_id):
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=get_text('view_resumes', lang)), KeyboardButton(text=get_text('download_word', lang))],
            [KeyboardButton(text=get_text('manage_vacancies', lang))]
        ], resize_keyboard=True)
        await callback.message.delete()
        await callback.message.answer(get_text('admin_panel', lang), reply_markup=kb)
        if user_id == SUPER_ADMIN_ID:
            await callback.message.answer(get_text('super_admin_help', lang))
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=get_text('fill_resume', lang))]], resize_keyboard=True)
        await callback.message.delete()
        await callback.message.answer("✅", reply_markup=kb)

# ================= SUPER ADMIN COMMANDS =================
@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    if message.from_user.id != SUPER_ADMIN_ID: return
    if not command.args: return await message.answer("ID kiriting. Masalan: /add_admin 12345678")
    try:
        new_id = int(command.args)
        db_query("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,), commit=True)
        await message.answer(f"✅ Admin qo'shildi: {new_id}")
    except: await message.answer("Xatolik.")

@dp.message(Command("del_admin"))
async def cmd_del_admin(message: Message, command: CommandObject):
    if message.from_user.id != SUPER_ADMIN_ID: return
    if not command.args: return await message.answer("ID kiriting.")
    try:
        target_id = int(command.args)
        if target_id == SUPER_ADMIN_ID: return await message.answer("O'zingizni o'chira olmaysiz.")
        db_query("DELETE FROM admins WHERE user_id=?", (target_id,), commit=True)
        await message.answer(f"❌ Admin o'chirildi: {target_id}")
    except: await message.answer("Xatolik.")

@dp.message(Command("admins"))
async def cmd_list_admins(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    admins = db_query("SELECT user_id, role FROM admins", fetchall=True)
    text = "📋 <b>Adminlar:</b>\n" + "\n".join([f"- {a[0]} ({a[1]})" for a in admins])
    await message.answer(text)

# ================= VAKANSIYA BOSHQARUVI (All Admins) =================
@dp.message(F.text.in_([TEXTS['uz']['manage_vacancies'], TEXTS['ru']['manage_vacancies']]))
async def admin_vacancies(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    lang = await get_state_lang(message.from_user.id)
    vacs = db_query("SELECT id, title FROM vacancies", fetchall=True)
    vac_list = "\n".join([f"🆔 <b>{v[0]}</b>. {v[1]}" for v in vacs]) if vacs else "(Bo'sh)"
    await state.set_state(AdminFSM.add_vacancy)
    await message.answer(f"{get_text('vacancies_title', lang)}\n\n{vac_list}", reply_markup=ReplyKeyboardRemove())

@dp.message(AdminFSM.add_vacancy)
async def add_vacancy_handler(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        if message.text.startswith("/del_vac"):
            try:
                vid = int(message.text.split()[1])
                db_query("DELETE FROM vacancies WHERE id=?", (vid,), commit=True)
                await message.answer("❌ O'chirildi.")
            except: await message.answer("Xato ID.")
        return 
    db_query("INSERT INTO vacancies (title, description) VALUES (?, '')", (message.text,), commit=True)
    lang = await get_state_lang(message.from_user.id)
    kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=get_text('view_resumes', lang)), KeyboardButton(text=get_text('download_word', lang))],
            [KeyboardButton(text=get_text('manage_vacancies', lang))]
        ], resize_keyboard=True)
    await message.answer(f"{get_text('vac_added', lang)}{message.text}", reply_markup=kb)
    await state.clear()

# ================= ADMIN FUNKSIYALARI =================
@dp.message(F.text.in_([TEXTS['uz']['download_word'], TEXTS['ru']['download_word']]))
async def admin_download_word(message: Message):
    if not is_admin(message.from_user.id): return
    m = await message.answer("⏳ Tayyorlanmoqda...")
    try:
        path = generate_word_file(message.from_user.id)
        file = FSInputFile(path)
        await message.answer_document(file, caption="📂 Rezyumelar")
        os.remove(path)
        await m.delete()
    except Exception as e:
        await m.edit_text(f"Xatolik: {e}")

@dp.message(F.text.in_([TEXTS['uz']['view_resumes'], TEXTS['ru']['view_resumes']]))
async def admin_view_resumes_list(message: Message):
    if not is_admin(message.from_user.id): return
    lang = await get_state_lang(message.from_user.id)
    resumes = db_query("SELECT id, full_name, score FROM resumes WHERE status='pending' ORDER BY created_at DESC", fetchall=True)
    if not resumes: return await message.answer(get_text('no_resumes', lang))
    builder = InlineKeyboardBuilder()
    for r in resumes:
        builder.button(text=f"{r[1]} ({r[2]} ball)", callback_data=f"show_res_{r[0]}")
    builder.adjust(1)
    await message.answer("Nomzodlardan birini tanlang:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("show_res_"))
async def admin_show_resume(call: types.CallbackQuery):
    res_id = call.data.split("_")[2]
    r = db_query("SELECT * FROM resumes WHERE id=?", (res_id,), fetchone=True)
    if not r: return await call.answer("Topilmadi", show_alert=True)
    caption = (f"👤 <b>{r[2]}</b>\n📞 {r[9]}\n💼 {r[12]}\n📊 Ball: {r[19]}\n📍 {r[6]}\n🗓 Yosh: {r[4]}\n🛠 {r[15]}")
    if r[7] and r[8]: caption += f"\n<a href='https://maps.google.com/maps?q={r[7]},{r[8]}'>📍 Lokatsiya</a>"
    await call.message.answer_photo(photo=r[13], caption=caption)
    await call.answer()

# ================= USER FLOW =================
@dp.message(F.text.in_([TEXTS['uz']['fill_resume'], TEXTS['ru']['fill_resume']]))
async def start_resume(message: Message, state: FSMContext):
    lang = await get_state_lang(message.from_user.id)
    await state.update_data(lang=lang)
    await state.set_state(ResumeFSM.full_name)
    await message.answer(get_text('ask_name', lang), reply_markup=ReplyKeyboardRemove())

@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeFSM.birth_date)
    await message.answer(get_text('ask_birth', data['lang']))

@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(birth_date=message.text)
    await state.set_state(ResumeFSM.age)
    await message.answer(get_text('ask_age', data['lang']))

@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.isdigit(): return await message.answer(get_text('err_age', data['lang']))
    await state.update_data(age=int(message.text))
    await state.set_state(ResumeFSM.gender)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]], resize_keyboard=True)
    await message.answer(get_text('ask_gender', data['lang']), reply_markup=kb)

@dp.message(ResumeFSM.gender)
async def s4(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(gender=message.text)
    await state.set_state(ResumeFSM.address)
    await message.answer(get_text('ask_address', data['lang']), reply_markup=ReplyKeyboardRemove())

@dp.message(ResumeFSM.address)
async def s5(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(address=message.text)
    await state.set_state(ResumeFSM.location)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Lokatsiya", request_location=True)]], resize_keyboard=True)
    await message.answer(get_text('ask_location', data['lang']), reply_markup=kb)

@dp.message(ResumeFSM.location, F.location)
async def s6(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(latitude=message.location.latitude, longitude=message.location.longitude)
    await state.set_state(ResumeFSM.phone_number)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📞 Tel", request_contact=True)]], resize_keyboard=True)
    await message.answer(get_text('ask_phone', data['lang']), reply_markup=kb)

@dp.message(ResumeFSM.phone_number)
async def s7(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number if message.contact else message.text
    if not re.match(r"^\+?[0-9]{9,15}$", phone): return await message.answer(get_text('err_phone', data['lang']))
    await state.update_data(phone_number=phone)
    await state.set_state(ResumeFSM.previous_job)
    await message.answer(get_text('ask_prev_job', data['lang']), reply_markup=ReplyKeyboardRemove())

@dp.message(ResumeFSM.previous_job)
async def s8(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(previous_job=message.text)
    await state.set_state(ResumeFSM.experience)
    await message.answer(get_text('ask_exp', data['lang']))

@dp.message(ResumeFSM.experience)
async def s9(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(experience=message.text)
    await state.set_state(ResumeFSM.position)
    vacs = db_query("SELECT title FROM vacancies", fetchall=True)
    builder = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs:
            builder.add(KeyboardButton(text=v[0]))
        builder.adjust(2)
    await message.answer(get_text('ask_position', data['lang']), reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.position)
async def s10(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(position=message.text)
    await state.set_state(ResumeFSM.photo)
    await message.answer(get_text('ask_photo', data['lang']), reply_markup=ReplyKeyboardRemove())

@dp.message(ResumeFSM.photo, F.photo)
async def s11(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(photo_id=message.photo[-1].file_id)
    await state.set_state(ResumeFSM.hobby)
    await message.answer(get_text('ask_hobby', data['lang']))

@dp.message(ResumeFSM.hobby)
async def s12(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(hobby=message.text)
    await state.set_state(ResumeFSM.skills)
    await message.answer(get_text('ask_skills', data['lang']))

@dp.message(ResumeFSM.skills)
async def s13(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(skills=message.text)
    await state.set_state(ResumeFSM.purpose)
    await message.answer(get_text('ask_purpose', data['lang']))

@dp.message(ResumeFSM.purpose)
async def s14(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(purpose=message.text)
    await state.set_state(ResumeFSM.guarantor)
    await message.answer(get_text('ask_guarantor', data['lang']))

@dp.message(ResumeFSM.guarantor)
async def s15(message: Message, state: FSMContext):
    await state.update_data(guarantor=message.text)
    data = await state.get_data()
    caption = f"📄 <b>MA'LUMOT</b>\n👤 {data['full_name']}\n💼 {data['position']}\n📞 {data['phone_number']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await message.answer_photo(data['photo_id'], caption=caption, reply_markup=kb)

@dp.callback_query(F.data == "confirm")
async def confirm(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = calculate_score(data.get('age', 0), data.get('experience', ''), data.get('skills', ''))
    db_query(
        """INSERT INTO resumes (user_id, full_name, birth_date, age, gender, address, latitude, longitude, phone_number,
                                previous_job, experience, position, photo_id, hobby, skills, purpose, guarantor, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
             (call.from_user.id, data.get('full_name'), data.get('birth_date'), data.get('age'), data.get('gender'), 
              data.get('address'), data.get('latitude'), data.get('longitude'), data.get('phone_number'), 
              data.get('previous_job'), data.get('experience'), data.get('position'), data.get('photo_id'), 
              data.get('hobby'), data.get('skills'), data.get('purpose'), data.get('guarantor'), score), commit=True)
    await call.message.delete()
    await call.message.answer("Qabul qilindi!")
    await state.clear()

async def main():
    setup_database()
    # Loglarni ekranga chiqarish (Render ko'rishi uchun)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # 1. Serverni ishga tushiramiz (Render uchun)
    await start_web_server()
    
    # 2. Botni ishga tushiramiz (Telegram uchun)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
