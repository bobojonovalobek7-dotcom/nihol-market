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
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ================= SOZLAMALAR =================
BOT_TOKEN = "8593426346:AAG9mRz-mYs79vTalBK-twGcQFTu7JbGAFo"
ADMIN_IDS = [356009218, 5341602920]  # Super Adminlar
DB_FILE = "resume_bot_final.db"

# ================= TEXTS =================
TEXTS = {
    'uz': {
        'admin_panel': "⚙️ <b>Admin panelga xush kelibsiz!</b>",
        'fill_resume': "📄 Rezyume to'ldirish",
        'btn_start': "🚀 Qayta boshlash",
        'btn_quit': "❌ Bekor qilish",
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
        'new_resume_admin': (
            "🎊 ✨ <b>YANGI NOMZOD QABUL QILINDI</b> ✨ 🎊\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Nomzod:</b> <code>{name}</code>\n"
            "📞 <b>Tel:</b> <code>{phone}</code>\n"
            "💼 <b>Lavozim:</b> <code>{pos}</code>\n"
            "📊 <b>Reyting:</b> 🔥 <b>{score} ball</b> 🔥\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🕒 <b>Vaqt:</b> <i>{time}</i>\n"
            "📥 <i>Ma'lumot saqlandi.</i>"
        )
    }
}

# ================= DATABASE =================
def db_query(query, params=(), commit=False, fetchall=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        if fetchall: return cursor.fetchall()

def setup_database():
    db_query("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)", commit=True)
    db_query("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, phone_number TEXT, 
        position TEXT, score INTEGER, photo_id TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""", commit=True)
    db_query("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)", commit=True)

# ================= KEYBOARDS =================
def get_std_kb(extra_btns=None):
    builder = ReplyKeyboardBuilder()
    if extra_btns:
        for btn in extra_btns: builder.add(btn)
    builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    return builder.as_markup(resize_keyboard=True)

# ================= STATES =================
class ResumeFSM(StatesGroup):
    full_name = State(); birth_date = State(); age = State(); gender = State(); address = State()
    location = State(); phone_number = State(); previous_job = State(); experience = State()
    position = State(); photo = State(); hobby = State(); skills = State(); purpose = State(); guarantor = State()

# ================= HANDLERS =================
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚠️ " + TEXTS['uz']['resume_cancelled'], reply_markup=get_std_kb([KeyboardButton(text=TEXTS['uz']['fill_resume'])]))

@dp.message(CommandStart())
@dp.message(F.text == TEXTS['uz']['btn_start'])
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    db_query("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (message.from_user.id, message.from_user.username), commit=True)
    await message.answer("👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldiring.", 
                         reply_markup=get_std_kb([KeyboardButton(text=TEXTS['uz']['fill_resume'])]))

@dp.message(F.text == TEXTS['uz']['fill_resume'])
async def start_resume(message: Message, state: FSMContext):
    await state.set_state(ResumeFSM.full_name)
    await message.answer(TEXTS['uz']['ask_name'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeFSM.birth_date)
    await message.answer(TEXTS['uz']['ask_birth'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    await state.update_data(birth_date=message.text)
    await state.set_state(ResumeFSM.age)
    await message.answer(TEXTS['uz']['ask_age'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer(TEXTS['uz']['err_age'], reply_markup=get_std_kb())
    await state.update_data(age=int(message.text))
    await state.set_state(ResumeFSM.gender)
    await message.answer(TEXTS['uz']['ask_gender'], reply_markup=get_std_kb([KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]))

@dp.message(ResumeFSM.gender)
async def s4(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(ResumeFSM.address)
    await message.answer(TEXTS['uz']['ask_address'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.address)
async def s5(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(ResumeFSM.location)
    await message.answer(TEXTS['uz']['ask_location'], reply_markup=get_std_kb([KeyboardButton(text="📍 Lokatsiya", request_location=True)]))

@dp.message(ResumeFSM.location, F.location)
async def s6(message: Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(ResumeFSM.phone_number)
    await message.answer(TEXTS['uz']['ask_phone'], reply_markup=get_std_kb([KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True)]))

@dp.message(ResumeFSM.phone_number, F.contact | F.text)
async def s7(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(ResumeFSM.previous_job)
    await message.answer(TEXTS['uz']['ask_prev_job'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.previous_job)
async def s8(message: Message, state: FSMContext):
    await state.update_data(prev_job=message.text)
    await state.set_state(ResumeFSM.experience)
    await message.answer(TEXTS['uz']['ask_exp'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.experience)
async def s9(message: Message, state: FSMContext):
    await state.update_data(exp=message.text)
    await state.set_state(ResumeFSM.position)
    vacs = db_query("SELECT title FROM vacancies", fetchall=True)
    btns = [KeyboardButton(text=v[0]) for v in vacs] if vacs else [KeyboardButton(text="Sotuvchi"), KeyboardButton(text="Kassir")]
    await message.answer(TEXTS['uz']['ask_position'], reply_markup=get_std_kb(btns))

@dp.message(ResumeFSM.position)
async def s10(message: Message, state: FSMContext):
    await state.update_data(pos=message.text)
    await state.set_state(ResumeFSM.photo)
    await message.answer(TEXTS['uz']['ask_photo'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.photo, F.photo)
async def s11(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(ResumeFSM.hobby)
    await message.answer(TEXTS['uz']['ask_hobby'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.hobby)
async def s12(message: Message, state: FSMContext):
    await state.update_data(hobby=message.text)
    await state.set_state(ResumeFSM.skills)
    await message.answer(TEXTS['uz']['ask_skills'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.skills)
async def s13(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    await state.set_state(ResumeFSM.purpose)
    await message.answer(TEXTS['uz']['ask_purpose'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.purpose)
async def s14(message: Message, state: FSMContext):
    await state.update_data(purpose=message.text)
    await state.set_state(ResumeFSM.guarantor)
    await message.answer(TEXTS['uz']['ask_guarantor'], reply_markup=get_std_kb())

@dp.message(ResumeFSM.guarantor)
async def s15(message: Message, state: FSMContext):
    await state.update_data(guarantor=message.text)
    data = await state.get_data()
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {data['full_name']}\n📞 {data['phone']}\n💼 {data['pos']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="conf_final")]])
    await message.answer_photo(data['photo'], caption=cap, reply_markup=kb)

@dp.callback_query(F.data == "conf_final")
async def process_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = 50 # Avtomatik ball
    now = datetime.now().strftime("%H:%M | %d.%m.%Y")
    
    db_query("INSERT INTO resumes (user_id, full_name, phone_number, position, score, photo_id) VALUES (?,?,?,?,?,?)",
             (call.from_user.id, data['full_name'], data['phone'], data['pos'], score, data['photo']), commit=True)

    msg = TEXTS['uz']['new_resume_admin'].format(name=data['full_name'], phone=data['phone'], pos=data['pos'], score=score, time=now)
    
    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, sticker="CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, photo=data['photo'], caption=msg)
        except: pass

    await call.message.delete()
    await call.message.answer("🎉 " + TEXTS['uz']['resume_accepted'], reply_markup=get_std_kb([KeyboardButton(text=TEXTS['uz']['fill_resume'])]))
    await state.clear()

async def main():
    setup_database()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
