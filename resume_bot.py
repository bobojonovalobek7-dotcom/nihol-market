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
ADMIN_IDS = [356009218, 5341602920] # Super Adminlar
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
        'ask_location': "6. <b>📍 Lokatsiyangizni yuboring:</b>",
        'ask_phone': "7
