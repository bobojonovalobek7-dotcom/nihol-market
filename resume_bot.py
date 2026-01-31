import asyncio
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton, Message, ReplyKeyboardMarkup, 
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ================= 1. SOZLAMALAR =================
# Tokenni shu yerga yozing
BOT_TOKEN = os.getenv("BOT_TOKEN", "8593426346:AAG9mRz-mYs79vTalBK-twGcQFTu7JbGAFo")

# Xabar boradigan Adminlar (Barchasi)
ADMIN_IDS = [356009218, 5341602920, 5777142647]

# Loglarni sozlash (Xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

# ================= 2. MATNLAR =================
TEXTS = {
    'start': "👋 <b>Assalomu alaykum!</b>\nIshga kirish anketasini to'ldirish uchun pastdagi tugmani bosing.",
    'btn_fill': "📄 Rezyume to'ldirish",
    'btn_cancel': "❌ Bekor qilish",
    'cancelled': "⚠️ Jarayon bekor qilindi. Qayta boshlash uchun tugmani bosing.",
    
    # Savollar
    'q1': "1. <b>F.I.O</b> to'liq kiriting:\n<i>Masalan: Bobojonov Alobek</i>",
    'q2': "2. <b>Tug'ilgan sanangiz</b> (kun.oy.yil):\n<i>Masalan: 25.10.1998</i>",
    'q3': "3. <b>Yoshingiz</b> (faqat raqamda):\n<i>Masalan: 26</i>",
    'q4': "4. <b>Jinsingizni tanlang:</b>",
    'q5': "5. <b>Oilaviy holatingiz:</b>\n<i>Masalan: Turmushga chiqqan, Bo'ydoq</i>",
    'q6': "6. <b>Manzilingizni kiriting:</b>\n<i>Masalan: Urganch shahri, Al-Xorazmiy 12</i>",
    'q7': "7. <b>📞 Telefon raqamingizni yuboring:</b>\n(Pastdagi tugmani bosing)",
    'q8': "8. <b>Oldingi ish joyingiz:</b>\n<i>Masalan: 'Nihol' marketi yoki 'Yo'q'</i>",
    'q9': "9. <b>Ish tajribangiz:</b>\n<i>Masalan: 2 yil sotuvchi</i>",
    'q10': "10. <b>Qaysi lavozimda ishlamoqchisiz?</b>",
    'q11': "11. <b>🖼 Rasm (3x4) yuboring:</b>",
    'q12': "12. <b>Shaxsiy qiziqishlaringiz:</b>\n<i>Masalan: Sport, Kitob o'qish</i>",
    'q13': "13. <b>Bilimlaringiz (Til, Kompyuter):</b>\n<i>Masalan: Rus tili, Excel, 1C</i>",
    'q14': "14. <b>Ishdan maqsad:</b>\n<i>Masalan: Rivojlanish va daromad</i>",
    'q15': "15. <b>Sizga kafil bo'la oladigan odam bormi?</b>\n(Ismi, Telefoni):\n<i>Masalan: Akam Vali, +998901234567</i>",
    
    # Xabarlar
    'confirm_ask': "📄 <b>Ma'lumotlaringiz to'g'rimi?</b>\nTasdiqlasangiz, anketangiz rahbariyatga yuboriladi.",
    'done': "✅ <b>Qabul qilindi!</b>\nAdminlarimiz tez orada siz bilan bog'lanishadi.",
    'err_text': "⚠️ Iltimos, faqat matn yozing!",
    'err_digit': "⚠️ Iltimos, faqat raqam yozing!",
    'err_photo': "⚠️ Iltimos, rasm yuboring!",
    
    # ADMIN UCHUN SHABLON
    'admin_tpl': (
        "🔔 <b>YANGI REZYUME!</b>\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "👤 <b>Nomzod:</b> {link}\n"
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

# ================= 3. STATE (HOLATLAR) =================
class Form(StatesGroup):
    name = State()
    birth = State()
    age = State()
    gender = State()
    family = State()
    address = State()
    phone = State()
    prev_job = State()
    exp = State()
    pos = State()
    photo = State()
    hobby = State()
    skills = State()
    purpose = State()
    guarantor = State()
    confirm = State()

# ================= 4. BOT SOZLAMALARI =================
# MemoryStorage - Eng tezkor usul (RAM da ishlaydi)
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# --- Yordamchi funksiyalar ---
def get_start_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS['btn_fill'])]],
        resize_keyboard=True
    )

