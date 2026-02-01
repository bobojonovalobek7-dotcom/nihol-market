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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8542250212:AAFlRdElR2y08jWkDFGfS2NgpE05051bojY")
ADMIN_IDS = [356009218, 5341602920, 5777142647]
DB_FILE = "resume_bot_final.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ================= 2. MATNLAR =================
TEXTS = {
    'uz': {
        'welcome': (
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "<b>Nihol Market</b> jamoasiga qo'shilish istagida ekanligingizdan xursandmiz.\n"
            "Ishga kirish uchun quyidagi anketani to'ldirishingiz kerak.\n\n"
            "<i>Boshlash uchun pastdagi tugmani bosing</i> 👇"
        ),
        'welcome_admin': "👑 <b>Admin Panelga xush kelibsiz!</b>",
        
        # Tugmalar
        'btn_fill': "✍️ Anketani to'ldirish",
        'btn_restart': "🔄 Boshidan boshlash",
        'btn_cancel': "❌ Bekor qilish",
        'btn_view': "📂 Rezyumelar (20)",
        'btn_stats': "📊 Statistika",
        'btn_phone': "📞 Kontaktni yuborish",
        'btn_back': "⬅️ Orqaga",
        
        # Savollar
        'q1': "<b>1. To'liq ism-familiyangizni kiriting:</b>\n\n<i>Masalan: Abdullayev Abdulla Abdulla o'g'li</i>",
        'q2': "<b>2. Tug'ilgan sanangizni kiriting:</b>\n\n<i>Format: kun.oy.yil (Masalan: 15.04.2000)</i>",
        'q3': "<b>3. Yoshingiz nechida?</b>\n\n<i>Faqat raqam yozing (Masalan: 22)</i>",
        'q4': "<b>4. Jinsingizni tanlang:</b> 👇",
        'q5': "<b>5. Oilaviy holatingiz qanday?</b>\n\n<i>(Bo'ydoq, Oilali, Ajrashgan)</i>",
        'q6': "<b>6. Yashash manzilingizni kiriting:</b>\n\n<i>Tuman, mahalla va ko'cha nomi</i>",
        'q7': "<b>7. Telefon raqamingizni yuboring:</b>\n\nPastdagi <b>\"📞 Kontaktni yuborish\"</b> tugmasini bosing 👇",
        'q8': "<b>8. Avval qayerda ishlagansiz?</b>\n\n<i>Ish joyi nomi va vazifangizni yozing (Agar ishlamagan bo'lsangiz 'Yo'q' deb yozing)</i>",
        'q9': "<b>9. Umumiy ish tajribangiz qancha?</b>\n\n<i>(Masalan: 1 yil, 6 oy yoki Yo'q)</i>",
        'q10': "<b>10. Qaysi lavozimda ishlamoqchisiz?</b>\n\n<i>Quyidagi bo'limlardan birini tanlang</i> 👇",
        'q11': "<b>11. O'zingizni rasmingizni yuboring:</b>\n\n<i>Iltimos, yuzi aniq tushgan rasm bo'lsin.</i>",
        'q12': "<b>12. Qiziqishlaringiz (Hobby) nimalar?</b>",
        'q13': "<b>13. Qo'shimcha bilimlaringiz:</b>\n\n<i>(Til bilish darajasi, Kompyuter dasturlari va h.k)</i>",
        'q14': "<b>14. Ishlashdan maqsadingiz nima?</b>",
        'q15': "<b>15. Sizga kim tavsiya beradi (Kafil)?</b>\n\n<i>Ismi va telefon raqamini yozing (Yoki 'O'zim' deb yozing)</i>",
        
        'done': "✅ <b>Tabriklaymiz! Sizning anketangiz qabul qilindi.</b>\n\nTez orada mutaxassislarimiz siz bilan bog'lanishadi.",
        'cancel': "⚠️ <b>Anketa bekor qilindi.</b> Qaytadan boshlash uchun tugmani bosing.",
        'err_txt': "⚠️ <b>Iltimos, matn ko'rinishida yozing!</b>",
        'err_num': "⚠️ <b>Iltimos, faqat raqam kiriting!</b>",
        
        # ADMIN UCHUN SHABLON
        'admin_tpl': (
            "🔔 <b>YANGI REZYUME!</b>\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "👤 <b>Nomzod:</b> {link}\n"
            "📅 <b>Yosh:</b> {age}\n"
            "🚻 <b>Jins:</b> {gender}\n"
            "💍 <b>Oila:</b> {family}\n"
            "📞 <b>Tel:</b> {phone}\n"
            "📍 <b>Manzil:</b> {address}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "💼 <b>Vakansiya:</b> {pos}\n"
            "📝 <b>Tajriba:</b> {exp}\n"
            "🏢 <b>Eski ish:</b> {prev}\n"
            "⚽ <b>Qiziqish:</b> {hobby}\n"
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
    await db_exec("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)", commit=True)
    for admin_id in ADMIN_IDS:
        await db_exec("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,), commit=True)

    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)", commit=True)
    
    await db_exec("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, birth TEXT, age INTEGER, gender TEXT, family TEXT,
        address TEXT, phone TEXT, prev TEXT, exp TEXT, pos TEXT, photo TEXT, hobby TEXT,
        skills TEXT, purpose TEXT, guarantor TEXT, score INTEGER, date TEXT)""", commit=True)

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

def kb_admin(back_btn=False):
    b = ReplyKeyboardBuilder()
    if back_btn:
        b.row(KeyboardButton(text=TEXTS['uz']['btn_back']))
    else:
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
@dp.message(F.text.in_([TEXTS['uz']['btn_restart'], TEXTS['uz']['btn_back']]))
async def start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    await db_exec("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,), commit=True)
    
    kb = kb_admin() if uid in ADMIN_IDS else kb_user()
    txt = TEXTS['uz']['welcome_admin'] if uid in ADMIN_IDS else TEXTS['uz']['welcome']
    await m.answer(txt, reply_markup=kb)

# --- ADMIN PANEL: RESUMELAR RO'YXATI ---
@dp.message(F.text == TEXTS['uz']['btn_stats'])
async def stats(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    rc = (await db_exec("SELECT COUNT(*) FROM resumes", fetchone=True))[0]
    uc = (await db_exec("SELECT COUNT(*) FROM users", fetchone=True))[0]
    await m.answer(f"📊 <b>Statistika:</b>\n👥 Userlar: {uc}\n📄 Rezyumelar: {rc}")

@dp.message(F.text == TEXTS['uz']['btn_view'])
async def view_resumes(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    # ID, Name, Position ni olamiz
    res = await db_exec("SELECT id, name, pos FROM resumes ORDER BY id DESC LIMIT 20", fetchall=True)
    
    if not res: 
        return await m.answer("📭 Hozircha rezyumelar yo'q")
    
    kb = ReplyKeyboardBuilder()
    # Har bir rezyume uchun tugma yasaymiz: "🆔 15 | Ism"
    for r in res: 
        kb.add(KeyboardButton(text=f"🆔 {r[0]} | {r[1]}"))
    
    kb.adjust(1)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_back'])) # Orqaga qaytish tugmasi
    
    await m.answer("📂 <b>So'nggi 20 ta rezyume:</b>\n<i>Batafsil ko'rish uchun nomzodni tanlang:</i>", reply_markup=kb.as_markup(resize_keyboard=True))

# --- ADMIN PANEL: ID ORQALI REZYUMENI OCHISH ---
@dp.message(F.text.startswith("🆔"))
async def show_resume_detail(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    try:
        # "🆔 15 | Ism" -> ["🆔", "15", "|", "Ism"] -> "15" ni olamiz
        r_id = m.text.split()[1]
        
        # Bazadan to'liq ma'lumotni olish
        r = await db_exec("SELECT * FROM resumes WHERE id=?", (r_id,), fetchone=True)
        
        if not r: 
            return await m.answer("❌ Bu rezyume topilmadi.")

        # Bazadagi ustunlar tartibi:
        # 0=id, 1=user_id, 2=name, 3=birth, 4=age, 5=gender, 6=family, 
        # 7=address, 8=phone, 9=prev, 10=exp, 11=pos, 12=photo, 
        # 13=hobby, 14=skills, 15=purpose, 16=guarantor, 17=score, 18=date

        link = f"<a href='tg://user?id={r[1]}'>{r[2]}</a>"
        cap = TEXTS['uz']['admin_tpl'].format(
            link=link, age=r[4], gender=r[5], family=r[6], phone=r[8],
            address=r[7], pos=r[11], exp=r[10], prev=r[9], hobby=r[13],
            skills=r[14], purpose=r[15], guarantor=r[16], score=r[17], time=r[18]
        )
        
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={r[1]}")]])
        
        await m.answer_photo(photo=r[12], caption=cap, reply_markup=btn)
        
    except Exception as e:
        logging.error(f"Resume detail error: {e}")
        await m.answer("⚠️ Xatolik yuz berdi. Qayta urinib ko'ring.")

# --- USER: REZYUME TO'LDIRISH ---
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
async def p_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await state.set_state(Form.birth)
    await m.answer(TEXTS['uz']['q2'])

@dp.message(Form.birth)
async def p_birth(m: Message, state: FSMContext):
    await state.update_data(birth=m.text)
    await state.set_state(Form.age)
    await m.answer(TEXTS['uz']['q3'])

@dp.message(Form.age)
async def p_age(m: Message, state: FSMContext):
    if not m.text.isdigit(): 
        return await m.answer(TEXTS['uz']['err_num'])
    await state.update_data(age=m.text)
    await state.set_state(Form.gender)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol"))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q4'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.gender)
async def p_gender(m: Message, state: FSMContext):
    await state.update_data(gender=m.text)
    await state.set_state(Form.family)
    await m.answer(TEXTS['uz']['q5'], reply_markup=kb_user(True))

@dp.message(Form.family)
async def p_family(m: Message, state: FSMContext):
    await state.update_data(family=m.text)
    await state.set_state(Form.address)
    await m.answer(TEXTS['uz']['q6'])

@dp.message(Form.address)
async def p_addr(m: Message, state: FSMContext):
    await state.update_data(address=m.text)
    await state.set_state(Form.phone)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=TEXTS['uz']['btn_phone'], request_contact=True))
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q7'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.phone, F.contact | F.text)
async def p_phone(m: Message, state: FSMContext):
    phone = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=phone)
    await state.set_state(Form.prev)
    await m.answer(TEXTS['uz']['q8'], reply_markup=kb_user(True))

@dp.message(Form.prev)
async def p_prev(m: Message, state: FSMContext):
    await state.update_data(prev=m.text)
    await state.set_state(Form.exp)
    await m.answer(TEXTS['uz']['q9'])

@dp.message(Form.exp)
async def p_exp(m: Message, state: FSMContext):
    await state.update_data(exp=m.text)
    await state.set_state(Form.pos)
    vacs = await db_exec("SELECT title FROM vacancies", fetchall=True)
    kb = ReplyKeyboardBuilder()
    if vacs:
        for v in vacs:
            kb.add(KeyboardButton(text=v[0]))
    kb.adjust(2)
    kb.row(KeyboardButton(text=TEXTS['uz']['btn_cancel']))
    await m.answer(TEXTS['uz']['q10'], reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.pos)
async def p_pos(m: Message, state: FSMContext):
    await state.update_data(pos=m.text)
    await state.set_state(Form.photo)
    await m.answer(TEXTS['uz']['q11'], reply_markup=kb_user(True))

@dp.message(Form.photo, F.photo)
async def p_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await state.set_state(Form.hobby)
    await m.answer(TEXTS['uz']['q12'])

@dp.message(Form.hobby)
async def p_hobby(m: Message, state: FSMContext):
    await state.update_data(hobby=m.text)
    await state.set_state(Form.skills)
    await m.answer(TEXTS['uz']['q13'])

@dp.message(Form.skills)
async def p_skills(m: Message, state: FSMContext):
    await state.update_data(skills=m.text)
    await state.set_state(Form.purpose)
    await m.answer(TEXTS['uz']['q14'])

@dp.message(Form.purpose)
async def p_purp(m: Message, state: FSMContext):
    await state.update_data(purpose=m.text)
    await state.set_state(Form.guarantor)
    await m.answer(TEXTS['uz']['q15'])

@dp.message(Form.guarantor)
async def p_guar(m: Message, state: FSMContext): 
    await state.update_data(guarantor=m.text)
    d = await state.get_data()
    
    cap = (
        "📄 <b>MA'LUMOTLARNI TASDIQLASH</b>\n\n"
        f"👤 <b>Ism:</b> {d['name']}\n"
        f"📞 <b>Tel:</b> {d['phone']}\n"
        f"💼 <b>Lavozim:</b> {d['pos']}\n\n"
        "<i>Ma'lumotlar to'g'ri bo'lsa, <b>TASDIQLASH</b> tugmasini bosing.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="confirm")]])
    await m.answer_photo(d['photo'], caption=cap, reply_markup=kb)

# --- FINAL ---
@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    await call.answer("Yuborilmoqda...", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)
    
    d = await state.get_data()
    uid = call.from_user.id
    
    score = 50
    skills = str(d.get('skills', '')).lower()
    if 'rus' in skills or 'excel' in skills: score += 20
        
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # BAZAGA YOZISH
    await db_exec("""INSERT INTO resumes (
        user_id, name, birth, age, gender, family, address, phone, prev, exp, 
        pos, photo, hobby, skills, purpose, guarantor, score, date) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
        (uid, d['name'], d['birth'], d['age'], d['gender'], d['family'], d['address'],
         d['phone'], d['prev'], d['exp'], d['pos'], d['photo'], d['hobby'], d['skills'], 
         d['purpose'], d['guarantor'], score, now), commit=True)
    
    # ADMINGA YUBORISH
    link = f"<a href='tg://user?id={uid}'>{d['name']}</a>"
    cap = TEXTS['uz']['admin_tpl'].format(
        link=link, age=d['age'], gender=d['gender'], family=d['family'], phone=d['phone'],
        address=d['address'], pos=d['pos'], exp=d['exp'], prev=d['prev'], hobby=d['hobby'],
        skills=d['skills'], purpose=d['purpose'], guarantor=d['guarantor'], score=score, time=now
    )
    btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Nomzodga yozish", url=f"tg://user?id={uid}")]])

    for adm in ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=adm, photo=d['photo'], caption=cap, reply_markup=btn)
        except Exception as e:
            logging.warning(f"Admin {adm} ga bormadi: {e}")
    
    kb = kb_admin() if uid in ADMIN_IDS else kb_user()
    await call.message.answer(TEXTS['uz']['done'], reply_markup=kb)
    await state.clear()

async def main():
    await setup_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
