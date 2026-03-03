import os
import time
import telebot

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

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
# VIDEO QABUL QILISH → yuklab olish → nomini o‘zgartirish → thumb qo‘yish → qayta yuklash
# ============================
@bot.message_handler(content_types=['video'])
def video_process(msg):
    uid = msg.from_user.id
    video = msg.video

    new_name = "@AniGonUz.mp4"

    bot.send_message(
        uid,
        f"🎬 <b>Video qabul qilindi</b>\n"
        f"📌 Turi: Video\n"
        f"📄 Yangi nom: <code>{new_name}</code>\n"
        f"⏳ Tayyor: 0%"
    )

    start = time.time()

    # 1) Videoni yuklab olish
    file_info = bot.get_file(video.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open(new_name, "wb") as f:
        f.write(downloaded)

    bot.send_message(uid, "⏳ Tayyor: 50%")

    # 2) Thumb bo‘lsa qo‘shamiz
    thumb = user_thumb.get(uid)

    # 3) Videoni qayta yuklash
    with open(new_name, "rb") as f:
        bot.send_video(
            uid,
            f,
            caption=msg.caption,
            thumb=thumb,
            supports_streaming=True
        )

    # 4) Faylni o‘chirish
    os.remove(new_name)

    duration = int(time.time() - start)

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
    pass


# ============================
# BOTNI ISHGA TUSHIRISH
# ============================
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Xato:", e)
        time.sleep(3)
