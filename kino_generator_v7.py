import os
import json
import time
import shutil
import traceback
import threading
import calendar
import re
import subprocess
import requests

from datetime import datetime, timedelta

import telebot
from telebot import types
from flask import Flask, request


# ============================================================
# KINO YASA BOT
# 1/8-QISM — ASOSIY SOZLAMALAR
# ============================================================


# =========================
# ENVIRONMENT SOZLAMALAR
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "5923596931"))

# AI API key

# ============================================================
# AI-SIZ VIDEO/KINO GENERATOR SOZLAMALARI
# ============================================================
# Bu generator generativ video AI xizmatlaridan foydalanmaydi.
# 2D puppet/skeletal animatsiya, Pillow/OpenCV va FFmpeg asosida ishlaydi.
MOVIE_FPS = int(os.environ.get("MOVIE_FPS", "5"))
MOVIE_WIDTH = int(os.environ.get("MOVIE_WIDTH", "854"))
MOVIE_HEIGHT = int(os.environ.get("MOVIE_HEIGHT", "480"))
MOVIE_SCENE_SECONDS = float(os.environ.get("MOVIE_SCENE_SECONDS", "12"))
MOVIE_MAX_SCENES = int(os.environ.get("MOVIE_MAX_SCENES", "600"))
MOVIE_RENDER_THREADS = max(1, int(os.environ.get("MOVIE_RENDER_THREADS", "1")))
MOVIE_TTS_ENABLED = os.environ.get("MOVIE_TTS_ENABLED", "1").lower() not in ("0", "false", "no")
MOVIE_TTS_VOICE = os.environ.get("MOVIE_TTS_VOICE", "tr")
MOVIE_JOBS_DIR = os.environ.get("MOVIE_JOBS_DIR", "kino_jobs")

# =========================
# ASOSIY TEKSHIRUVLAR
# =========================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable topilmadi."
    )

if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID environment variable topilmadi."
    )


# =========================
# TELEGRAM
# =========================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# =========================
# JSON SAQLASH
# =========================

DATA_FILE = "kino_yasa_data.json"


def load_json_data():
    default = {"users": {}, "referral_map": {}, "sales": [], "withdrawals": [], "month": {}, "month_reward": {}}
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key, value in default.items():
                    data.setdefault(key, value)
                return data
    except Exception as e:
        print("❌ JSON maʼlumotlarini yuklash xatosi:", type(e).__name__, e, flush=True)
    return default


def save_json_data():
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(DATA, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
        return True
    except Exception as e:
        print("❌ JSON saqlash xatosi:", type(e).__name__, e, flush=True)
        return False


DATA = load_json_data()
users = DATA["users"]
referral_map = DATA["referral_map"]
sales_rows = DATA["sales"]
withdrawals = DATA["withdrawals"]
month_reward = DATA["month_reward"]

print("🗄 JSON: lokal saqlash faol", flush=True)

# =========================
# FLASK
# =========================

app = Flask(__name__)


# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        json_string = request.get_data().decode("utf-8")

        update = telebot.types.Update.de_json(
            json_string
        )

        bot.process_new_updates(
            [update]
        )

        return "OK", 200

    except Exception as e:

        print(
            "❌ Webhook xatosi:",
            type(e).__name__,
            e,
            flush=True
        )

        traceback.print_exc()

        return "ERROR", 500

@app.route("/", methods=["GET"])
def home():

    return "Kino Yasa Bot ishlayapti!", 200


# =========================
# KANALLAR
# =========================

CHANNELS = [
    "@RIYAL_FIT_1",
    "@kupon_uz_bepul"
]


# =========================
# Vaqtinchalik HOLATLAR
# =========================

holat = {}


# =========================
# USERLAR
# =========================



# =========================
# BALANSLAR
# =========================

balances = {}


# =========================
# JSON SAQLASH HOLATLARI
# =========================

REFERRAL_FILE = DATA_FILE
MONTH_FILE = DATA_FILE

# =========================
# AI KINO YARATISH HOLATI
# =========================

movie_generation_state = {}
movie_add_state = {}
withdraw_state = {}

MOVIES_FILE = "kinolar.json"
# Kino beruvchi alohida Telegram bot username
MOVIE_BOT_USERNAME = os.environ.get("MOVIE_BOT_USERNAME", "").strip().lstrip("@").replace("https://t.me/", "").strip("/")
try:
    with open(MOVIES_FILE, "r", encoding="utf-8") as f:
        kinolar = json.load(f)
except Exception:
    kinolar = {}

def save_movies():
    try:
        with open(MOVIES_FILE, "w", encoding="utf-8") as f:
            json.dump(kinolar, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("❌ Kinolarni saqlash xatosi:", type(e).__name__, e, flush=True)
        return False


# =========================
# BOTNING ISH REJIMI
# =========================

BOT_NAME = "Kino Yasa Bot"


# =========================
# DIAGNOSTIKA
# =========================

diagnostic_errors = {}


# =========================
# BACKUP
# =========================

AUTO_BACKUP_FILE = "kino_yasa_bot_AUTO_BACKUP.py"


# =========================
# YORDAMCHI FUNKSIYA
# =========================

def send_ai_text(chat_id, title, text, reply_markup=None):
    text = str(text or "").strip()
    if not text:
        return
    limit = 3900
    parts = [text[i:i+limit] for i in range(0, len(text), limit)]
    for i, part in enumerate(parts):
        prefix = title if i == 0 else ""
        markup = reply_markup if i == len(parts) - 1 else None
        bot.send_message(chat_id, (prefix + "\n\n" if prefix else "") + part, reply_markup=markup)


def safe_int(value, default=0):

    try:
        return int(value or default)

    except Exception:

        return default


# =========================
# USER DEFAULT
# =========================

def user_defaults(
    uid,
    name,
    username=None
):

    return {

        "user_id": int(uid),

        "full_name": name or "Foydalanuvchi",

        "username": username,

        "balance": 0,

        "rating_ball": 0,

        "monthly_rating_ball": 0,

        "referrals": 0,

        "referral_bonus": 0,

        "total_movies": 0,

        "total_sales": 0,

        "movie_rights": 0,

        "premium_until": None,

    }


# =========================
# LEVEL
# =========================

def level_from_ball(ball):

    ball = safe_int(ball)

    if ball >= 80:
        return "💎 Elita hamkor"

    if ball >= 40:
        return "🥈 Kumush hamkor"

    if ball >= 20:
        return "🥉 Faol hamkor"

    return "🌱 Yangi hamkor"


# =========================
# JSON SAQLASH FUNKSIYALARI
# =========================

def save_referral_map():
    DATA["referral_map"] = referral_map
    return save_json_data()

def save_month_reward():
    DATA["month_reward"] = month_reward
    return save_json_data()


def save_user_to_json(uid):
    uid = str(uid)
    if uid not in users:
        return False
    user = users[uid]
    for key in ("balance", "rating_ball", "monthly_rating_ball", "referrals", "referral_bonus", "total_movies", "total_sales", "movie_rights"):
        user[key] = safe_int(user.get(key))
    user["level"] = level_from_ball(user.get("rating_ball"))
    DATA["users"] = users
    return save_json_data()


def get_user(uid):
    uid = str(uid)
    row = users.get(uid)
    if not row:
        return None
    row = dict(row)
    for key in ("user_id", "balance", "rating_ball", "monthly_rating_ball", "referrals", "referral_bonus", "total_movies", "total_sales", "movie_rights"):
        row[key] = safe_int(row.get(key))
    row["level"] = level_from_ball(row.get("rating_ball"))
    users[uid] = row
    return row


def add_user(uid, name, username=None):
    uid = str(uid)
    if uid in users:
        user = users[uid]
        changed = False
        if name and user.get("full_name") != name:
            user["full_name"] = name; changed = True
        if username is not None and user.get("username") != username:
            user["username"] = username; changed = True
        if changed:
            save_user_to_json(uid)
        return user
    user = user_defaults(uid, name, username)
    users[uid] = user
    save_user_to_json(uid)
    return user

print(
    "🚀 Kino Yasa Bot 1/8-qism yuklandi",
    flush=True
)# ============================================================
# KINO YASA BOT
# 3/8-QISM — MAJBURIY OBUNA / START / REFERAL
# ============================================================


# =========================
# MAJBURIY OBUNA TEKSHIRISH
# =========================

def check_sub(user_id):

    try:

        for channel in CHANNELS:

            member = bot.get_chat_member(
                channel,
                user_id
            )

            if member.status not in [
                "member",
                "administrator",
                "creator"
            ]:

                return False

        return True

    except Exception as e:

        print(
            "❌ Obuna tekshirish xatosi:",
            type(e).__name__,
            e
        )

        return False


# =========================
# START
# =========================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    uid = str(
        message.chat.id
    )

    user = add_user(
        uid,
        message.from_user.first_name
        or "Foydalanuvchi",
        message.from_user.username
    )

    if not user:

        bot.send_message(
            message.chat.id,
            "❌ Hisobingizni yaratishda "
            "xatolik yuz berdi."
        )

        return


    # =========================
    # REFERAL /START ID
    # =========================

    args = (
        message.text or ""
    ).split()

    if len(args) > 1:

        ref = str(
            args[1]
        ).strip()

        if (
            ref != uid
            and ref in users
            and uid not in referral_map
        ):

            referral_map[uid] = ref

            save_referral_map()

            users[ref]["referrals"] = (
                safe_int(
                    users[ref].get(
                        "referrals"
                    )
                ) + 1
            )

            save_user_to_json(
                ref
            )


    # =========================
    # MAJBURIY OBUNA
    # =========================

    if not check_sub(
        message.chat.id
    ):

        markup = (
            types.InlineKeyboardMarkup()
        )

        markup.add(

            types.InlineKeyboardButton(
                "📢 1-kanal",
                url="https://t.me/kupon_uz_bepul"
            )

        )

        markup.add(

            types.InlineKeyboardButton(
                "📢 2-kanal",
                url="https://t.me/RIYAL_FIT_1"
            )

        )

        markup.add(

            types.InlineKeyboardButton(
                "✅ Tekshirish",
                callback_data="check_sub"
            )

        )

        bot.send_message(

            message.chat.id,

            "❌ Avval quyidagi "
            "kanallarga obuna bo'ling.\n\n"
            "Obuna bo'lgach "
            "«✅ Tekshirish» tugmasini bosing.",

            reply_markup=markup
        )

        return


    # =========================
    # ASOSIY MENYU
    # =========================

    markup = (
        types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )
    )

    markup.row(
        "🎬 Kino yaratish",
        "🎥 Kino tavsiya"
    )

    markup.row(
        "🤝 Hamkorlik"
    )

    markup.row(
        "👨‍🦱 Mening hisobim",
        "🏆 TOP 10"
    )

    bot.send_message(

        message.chat.id,

        "🏠 Xush kelibsiz!\n\n"
        "🤖 Kino Yasa Botga xush kelibsiz.\n\n"
        "Bo'limlardan birini tanlang.",

        reply_markup=markup
    )


# =========================
# OBUNANI QAYTA TEKSHIRISH
# =========================

@bot.callback_query_handler(
    func=lambda c:
        c.data == "check_sub"
)
def check_sub_button(call):

    if check_sub(
        call.message.chat.id
    ):

        bot.answer_callback_query(
            call.id,
            "✅ Obuna tasdiqlandi!"
        )

        try:

            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

        except Exception:
            pass

        start(
            call.message
        )

    else:

        bot.answer_callback_query(
            call.id,
            "❌ Hali barcha kanallarga obuna bo'lmagansiz. Avval obunani yakunlang va qayta tekshiring.",
            show_alert=True
        )

# ============================================================
# OPENROUTER — FAQAT SSENARIY VA DAVOMIYLIK UCHUN
# ============================================================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "openrouter/free")

