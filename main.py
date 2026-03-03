import telebot
import threading
import time
import os
from keep_alive import keep_alive

TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [7797502113]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# RAM
user_mode = {}
user_rejim = {}
user_text = {}
user_rasm = {}
user_queue = {}
user_last = {}
user_ignore_limit = {}

limit_video = 0
limit_file = 0
user_today_video = {}
user_today_file = {}

help_url = None

# ============================
# 10 SONIYALIK ESLATMA
# ============================
def eslatma_checker():
    while True:
        now = time.time()
        for uid in list(user_last.keys()):
            if now - user_last[uid] >= 10:
                try:
                    bot.send_message(
                        uid,
                        "Agar yana video/fayl tashlashni reja qilgan bo‘lsangiz iltimos yana tashlang.\n"
                        "Agar tamom qilgan bo‘lsangiz /tamom buyrug‘ini bering."
                    )
                except:
                    pass
                user_last[uid] = now
        time.sleep(2)

threading.Thread(target=eslatma_checker, daemon=True).start()

# ============================
# START
# ============================
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    uid = msg.from_user.id

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Fayl", "Video")
    kb.row("Rasm")
    if uid in ADMINS:
        kb.row("Boshqarish")

    bot.send_message(uid, "Fayl yoki Video tanlang:", reply_markup=kb)

    for d in [user_mode, user_rejim, user_text, user_rasm, user_queue, user_last]:
        d.pop(uid, None)

# ============================
# /deletthumb
# ============================
@bot.message_handler(commands=['deletthumb'])
def deletthumb(msg):
    uid = msg.from_user.id
    user_rasm.pop(uid, None)
    bot.send_message(uid, "Rasm (thumb) o‘chirildi ✅")

# ============================
# RASM QABUL QILISH
# ============================
@bot.message_handler(content_types=['photo'])
def rasm_qabul(msg):
    uid = msg.from_user.id
    user_rasm[uid] = msg.photo[-1].file_id
    bot.reply_to(msg, "Rasm qabul qilindi (thumb sifatida ishlatiladi) ✅")

# ============================
# VIDEO / FAYL TANLASH
# ============================
@bot.message_handler(func=lambda m: m.text in ["Video", "Fayl"])
def bolim(msg):
    uid = msg.from_user.id
    user_mode[uid] = "video" if msg.text == "Video" else "file"

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("Hardoim", callback_data="rejim_hardoim"))
    kb.add(telebot.types.InlineKeyboardButton("Raqamli", callback_data="rejim_raqamli"))
    kb.add(telebot.types.InlineKeyboardButton("Shunday qoldirish", callback_data="rejim_qoldirish"))

    if help_url:
        kb.add(telebot.types.InlineKeyboardButton("Chunmadingizmi?", url=help_url))
    elif uid in ADMINS:
        kb.add(telebot.types.InlineKeyboardButton("Chunmadingizmi?", callback_data="add_help_url"))

    bot.send_message(uid, "Qanday turda nomlansin?", reply_markup=kb)

# ============================
# CALLBACK — REJIMLAR
# ============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rejim_"))
def rejim_handler(call):
    uid = call.from_user.id

    if call.data == "rejim_hardoim":
        user_rejim[uid] = "hardoim"
        bot.send_message(uid, "Nomda qoladigan so‘zni yuboring:")
        bot.register_next_step_handler(call.message, hardoim_text)

    elif call.data == "rejim_raqamli":
        user_rejim[uid] = "raqamli"
        bot.send_message(uid, "Nomni yozing va {raqam} qo‘ying:")
        bot.register_next_step_handler(call.message, raqamli_text)

    elif call.data == "rejim_qoldirish":
        user_rejim[uid] = "qoldirish"
        user_queue[uid] = []
        user_last[uid] = time.time()
        bot.send_message(uid, "Endi video/fayllarni tashlang. /tamom deb yozing.")

# ============================
# HARDOIM MATN
# ============================
def hardoim_text(msg):
    uid = msg.from_user.id
    user_text[uid] = msg.text
    user_queue[uid] = []
    user_last[uid] = time.time()
    bot.send_message(uid, "Endi video/fayllarni tashlang.")

# ============================
# RAQAMLI MATN
# ============================
def raqamli_text(msg):
    uid = msg.from_user.id
    matn = msg.text

    if "{raqam}" not in matn:
        user_rejim[uid] = "hardoim"

    user_text[uid] = matn
    user_queue[uid] = []
    user_last[uid] = time.time()
    bot.send_message(uid, "Endi video/fayllarni tashlang.")

# ============================
# MEDIA QABUL QILISH
# ============================
@bot.message_handler(content_types=['video', 'document'])
def media_qabul(msg):
    uid = msg.from_user.id

    if uid not in user_rejim:
        return

    if uid not in user_queue:
        user_queue[uid] = []

    if msg.content_type == "video":
        user_queue[uid].append(("video", msg.video.file_id, msg.video.file_name))
    else:
        user_queue[uid].append(("file", msg.document.file_id, msg.document.file_name))

    user_last[uid] = time.time()

    bot.reply_to(msg, "Qabul qilindi. /tamom deb yozing.")

# ============================
# /TAMOM — FAYL NOMINI HAQIQIY O‘ZGARTIRISH
# ============================
@bot.message_handler(commands=['tamom'])
def tamom_cmd(msg):
    uid = msg.from_user.id

    if uid not in user_queue or len(user_queue[uid]) == 0:
        bot.send_message(uid, "Hech narsa qabul qilinmagan.")
        return

    bot.send_message(uid, "Qayta ishlash boshlandi...")

    rejim = user_rejim.get(uid)
    matn = user_text.get(uid)
    rasm = user_rasm.get(uid)
    queue = user_queue[uid]

    counter = 1

    for turi, file_id, old_name in queue:

        if rejim == "hardoim":
            new_name = matn + ".mp4"

        elif rejim == "raqamli":
            if "{raqam}" in matn:
                new_name = matn.replace("{raqam}", str(counter)) + ".mp4"
            else:
                new_name = matn + ".mp4"

        else:
            new_name = old_name

        # FAYL NOMINI HAQIQIY O‘ZGARTIRISH
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        with open(new_name, "wb") as f:
            f.write(downloaded)

        if turi == "video":
            bot.send_video(uid, open(new_name, "rb"), caption=new_name, thumb=rasm)
        else:
            bot.send_document(uid, open(new_name, "rb"), caption=new_name)

        os.remove(new_name)
        counter += 1

    bot.send_message(uid, "Barcha fayllar yuborildi ✅")

    for d in [user_queue, user_rejim, user_text, user_last]:
        d.pop(uid, None)

# ============================
# ADMIN PANEL
# ============================
@bot.message_handler(func=lambda m: m.text == "Boshqarish")
def admin_panel(msg):
    if msg.from_user.id not in ADMINS:
        return

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Majburi obuna")
    kb.row("Statistika")
    kb.row("Habar yuborish")
    kb.row("Cheklovlar")
    kb.row("Cheklovdan ozod qilish")
    kb.row("Orqaga")

    bot.send_message(msg.chat.id, "Admin paneli:", reply_markup=kb)

# ============================
# BOTNI ISHGA TUSHIRISH
# ============================
keep_alive()
bot.infinity_polling()
