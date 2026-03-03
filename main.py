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
        bot.send_message(uid, "Thumb rasm mavjud emas. Rasm yuboring — saqlab qo‘yaman.")
        return

    bot.send_photo(uid, user_thumb[uid], caption="Saqlangan thumb rasm.")


# ============================
# /deletthumb — rasmni o‘chirish
# ============================
@bot.message_handler(commands=['deletthumb'])
def deletthumb_cmd(msg):
    uid = msg.from_user.id
    user_thumb.pop(uid, None)
    bot.send_message(uid, "Thumb rasm o‘chirildi.")


# ============================
# RASM QABUL QILISH → thumb sifatida saqlash
# ============================
@bot.message_handler(content_types=['photo'])
def save_thumb(msg):
    uid = msg.from_user.id
    user_thumb[uid] = msg.photo[-1].file_id
    bot.reply_to(msg, "Rasm thumb sifatida saqlandi.")


# ============================
# VIDEO QABUL QILISH
# ============================
@bot.message_handler(content_types=['video'])
def video_process(msg):
    uid = msg.from_user.id
    video = msg.video

    # Yangi nom
    new_name = f"{video.file_unique_id}.mp4"

    # Jarayonni boshlash
    bot.send_message(
        uid,
        f"🎬 <b>Video qabul qilindi</b>\n"
        f"📌 Turi: Video\n"
        f"📄 Yangi nom: <code>{new_name}</code>\n"
        f"⏳ Tayyor: 0%\n"
        f"⌛ Taxminiy vaqt: 5–10 soniya"
    )

    # Yuklab olish
    start = time.time()
    file_info = bot.get_file(video.file_id)
    downloaded = bot.download_file(file_info.file_path)

    # Saqlash
    with open(new_name, "wb") as f:
        f.write(downloaded)

    # 50% holat
    bot.send_message(uid, "⏳ Tayyor: 50%")

    # Thumb bo‘lsa qo‘shamiz
    thumb = user_thumb.get(uid)

    # Yuborish
    bot.send_video(
        uid,
        open(new_name, "rb"),
        caption=f"{new_name}",
        thumb=thumb
    )

    # O‘chirish
    os.remove(new_name)

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
