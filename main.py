import os
import time
import telebot
from telebot import types
from keep_alive import keep_alive

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Thumb saqlash
user_thumb = {}   # {user_id: file_id}


# ============================
# /start
# ============================
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    bot.send_message(
        msg.chat.id,
        "⚠️ Bu bot faqat <b>@Shadow_Sxi</b> uchun ishlaydi."
    )


# ============================
# /thumb — saqlangan rasmni ko‘rsatish
# ============================
@bot.message_handler(commands=['thumb'])
def thumb_cmd(msg):
    uid = msg.from_user.id

    if uid not in user_thumb:
        bot.send_message(uid, "Rasm mavjud emas. Rasmni hozir yuboring — saqlab qo‘yaman.")
        return

    bot.send_photo(uid, user_thumb[uid], caption="Saqlangan rasm.")


# ============================
# /deletthumb — rasmni o‘chirish
# ============================
@bot.message_handler(commands=['deletthumb'])
def deletthumb_cmd(msg):
    uid = msg.from_user.id
    user_thumb.pop(uid, None)
    bot.send_message(uid, "Rasm o‘chirildi.")


# ============================
# RASM QABUL QILISH → thumb sifatida saqlash
# ============================
@bot.message_handler(content_types=['photo'])
def save_thumb(msg):
    uid = msg.from_user.id
    user_thumb[uid] = msg.photo[-1].file_id
    bot.reply_to(msg, "Rasm saqlandi.")


# ============================
# VIDEO QABUL QILISH
# ============================
@bot.message_handler(content_types=['video'])
def video_process(msg):
    uid = msg.from_user.id
    video = msg.video

    # Yangi nom — faqat @AniGonUz.mp4
    new_name = "@AniGonUz.mp4"

    # Jarayonni boshlash
    bot.send_message(
        uid,
        f"🎬 <b>Video qabul qilindi</b>\n"
        f"📌 Turi: Video\n"
        f"📄 Yangi nom: <code>{new_name}</code>\n"
        f"⏳ Tayyor: 0%\n"
        f"⌛ Hisoblanmoqda..."
    )

    start = time.time()

    # 50% holat
    bot.send_message(uid, "⏳ Tayyor: 50%")

    # Thumb bo‘lsa qo‘shamiz
    thumb = user_thumb.get(uid)

    # Videoni qayta yuborish (yuklab olish shart emas!)
    bot.send_video(
        uid,
        video.file_id,
        caption=new_name,
        thumb=thumb
    )

    end = time.time()
    duration = int(end - start)

    # Yakuniy xabar
    bot.send_message(
        uid,
        f"✅ Tayyor: 100%\n"
        f"⌛ Sarflangan vaqt: {duration} soniya"
    )


# ============================
# FAYL QABUL QILINSA → E’TIBOR BERILMAYDI
# ============================
@bot.message_handler(content_types=['document'])
def ignore_files(msg):
    pass  # jim turadi


# ============================
# BOTNI ISHGA TUSHIRISH
# ============================
keep_alive()

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Xato:", e)
        time.sleep(3)