def ask_ai(prompt, max_retries=3):
    if not OPENROUTER_API_KEY:
        return None
    payload={"model":AI_MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":6000}
    for attempt in range(max_retries):
        try:
            r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json","HTTP-Referer":"https://openrouter.ai/","X-Title":"Kino Yasa Bot"},json=payload,timeout=(20,180))
            if r.status_code in (408,429,500,502,503,504):
                if attempt < max_retries-1: time.sleep(3*(attempt+1)); continue
            r.raise_for_status()
            choices=r.json().get("choices") or []
            content=(choices[0].get("message") or {}).get("content") if choices else None
            if isinstance(content,list): content="".join(x.get("text","") if isinstance(x,dict) else str(x) for x in content)
            if content and str(content).strip(): return str(content).strip()
        except Exception:
            if attempt < max_retries-1: time.sleep(3*(attempt+1))
    return None

def _scenario_prompt(description):
    return (
        "Sen professional o'zbek kino ssenariy muallifisan. Foydalanuvchi bergan oddiy g'oya yoki voqeani TO'LIQ kino ssenariysiga aylantir. "
        "Foydalanuvchi faqat nima bo'lishini qisqa yozgan bo'lsa ham, uni sahnalarga bo'l, qahramonlarni aniq nomla, harakatlar, joy, kamera tasviri va dialoglar qo'sh. "
        "Har bir dialog aynan 'Ism: gap' shaklida bo'lsin. Qahramonlar bo'limida ism va rolini ko'rsat. Sahnalar ketma-ket va ijroga tayyor bo'lsin. "
        "Matn faqat o'zbek tilida bo'lsin.\n\nFOYDALANUVCHI G'OYASI:\n" + str(description) + "\n\n"
        "Format: 🎬 Kino nomi; 🎭 Janr; 👤 Qahramonlar; 🎞 Sahnalar; 💬 Dialoglar; 🏁 Yakun.\n"
    )

def _duration_prompt(state, duration):
    return (
        "Quyidagi ssenariyni " + str(duration) + " davomiylikka moslab PROFESSIONAL kino ssenariysiga aylantir. "
        "Kerak bo'lsa yangi sahnalar, harakatlar, dialoglar va o'tishlarni qo'sh. Qahramon nomlarini o'zgartirma. "
        "Har bir dialog 'Ism: gap' ko'rinishida bo'lsin.\n\nSSENARIY:\n" + str(state.get("scenario", "")) + "\n"
    )

# ============================================================
# AI-SIZ KINO GENERATOR — BOSQICHLAR
# ============================================================


def _movie_buttons(uid, step="character_menu"):
    markup = types.InlineKeyboardMarkup()
    if step == "character_menu":
        markup.add(types.InlineKeyboardButton("🖼 Personaj rasmi yuborish", callback_data=f"actor_photo:{uid}"))
        markup.add(types.InlineKeyboardButton("⏭ Personaj tanlamaslik", callback_data=f"chars_done:{uid}"))
        markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"main_menu:{uid}"))
    elif step == "photo_actor_next":
        markup.add(types.InlineKeyboardButton("➕ Keyingi personaj rasmi", callback_data=f"actor_photo_more:{uid}"))
        markup.add(types.InlineKeyboardButton("✅ Tayyor", callback_data=f"chars_done:{uid}"))
    elif step == "location_menu":
        markup.add(types.InlineKeyboardButton("🖼 Lokatsiya rasmi yuborish", callback_data=f"loc_photo:{uid}"))
        markup.add(types.InlineKeyboardButton("⏭ Lokatsiya tanlamaslik", callback_data=f"loc_skip:{uid}"))
        markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"chars_done:{uid}"))
    elif step == "photo_location_next":
        markup.add(types.InlineKeyboardButton("➕ Yana lokatsiya rasmi", callback_data=f"loc_photo_more:{uid}"))
        markup.add(types.InlineKeyboardButton("✅ Tayyor", callback_data=f"location_done:{uid}"))
    elif step == "cancel_confirm":
        markup.add(types.InlineKeyboardButton("✅ Ha, bekor qilish", callback_data=f"cancel_yes:{uid}"))
        markup.add(types.InlineKeyboardButton("❌ Yo'q", callback_data=f"cancel_no:{uid}"))
    elif step == "create":
        markup.add(types.InlineKeyboardButton("🎬 Kino yasash", callback_data=f"generate_video:{uid}"))
        markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"duration_back:{uid}"))
    return markup


def _show_character_menu(chat_id, uid):
    state = movie_generation_state.get(uid)
    if not state:
        return
    state["step"] = "character_menu"
    bot.send_message(chat_id, "👤 <b>Personajlar</b>\n\nSsenariydagi rollar avtomatik aniqlanadi. Xohlasangiz har bir personaj uchun o'zingizning rasmingizni yuboring. Rasm yubormasangiz, personaj avtomatik chizilgan puppet sifatida yaratiladi.", reply_markup=_movie_buttons(uid, "character_menu"))


def _show_location_menu(chat_id, uid):
    state = movie_generation_state.get(uid)
    if not state:
        return
    state["step"] = "location_menu"
    bot.send_message(chat_id, "📍 <b>Lokatsiya</b>\n\nXohlasangiz lokatsiya rasmini yuboring. Rasm yubormasangiz, ssenariy mazmunidagi kalit so'zlarga mos dekorativ lokatsiya avtomatik chiziladi.", reply_markup=_movie_buttons(uid, "location_menu"))


