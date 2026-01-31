import asyncio
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

# ================= CONFIG (SOZLAMALAR) =================
# Tokenni shu yerga yozing
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAGvOLyfs3t3nK2eGdkzxy1Qb_6A--xhieA")

# Xabar boradigan Adminlar
ADMIN_IDS = [356009218, 5341602920, 5777142647]

# Loglarni yoqish
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

# ================= MATNLAR =================
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Assalomu alaykum!</b>\nIshga kirish uchun anketani to'ldirishni boshlang.",
        'btn_fill': "📄 Rezyume to'ldirish",
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
        'ask_interests': "12. <b>Shaxsiy qiziqishlaringiz:</b>\n<i>Masalan: Sport, Kitob o'qish</i>",
        'ask_skills': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili, Excel, 1C</i>",
        'ask_purpose': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Rivojlanish va daromad</i>",
        'ask_guarantor': "15. <b>Sizga kafil bo'la oladigan odam bormi?</b>\n(Ismi, Telefoni):\n<i>Masalan: Akam Vali, +998901234567</i>",
        
        'resume_accepted': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
        'resume_cancelled': "⚠️ <b>Amaliyot bekor qilindi.</b>",
        'err_type': "⚠️ <b>Iltimos, matn ko'rinishida yozing!</b>",
        'err_age': "⚠️ <b>Xato!</b> Faqat raqam kiriting (Masalan: 25):",
        
        # Admin xabarnomasi
        'admin_notification': (
            "🔔 <b>YANGI REZYUME!</b>\n"
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
            "🕒 <b>Vaqt:</b> {time}"
        )
    }
}

# ================= KEYBOARDS =================
def get_kb(in_process=False):
    builder = ReplyKeyboardBuilder()
    if in_process:
        builder.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    else:
        builder.add(KeyboardButton(text=TEXTS['uz']['btn_fill']))
        builder.adjust(1)
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

@dp.message(CommandStart())
@dp.message(F.text == TEXTS['uz']['btn_start'])
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS['uz']['welcome'], reply_markup=get_kb())

@dp.message(F.text == TEXTS['uz']['btn_quit'])
async def quit_process(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS['uz']['resume_cancelled'], reply_markup=get_kb())

# --- QADAMLAR ---
@dp.message(F.text == TEXTS['uz']['btn_fill'])
async def start_resume(message: Message, state: FSMContext):
    await state.set_state(ResumeFSM.full_name)
    await message.answer(TEXTS['uz']['ask_name'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.full_name)
async def s1(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeFSM.birth_date)
    await message.answer(TEXTS['uz']['ask_birth'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.birth_date)
async def s2(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(birth_date=message.text)
    await state.set_state(ResumeFSM.age)
    await message.answer(TEXTS['uz']['ask_age'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.age)
async def s3(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        return await message.answer(TEXTS['uz']['err_age'], reply_markup=get_kb(True))
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
    await message.answer(TEXTS['uz']['ask_family'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.family_status)
async def s5(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(family_status=message.text)
    await state.set_state(ResumeFSM.address)
    await message.answer(TEXTS['uz']['ask_address'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.address)
async def s6(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(address=message.text)
    await state.set_state(ResumeFSM.phone_number)
    kb = ReplyKeyboardBuilder().add(KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_phone'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.phone_number, F.contact | F.text)
async def s7(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    if not phone: return await message.answer("Telefon raqam yuboring!")
    await state.update_data(phone=phone)
    await state.set_state(ResumeFSM.previous_job)
    await message.answer(TEXTS['uz']['ask_prev_job'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.previous_job)
async def s8(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(prev_job=message.text)
    await state.set_state(ResumeFSM.experience)
    await message.answer(TEXTS['uz']['ask_exp'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.experience)
async def s9(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(exp=message.text)
    await state.set_state(ResumeFSM.position)
    # Vakansiyalar statik (Baza yo'qligi uchun)
    vacancies = ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]
    kb = ReplyKeyboardBuilder()
    for v in vacancies: kb.add(KeyboardButton(text=v))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_start']), KeyboardButton(text=TEXTS['uz']['btn_quit']))
    await message.answer(TEXTS['uz']['ask_position'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(ResumeFSM.position)
async def s10(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(pos=message.text)
    await state.set_state(ResumeFSM.photo)
    await message.answer(TEXTS['uz']['ask_photo'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.photo, F.photo)
async def s11(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(ResumeFSM.interests)
    await message.answer(TEXTS['uz']['ask_interests'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.interests)
async def s12(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(interests=message.text)
    await state.set_state(ResumeFSM.skills)
    await message.answer(TEXTS['uz']['ask_skills'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.skills)
async def s13(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(skills=message.text)
    await state.set_state(ResumeFSM.purpose)
    await message.answer(TEXTS['uz']['ask_purpose'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.purpose)
async def s14(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(purpose=message.text)
    await state.set_state(ResumeFSM.guarantor)
    await message.answer(TEXTS['uz']['ask_guarantor'], reply_markup=get_kb(True))

@dp.message(ResumeFSM.guarantor)
async def s15(message: Message, state: FSMContext):
    if not await validate_text(message): return
    await state.update_data(guarantor=message.text)
    d = await state.get_data()
    
    cap = f"📄 <b>TASDIQLASH</b>\n\n👤 {d['full_name']}\n📞 {d['phone']}\n💼 {d['pos']}\n💍 {d['family_status']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await message.answer_photo(d['photo'], caption=cap, reply_markup=kb)

# --- FINAL (BAZASIZ, FAQAT YUBORISH) ---
@dp.callback_query(F.data == "confirm")
async def process_confirm(call: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    user_id = call.from_user.id
    username = call.from_user.username
    
    # Ball hisoblash
    score = 50
    if any(x in str(d.get('skills', '')).lower() for x in ['rus', 'excel']): score += 20
    now = datetime.now().strftime("%H:%M | %d.%m.%Y")
    
    # Ismga havola (Link)
    link_name = f"<a href='tg://user?id={user_id}'>{d['full_name']}</a>"
    
    # Adminga tayyor shablon
    admin_msg = TEXTS['uz']['admin_notification'].format(
        link_name=link_name, age=d['age'], gender=d['gender'], family=d['family_status'], 
        phone=d['phone'], address=d['address'], pos=d['pos'], exp=d['exp'], 
        prev_job=d['prev_job'], hobby=d['interests'], skills=d['skills'],
        purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    
    # "Nomzodga yozish" tugmasi
    chat_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={user_id}")]
    ])

    # Adminlarga tarqatish
    sent_count = 0
    for adm in ADMIN_IDS:
        try:
            await bot.send_sticker(adm, "CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            await bot.send_photo(adm, d['photo'], caption=admin_msg, reply_markup=chat_btn)
            sent_count += 1
        except Exception as e:
            logging.warning(f"Admin {adm} ga bormadi: {e}")

    await call.message.delete()
    if sent_count > 0:
        await call.message.answer(TEXTS['uz']['resume_accepted'], reply_markup=get_kb())
    else:
        await call.message.answer("⚠️ Tizimda xatolik bo'ldi, qayta urinib ko'ring.", reply_markup=get_kb())
        
    # Xotirani tozalash (RAM bo'shatish)
    await state.clear()

async def main():
    logging.info("Bot ishga tushdi (Bazasiz rejim)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