def get_cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS['btn_cancel'])]],
        resize_keyboard=True
    )

# ================= 5. HANDLERLAR (MANTIQ) =================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS['start'], reply_markup=get_start_kb())

@dp.message(F.text == TEXTS['btn_cancel'])
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS['cancelled'], reply_markup=get_start_kb())

# --- 1. ISM ---
@dp.message(F.text == TEXTS['btn_fill'])
async def start_form(message: Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer(TEXTS['q1'], reply_markup=get_cancel_kb())

@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(name=message.text)
    await state.set_state(Form.birth)
    await message.answer(TEXTS['q2'])

# --- 2. TUG'ILGAN SANA ---
@dp.message(Form.birth)
async def process_birth(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(birth=message.text)
    await state.set_state(Form.age)
    await message.answer(TEXTS['q3'])

# --- 3. YOSH ---
@dp.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        return await message.answer(TEXTS['err_digit'])
    await state.update_data(age=message.text)
    await state.set_state(Form.gender)
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")],
        [KeyboardButton(text=TEXTS['btn_cancel'])]
    ], resize_keyboard=True)
    await message.answer(TEXTS['q4'], reply_markup=kb)

# --- 4. JINS ---
@dp.message(Form.gender)
async def process_gender(message: Message, state: FSMContext):
    if message.text not in ["Erkak", "Ayol"]: return await message.answer(TEXTS['err_text'])
    await state.update_data(gender=message.text)
    await state.set_state(Form.family)
    await message.answer(TEXTS['q5'], reply_markup=get_cancel_kb())

# --- 5. OILA ---
@dp.message(Form.family)
async def process_family(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(family=message.text)
    await state.set_state(Form.address)
    await message.answer(TEXTS['q6'])

# --- 6. MANZIL ---
@dp.message(Form.address)
async def process_address(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(address=message.text)
    await state.set_state(Form.phone)
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True)],
        [KeyboardButton(text=TEXTS['btn_cancel'])]
    ], resize_keyboard=True)
    await message.answer(TEXTS['q7'], reply_markup=kb)

