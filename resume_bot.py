import asyncio
import sqlite3
import logging
import re
import os
import sys
import time
from datetime import datetime

# Render va kutubxonalar
from aiohttp import web
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
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, CallbackQuery
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ================= SOZLAMALAR =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8593426346:AAG9mRz-mYs79vTalBK-twGcQFTu7JbGAFo")
# Ikki ta Super Admin ID raqamlari
ADMIN_IDS = [356009218, 5341602920]
DB_FILE = "resume_bot_final.db"
TIMEOUT_SECONDS = 600

# ================= TEXTS =================
TEXTS = {
    'uz': {
        'admin_panel': "⚙️ <b>Admin panelga xush kelibsiz!</b>",
        'view_resumes': "📂 Rezyumelarni ko'rish",
        'download_word': "📥 Word yuklash",
        'manage_vacancies': "💼 Vakansiyalar",
        'fill_resume': "📄 Rezyume to'ldirish",
        'btn_start': "🚀 Qayta boshlash",
        'btn_quit': "❌ Bekor qilish",
        'ask_name': "1. <b>F.I.O</b> to'liq kiriting:\n<i>Masalan: Bobojonov Alobek</i>",
        'ask_birth': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):\n<i>Masalan: 25.10.1998</i>",
        'ask_age': "3. <b>Yoshingiz</b> (faqat raqamda):\n<i>Masalan: 26</i>",
        'ask_gender': "4. <b>Jinsingizni tanlang:</b>",
        'ask_address': "5. <b>Manzilingizni kiriting:</b>\n<i>Masalan: Urganch shahri, Al-Xorazmiy ko'chasi 12-uy</i>",
        'ask_location': "6. <b>Lokatsiyangizni yuboring:</b> (Pastdagi tugmani bosing)",
        'ask_phone': "7. <b>Telefon raqamingiz:</b>\n<i>Masalan: +998952359655</i>",
        'ask_prev_job': "8. <b>Oldingi ish joyingiz:</b>\n<i>Masalan: 'Nihol' marketi yoki 'Yo'q'</i>",
        'ask_exp': "9. <b>Ish tajribangiz:</b>\n<i>Masalan: 2 yil sotuvchi bo'lib ishlaganman</i>",
        'ask_position': "10. <b>Lavozimni tanlang:</b>",
        'ask_photo': "11. <b>Rasm (3x4) yuboring:</b>",
        'ask_hobby': "12. <b>Qiziqishlaringiz (hobbi):</b>\n<i>Masalan: Kitob o'qish, Futbol</i>",
        'ask_skills': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili (a'lo), Excel</i>",
        'ask_purpose': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Jamoaga foyda keltirish va rivojlanish</i>",
        'ask_guarantor': "15. <b>Kafil (Ism, Tel):</b>\n<i>Masalan: Alimov Vali, +998901234567</i>",
        'resume_accepted': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'resume_cancelled': "⚠️ <b>Amaliyot bekor qilindi.</b>",
        'err_age': "❗️ Faqat raqam kiriting!",
        'no_resumes': "📭 Yangi rezyumelar yo'q.",
        'new_resume_admin': "🆕 <b>Yangi rezyume!</b>\n\n👤 Nomzod: {name}\n📞 Tel: {phone}\n💼 Lavozim: {pos}\n📊 Ball: {score}"
    },
    'ru': {
        'admin_panel': "⚙️ <b>Добро пожаловать!</b>",
        'fill_resume': "📄 Заполнить резюме",
        'btn_start': "🚀 Рестарт",
        'btn_quit': "❌ Отмена",
        'resume_accepted': "✅ <b>Принято!</b>",
        'resume_cancelled': "⚠️ <b>Отменено.</b>"
    }
}


def get_text(key, lang='uz'):
    return TEXTS.get(lang, TEXTS['uz']).get(key, key)