def _start_duration(chat_id, uid):
    state = movie_generation_state.get(uid)
    if not state:
        return
    state["step"] = "video_duration"
    bot.send_message(chat_id, "⏱ <b>Kino davomiyligini yozing.</b>\n\nMasalan: <b>1 daqiqa</b>, <b>5 daqiqa</b>, <b>30 daqiqa</b> yoki <b>1 soat</b>.\n\n⚠️ Maksimal: 2 soat.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("main_menu:"))
def main_menu_callback(call):
    uid = str(call.message.chat.id)
    movie_generation_state.pop(uid, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🏠 Asosiy menyu", reply_markup=main_menu_markup())


@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_yes:") or c.data.startswith("cancel_no:"))
def cancel_movie_callback(call):
    uid = str(call.message.chat.id)
    if call.data.startswith("cancel_yes:"):
        movie_generation_state.pop(uid, None)
        bot.answer_callback_query(call.id, "✅ Bekor qilindi")
        bot.send_message(call.message.chat.id, "🏠 Asosiy menyu", reply_markup=main_menu_markup())
    else:
        _show_character_menu(call.message.chat.id, uid)
        bot.answer_callback_query(call.id, "↩️ Davom etamiz")


@bot.callback_query_handler(func=lambda c: c.data.startswith("actor_photo:") or c.data.startswith("actor_photo_more:"))
def actor_photo_callback(call):
    uid = str(call.message.chat.id)
    state = movie_generation_state.get(uid)
    if not state or not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Kino holati topilmadi.", show_alert=True)
        return
    state["step"] = "actor_photo"
    bot.answer_callback_query(call.id, "🖼 Rasm yuboring")
    bot.send_message(call.message.chat.id, "🖼 <b>Personaj rasmini yuboring.</b>\n\nEng yaxshi natija uchun odamning to'liq bo'yi ko'ringan rasm yuboring. Keyin qaysi qahramon roliga tegishli ekanini yozasiz.")


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "actor_photo", content_types=["photo"])
def receive_actor_photo(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    if not state:
        return
    state["pending_actor_photo"] = message.photo[-1].file_id
    state["step"] = "actor_photo_role"
    bot.send_message(message.chat.id, "👤 Bu rasm qaysi ssenariy qahramoniga tegishli?\n\nMasalan: <b>Sardor</b>")


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "actor_photo_role")
def receive_actor_photo_role(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    role = (message.text or "").strip()
    if not state:
        return
    if not role:
        bot.send_message(message.chat.id, "❌ Qahramon nomini yozing.")
        return
    state.setdefault("actor_photos", []).append({"role": role, "photo": state.pop("pending_actor_photo", None)})
    state["step"] = "actor_photo_wait"
    bot.send_message(message.chat.id, f"✅ <b>{role}</b> uchun rasm saqlandi.", reply_markup=_movie_buttons(uid, "photo_actor_next"))


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "actor_photo_wait")
def receive_actor_photo_wait(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    text = (message.text or "").strip().lower()
    if not state:
        return
    if text in ("tayyor", "tayyor.", "ok", "ok."):
        _show_location_menu(message.chat.id, uid)
        return
    if message.photo:
        state["step"] = "actor_photo"
        receive_actor_photo(message)
        return
    bot.send_message(message.chat.id, "🖼 Rasm yuboring yoki <b>TAYYOR</b> deb yozing.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("chars_done:"))
def chars_done_callback(call):
    uid = str(call.message.chat.id)
    if not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Avval obuna bo'ling.", show_alert=True)
        return
    if uid in movie_generation_state:
        _show_location_menu(call.message.chat.id, uid)
    bot.answer_callback_query(call.id, "✅ Personajlar bosqichi tugadi")


@bot.callback_query_handler(func=lambda c: c.data.startswith("loc_photo:") or c.data.startswith("loc_photo_more:"))
def location_photo_callback(call):
    uid = str(call.message.chat.id)
    state = movie_generation_state.get(uid)
    if not state or not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Kino holati topilmadi.", show_alert=True)
        return
    state["step"] = "location_photo"
    bot.answer_callback_query(call.id, "🖼 Lokatsiya rasmi")
    bot.send_message(call.message.chat.id, "🖼 <b>Lokatsiya rasmini yuboring.</b> Bir nechta rasm yuborishingiz mumkin.")


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "location_photo", content_types=["photo"])
def receive_location_photo(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    if not state:
        return
    state.setdefault("location_images", []).append(message.photo[-1].file_id)
    state["step"] = "location_photo_wait"
    bot.send_message(message.chat.id, f"✅ Lokatsiya rasmi qabul qilindi ({len(state['location_images'])}).", reply_markup=_movie_buttons(uid, "photo_location_next"))


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "location_photo_wait")
def receive_location_photo_wait(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    text = (message.text or "").strip().lower()
    if not state:
        return
    if text in ("tayyor", "tayyor.", "ok", "ok."):
        state["step"] = "location_done"
        _start_duration(message.chat.id, uid)
        return
    if message.photo:
        state["step"] = "location_photo"
        receive_location_photo(message)
        return
    bot.send_message(message.chat.id, "🖼 Yana rasm yuboring yoki <b>TAYYOR</b> deb yozing.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("loc_skip:"))
def location_skip_callback(call):
    uid = str(call.message.chat.id)
    state = movie_generation_state.get(uid)
    if not state or not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Kino holati topilmadi.", show_alert=True)
        return
    state["location_auto"] = True
    state["location_images"] = []
    bot.answer_callback_query(call.id, "⏭ Lokatsiya avtomatik tanlanadi")
    _start_duration(call.message.chat.id, uid)


@bot.callback_query_handler(func=lambda c: c.data.startswith("location_done:"))
def location_done_callback(call):
    uid = str(call.message.chat.id)
    if uid in movie_generation_state:
        _start_duration(call.message.chat.id, uid)
    bot.answer_callback_query(call.id, "✅ Lokatsiya bosqichi tugadi")


@bot.callback_query_handler(func=lambda c: c.data.startswith("duration_back:"))
def duration_back_callback(call):
    uid = str(call.message.chat.id)
    if uid in movie_generation_state:
        _show_location_menu(call.message.chat.id, uid)
    bot.answer_callback_query(call.id, "⬅️ Orqaga")


def parse_duration_minutes(value):
    text = str(value or "").lower().strip()
    h = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:soat|hour|h)", text)
    m = re.search(r"(\d+)\s*(?:daqiqa|daq|min|minute|m)", text)
    total = 0.0
    if h:
        total += float(h.group(1).replace(",", ".")) * 60
    if m:
        total += float(m.group(1))
    if total == 0:
        try:
            total = float(text.replace(",", "."))
        except Exception:
            return None
    return int(round(total))


def movie_price(minutes):
    if minutes is None or minutes <= 0 or minutes > 120:
        return None
    if minutes <= 20:
        return 2000
    if minutes <= 40:
        return 5000
    return 30000


def payment_markup(uid):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 To'lov qilish", callback_data=f"movie_pay:{uid}"))
    markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"movie_cancel:{uid}"))
    return markup


def deliver_paid_movie(uid):
    state = movie_generation_state.get(str(uid))
    if not state:
        return False
    video_path = state.get("video_path")
    try:
        _send_saved_movie(int(uid), video_path, "🎬 Kino tayyor! To'lovingiz tasdiqlandi.", protect_content=False)
        state["delivered"] = True
        state["step"] = "delivered"
        return True
    except Exception as e:
        print("❌ To'lovdan keyingi video yuborish xatosi:", type(e).__name__, e, flush=True)
        try:
            bot.send_message(int(uid), "⚠️ To'lov tasdiqlandi, lekin video yuborishda texnik xato bo'ldi. Admin qayta yuborishni tekshiradi.")
        except Exception:
            pass
        return False

@bot.callback_query_handler(func=lambda c: c.data.startswith("movie_pay:"))
def movie_pay_callback(call):
    uid = str(call.message.chat.id)
    state = movie_generation_state.get(uid)
    if not state or state.get("step") != "payment_pending":
        bot.answer_callback_query(call.id, "❌ To'lov holati topilmadi.", show_alert=True)
        return
    price = safe_int(state.get("price"))
    bot.answer_callback_query(call.id, "💳 To'lov bosqichi ochildi.")
    state["step"] = "payment_receipt"
    bot.send_message(
        call.message.chat.id,
        f"💳 <b>To'lov: {price:,} so'm</b>\n\n"
        "To'lovni admin ko'rsatgan karta/rekvizitga amalga oshiring va to'lov cheki (rasm yoki fayl)ni shu yerga yuboring.\n\n"
        "📩 Chek kelgach admin tasdiqlaydi va video sizga yuboriladi.\n\n"
        "👤 Admin: @abdulqodir_royal"
    )


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step") == "payment_receipt", content_types=["photo", "document", "text"])
def receive_payment_receipt(message):
    uid = str(message.chat.id)
    state = movie_generation_state.get(uid)
    if not state:
        return
    receipt = None
    if message.photo:
        receipt = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.document:
        receipt = {"type": "document", "file_id": message.document.file_id}
    elif message.text:
        bot.send_message(message.chat.id, "📩 Iltimos, to'lov chekini rasm yoki fayl ko'rinishida yuboring.")
        return
    state["receipt"] = receipt
    state["step"] = "payment_review"
    price = safe_int(state.get("price"))
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ To'lovni tasdiqlash", callback_data=f"movie_payment_ok:{uid}"), types.InlineKeyboardButton("❌ Rad etish", callback_data=f"movie_payment_no:{uid}"))
    bot.send_message(message.chat.id, f"📩 Chek qabul qilindi. Admin tekshiradi.\n\n💰 Summa: {price:,} so'm")
    admin_text = f"💳 <b>Kino to'lovi</b>\n\n👤 Foydalanuvchi: {uid}\n💰 Summa: {price:,} so'm\n⏱ Davomiylik: {state.get('duration_minutes')} daqiqa"
    bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
    try:
        if receipt["type"] == "photo":
            bot.send_photo(ADMIN_ID, receipt["file_id"], caption="📩 To'lov cheki")
        else:
            bot.send_document(ADMIN_ID, receipt["file_id"], caption="📩 To'lov cheki")
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("movie_payment_ok:") or c.data.startswith("movie_payment_no:"))
def movie_payment_review(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q.", show_alert=True)
        return
    uid = call.data.split(":", 1)[1]
    state = movie_generation_state.get(uid)
    if not state or state.get("step") != "payment_review":
        bot.answer_callback_query(call.id, "❌ To'lov holati topilmadi.", show_alert=True)
        return
    if call.data.startswith("movie_payment_no:"):
        state["step"] = "payment_pending"
        bot.answer_callback_query(call.id, "❌ To'lov rad etildi.")
        bot.send_message(int(uid), "❌ To'lov cheki tasdiqlanmadi. Iltimos, to'g'ri chek yuboring.", reply_markup=payment_markup(uid))
        return
    price = safe_int(state.get("price"))
    if record_sale(uid, f"MOVIE_{state.get('duration_minutes', 0)}", price):
        users[uid]["total_movies"] = safe_int(users[uid].get("total_movies")) + 1
        save_user_to_json(uid)
        state["step"] = "paid"
        bot.answer_callback_query(call.id, "✅ To'lov tasdiqlandi.")
        bot.send_message(int(uid), "✅ To'lovingiz tasdiqlandi.\n\n🎬 Video hozir yuboriladi.")
        deliver_paid_movie(uid)
    else:
        bot.answer_callback_query(call.id, "❌ Sotuvni saqlashda xato.", show_alert=True)

# =========================
# REFERAL BUYRUQI
# =========================

@bot.message_handler(
    commands=["referal"]
)
def referal(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    try:

        username = (
            bot.get_me().username
        )

        link = (
            f"https://t.me/"
            f"{username}"
            f"?start={message.chat.id}"
        )

        bot.send_message(

            message.chat.id,

            "👥 Referal havolangiz:\n\n"
            f"{link}\n\n"
            "💰 Sizning havolangiz "
            "orqali kelgan foydalanuvchi "
            "Premium yoki boshqa "
            "pullik xizmat sotib olsa, "
            "sizga bonus beriladi."

        )

    except Exception as e:

        print(
            "❌ Referal link xatosi:",
            type(e).__name__,
            e
        )

        bot.send_message(
            message.chat.id,
            "❌ Referal havolasini "
            "yaratishda xato yuz berdi."
        )


# =========================
# HAMKORLIK
# =========================

@bot.message_handler(
    func=lambda m:
        m.text == "🤝 Hamkorlik"
)
def hamkorlik(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    try:

        username = (
            bot.get_me().username
        )

        link = (
            f"https://t.me/"
            f"{username}"
            f"?start={message.chat.id}"
        )

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )
        )

        markup.row(
            "💰 Balans",
            "💸 Pul yechish"
        )

        markup.row(
            "🏡 Bosh menyu"
        )

        bot.send_message(

            message.chat.id,

            "🤝 Assalomu alaykum!\n\n"

            "😊 Hamkorlik dasturiga "
            "xush kelibsiz!\n"
            "Sizni ko'rganimizdan "
            "xursandmiz. ❤️\n\n"

            "❓ Hamkorlik dasturi "
            "qanday ishlaydi?\n\n"

            "🔗 Referal havolangizni "
            "do'stlaringizga yuboring.\n"

            "💎 Agar ular sizning "
            "havolangiz orqali botga "
            "kirib, pullik xizmat "
            "sotib olsa,\n"

            "💰 sizning balansingizga "
            "500 so'm bonus qo'shiladi.\n\n"

            "💵 Yig'ilgan bonusni "
            "istalgan vaqtda kartaingizga "
            "yechib olishingiz mumkin.\n\n"

            f"👥 Referal havolangiz:\n\n"
            f"{link}\n\n"

            "👇 Quyidagi tugmalardan "
            "foydalaning.",

            reply_markup=markup
        )

    except Exception as e:

        print(
            "❌ Hamkorlik xatosi:",
            type(e).__name__,
            e
        )


def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎬 Kino yaratish", "🎥 Kino tavsiya")
    markup.row("🤝 Hamkorlik")
    markup.row("👨‍🦱 Mening hisobim", "🏆 TOP 10")
    return markup


# =========================
# BOSH MENYU
# =========================

@bot.message_handler(func=lambda m: m.text == "🏡 Bosh menyu")
def back_menu(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return
    bot.send_message(message.chat.id, "🏠 Asosiy menyu", reply_markup=main_menu_markup())

# ============================================================
# KINO YASA BOT
# 4/8-QISM — PREMIUM / SOTUV / SALES / HISOB
# ============================================================


# =========================
# PREMIUM BALL
# =========================

def rating_points_for_user(current_ball):

    current_ball = safe_int(
        current_ball
    )

    if current_ball >= 80:
        return 5

    if current_ball >= 40:
        return 3

    if current_ball >= 20:
        return 2

    return 1


# =========================
# PREMIUM BERISH
# =========================

def give_premium_to_user(
    uid,
    days=30
):

    uid = str(uid)

    if uid not in users:
        return False

    users[uid]["premium_until"] = (
        datetime.now()
        + timedelta(days=days)
    ).strftime(
        "%Y-%m-%d"
    )

    return save_user_to_json(
        uid
    )


# =========================
# PREMIUM MENU
# =========================

@bot.message_handler(
    commands=["premium"]
)
def premium_menu(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    if message.chat.id != ADMIN_ID:
        return

    bot.send_message(

        message.chat.id,

        "💎 Premium boshqaruv\n\n"

        "/givepremium ID - "
        "Premium berish\n"

        "/delpremium ID - "
        "Premiumni olish"
    )


# =========================
# ADMIN PREMIUM BERISH
# =========================

@bot.message_handler(
    commands=["givepremium"]
)
def give_premium(message):

    if message.chat.id != ADMIN_ID:
        return

    data = (
        message.text or ""
    ).split()

    if len(data) < 2:

        bot.send_message(
            message.chat.id,
            "❌ ID kiriting."
        )

        return

    uid = str(
        data[1]
    )

    user = get_user(
        uid
    )

    if not user:

        bot.send_message(
            message.chat.id,
            "❌ Foydalanuvchi "
            "topilmadi."
        )

        return

    users[uid] = user

    users[uid][
        "premium_until"
    ] = (
        datetime.now()
        + timedelta(days=30)
    ).strftime(
        "%Y-%m-%d"
    )

    if save_user_to_json(
        uid
    ):

        bot.send_message(
            message.chat.id,
            "✅ Premium berildi "
            "va JSON'ga saqlandi."
        )

    else:

        bot.send_message(
            message.chat.id,
            "❌ Premium berildi, "
            "lekin JSON'ga "
            "saqlashda xato."
        )


# =========================
# PREMIUM OLIB TASHLASH
# =========================

@bot.message_handler(
    commands=["delpremium"]
)
def del_premium(message):

    if message.chat.id != ADMIN_ID:
        return

    data = (
        message.text or ""
    ).split()

    if len(data) < 2:

        bot.send_message(
            message.chat.id,
            "❌ ID kiriting."
        )

        return

    uid = str(
        data[1]
    )

    user = get_user(
        uid
    )

    if not user:

        bot.send_message(
            message.chat.id,
            "❌ Foydalanuvchi "
            "topilmadi."
        )

        return

    users[uid] = user

    users[uid][
        "premium_until"
    ] = None

    if save_user_to_json(
        uid
    ):

        bot.send_message(
            message.chat.id,
            "✅ Premium olib "
            "tashlandi va JSON "
            "yangilandi."
        )

    else:

        bot.send_message(
            message.chat.id,
            "❌ Premium olib tashlandi, "
            "lekin JSON'ga "
            "saqlashda xato."
        )


# =========================
# SALES YUKLASH
# =========================

def fetch_sales_rows(columns="user_id,movie_code,amount", start_date=None, end_date=None):
    rows = list(sales_rows)
    if start_date or end_date:
        filtered = []
        for row in rows:
            created = str(row.get("created_at", ""))
            if start_date and created < str(start_date):
                continue
            if end_date and created >= str(end_date):
                continue
            filtered.append(row)
        rows = filtered
    return [{k: row.get(k) for k in columns.split(",")} for row in rows]


def record_sale(user_id, movie_code, amount):
    """Sotuvni JSON'ga yozadi va referal egasiga bonus beradi."""
    uid = str(user_id)
    amount = safe_int(amount)
    row = {"user_id": int(uid), "movie_code": str(movie_code), "amount": amount, "created_at": datetime.now().isoformat()}
    sales_rows.append(row)
    if uid in users:
        users[uid]["total_sales"] = safe_int(users[uid].get("total_sales")) + 1
        users[uid]["rating_ball"] = safe_int(users[uid].get("rating_ball")) + 1
        users[uid]["monthly_rating_ball"] = safe_int(users[uid].get("monthly_rating_ball")) + 1
    ref = referral_map.get(uid)
    if ref and ref in users:
        bonus = 500
        users[ref]["balance"] = safe_int(users[ref].get("balance")) + bonus
        users[ref]["referral_bonus"] = safe_int(users[ref].get("referral_bonus")) + bonus
    DATA["sales"] = sales_rows
    DATA["users"] = users
    return save_json_data()

# =========================
# /SALES
# =========================

@bot.message_handler(
    commands=["sales"]
)
def sales_info(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    print(
        f"🔎 /sales handler chaqirildi: "
        f"chat_id={message.chat.id}, "
        f"ADMIN_ID={ADMIN_ID}",
        flush=True
    )

    if message.chat.id != ADMIN_ID:
        return

    try:

        rows = fetch_sales_rows(
            "user_id,movie_code,amount"
        )

        premium_soni = 0

        umumiy_tushum = 0

        for row in rows:

            amount = safe_int(
                row.get("amount")
            )

            movie_code = (
                row.get("movie_code")
                or ""
            )

            umumiy_tushum += amount

            if (
                movie_code
                == "PREMIUM"
            ):

                premium_soni += 1


        mukofot = int(
            umumiy_tushum * 0.25
        )

        bot.send_message(

            message.chat.id,

            "📊 Sotuvlar hisoboti\n\n"

            f"⭐ Premium: "
            f"{premium_soni} ta\n\n"

            f"💰 Umumiy tushum: "
            f"{umumiy_tushum} so'm\n\n"

            "🏆 Oylik mukofot fondi "
            "(25%):\n"

            f"{mukofot} so'm"
        )

    except Exception as e:

        error_text = (
            f"{type(e).__name__}: {e}"
        )

        print(
            "❌ Sales statistikasi "
            "xatosi:",
            error_text
        )

        bot.send_message(
            message.chat.id,
            "❌ Sotuvlar statistikasini "
            "olishda xato."
        )


# =========================
# MENING HISOBIM
# =========================

@bot.message_handler(
    func=lambda m:
        m.text == "👨‍🦱 Mening hisobim"
)
def my_account(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    uid = str(
        message.chat.id
    )

    user = (
        get_user(uid)
        or users.get(uid, {})
    )

    if not user:

        bot.send_message(
            message.chat.id,
            "❌ Hisob ma'lumotlari "
            "topilmadi."
        )

        return

    users[uid] = user

    pul = safe_int(
        user.get(
            "balance",
            balances.get(uid, 0)
        )
    )

    balances[uid] = pul

    referrals = safe_int(
        user.get("referrals")
    )

    total_sales = safe_int(
        user.get("total_sales")
    )

    level = level_from_ball(
        user.get("rating_ball")
    )

    rating_ball = safe_int(
        user.get("rating_ball")
    )

    premium_sale = sum(1 for row in sales_rows if str(row.get("user_id")) == uid and row.get("movie_code") == "PREMIUM")


    bot.send_message(

        message.chat.id,

        f"""👨‍🦱 Mening hisobim

🆔 ID: {uid}
👤 Ism: {user.get("full_name") or message.from_user.first_name}

👥 Taklif qilganlar: {referrals} ta
💎 Premium sotuv: {premium_sale} ta
🛒 Jami sotuv: {total_sales} ta

🏅 Unvon: {level}
⭐ Reyting bali: {rating_ball}

💰 Balans: {pul} so'm
🎁 Bepul kino huquqi: {safe_int(user.get("movie_rights"))} ta
"""
    )


# =========================
# BALANS
# =========================

@bot.message_handler(
    commands=["balance"]
)
def balance(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    uid = str(
        message.chat.id
    )

    if uid not in users:

        user = get_user(
            uid
        )

        if user:

            users[uid] = user

            balances[uid] = safe_int(
                user.get("balance")
            )

    pul = safe_int(
        balances.get(uid)
    )

    bot.send_message(

        message.chat.id,

        f"💰 Balansingiz: "
        f"{pul} so'm"
    )


@bot.message_handler(
    func=lambda m:
        m.text == "💰 Balans"
)
def balance_button(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    uid = str(
        message.chat.id
    )

    if uid not in users:

        user = get_user(
            uid
        )

        if user:

            users[uid] = user

            balances[uid] = safe_int(
                user.get("balance")
            )

    pul = safe_int(
        balances.get(uid)
    )

    bot.send_message(

        message.chat.id,

        f"💰 Sizning balansingiz: "
        f"{pul} so'm"
    )


print(
    "✅ 4/8-qism yuklandi",
    flush=True
)

# ============================================================
# KINO YASA BOT
# 5/8-QISM — REYTING TIZIMI
# ============================================================


# =========================
# REYTING BALLINI YANGILASH
# =========================

def add_rating_points(uid, points):
    uid = str(uid)
    if uid not in users:
        user = get_user(uid)
        if not user:
            return False
        users[uid] = user
    user = users[uid]
    points = safe_int(points)
    user["rating_ball"] = safe_int(user.get("rating_ball")) + points
    user["monthly_rating_ball"] = safe_int(user.get("monthly_rating_ball")) + points
    user["level"] = level_from_ball(user.get("rating_ball"))
    return save_user_to_json(uid)


# =========================
# MENING REYTINGIM
# =========================

@bot.message_handler(
    func=lambda m:
        m.text == "🏅 Mening reytingim"
)
def my_rating(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    uid = str(
        message.chat.id
    )

    user = (
        get_user(uid)
        or users.get(uid)
    )

    if not user:

        bot.send_message(
            message.chat.id,
            "❌ Reyting ma'lumotlari "
            "topilmadi."
        )

        return

    users[uid] = user

    rating_ball = safe_int(
        user.get("rating_ball")
    )

    monthly_rating_ball = safe_int(
        user.get("monthly_rating_ball")
    )

    level = level_from_ball(
        rating_ball
    )

    bot.send_message(

        message.chat.id,

        "🏅 <b>Mening reytingim</b>\n\n"

        f"⭐ Umumiy reyting bali: "
        f"<b>{rating_ball}</b>\n\n"

        f"📅 Oylik reyting bali: "
        f"<b>{monthly_rating_ball}</b>\n\n"

        f"🏆 Unvon: <b>{level}</b>"
    )


# =========================
# TOP 10
# =========================

def get_top10():
    # JSONdagi barcha foydalanuvchilarni ham, xotiradagi yangilanganlarini ham birlashtiramiz.
    merged = {}
    for uid, row in (DATA.get("users", {}) or {}).items():
        merged[str(uid)] = dict(row)
    for uid, row in users.items():
        merged[str(uid)] = dict(row)
    rows = []
    for uid, row in merged.items():
        item = dict(row)
        item["user_id"] = safe_int(item.get("user_id", uid))
        item["rating_ball"] = safe_int(item.get("rating_ball"))
        item["monthly_rating_ball"] = safe_int(item.get("monthly_rating_ball"))
        rows.append(item)
    rows.sort(key=lambda x: (safe_int(x.get("monthly_rating_ball")), safe_int(x.get("rating_ball"))), reverse=True)
    return rows[:10]

# =========================
# TOP 10 KO'RSATISH
# =========================

@bot.message_handler(
    func=lambda m:
        m.text == "🏆 TOP 10"
)
def top_rating(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return

    rows = get_top10()

    if not rows:

        bot.send_message(
            message.chat.id,
            "❌ Reyting ma'lumotlari "
            "topilmadi."
        )

        return

    text = (
        "🏆 <b>TOP 10 HAMKOR</b>\n\n"
    )

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, row in enumerate(
        rows,
        start=1
    ):

        if index <= 3:
            medal = medals[index - 1]
        else:
            medal = f"{index}."

        name = (
            row.get("full_name")
            or "Foydalanuvchi"
        )

        points = safe_int(
            row.get("rating_ball")
        )

        text += (
            f"{medal} {name} — "
            f"⭐ {points}\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================
# REYTING TIZIMI TEST
# =========================

@bot.message_handler(
    commands=["myrating"]
)
def my_rating_command(message):

    my_rating(message)


print(
    "✅ 5/8-qism yuklandi",
    flush=True
)

# ============================================================
# KINO YASA BOT — AI-SIZ PUPPET/SCENE ENGINE
# ============================================================

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import hashlib
import math
import wave


def _safe_font(size=28, bold=False):
    candidates = []
    if bold:
        candidates += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    candidates += ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _hash_color(text, offset=0):
    h = hashlib.sha256((str(text) + str(offset)).encode("utf-8")).digest()
    return tuple(70 + (h[i] % 150) for i in range(3))


def _extract_characters(scenario):
    text = str(scenario or "")
    found = []
    # Explicit dialogue speakers: Name: ..., Name — ..., Name - ...
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻ’'\- ]{2,32})\s*(?::|—|–|-|>)+\s*\S", line)
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip(" -—–")
            if name and name.lower() not in {x.lower() for x in found}:
                found.append(name)
    # Character section / role-like lines.
    for m in re.finditer(r"(?:qahramon|personaj|rol)\s*[:\-]?\s*([A-ZА-ЯЎҚҒҲ][A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻ’'\-]{2,24})", text, re.I):
        name = m.group(1).strip()
        if name.lower() not in {x.lower() for x in found}:
            found.append(name)
    # Common dialogue pattern: «Sardor»
    for m in re.finditer(r'(?:^|[\n.!?])\s*([A-ZА-ЯЎҚҒҲ][\wʻ’\-]{2,24})\s*[" :«]', text):
        name = m.group(1)
        if name.lower() not in {x.lower() for x in found}:
            found.append(name)
    if not found:
        # Deterministic generic roles; no AI inference.
        lower = text.lower()
        if any(x in lower for x in ("ikki do'st", "ikki do‘st", "ikki kishi", "er-xotin", "aka-uka")):
            found = ["Qahramon 1", "Qahramon 2"]
        elif any(x in lower for x in ("uch do'st", "uch do‘st", "uch kishi")):
            found = ["Qahramon 1", "Qahramon 2", "Qahramon 3"]
        else:
            found = ["Qahramon"]
    return found[:12]


def _extract_dialogues(scenario, characters):
    dialogues = []
    known = {x.lower(): x for x in characters}
    for line in str(scenario or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\s*([^:—–>-]{2,32})\s*(?::|—|–|-|>)\s*(.+)$", line)
        if m:
            speaker = re.sub(r"\s+", " ", m.group(1)).strip()
            text = m.group(2).strip()
            if speaker.lower() in known and text:
                dialogues.append({"speaker": known[speaker.lower()], "text": text})
    return dialogues


def _scenario_sentences(scenario):
    text = re.sub(r"\s+", " ", str(scenario or "")).strip()
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    parts = [x.strip() for x in parts if len(x.strip()) > 3]
    return parts or ["Hikoya boshlanadi."]


def _scene_count_for_duration(minutes):
    count = int(math.ceil((minutes * 60) / MOVIE_SCENE_SECONDS))
    return max(1, min(MOVIE_MAX_SCENES, count))


def _download_telegram_photo(file_id, target):
    info = bot.get_file(file_id)
    data = bot.download_file(info.file_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as f:
        f.write(data)
    return target


def _grabcut_person(image):
    """Deterministic foreground extraction for full-body photos; no generative AI."""
    try:
        import cv2
        import numpy as np
        rgb = image.convert("RGB")
        arr = np.array(rgb)
        h, w = arr.shape[:2]
        if h < 120 or w < 80:
            return rgb.convert("RGBA")
        mask = np.zeros((h, w), np.uint8)
        rect = (max(2, int(w*0.05)), max(2, int(h*0.02)), max(10, int(w*0.90)), max(10, int(h*0.96)))
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        cv2.grabCut(arr, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)
        # Keep central subject when GrabCut becomes overly conservative.
        if (alpha > 0).sum() < w*h*0.03:
            alpha[int(h*.03):int(h*.97), int(w*.18):int(w*.82)] = 255
        rgba = np.dstack([arr, alpha])
        return Image.fromarray(rgba, "RGBA")
    except Exception:
        return image.convert("RGBA")


def _make_photo_puppet(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((420, 620), Image.Resampling.LANCZOS)
    fg = _grabcut_person(im)
    bbox = fg.getbbox() or (0, 0, fg.width, fg.height)
    fg = fg.crop(bbox)
    fg.thumbnail((360, 600), Image.Resampling.LANCZOS)
    return {"kind": "photo", "image": fg}


def _make_auto_puppet(name):
    return {"kind": "auto", "name": name, "skin": _hash_color(name, 1), "shirt": _hash_color(name, 2), "pants": _hash_color(name, 3), "hair": _hash_color(name, 4)}


def _make_skeleton(w, h):
    return {
        "head": (w*0.50, h*0.12), "neck": (w*0.50, h*0.23),
        "ls": (w*0.37, h*0.27), "rs": (w*0.63, h*0.27),
        "le": (w*0.25, h*0.42), "re": (w*0.75, h*0.42),
        "lh": (w*0.43, h*0.56), "rh": (w*0.57, h*0.56),
        "lk": (w*0.40, h*0.74), "rk": (w*0.60, h*0.74),
        "lf": (w*0.35, h*0.94), "rf": (w*0.65, h*0.94),
    }


def _outfit_for(name, scene_index):
    outfits = [
        ((48, 92, 170), (35, 45, 65)),
        ((150, 55, 55), (55, 55, 60)),
        ((45, 125, 75), (45, 50, 40)),
        ((170, 125, 45), (55, 70, 105)),
        ((115, 65, 145), (50, 45, 60)),
        ((55, 125, 135), (70, 55, 40)),
    ]
    idx=(hashlib.sha256((str(name)+str(scene_index//3)).encode("utf-8")).digest()[0]) % len(outfits)
    return outfits[idx]


def _draw_auto_puppet(base, puppet, skel, t, speaking=False, outfit=None):
    if outfit:
        puppet = dict(puppet, shirt=outfit[0], pants=outfit[1])
    d = ImageDraw.Draw(base, "RGBA")
    # breathing + body sway
    sway = math.sin(t*math.pi*2) * 3
    breath = math.sin(t*math.pi*2) * 2
    for side in ("l", "r"):
        arm_phase = math.sin(t*math.pi*2 + (0 if side == "l" else 1.4))
        leg_phase = math.sin(t*math.pi*2 + (math.pi if side == "l" else 0))
        if side == "l":
            s, e, hand = skel["ls"], skel["le"], (skel["le"][0]-22, skel["le"][1]+8*arm_phase)
            hip, knee, foot = skel["lh"], skel["lk"], skel["lf"]
        else:
            s, e, hand = skel["rs"], skel["re"], (skel["re"][0]+22, skel["re"][1]-8*arm_phase)
            hip, knee, foot = skel["rh"], skel["rk"], skel["rf"]
        e = (e[0], e[1] + 7*arm_phase)
        knee = (knee[0], knee[1] + 8*leg_phase)
        foot = (foot[0] + 8*leg_phase, foot[1])
        d.line([s, e, hand], fill=puppet["shirt"]+(255,), width=24, joint="curve")
        d.ellipse((e[0]-12,e[1]-12,e[0]+12,e[1]+12), fill=puppet["skin"]+(255,))
        d.line([hip, knee, foot], fill=puppet["pants"]+(255,), width=27, joint="curve")
        d.ellipse((knee[0]-13,knee[1]-13,knee[0]+13,knee[1]+13), fill=puppet["pants"]+(255,))
    neck=(skel["neck"][0]+sway, skel["neck"][1]+breath)
    ls=(skel["ls"][0]+sway, skel["ls"][1]+breath); rs=(skel["rs"][0]+sway, skel["rs"][1]+breath)
    d.line([ls, rs], fill=puppet["shirt"]+(255,), width=58)
    d.polygon([ls, rs, (rs[0]-8, skel["rh"][1]), (ls[0]+8, skel["lh"][1])], fill=puppet["shirt"]+(255,))
    d.ellipse((neck[0]-38,neck[1]-52,neck[0]+38,neck[1]+52), fill=puppet["skin"]+(255,))
    d.arc((neck[0]-25,neck[1]-15,neck[0]-5,neck[1]+4), 200, 340, fill=(30,30,30,255), width=4)
    d.arc((neck[0]+5,neck[1]-15,neck[0]+25,neck[1]+4), 200, 340, fill=(30,30,30,255), width=4)
    d.arc((neck[0]-17,neck[1]+10,neck[0]+17,neck[1]+30), 0, 180, fill=(120,30,30,255), width=5 if speaking else 3)
    # Hair
    d.pieslice((neck[0]-40,neck[1]-58,neck[0]+40,neck[1]+22), 180, 360, fill=puppet["hair"]+(255,))


def _photo_part_crop(img, p1, p2, width=40):
    # Crop a limb corridor from the transparent foreground.
    x1,y1=p1; x2,y2=p2
    pad=width+12
    left=max(0,int(min(x1,x2)-pad)); top=max(0,int(min(y1,y2)-pad))
    right=min(img.width,int(max(x1,x2)+pad)); bottom=min(img.height,int(max(y1,y2)+pad))
    crop=img.crop((left,top,right,bottom))
    return crop, left, top


def _draw_photo_puppet(base, puppet, skel, t, speaking=False, outfit=None):
    img=puppet["image"]
    # Scale to fit skeleton body height; then use a full-body cutout with subtle articulated illusion.
    target_h=int(base.height*0.68)
    scale=target_h/max(1,img.height)
    im=img.resize((max(1,int(img.width*scale)),target_h), Image.Resampling.LANCZOS)
    x=int(base.width*0.5-im.width/2); y=int(base.height*0.12)
    # Whole-body puppet bob/sway; limbs get additional visual motion via transparent overlay strokes.
    bob=int(math.sin(t*math.pi*2)*3)
    rot=math.sin(t*math.pi*2)*2.0
    im=im.rotate(rot, resample=Image.Resampling.BICUBIC, expand=True)
    base.alpha_composite(im,(x-(im.width-img.width)//2,y+bob))
    d=ImageDraw.Draw(base,"RGBA")
    # Articulated joint markers are subtle, not exposed as a preview.
    for key in ("le","re","lk","rk"):
        px,py=skel[key]
        d.ellipse((px-3,py-3,px+3,py+3),fill=(255,255,255,35))
    if outfit:
        shirt,pants=outfit
        d.polygon([(skel["ls"][0]-12,skel["ls"][1]-2),(skel["rs"][0]+12,skel["rs"][1]-2),(skel["rh"][0]+18,skel["rh"][1]+20),(skel["lh"][0]-18,skel["lh"][1]+20)],fill=shirt+(105,))
        d.polygon([(skel["lh"][0]-14,skel["lh"][1]+12),(skel["rh"][0]+14,skel["rh"][1]+12),(skel["rf"][0]+12,skel["rf"][1]),(skel["lf"][0]-12,skel["lf"][1])],fill=pants+(80,))
    if speaking:
        cx,cy=skel["head"]
        d.ellipse((cx-7,cy+25,cx+7,cy+31),fill=(80,20,20,120))


def _location_palette(text):
    low=str(text or "").lower()
    if any(x in low for x in ("o'rmon", "o‘rmon", "forest", "tog'", "tog‘")):
        return ((50,90,55),(150,190,120))
    if any(x in low for x in ("dengiz", "sohil", "plyaj", "sea", "beach")):
        return ((55,115,165),(205,220,170))
    if any(x in low for x in ("uy", "xona", "ofis", "maktab", "shahar", "ko'cha", "ko‘cha")):
        return ((90,95,110),(210,185,145))
    if any(x in low for x in ("tun", "kecha")):
        return ((20,28,60),(85,95,145))
    return ((75,105,135),(190,175,135))


def _make_background(state, scene_index, size):
    w,h=size
    if state.get("location_images"):
        try:
            idx=(scene_index-1)%len(state["location_images"])
            path=state["location_local_images"][idx]
            bg=Image.open(path).convert("RGB")
            bg.thumbnail((w,h),Image.Resampling.LANCZOS)
            canvas=Image.new("RGB",(w,h),(30,30,30)); canvas.paste(bg,((w-bg.width)//2,(h-bg.height)//2))
            return canvas.convert("RGBA").filter(ImageFilter.GaussianBlur(0.3))
        except Exception:
            pass
    a,b=_location_palette(state.get("scene_texts",[state.get("scenario","")])[max(0,scene_index-1)])
    bg=Image.new("RGBA",(w,h),a+(255,)); d=ImageDraw.Draw(bg,"RGBA")
    for yy in range(int(h*0.55),h):
        q=(yy-int(h*.55))/max(1,h*.45); col=tuple(int(a[i]*(1-q)+b[i]*q) for i in range(3))+(255,)
        d.line((0,yy,w,yy),fill=col,width=2)
    # Simple depth layers.
    for i in range(9):
        x=int((i+1)*w/10); hh=int(h*(0.12+(i%3)*0.06))
        d.rectangle((x,int(h*.55)-hh,x+int(w*.07),int(h*.55)),fill=(35,45,55,150))
    for i in range(3):
        d.ellipse((w*.65+i*80,h*.12+i*15,w*.75+i*80,h*.22+i*15),fill=(240,240,220,80))
    return bg


def _add_camera_motion(frame, t, scene_index):
    # Natural slow pan/zoom without generative AI.
    w,h=frame.size
    zoom=1.0+0.025*math.sin((t+scene_index*.17)*math.pi*2)
    nw=int(w*zoom); nh=int(h*zoom)
    scaled=frame.resize((nw,nh),Image.Resampling.BICUBIC)
    ox=int((nw-w)*(0.5+0.18*math.sin(t*math.pi*2+scene_index)))
    oy=int((nh-h)*(0.5+0.10*math.cos(t*math.pi*2)))
    return scaled.crop((ox,oy,ox+w,oy+h))


def _tts_voice_for(name):
    # Per-character deterministic local TTS profile. Uzbek quality depends on installed espeak voice.
    digest=hashlib.sha256(str(name).encode("utf-8")).digest()
    pitch=45 + digest[0]%35
    speed=135 + digest[1]%35
    return pitch, speed


def _synthesize_dialogue(text, speaker, wav_path):
    if not MOVIE_TTS_ENABLED or not shutil.which("espeak"):
        return False
    pitch,speed=_tts_voice_for(speaker)
    safe=str(text).replace("\n"," ").strip()
    if not safe:
        return False
    cmd=["espeak","-v",MOVIE_TTS_VOICE,"-w",wav_path,"-p",str(pitch),"-s",str(speed),"-a","150",safe]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
        return p.returncode==0 and os.path.exists(wav_path) and os.path.getsize(wav_path)>100
    except Exception:
        return False


def _wav_duration(path):
    try:
        with wave.open(path,"rb") as wf:
            return wf.getnframes()/float(wf.getframerate() or 1)
    except Exception:
        return 0.0


def _concat_audio_files(paths, out):
    valid=[p for p in paths if os.path.exists(p)]
    if not valid:
        return False
    if len(valid)==1:
        shutil.copyfile(valid[0],out); return True
    if not shutil.which("ffmpeg"):
        return False
    list_file=out+".txt"
    with open(list_file,"w",encoding="utf-8") as f:
        for p in valid:
            f.write("file '"+os.path.abspath(p).replace("'","'\\''")+"'\n")
    cmd=["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,"-ar","44100","-ac","1",out]
    try:
        ok=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300).returncode==0
    finally:
        try: os.remove(list_file)
        except Exception: pass
    return ok


def _render_scene(state, scene_index, total_scenes, job_dir, characters, puppets, dialogue_map):
    scene_dir=os.path.join(job_dir,f"scene_{scene_index:04d}")
    os.makedirs(scene_dir,exist_ok=True)
    sentence=state["scene_texts"][scene_index-1]
    speaker=None
    # Dialogue belongs to exact speaker; if scene sentence contains speaker name, use it.
    low=sentence.lower()
    for name in characters:
        if name.lower() in low:
            speaker=name; break
    if speaker is None and dialogue_map:
        speaker=dialogue_map[(scene_index-1)%len(dialogue_map)]["speaker"]
    audio_paths=[]
    if speaker and dialogue_map:
        for d in dialogue_map:
            if d["speaker"]==speaker and d["text"] in sentence:
                wp=os.path.join(scene_dir,"voice.wav")
                if _synthesize_dialogue(d["text"],speaker,wp): audio_paths.append(wp)
                break
    audio=None
    if audio_paths:
        audio=os.path.join(scene_dir,"audio.wav")
        _concat_audio_files(audio_paths,audio)
    frame_count=max(1,int(round(MOVIE_SCENE_SECONDS*MOVIE_FPS)))
    for fi in range(frame_count):
        t=fi/max(1,frame_count-1)
        frame=_make_background(state,scene_index,(MOVIE_WIDTH,MOVIE_HEIGHT))
        d=ImageDraw.Draw(frame,"RGBA")
        d.rectangle((0,0,MOVIE_WIDTH,90),fill=(0,0,0,75))
        # Scene title is subtle and optional; no technical status.
        d.text((35,28),f"{state.get('title','Kino')}  •  {scene_index}",font=_safe_font(26,True),fill=(255,255,255,220))
        for i,name in enumerate(characters):
            puppet=puppets.get(name)
            if not puppet: continue
            skel=_make_skeleton(MOVIE_WIDTH,MOVIE_HEIGHT)
            # Natural entrance / staging: alternate sides, then converge.
            offset=(-170+i*170) if len(characters)>1 else 0
            local=frame.copy()
            if puppet["kind"]=="auto":
                # shift skeleton horizontally for multiple actors
                skel={k:(v[0]+offset,v[1]) for k,v in skel.items()}
                _draw_auto_puppet(local,puppet,skel,t,speaking=(speaker==name and int(t*8)%2==0),outfit=_outfit_for(name,scene_index))
            else:
                skel={k:(v[0]+offset,v[1]) for k,v in skel.items()}
                _draw_photo_puppet(local,puppet,skel,t,speaking=(speaker==name and int(t*8)%2==0),outfit=_outfit_for(name,scene_index))
            frame=Image.alpha_composite(frame,local)
        # Cinematic caption derived from scenario sentence; not a technical message.
        caption=sentence[:120]
        if caption:
            d=ImageDraw.Draw(frame,"RGBA")
            d.rounded_rectangle((35,MOVIE_HEIGHT-105,MOVIE_WIDTH-35,MOVIE_HEIGHT-35),radius=18,fill=(0,0,0,90))
            d.text((55,MOVIE_HEIGHT-85),caption,font=_safe_font(22),fill=(255,255,255,235))
        frame=_add_camera_motion(frame,t,scene_index)
        frame.convert("RGB").save(os.path.join(scene_dir,f"frame_{fi:05d}.jpg"),quality=88)
    video_path=os.path.join(job_dir,f"scene_{scene_index:04d}.mp4")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg topilmadi")
    pattern=os.path.join(scene_dir,"frame_%05d.jpg")
    cmd=["ffmpeg","-y","-framerate",str(MOVIE_FPS),"-i",pattern]
    if audio and os.path.exists(audio):
        cmd += ["-i",audio,"-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-shortest",video_path]
    else:
        cmd += ["-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p",video_path]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=900)
    if p.returncode!=0 or not os.path.exists(video_path):
        raise RuntimeError("Sahna videosini yaratib bo'lmadi")
    shutil.rmtree(scene_dir,ignore_errors=True)
    return video_path


def _concat_videos(video_files, output_path):
    if not video_files or not shutil.which("ffmpeg"):
        raise RuntimeError("Video birlashtirish uchun FFmpeg kerak")
    os.makedirs(os.path.dirname(output_path),exist_ok=True)
    list_file=output_path+".txt"
    with open(list_file,"w",encoding="utf-8") as f:
        for item in video_files:
            f.write("file '"+os.path.abspath(item).replace("'","'\\''")+"'\n")
    cmd=["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,"-c","copy","-movflags","+faststart",output_path]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3600)
    if p.returncode!=0:
        cmd=["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,"-c:v","libx264","-preset","ultrafast","-crf","23","-c:a","aac","-movflags","+faststart",output_path]
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3600)
    try: os.remove(list_file)
    except Exception: pass
    if p.returncode!=0 or not os.path.exists(output_path):
        raise RuntimeError("Kino kliplarini birlashtirib bo'lmadi")
    return output_path


def _prepare_local_assets(state, job_dir):
    state["location_local_images"]=[]
    for i,file_id in enumerate(state.get("location_images",[])):
        try:
            path=os.path.join(job_dir,f"location_{i:02d}.jpg")
            _download_telegram_photo(file_id,path)
            state["location_local_images"].append(path)
        except Exception as e:
            print("Lokatsiya rasmini olish xatosi:",type(e).__name__,e,flush=True)
    puppets={}
    for item in state.get("actor_photos",[]):
        role=item.get("role")
        file_id=item.get("photo")
        if not role: continue
        try:
            path=os.path.join(job_dir,"actor_"+re.sub(r"[^\w-]","_",role)+".jpg")
            _download_telegram_photo(file_id,path)
            puppets[role]=_make_photo_puppet(path)
        except Exception:
            puppets[role]=_make_auto_puppet(role)
    return puppets


def _make_title(scenario):
    first=_scenario_sentences(scenario)[0]
    words=re.findall(r"[A-Za-zА-Яа-яЎўҚқҒғҲҳʻ’']+",first)
    return " ".join(words[:5]).strip().title() or "Kino"


@bot.message_handler(func=lambda m: m.text == "🎬 Kino yaratish")
def start_ai_movie(message):
    uid=str(message.chat.id)
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id,"❌ <b>Avval kanallarga obuna bo'ling.</b>")
        return
    user=get_user(uid) or users.get(uid)
    if not user:
        bot.send_message(message.chat.id,"❌ Foydalanuvchi ma'lumotlari topilmadi.")
        return
    users[uid]=user
    movie_generation_state[uid]={"step":"description","created_at":time.time(),"characters":[],"actor_photos":[],"location_images":[]}
    bot.send_message(message.chat.id,"🎬 <b>Kino yaratish</b>\n\n📝 Ssenariyni to'liq yozing.\n\nMasalan:\n<b>Sardor:</b> Salom, Malika. Bugun safarga chiqamiz.\n<b>Malika:</b> Mayli, ketdik.\n\nSsenariyda ism: dialog shaklida yozilsa, bot dialog egasini aniq bog'laydi.")


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step")=="description")
def receive_movie_description(message):
    uid=str(message.chat.id); text=(message.text or "").strip()
    if len(text)<5:
        bot.send_message(message.chat.id,"❌ Ssenariy juda qisqa. Kamida bir nechta gap yozing.")
        return
    state=movie_generation_state[uid]
    state["raw_description"]=text
    state["step"]="scenario_generating"
    bot.send_message(message.chat.id,"📝 <b>Siz yozgan g'oya professional ssenariyga aylantirilmoqda...</b>\n\n🤖 AI ssenariyni tayyorlayapti.")
    def worker():
        result=ask_ai(_scenario_prompt(text),max_retries=3)
        current=movie_generation_state.get(uid)
        if not current: return
        scenario=result or text
        current["scenario"]=scenario
        current["characters"]=_extract_characters(scenario)
        current["dialogues"]=_extract_dialogues(scenario,current["characters"])
        current["title"]=_make_title(scenario)
        current["step"]="scenario_ready"
        send_ai_text(message.chat.id,"🎬 <b>Tayyor ssenariy</b>",scenario)
        _show_character_menu(message.chat.id,uid)
    threading.Thread(target=worker,daemon=True).start()


@bot.message_handler(func=lambda m: str(m.chat.id) in movie_generation_state and movie_generation_state[str(m.chat.id)].get("step")=="video_duration")
def receive_video_duration(message):
    uid=str(message.chat.id); state=movie_generation_state.get(uid)
    if not state: return
    minutes=parse_duration_minutes((message.text or "").strip())
    if minutes is None or minutes<1 or minutes>120:
        bot.send_message(message.chat.id,"❌ Davomiylik noto'g'ri. 1 daqiqadan 2 soatgacha yozing.")
        return
    state["duration_minutes"]=minutes; state["duration"]=(message.text or "").strip(); state["step"]="duration_generating"
    bot.send_message(message.chat.id,f"⏱ <b>{minutes} daqiqalik ssenariy tayyorlanmoqda...</b>\n\n🤖 AI sahnalar va dialoglarni shu davomiylikka moslamoqda.")
    def worker():
        result=ask_ai(_duration_prompt(state,state["duration"]),max_retries=3)
        current=movie_generation_state.get(uid)
        if not current: return
        if result: current["scenario"]=result
        current["characters"]=_extract_characters(current.get("scenario",""))
        current["dialogues"]=_extract_dialogues(current.get("scenario",""),current["characters"])
        current["title"]=_make_title(current.get("scenario",""))
        current["step"]="video_ready"
        if result: send_ai_text(message.chat.id,"✅ <b>Ssenariy davomiylikka moslandi</b>",result)
        bot.send_message(message.chat.id,f"🎬 <b>{minutes} daqiqalik ssenariy tayyor.</b>\n\nEndi kinoni yaratishingiz mumkin:",reply_markup=_movie_buttons(uid,"create"))
    threading.Thread(target=worker,daemon=True).start()


@bot.callback_query_handler(func=lambda c: c.data.startswith("generate_video:"))
def generate_video_callback(call):
    uid=str(call.message.chat.id)
    if not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id,"❌ Avval obuna bo'ling.",show_alert=True); return
    state=movie_generation_state.get(uid)
    if not state:
        bot.answer_callback_query(call.id,"❌ Kino holati topilmadi.",show_alert=True); return
    minutes=safe_int(state.get("duration_minutes")); price=movie_price(minutes)
    if price is None:
        bot.answer_callback_query(call.id,"❌ Davomiylik noto'g'ri.",show_alert=True); return
    if state.get("video_job_running"):
        bot.answer_callback_query(call.id,"⏳ Kino allaqachon yaratilmoqda."); return
    state["price"]=price; state["video_job_running"]=True; state["step"]="rendering"
    bot.answer_callback_query(call.id,"🎬 Kino yaratish boshlandi")
    # Status foydalanuvchiga alohida oddiy xabar sifatida yuboriladi. Callback oynasida emas.
    # Render texnik jarayoni oddiy foydalanuvchiga ko'rsatilmaydi.
    # Monitoring faqat server loglari/admin uchun.
    status_msg = None
    admin_status_msg = None
    if ADMIN_ID and call.message.chat.id != ADMIN_ID:
        try:
            admin_status_msg = bot.send_message(
                ADMIN_ID,
                f"🛠 <b>Kino render boshlandi</b>\n\n👤 User: <code>{uid}</code>\n🎬 Davomiylik: {minutes} daqiqa\n📊 Sahna: 0/0"
            )
        except Exception:
            admin_status_msg = None

    def worker():
        job_dir=os.path.abspath(os.path.join(MOVIE_JOBS_DIR,uid,str(int(time.time()))))
        try:
            os.makedirs(job_dir,exist_ok=True)
            puppets=_prepare_local_assets(state,job_dir)
            for name in state.get("characters",[]):
                puppets.setdefault(name,_make_auto_puppet(name))
            # Scene text repeats/cycles naturally to fill requested duration.
            base_sentences=_scenario_sentences(state.get("scenario",""))
            scene_count=_scene_count_for_duration(minutes)
            state["scene_texts"]=[base_sentences[i%len(base_sentences)] for i in range(scene_count)]
            dialogue_map=state.get("dialogues",[])
            video_files=[]
            started=time.time()
            last_status=0.0
            for idx in range(1,scene_count+1):
                video_files.append(_render_scene(state,idx,scene_count,job_dir,state.get("characters",[]),puppets,dialogue_map))
                now=time.time()
                if idx == 1 or idx == scene_count or now-last_status >= 3.0:
                    elapsed=max(0.1,now-started)
                    rate=idx/elapsed
                    remaining=max(0,scene_count-idx)
                    eta=remaining/rate if rate>0 else 0
                    mins_eta=int(eta//60); secs_eta=int(eta%60)
                    pct=idx*100/scene_count
                    # Foydalanuvchiga texnik progress yuborilmaydi.
                    # Admin uchun bitta xabar ichida progress yangilanadi.
                    try:
                        if admin_status_msg:
                            bot.edit_message_text(
                                f"🛠 <b>Kino render qilinmoqda</b>\n\n"
                                f"👤 User: <code>{uid}</code>\n"
                                f"🎬 Davomiylik: {minutes} daqiqa\n"
                                f"📊 Sahna: {idx}/{scene_count} ({pct:.1f}%)\n"
                                f"⏱ Qolgan vaqt: {mins_eta} daqiqa {secs_eta} soniya",
                                ADMIN_ID, admin_status_msg.message_id)
                    except Exception:
                        pass
                    last_status=now
            output=os.path.join(job_dir,"kino.mp4")
            _concat_videos(video_files,output)
            if not os.path.exists(output) or os.path.getsize(output)<1024:
                raise RuntimeError("Yakuniy kino fayli yaratilmadi")
            video_size=os.path.getsize(output)
            state["video_path"]=output; state["video_url"]=None; state["video_size"]=video_size; state["video_job_running"]=False
            print(f"🎬 Render tayyor: {output} | {video_size/1024/1024:.2f} MB", flush=True)

            # Telegramga yuborish alohida bosqich: video tayyor bo'lsa ham upload
            # muvaffaqiyatsiz tugashi mumkin. Foydalanuvchiga aniq xabar beramiz.
            def send_movie(chat_id, caption):
                return _send_saved_movie(chat_id, output, caption, protect_content=False)

            try:
                if admin_status_msg:
                    bot.edit_message_text(
                        f"✅ <b>Kino render tayyor</b>\n\n👤 User: <code>{uid}</code>\n📦 Hajmi: {video_size/1024/1024:.2f} MB\n📤 Telegram yuborilishi kutilmoqda.",
                        ADMIN_ID, admin_status_msg.message_id)
            except Exception:
                pass

            try:
                if call.message.chat.id==ADMIN_ID:
                    send_movie(call.message.chat.id,"🎬 Kino tayyor!")
                    state["delivered"]=True; state["step"]="delivered"
                    try: bot.send_message(call.message.chat.id,"🎬 Kino tayyor.",reply_markup=_resend_movie_markup(uid))
                    except Exception: pass
                    return

                user=users.get(uid) or get_user(uid)
                rights=safe_int(user.get("movie_rights")) if user else 0
                if rights>0:
                    send_movie(call.message.chat.id,"🎬 Kino tayyor!")
                    user["movie_rights"]=rights-1; user["total_movies"]=safe_int(user.get("total_movies"))+1; save_user_to_json(uid)
                    state["delivered"]=True; state["step"]="delivered"
                    try: bot.send_message(call.message.chat.id,"🎬 Kino tayyor.",reply_markup=_resend_movie_markup(uid))
                    except Exception: pass
                    return

                state["step"]="payment_pending"
                bot.send_message(call.message.chat.id,"💳 <b>Kino tayyor.</b> To'lov bosqichiga o'tishingiz mumkin.",reply_markup=payment_markup(uid))
            except Exception as upload_err:
                state["step"]="video_ready"
                print("❌ Video tayyor, lekin Telegramga yuborilmadi:",type(upload_err).__name__,upload_err,flush=True)
                try:
                    if ADMIN_ID:
                        bot.send_message(
                            ADMIN_ID,
                            f"⚠️ <b>Video Telegramga yuborilmadi</b>\n\n👤 User: <code>{uid}</code>\n"
                            f"<code>{type(upload_err).__name__}: {upload_err}</code>"
                        )
                except Exception:
                    pass
                try:
                    bot.send_message(call.message.chat.id,
                        "⚠️ Video tayyor, lekin Telegramga yuborilmadi.\n"
                        "🔄 Qayta yuborishni sinab ko'ring.",
                        reply_markup=_movie_buttons(uid,"create"))
                except Exception:
                    pass
        except Exception as e:
            state["video_job_running"]=False; state["step"]="video_ready"
            print("❌ Kino jarayoni xatosi:",type(e).__name__,e,flush=True)
            # To'liq texnik xato faqat admin uchun. Oddiy userga qisqa xabar.
            try:
                if admin_status_msg:
                    tb = traceback.format_exc()
                    if len(tb) > 3500:
                        tb = tb[-3500:]
                    bot.edit_message_text(
                        f"❌ <b>Kino render xatosi</b>\n\n👤 User: <code>{uid}</code>\n"
                        f"<code>{type(e).__name__}: {e}</code>\n\n<pre>{tb}</pre>",
                        ADMIN_ID, admin_status_msg.message_id)
                elif ADMIN_ID:
                    bot.send_message(ADMIN_ID, f"❌ Kino render xatosi | user={uid} | {type(e).__name__}: {e}")
            except Exception:
                pass
            try:
                bot.send_message(call.message.chat.id,"❌ Kino yaratib bo'lmadi. Iltimos, qayta urinib ko'ring.",reply_markup=_movie_buttons(uid,"create"))
            except Exception:
                pass
    threading.Thread(target=worker,daemon=True).start()


@bot.callback_query_handler(func=lambda c: c.data.startswith("movie_cancel:"))
def movie_cancel_callback(call):
    uid=str(call.message.chat.id)
    movie_generation_state.pop(uid,None)
    bot.answer_callback_query(call.id,"Bekor qilindi.")
    bot.send_message(call.message.chat.id,"❌ Kino jarayoni bekor qilindi.",reply_markup=main_menu_markup())


# =========================
# KINO TAVSIYALARI VA ADMIN ADD
# =========================

def _resend_movie_markup(uid):
    markup=types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔄 Kino boshidan yuborish", callback_data=f"resend_movie:{uid}"))
    return markup

def _send_saved_movie(chat_id, video_path, caption="🎬 Kino tayyor!", protect_content=False):
    if not video_path or not os.path.exists(video_path):
        raise FileNotFoundError("Saqlangan video fayli topilmadi")
    size=os.path.getsize(video_path)
    if size < 1024:
        raise RuntimeError("Video fayli juda kichik yoki buzilgan")
    try:
        with open(video_path,"rb") as vf:
            return bot.send_video(chat_id,vf,caption=caption,protect_content=protect_content,timeout=1800)
    except Exception as video_err:
        print("❌ Telegram send_video xatosi:",type(video_err).__name__,video_err,flush=True)
        try:
            with open(video_path,"rb") as vf:
                return bot.send_document(chat_id,vf,caption=caption,protect_content=protect_content,timeout=1800)
        except Exception as doc_err:
            print("❌ Telegram send_document xatosi:",type(doc_err).__name__,doc_err,flush=True)
            raise RuntimeError(f"video: {type(video_err).__name__}: {video_err} | document: {type(doc_err).__name__}: {doc_err}") from video_err

@bot.callback_query_handler(func=lambda c: c.data.startswith("resend_movie:"))
def resend_movie_callback(call):
    uid=str(call.message.chat.id)
    state=movie_generation_state.get(uid)
    if not state:
        bot.answer_callback_query(call.id,"❌ Kino holati topilmadi. Kino qayta yaratilishi kerak.",show_alert=True)
        return
    path=state.get("video_path")
    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id,"❌ Saqlangan video topilmadi. Kinoni qayta yarating.",show_alert=True)
        return
    bot.answer_callback_query(call.id,"📤 Video qayta yuborilmoqda...")
    try:
        _send_saved_movie(call.message.chat.id,path,"🎬 Kino tayyor!",protect_content=False)
        state["delivered"]=True; state["step"]="delivered"
        bot.send_message(call.message.chat.id,"✅ Video muvaffaqiyatli yuborildi!")
    except Exception as e:
        print("❌ Qayta yuborish xatosi:",type(e).__name__,e,flush=True)
        bot.send_message(call.message.chat.id,"⚠️ Video hali yuborilmadi. Internet yoki Telegram ulanishini tekshirib, yana urinib ko'ring.",reply_markup=_resend_movie_markup(uid))


def movie_categories_markup():
    markup=types.InlineKeyboardMarkup()
    for key,title in [("fantastika","🚀 Fantastik kinolar"),("jangari","💥 Jangari kinolar"),("romantik","❤️ Romantik kinolar"),("komediya","😂 Komediya kinolar"),("qorqinchli","👻 Qo'rqinchli kinolar")]:
        markup.add(types.InlineKeyboardButton(title, callback_data=f"recommend:{key}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "🎥 Kino tavsiya")
def movie_recommend_menu(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return
    bot.send_message(message.chat.id,"🎥 <b>Kino tavsiyalari</b>\n\nJanrni tanlang:",reply_markup=movie_categories_markup())

@bot.callback_query_handler(func=lambda c: c.data.startswith("recommend:"))
def recommend_movies(call):
    """Janr tanlanganda videolarni emas, faqat kino nomlarini tugma qilib ko'rsatadi."""
    if not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Avval kanallarga obuna bo'ling.", show_alert=True)
        return
    genre = call.data.split(":", 1)[1].lower().strip()
    aliases = {
        "fantastika": {"fantastika", "fantastic", "fantastik"},
        "jangari": {"jangari", "jangovar", "action", "jangi"},
        "romantik": {"romantik", "romance", "romantic"},
        "komediya": {"komediya", "komedik", "comedy"},
        "qorqinchli": {"qorqinchli", "qorqinchilik", "horror", "qo'rqinchli", "qo‘rqinchli"},
    }
    wanted = aliases.get(genre, {genre})
    rows = []
    for code, movie in kinolar.items():
        saved_genre = str(movie.get("janr", "")).lower().strip()
        if saved_genre in wanted:
            rows.append((code, movie))
    bot.answer_callback_query(call.id)
    if not rows:
        bot.send_message(call.message.chat.id, "❌ Bu janrda hozircha kino yo'q.")
        return

    markup = types.InlineKeyboardMarkup()
    for code, movie in rows:
        name = str(movie.get("nom", "Nomsiz"))[:55]
        markup.add(types.InlineKeyboardButton(f"🎬 {name}", callback_data=f"movie_info:{code}:{genre}"))
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga qaytish", callback_data="recommend_back"))
    bot.send_message(
        call.message.chat.id,
        f"🎭 <b>{genre.title()} kinolar</b>\n\nKino nomini tanlang:",
        reply_markup=markup,
    )

@bot.callback_query_handler(func=lambda c: c.data == "recommend_back")
def recommend_back_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "🎥 <b>Kino tavsiyalari</b>\n\nJanrni tanlang:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=movie_categories_markup(),
        )
    except Exception:
        bot.send_message(call.message.chat.id, "🎥 <b>Kino tavsiyalari</b>\n\nJanrni tanlang:", reply_markup=movie_categories_markup())

@bot.callback_query_handler(func=lambda c: c.data.startswith("movie_info:"))
def movie_info_callback(call):
    if not check_sub(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Avval kanallarga obuna bo'ling.", show_alert=True)
        return
    parts = call.data.split(":", 2)
    code = parts[1] if len(parts) > 1 else ""
    genre = parts[2] if len(parts) > 2 else str(kinolar.get(code, {}).get("janr", ""))
    movie = kinolar.get(code)
    if not movie:
        bot.answer_callback_query(call.id, "❌ Kino topilmadi.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    caption = (
        f"🎬 <b>{movie.get('nom', 'Nomsiz')}</b>\n"
        f"📅 Kino yili: {movie.get('yil', '-')}\n"
        f"💾 Kino hajmi: {movie.get('hajm', '-')}\n"
        f"🎭 Kino yo'nalishi: {movie.get('janr', '-')}\n\n"
        "ℹ️ Kinoni ko'rish/olish uchun pastdagi tugmani bosing."
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    if MOVIE_BOT_USERNAME:
        url = f"https://t.me/{MOVIE_BOT_USERNAME}?start={code}"
        markup.add(types.InlineKeyboardButton("🎬 Kinoni olish", url=url))
    else:
        # Username hali sozlanmagan bo'lsa, foydalanuvchiga kodni ko'rsatamiz.
        markup.add(types.InlineKeyboardButton("🔑 Kino kodini ko'rsatish", callback_data=f"show_movie_code:{code}"))
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga qaytish", callback_data=f"recommend:{genre}"))

    try:
        (bot.send_video(call.message.chat.id, movie.get("video"), caption=caption, reply_markup=markup) if movie.get("video_type", "video") == "video" else bot.send_document(call.message.chat.id, movie.get("video"), caption=caption, reply_markup=markup))
    except Exception as e:
        print("❌ Tavsiya videosini yuborish xatosi:", type(e).__name__, e, flush=True)
        bot.send_message(call.message.chat.id, caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("show_movie_code:"))
def show_movie_code_callback(call):
    code = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, f"Kino kodi: {code}", show_alert=True)

@bot.message_handler(commands=["add"])
def admin_add_movie(message):
    if message.chat.id != ADMIN_ID: return
    movie_add_state[str(message.chat.id)]={"step":"name"}
    bot.send_message(message.chat.id,"🎥 <b>Kino tavsiyasiga saqlash</b>\n\nKino nomini yuboring:")

@bot.message_handler(func=lambda m: str(m.chat.id) in movie_add_state, content_types=["text","video","document"])
def add_movie_steps(message):
    uid=str(message.chat.id); state=movie_add_state[uid]
    text=(message.text or "").strip()
    step=state["step"]
    if step=="name": state["nom"]=text; state["step"]="yil"; bot.send_message(message.chat.id,"📅 Kino yilini yozing:"); return
    if step=="yil": state["yil"]=text; state["step"]="hajm"; bot.send_message(message.chat.id,"💾 Kino hajmini yozing:"); return
    if step=="hajm": state["hajm"]=text; state["step"]="janr"; bot.send_message(message.chat.id,"🎭 Kino yo'nalishi/janrini yozing (masalan: fantastika):"); return
    if step=="janr": state["janr"]=text.lower(); state["step"]="video"; bot.send_message(message.chat.id,"🎥 Kino videosini yuboring (video yoki video fayl):"); return
    if step=="video":
        media_type = None
        file_id = None
        if message.video:
            media_type = "video"
            file_id = message.video.file_id
        elif message.document and str(message.document.mime_type or "").lower().startswith("video/"):
            media_type = "document"
            file_id = message.document.file_id
        if not file_id:
            bot.send_message(message.chat.id,"❌ Video yuboring. 🎥 Video ko'rinishida yoki video fayl sifatida yuborishingiz mumkin.")
            return
        code=str(int(time.time()*1000))
        kinolar[code]={"nom":state["nom"],"yil":state["yil"],"hajm":state["hajm"],"janr":state["janr"],"video":file_id,"video_type":media_type}
        if save_movies():
            movie_add_state.pop(uid,None)
            bot.send_message(message.chat.id,f"✅ Kino tavsiyalarga saqlandi!\n\n🎬 {state['nom']}\n🎭 {state['janr']}\n🔑 Kod: <b>{code}</b>")
        else:
            bot.send_message(message.chat.id,"❌ Kino saqlanmadi: kinolar.json ga yozishda xato bo'ldi.")

# =========================
# PUL YECHISH
# =========================

@bot.message_handler(func=lambda m: m.text == "💸 Pul yechish")
def withdraw_start(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.")
        return
    uid = str(message.chat.id)
    user = get_user(uid) or users.get(uid)
    if not user:
        bot.send_message(message.chat.id, "❌ Hisobingiz topilmadi.")
        return
    balance = safe_int(user.get("balance"))
    if balance <= 0:
        bot.send_message(message.chat.id, "❌ Balansingizda pul yo'q.")
        return
    withdraw_state[uid] = {"step": "amount"}
    bot.send_message(message.chat.id, f"💸 Yechmoqchi bo'lgan summani yozing.\n\n💰 Balans: {balance} so'm")


@bot.message_handler(func=lambda m: str(m.chat.id) in withdraw_state)
def withdraw_steps(message):
    uid = str(message.chat.id)
    state = withdraw_state.get(uid, {})
    text = (message.text or "").strip()
    if state.get("step") == "amount":
        try:
            amount = int(text.replace(" ", "").replace(",", ""))
        except Exception:
            bot.send_message(message.chat.id, "❌ Summani faqat raqam bilan yozing.")
            return
        balance = safe_int(users.get(uid, {}).get("balance"))
        if amount <= 0 or amount > balance:
            bot.send_message(message.chat.id, f"❌ Noto'g'ri summa. Balans: {balance} so'm")
            return
        state["amount"] = amount
        state["step"] = "card"
        bot.send_message(message.chat.id, "💳 Karta raqamingizni yuboring:")
        return
    if state.get("step") == "card":
        card = re.sub(r"[^0-9]", "", text)
        if len(card) not in (16, 18):
            bot.send_message(message.chat.id, "❌ Karta raqami noto'g'ri.")
            return
        amount = safe_int(state.get("amount"))
        user = users.get(uid)
        if not user or safe_int(user.get("balance")) < amount:
            bot.send_message(message.chat.id, "❌ Balans yetarli emas.")
            withdraw_state.pop(uid, None)
            return
        withdrawal = {"id": str(int(time.time() * 1000)), "user_id": int(uid), "amount": amount, "card": card, "status": "pending", "created_at": datetime.now().isoformat()}
        withdrawals.append(withdrawal)
        DATA["withdrawals"] = withdrawals
        save_json_data()
        withdraw_state.pop(uid, None)
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"withdraw_approve:{withdrawal['id']}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"withdraw_reject:{withdrawal['id']}")
        )
        bot.send_message(message.chat.id, f"✅ Pul yechish so'rovi qabul qilindi.\n\n💰 Summa: {amount} so'm\n💳 Karta: ****{card[-4:]}\n\n⏳ Admin tasdiqlashini kuting.")
        bot.send_message(ADMIN_ID, f"💸 Yangi pul yechish so'rovi\n\n👤 ID: {uid}\n💰 Summa: {amount} so'm\n💳 Karta: {card}\n🆔 So'rov: {withdrawal['id']}", reply_markup=markup)


# =========================
# PUL YECHISH ADMIN TASDIQLASH
# =========================

@bot.callback_query_handler(func=lambda c: c.data.startswith("withdraw_approve:") or c.data.startswith("withdraw_reject:"))
def withdraw_admin_callback(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q.", show_alert=True)
        return
    action, wid = call.data.split(":", 1)
    item = next((x for x in withdrawals if str(x.get("id")) == wid), None)
    if not item or item.get("status") != "pending":
        bot.answer_callback_query(call.id, "❌ So'rov topilmadi yoki allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    uid = str(item.get("user_id"))
    amount = safe_int(item.get("amount"))
    if action == "withdraw_approve":
        user = users.get(uid)
        if not user or safe_int(user.get("balance")) < amount:
            item["status"] = "rejected"
            DATA["withdrawals"] = withdrawals
            save_json_data()
            bot.answer_callback_query(call.id, "❌ Foydalanuvchi balansida yetarli mablag' qolmagan.", show_alert=True)
            return
        user["balance"] = safe_int(user.get("balance")) - amount
        item["status"] = "approved"
        item["approved_at"] = datetime.now().isoformat()
        save_user_to_json(uid)
        DATA["withdrawals"] = withdrawals
        save_json_data()
        bot.answer_callback_query(call.id, "✅ Pul yechish tasdiqlandi.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        try:
            bot.send_message(int(uid), f"✅ Pul yechish so'rovingiz tasdiqlandi.\n\n💰 {amount} so'm kartaingizga o'tkazish uchun qabul qilindi.")
        except Exception:
            pass
    else:
        item["status"] = "rejected"
        item["rejected_at"] = datetime.now().isoformat()
        DATA["withdrawals"] = withdrawals
        save_json_data()
        bot.answer_callback_query(call.id, "❌ So'rov rad etildi.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        try:
            bot.send_message(int(uid), f"❌ Pul yechish so'rovingiz rad etildi.\n\n💰 {amount} so'm balansingizda saqlanib qoldi.")
        except Exception:
            pass


# =========================
# OYLIK TOP 10 MUKOFOTLARI
# =========================

def build_month_end_message(top, rewards, fund):
    lines = [
        "Assalomu alaykum, hurmatli Kino Yasa yaratuvchilari va hamkorlar! ❤️",
        "",
        "Bu oy yaxshi natijalar ko'rsatib, TOP 10 talikka kirgan barcha hamkorlarimizni chin dildan tabriklaymiz! 🏆",
        "",
    ]
    for i, row in enumerate(top, 1):
        name = row.get("full_name") or "Foydalanuvchi"
        ball = safe_int(row.get("monthly_rating_ball"))
        title = level_from_ball(row.get("rating_ball"))
        if i <= 3:
            medal = ["🥇", "🥈", "🥉"][i-1]
            lines += [f"{medal} {i}-o'rin — {name}", f"🏆 Unvon: {title}", f"⭐ Ball: {ball}", f"💰 Mukofot: {rewards.get(str(i), 0)} so'm", "💳 Mukofot balansingizga qo'shildi.", ""]
        else:
            lines += [f"🎖 {i}-o'rin — {name}", f"🏆 Unvon: {title}", f"⭐ Ball: {ball}", "🎁 Mukofot: 3 marta bepul kino yaratish huquqi.", ""]
    lines += [
        f"💰 Oylik sotuvlardan ajratilgan mukofot fondi: {fund} so'm.",
        "",
        "🥇 1-, 🥈 2-, 🥉 3-o'rin mukofotlari balansingizga qo'shildi.",
        "🎁 4–10-o'rinlarga 3 marta bepul kino yaratish huquqi hisobingizga qo'shildi.",
        "",
        "TOP 10 talikka kira olmagan hamkorlarimiz tushkunlikka tushmasin. 💪 Keyingi oy hali oldinda — yaxshi natija ko'rsatib, TOP 10 ga, hatto 1-o'ringa chiqishingiz mumkin!",
        "",
        "Hurmat bilan, Kino Yasa administratsiyasi",
        "@abdulqodir_royal",
    ]
    return "\n".join(lines)


def build_month_start_message():
    return ("Assalomu alaykum, hurmatli Kino Yasa hamkorlari! ❤️\n\n"
            "O'tgan oy ko'pchilik juda yaxshi natijalar ko'rsatdi. Ishonamizki, bu oy yanada yaxshi natijalar ko'rsatasizlar! 🚀\n\n"
            "O'tgan oy TOP 10 talikka kira olmaganlar tushkunlikka tushmasin — bu oy hali oldinda. Siz ham TOP 10 ga, hatto 1-o'ringa chiqishingiz mumkin! 🏆\n\n"
            "⚠️ Diqqat: 1-, 2-, 3-o'rinlarga beriladigan pul mukofoti shu oyda amalga oshirilgan kino sotuvlariga bog'liq. Sotuvlar qancha ko'p bo'lsa, mukofot fondi ham shuncha ko'p bo'ladi.\n\n"
            "Hurmat bilan, Kino Yasa administratsiyasi\n@abdulqodir_royal")


def distribute_monthly_rewards(target_month=None):
    top = get_top10()
    target_month = target_month or datetime.now().strftime("%Y-%m")
    monthly_sales = sum(safe_int(r.get("amount")) for r in sales_rows if str(r.get("created_at", ""))[:7] == target_month)
    fund = int(monthly_sales * 0.25)
    rewards = {"1": int(fund * 0.50), "2": int(fund * 0.30), "3": fund - int(fund * 0.50) - int(fund * 0.30)}
    for i, row in enumerate(top, 1):
        uid = str(row.get("user_id"))
        if uid not in users:
            continue
        if i <= 3:
            users[uid]["balance"] = safe_int(users[uid].get("balance")) + rewards[str(i)]
        else:
            users[uid]["movie_rights"] = safe_int(users[uid].get("movie_rights")) + 3
        save_user_to_json(uid)
    return top, rewards, fund


def monthly_scheduler():
    while True:
        try:
            now = datetime.now()
            key = now.strftime("%Y-%m")
            previous_key = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            last = month_reward.get("last_processed")
            # Bot oyning 1-kunida ishlamagan bo'lsa ham, keyin ishga tushganda
            # o'tgan oy mukofotlari va yangi oy xabarlarini bir marta yuboradi.
            if last != previous_key:
                top, rewards, fund = distribute_monthly_rewards(previous_key)
                end_text = build_month_end_message(top, rewards, fund)
                end_ok = 0
                for uid in list(users):
                    try:
                        bot.send_message(int(uid), end_text)
                        end_ok += 1
                    except Exception as e:
                        print(f"⚠️ Oy yakuni xabari {uid} ga yuborilmadi: {type(e).__name__}: {e}",flush=True)
                month_reward["last_processed"] = previous_key
                month_reward["current_month"] = key
                save_month_reward()
                for uid in list(users):
                    try:
                        users[uid]["monthly_rating_ball"] = 0
                        save_user_to_json(uid)
                    except Exception as e:
                        print(f"⚠️ {uid} oylik ball reset xatosi: {type(e).__name__}: {e}",flush=True)
                start_text = build_month_start_message()
                start_ok = 0
                for uid in list(users):
                    try:
                        bot.send_message(int(uid), start_text)
                        start_ok += 1
                    except Exception as e:
                        print(f"⚠️ Oy boshi xabari {uid} ga yuborilmadi: {type(e).__name__}: {e}",flush=True)
                print(f"📅 Oylik xabarlar yuborildi: yakun={end_ok}, boshlandi={start_ok}, oy={key}",flush=True)
        except Exception as e:
            print("❌ Oylik mukofot scheduler xatosi:", type(e).__name__, e, flush=True)
        time.sleep(60)

threading.Thread(target=monthly_scheduler, daemon=True).start()

print(
    "✅ 7/8-qism yuklandi",
    flush=True
)

# ============================================================
# KINO YASA BOT
# 8/8-QISM — YAKUNIY ISHGA TUSHIRISH / AI-SIZ KINO
# ============================================================


# =========================
# GLOBAL XATO HANDLER
# =========================

@bot.message_handler(
    func=lambda message: False
)
def unused_handler(message):
    pass


# =========================
# STARTUP
# =========================

def start_bot():

    print(
        "🚀 Kino Yasa Bot ishga tushmoqda...",
        flush=True
    )

    print(
        f"🤖 Bot: {BOT_NAME}",
        flush=True
    )

    print(
        "🗄 JSON: ulangan",
        flush=True
    )


    print(
        "🌐 Flask server ishga tushmoqda...",
        flush=True
    )

    print(
        "🤖 Telegram polling ishga tushmoqda...",
        flush=True
    )
    print("🛠 Kino Yasa Bot v3: video retry + admin video qabul qilish + oy xabarlari catch-up faol", flush=True)

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )


# =========================
# MAIN
# =========================


# =========================
# ASOSIY MENYU — NOTO'G'RI MATNGA JAVOB
# =========================

@bot.message_handler(func=lambda m: bool(m.text) and str(m.chat.id) not in movie_generation_state and str(m.chat.id) not in movie_add_state and str(m.chat.id) not in withdraw_state)
def menu_text_guard(message):
    if not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling.\n\nObuna bo'lmasdan bot bo'limlari ishlamaydi.")
        return
    bot.send_message(message.chat.id, "👇 Iltimos, asosiy menyudagi tugmalardan foydalaning.", reply_markup=main_menu_markup())

if __name__ == "__main__":

    try:

        start_bot()

    except Exception as e:

        print(
            "❌ BOT ISHGA TUSHISHIDA XATO:",
            type(e).__name__,
            e,
            flush=True
        )

        traceback.print_exc()

        raise