# --- 7. TELEFON ---
@dp.message(Form.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    if not phone: return await message.answer(TEXTS['err_text'])
    
    await state.update_data(phone=phone)
    await state.set_state(Form.prev_job)
    await message.answer(TEXTS['q8'], reply_markup=get_cancel_kb())

# --- 8. ESKI ISH ---
@dp.message(Form.prev_job)
async def process_prev(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(prev_job=message.text)
    await state.set_state(Form.exp)
    await message.answer(TEXTS['q9'])

# --- 9. TAJRIBA ---
@dp.message(Form.exp)
async def process_exp(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(exp=message.text)
    await state.set_state(Form.pos)
    
    # Lavozimlar
    roles = ["Kassir", "Sotuvchi", "Gruzchik", "Oshpaz", "Bugalter yordamchisi", "SMM", "Tozalovchi"]
    kb_builder = ReplyKeyboardBuilder()
    for role in roles:
        kb_builder.add(KeyboardButton(text=role))
    kb_builder.adjust(2)
    kb_builder.row(KeyboardButton(text=TEXTS['btn_cancel']))
    
    await message.answer(TEXTS['q10'], reply_markup=kb_builder.as_markup(resize_keyboard=True))

# --- 10. LAVOZIM ---
@dp.message(Form.pos)
async def process_pos(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(pos=message.text)
    await state.set_state(Form.photo)
    await message.answer(TEXTS['q11'], reply_markup=get_cancel_kb())

# --- 11. RASM ---
@dp.message(Form.photo)
async def process_photo(message: Message, state: FSMContext):
    if not message.photo: return await message.answer(TEXTS['err_photo'])
    
    # Eng katta sifatli rasmni olamiz
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    
    await state.set_state(Form.hobby)
    await message.answer(TEXTS['q12'])

# --- 12. HOBBI ---
@dp.message(Form.hobby)
async def process_hobby(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(hobby=message.text)
    await state.set_state(Form.skills)
    await message.answer(TEXTS['q13'])

# --- 13. BILIMLAR ---
@dp.message(Form.skills)
async def process_skills(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(skills=message.text)
    await state.set_state(Form.purpose)
    await message.answer(TEXTS['q14'])

# --- 14. MAQSAD ---
@dp.message(Form.purpose)
async def process_purpose(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(purpose=message.text)
    await state.set_state(Form.guarantor)
    await message.answer(TEXTS['q15'])

# --- 15. KAFIL (PREVIEW) ---
@dp.message(Form.guarantor)
async def process_guarantor(message: Message, state: FSMContext):
    if not message.text: return await message.answer(TEXTS['err_text'])
    await state.update_data(guarantor=message.text)
    
    data = await state.get_data()
    
    # Preview (User o'zi ko'rishi uchun)
    caption = (
        f"📄 <b>TASDIQLASH</b>\n\n"
        f"👤 <b>{data['name']}</b>\n"
        f"📞 {data['phone']}\n"
        f"💼 {data['pos']}\n"
        f"⚠️ <i>Ma'lumotlar to'g'rimi?</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ TASDIQLASH va YUBORISH", callback_data="send_admin")]
    ])
    
    await message.answer_photo(photo=data['photo'], caption=caption, reply_markup=kb)
    await state.set_state(Form.confirm) # Holatni kutish rejimiga o'tkazamiz

# ================= 6. ADMINGA YUBORISH (FINAL) =================

@dp.callback_query(F.data == "send_admin", Form.confirm)
async def send_to_admins(call: CallbackQuery, state: FSMContext):
    # Userga "Kuting..." degan ma'noda soat iconi chiqadi
    await call.answer("Yuborilmoqda...") 
    
    data = await state.get_data()
    user_id = call.from_user.id
    
    # Ballni hisoblash (RAM da)
    score = 50
    skills_text = str(data.get('skills', '')).lower()
    if 'rus' in skills_text or 'excel' in skills_text:
        score += 20
        
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Link yasash
    user_link = f"<a href='tg://user?id={user_id}'>{data['name']}</a>"
    
    # Admin uchun tayyor matn
    admin_caption = TEXTS['admin_tpl'].format(
        link=user_link,
        age=data['age'], gender=data['gender'], family=data['family'],
        phone=data['phone'], address=data['address'],
        pos=data['pos'], exp=data['exp'], prev=data['prev_job'],
        hobby=data['hobby'], skills=data['skills'],
        purpose=data['purpose'], guarantor=data['guarantor'],
        score=score, time=now
    )
    
    # Admin tugmasi
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={user_id}")]
    ])
    
    # BARCHA ADMINLARGA YUBORISH
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            # 1. Stiker
            await bot.send_sticker(chat_id=admin_id, sticker="CAACAgIAAxkBAAEL7Rxl_U6XnS7fS_R9S_R9S_R9")
            # 2. Anketa
            await bot.send_photo(
                chat_id=admin_id,
                photo=data['photo'],
                caption=admin_caption,
                reply_markup=admin_kb
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Adminga yuborishda xato ({admin_id}): {e}")
    
    # Foydalanuvchiga javob
    await call.message.delete()
    
    if success_count > 0:
        await call.message.answer(TEXTS['done'], reply_markup=get_start_kb())
    else:
        await call.message.answer("⚠️ Tizimda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.", reply_markup=get_start_kb())
        
    # Xotirani tozalash
    await state.clear()

# ================= 7. MAIN =================
async def main():
    logging.info("Bot ishga tushdi (BAZASIZ REJIM)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