# ================= MENYULAR =================
def get_main_menu(lang='uz'):
    kb = [
        [KeyboardButton(text=get_text('fill_resume', lang))],
        [KeyboardButton(text=get_text('btn_start', lang)), KeyboardButton(text=get_text('btn_quit', lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, is_persistent=True)


def get_admin_menu(lang='uz'):
    kb = [
        [KeyboardButton(text=get_text('view_resumes', lang)), KeyboardButton(text=get_text('download_word', lang))],
        [KeyboardButton(text=get_text('manage_vacancies', lang))],
        [KeyboardButton(text=get_text('btn_start', lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ================= DATABASE =================
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit(); return
        if fetchone: return cursor.fetchone()
        if fetchall: return cursor.fetchall()


def setup_database():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, role TEXT DEFAULT 'admin')")
        for admin_id in ADMIN_IDS:
            cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (admin_id,))
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, language TEXT DEFAULT 'uz')")
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS resumes
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           full_name
                           TEXT,
                           birth_date
                           TEXT,
                           age
                           INTEGER,
                           gender
                           TEXT,
                           address
                           TEXT,
                           latitude
                           REAL,
                           longitude
                           REAL,
                           phone_number
                           TEXT,
                           previous_job
                           TEXT,
                           experience
                           TEXT,
                           position
                           TEXT,
                           photo_id
                           TEXT,
                           hobby
                           TEXT,
                           skills
                           TEXT,
                           purpose
                           TEXT,
                           guarantor
                           TEXT,
                           status
                           TEXT
                           DEFAULT
                           'pending',
                           score
                           INTEGER
                           DEFAULT
                           0,
                           created_at
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )""")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL)")
        conn.commit()


def is_admin(user_id):
    res = db_query("SELECT user_id FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
    return res is not None


async def get_state_lang(user_id):
    res = db_query("SELECT language FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return res[0] if res else 'uz'


def calculate_score(age, exp, skills):
    s = 0
    try:
        if 18 <= int(age) <= 35: s += 20
        if any(w in str(skills).lower() for w in ["rus", "ingliz", "excel", "word"]): s += 15
    except:
        pass
    return s


# ================= BOT SETUP =================
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))


class ResumeFSM(StatesGroup):
    full_name = State();
    birth_date = State();
    age = State();
    gender = State();
    address = State()
    location = State();
    phone_number = State();
    previous_job = State();
    experience = State()
    position = State();
    photo = State();
    hobby = State();
    skills = State();
    purpose = State();
    guarantor = State()


# ================= HANDLERS =================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db_query("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (uid, message.from_user.username),
             commit=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")]])
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=kb)


@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    uid = callback.from_user.id
    db_query("UPDATE users SET language = ? WHERE user_id = ?", (lang, uid), commit=True)
    await callback.message.delete()
    if is_admin(uid):
        await callback.message.answer(get_text('admin_panel', lang), reply_markup=get_admin_menu(lang))
    else:
        await callback.message.answer("🏠 Asosiy sahifa", reply_markup=get_main_menu(lang))


@dp.message(F.text.in_([TEXTS['uz']['btn_quit'], TEXTS['ru']['btn_quit']]))
async def quit_process(message: Message, state: FSMContext):
    lang = await get_state_lang(message.from_user.id)
    await state.clear()
    await message.answer("🫠 " + get_text('resume_cancelled', lang), reply_markup=get_main_menu(lang))


@dp.message(F.text.in_([TEXTS['uz']['btn_start'], TEXTS['ru']['btn_start']]))
async def restart_process(message: Message, state: FSMContext):
    await cmd_start(message, state)


@dp.message(F.text.in_([TEXTS['uz']['fill_resume'], TEXTS['ru']['fill_resume']]))
async def start_resume(message: Message, state: FSMContext):
    lang = await get_state_lang(message.from_user.id)
    await state.update_data(lang=lang)
    await state.set_state(ResumeFSM.full_name)
    await message.answer(get_text('ask_name', lang), reply_markup=get_main_menu(lang))


# --- BOSQICHLAR ---
@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeFSM.birth_date);
    await message.answer(get_text('ask_birth', data['lang']))


@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(birth_date=message.text)
    await state.set_state(ResumeFSM.age);
    await message.answer(get_text('ask_age', data['lang']))


@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.isdigit(): return await message.answer(get_text('err_age', data['lang']))
    await state.update_data(age=int(message.text));
    await state.set_state(ResumeFSM.gender)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]],
                             resize_keyboard=True)
    await message.answer(get_text('ask_gender', data['lang']), reply_markup=kb)


@dp.message(ResumeFSM.gender)
async def s4(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(gender=message.text)
    await state.set_state(ResumeFSM.address);
    await message.answer(get_text('ask_address', data['lang']), reply_markup=get_main_menu(data['lang']))


@dp.message(ResumeFSM.address)
async def s5(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(address=message.text)
    await state.set_state(ResumeFSM.location)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Lokatsiya", request_location=True)]],
                             resize_keyboard=True)
    await message.answer(get_text('ask_location', data['lang']), reply_markup=kb)


@dp.message(ResumeFSM.location, F.location)
async def s6(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(latitude=message.location.latitude, longitude=message.location.longitude)
    await state.set_state(ResumeFSM.phone_number)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True)]],
                             resize_keyboard=True)
    await message.answer(get_text('ask_phone', data['lang']), reply_markup=kb)


@dp.message(ResumeFSM.phone_number)
async def s7(message: Message, state: FSMContext):
    data = await state.get_data();
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone_number=phone);
    await state.set_state(ResumeFSM.previous_job)
    await message.answer(get_text('ask_prev_job', data['lang']), reply_markup=get_main_menu(data['lang']))


@dp.message(ResumeFSM.previous_job)
async def s8(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(previous_job=message.text)
    await state.set_state(ResumeFSM.experience);
    await message.answer(get_text('ask_exp', data['lang']))


@dp.message(ResumeFSM.experience)
async def s9(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(experience=message.text)
    await state.set_state(ResumeFSM.position)
    vacs = db_query("SELECT title FROM vacancies", fetchall=True)
    builder = ReplyKeyboardBuilder()
    for v in vacs: builder.add(KeyboardButton(text=v[0]))
    builder.adjust(2)
    await message.answer(get_text('ask_position', data['lang']), reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(ResumeFSM.position)
async def s10(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(position=message.text)
    await state.set_state(ResumeFSM.photo);
    await message.answer(get_text('ask_photo', data['lang']), reply_markup=get_main_menu(data['lang']))


@dp.message(ResumeFSM.photo, F.photo)
async def s11(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(photo_id=message.photo[-1].file_id)
    await state.set_state(ResumeFSM.hobby);
    await message.answer(get_text('ask_hobby', data['lang']))


@dp.message(ResumeFSM.hobby)
async def s12(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(hobby=message.text)
    await state.set_state(ResumeFSM.skills);
    await message.answer(get_text('ask_skills', data['lang']))


@dp.message(ResumeFSM.skills)
async def s13(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(skills=message.text)
    await state.set_state(ResumeFSM.purpose);
    await message.answer(get_text('ask_purpose', data['lang']))


@dp.message(ResumeFSM.purpose)
async def s14(message: Message, state: FSMContext):
    data = await state.get_data();
    await state.update_data(purpose=message.text)
    await state.set_state(ResumeFSM.guarantor);
    await message.answer(get_text('ask_guarantor', data['lang']))


@dp.message(ResumeFSM.guarantor)
async def s15(message: Message, state: FSMContext):
    await state.update_data(guarantor=message.text);
    data = await state.get_data()
    cap = f"📄 <b>TASDIQLASH</b>\n👤 {data['full_name']}\n📞 {data['phone_number']}\n💼 {data['position']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await message.answer_photo(data['photo_id'], caption=cap, reply_markup=kb)


@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data();
    lang = data['lang']
    score = calculate_score(data['age'], data['experience'], data['skills'])
    db_query("""INSERT INTO resumes (user_id, full_name, birth_date, age, gender, address, latitude, longitude,
                                     phone_number, previous_job, experience, position, photo_id, hobby, skills, purpose,
                                     guarantor, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
             (call.from_user.id, data['full_name'], data['birth_date'], data['age'], data['gender'], data['address'],
              data['latitude'], data['longitude'], data['phone_number'], data['previous_job'], data['experience'],
              data['position'], data['photo_id'], data['hobby'], data['skills'], data['purpose'], data['guarantor'],
              score), commit=True)

    admins = db_query("SELECT user_id FROM admins", fetchall=True)
    notif = get_text('new_resume_admin', 'uz').format(name=data['full_name'], phone=data['phone_number'],
                                                      pos=data['position'], score=score)
    for admin in admins:
        try:
            await bot.send_photo(chat_id=admin[0], photo=data['photo_id'], caption=notif)
        except:
            pass

    await call.message.delete();
    await call.message.answer("🎉 " + get_text('resume_accepted', lang), reply_markup=get_main_menu(lang))
    await state.clear()


async def main():
    setup_database();
    logging.basicConfig(level=logging.INFO);
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
