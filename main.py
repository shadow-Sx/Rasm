import os
import time
import threading
import telebot
from telebot import types
from keep_alive import keep_alive

# ============================
# CONFIG
# ============================
TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [7797502113]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ============================
# GLOBAL STATE
# ============================
# User flow
user_mode = {}          # {user_id: "video" / "file"}
user_rejim = {}         # {user_id: "hardoim" / "raqamli" / "qoldirish"}
user_text = {}          # {user_id: text}
user_rasm = {}          # {user_id: thumb_file_id}
user_queue = {}         # {user_id: [(type, file_id, file_name), ...]}
user_last = {}          # {user_id: last_activity_timestamp}
user_processing = {}    # {user_id: True} while /tamom processing

# Start screen
START_TEXT = "Iltimos o'zingizga kerakli variantni tanlang"
START_MEDIA = None       # file_id
START_MEDIA_TYPE = None  # "photo" / "video"

# Stats
all_users = set()
active_users = set()

# Limits
limit_video = 0
limit_file = 0
user_daily_video = {}    # {user_id: count}
user_daily_file = {}     # {user_id: count}
user_custom_limit = {}   # {user_id: limit or 0}

# Mandatory subscriptions
mandatory_subs = []      # list of dicts:
# {
#   "type": 1/2/3,
#   "title": str,
#   "url": str,
#   "limit": int or None,
#   "channel_id": int or None
# }

# Post builder
post_builder = {}        # {admin_id: {"text": Message|str, "buttons":[{"name":..., "url":...}]}}

# Admin flows (for majburi obuna steps)
admin_flow = {}          # {admin_id: {"step":..., "data":{...}}}


# ============================
# HELPERS
# ============================
def register_user(uid: int):
    all_users.add(uid)
    active_users.add(uid)


def check_subs(uid: int):
    """
    Agar majburi obuna bo'lsa va foydalanuvchi kanalga a'zo bo'lmasa,
    qaytadi: sub (dict). Aks holda None.
    """
    for sub in mandatory_subs:
        if sub["type"] in [1, 2] and sub["channel_id"]:
            try:
                member = bot.get_chat_member(sub["channel_id"], uid)
                if member.status in ["left", "kicked"]:
                    return sub
            except:
                return sub
    return None


def build_start_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📁 Fayl", callback_data="mode_file"))
    kb.add(types.InlineKeyboardButton("🎬 Video", callback_data="mode_video"))
    return kb


def build_admin_main_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("Majburi obuna", callback_data="admin_subs"),
        types.InlineKeyboardButton("Statistika", callback_data="admin_stats")
    )
    kb.row(
        types.InlineKeyboardButton("Habar yuborish", callback_data="admin_post"),
        types.InlineKeyboardButton("Cheklovlar", callback_data="admin_limits")
    )
    kb.row(
        types.InlineKeyboardButton("Cheklovlardan ozod qilish", callback_data="admin_unlimit"),
        types.InlineKeyboardButton("Orqaga", callback_data="admin_back")
    )
    kb.row(
        types.InlineKeyboardButton("Start matnini tahrirlash", callback_data="admin_edit_start")
    )
    return kb


# ============================
# 60 SONIYALIK ESLATMA
# ============================
def eslatma_checker():
    while True:
        now = time.time()
        for uid in list(user_last.keys()):
            if uid in user_processing:
                continue
            if now - user_last[uid] >= 60:
                try:
                    bot.send_message(
                        uid,
                        "Agar yana video/fayl tashlamoqchi bo‘lsangiz tashlang.\n"
                        "Agar tamom bo‘lsa /tamom deb yozing."
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
    register_user(uid)

    # Majburi obuna tekshiruvi
    sub = check_subs(uid)
    if sub:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(sub["title"], url=sub["url"]))
        bot.send_message(
            uid,
            "Botdan foydalanish uchun quyidagi kanalga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    kb = build_start_keyboard()

    if START_MEDIA:
        if START_MEDIA_TYPE == "photo":
            bot.send_photo(uid, START_MEDIA, caption=START_TEXT, reply_markup=kb)
        else:
            bot.send_video(uid, START_MEDIA, caption=START_TEXT, reply_markup=kb)
    else:
        bot.send_message(uid, START_TEXT, reply_markup=kb)

    for d in [user_mode, user_rejim, user_text, user_rasm, user_queue, user_last, user_processing]:
        d.pop(uid, None)


# ============================
# /thumb va /deletthumb
# ============================
@bot.message_handler(commands=['thumb'])
def thumb_cmd(msg):
    uid = msg.from_user.id
    register_user(uid)

    if uid in user_rasm:
        bot.send_photo(uid, user_rasm[uid], caption="Saqlangan rasm (thumb)")
    else:
        bot.send_message(uid, "Thumb rasm yo‘q. Rasm yuboring — avtomatik saqlanadi.")


@bot.message_handler(commands=['deletthumb'])
def deletthumb_cmd(msg):
    uid = msg.from_user.id
    register_user(uid)

    user_rasm.pop(uid, None)
    bot.send_message(uid, "Thumb rasm o‘chirildi.")


@bot.message_handler(content_types=['photo'])
def rasm_qabul(msg):
    uid = msg.from_user.id
    register_user(uid)

    user_rasm[uid] = msg.photo[-1].file_id
    bot.reply_to(msg, "Rasm thumb sifatida saqlandi.")


# ============================
# ADMIN PANELI (TEXT TUGMA)
# ============================
@bot.message_handler(func=lambda m: m.text == "Boshqarish")
def admin_panel_entry(msg):
    uid = msg.from_user.id
    register_user(uid)

    if uid not in ADMINS:
        return

    kb = build_admin_main_keyboard()
    bot.send_message(uid, "Admin paneli:", reply_markup=kb)


# ============================
# ADMIN PANELI CALLBACKLAR
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_back")
def admin_back(call):
    if call.from_user.id not in ADMINS:
        return
    kb = build_admin_main_keyboard()
    bot.edit_message_text(
        "Admin paneli:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_edit_start")
def admin_edit_start(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    bot.send_message(
        uid,
        "Yangi start matnini yuboring.\n"
        "Agar rasm/video yuborsangiz — start media sifatida saqlanadi."
    )
    bot.register_next_step_handler(call.message, save_start_content)


def save_start_content(msg):
    global START_TEXT, START_MEDIA, START_MEDIA_TYPE
    uid = msg.from_user.id
    if uid not in ADMINS:
        return

    if msg.content_type == "text":
        START_TEXT = msg.text
        START_MEDIA = None
        START_MEDIA_TYPE = None
        bot.send_message(uid, "Start matni yangilandi.")
    elif msg.content_type == "photo":
        START_MEDIA = msg.photo[-1].file_id
        START_MEDIA_TYPE = "photo"
        if msg.caption:
            START_TEXT = msg.caption
        bot.send_message(uid, "Start rasmi yangilandi.")
    elif msg.content_type == "video":
        START_MEDIA = msg.video.file_id
        START_MEDIA_TYPE = "video"
        if msg.caption:
            START_TEXT = msg.caption
        bot.send_message(uid, "Start videosi yangilandi.")
    else:
        bot.send_message(uid, "Faqat matn, rasm yoki video yuboring.")


# ============================
# MODE TANLASH (FAYL / VIDEO)
# ============================
@bot.callback_query_handler(func=lambda c: c.data in ["mode_file", "mode_video"])
def mode_select(call):
    uid = call.from_user.id
    register_user(uid)

    if call.data == "mode_file":
        user_mode[uid] = "file"
    else:
        user_mode[uid] = "video"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("♾ Hardoim", callback_data="rejim_hardoim"))
    kb.add(types.InlineKeyboardButton("🔢 Raqamli", callback_data="rejim_raqamli"))
    kb.add(types.InlineKeyboardButton("📌 Shunday qoldirish", callback_data="rejim_qoldirish"))

    bot.edit_message_text(
        "Qanday turda nomlansin?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# ============================
# REJIMLAR
# ============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rejim_"))
def rejim_handler(call):
    uid = call.from_user.id
    register_user(uid)

    if call.data == "rejim_hardoim":
        user_rejim[uid] = "hardoim"
        bot.send_message(uid, "Nomda qoladigan so‘zni yuboring:")
        bot.register_next_step_handler(call.message, hardoim_text)

    elif call.data == "rejim_raqamli":
        user_rejim[uid] = "raqamli"
        bot.send_message(uid, "Nomni yozing va {raqam} qo‘ying:")
        bot.register_next_step_handler(call.message, raqamli_text)

    else:
        user_rejim[uid] = "qoldirish"
        user_queue[uid] = []
        user_last[uid] = time.time()
        bot.send_message(uid, "Endi video/fayllarni tashlang. /tamom deb yozing.")


def hardoim_text(msg):
    uid = msg.from_user.id
    register_user(uid)

    user_text[uid] = msg.text
    user_queue[uid] = []
    user_last[uid] = time.time()
    bot.send_message(uid, "Endi video/fayllarni tashlang.")


def raqamli_text(msg):
    uid = msg.from_user.id
    register_user(uid)

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
    register_user(uid)

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
# /TAMOM
# ============================
@bot.message_handler(commands=['tamom'])
def tamom_cmd(msg):
    uid = msg.from_user.id
    register_user(uid)

    if uid not in user_queue or len(user_queue[uid]) == 0:
        bot.send_message(uid, "Hech narsa qabul qilinmagan.")
        return

    user_processing[uid] = True
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

    for d in [user_queue, user_rejim, user_text, user_last, user_processing]:
        d.pop(uid, None)


# ============================
# STATISTIKA
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
def admin_stats(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    total = len(all_users)
    active = len(active_users)

    bot.edit_message_text(
        f"📊 Statistika:\n\n"
        f"👥 Barcha foydalanuvchilar: {total}\n"
        f"🟢 Aktiv foydalanuvchilar: {active}",
        call.message.chat.id,
        call.message.message_id
    )


# ============================
# CHEKLOVLAR
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_limits")
def admin_limits(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🎬 Video cheklovi", callback_data="limit_video"),
        types.InlineKeyboardButton("📁 Fayl cheklovi", callback_data="limit_file")
    )
    kb.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))

    bot.edit_message_text(
        f"Cheklovlar:\n\n"
        f"🎬 Video: {limit_video}\n"
        f"📁 Fayl: {limit_file}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data in ["limit_video", "limit_file"])
def limit_change(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    limit_type = call.data
    bot.send_message(uid, "Yangi cheklovni kiriting (0 = cheklov yo‘q):")
    bot.register_next_step_handler(call.message, save_limit, limit_type)


def save_limit(msg, limit_type):
    global limit_video, limit_file
    try:
        value = int(msg.text)
    except:
        bot.send_message(msg.chat.id, "Faqat son kiriting.")
        return

    if limit_type == "limit_video":
        limit_video = value
        bot.send_message(msg.chat.id, f"Video cheklovi {value} ga o‘rnatildi.")
    else:
        limit_file = value
        bot.send_message(msg.chat.id, f"Fayl cheklovi {value} ga o‘rnatildi.")


# ============================
# CHEKLOVLARDAN OZOD QILISH
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_unlimit")
def admin_unlimit(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    bot.send_message(uid, "Foydalanuvchi ID raqamini yuboring:")
    bot.register_next_step_handler(call.message, unlimit_user_id)


def unlimit_user_id(msg):
    try:
        target_id = int(msg.text)
    except:
        bot.send_message(msg.chat.id, "ID faqat son bo‘lishi kerak.")
        return

    admin_flow[msg.chat.id] = {"step": "unlimit", "uid": target_id}
    bot.send_message(msg.chat.id, "Ushbu foydalanuvchi uchun kunlik limitni kiriting (0 = cheklov yo‘q):")
    bot.register_next_step_handler(msg, unlimit_user_limit)


def unlimit_user_limit(msg):
    admin_id = msg.chat.id
    if admin_id not in admin_flow or admin_flow[admin_id].get("step") != "unlimit":
        bot.send_message(admin_id, "Jarayon topilmadi.")
        return

    try:
        limit = int(msg.text)
    except:
        bot.send_message(admin_id, "Faqat son kiriting.")
        return

    uid = admin_flow[admin_id]["uid"]
    user_custom_limit[uid] = limit
    bot.send_message(admin_id, f"{uid} foydalanuvchi uchun limit {limit} ga o‘rnatildi.")
    admin_flow.pop(admin_id, None)


# ============================
# HABAR YUBORISH (POST BUILDER)
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_post")
def admin_post(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    post_builder[uid] = {"text": None, "buttons": []}
    bot.send_message(uid, "Habar yuboring (matn yoki forward):")
    bot.register_next_step_handler(call.message, post_receive)


def post_receive(msg):
    uid = msg.from_user.id
    if uid not in ADMINS:
        return

    if msg.forward_from or msg.forward_from_chat:
        post_builder[uid]["text"] = msg
        bot.send_message(uid, "Forward qabul qilindi. Tugma qo‘shib bo‘lmaydi.")
        show_post_menu(uid, forward=True)
        return

    post_builder[uid]["text"] = msg.text
    show_post_menu(uid, forward=False)


def show_post_menu(uid, forward: bool):
    kb = types.InlineKeyboardMarkup()
    if not forward:
        kb.add(types.InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="post_add_btn"))
    kb.add(
        types.InlineKeyboardButton("👁 Ko‘rish", callback_data="post_preview"),
        types.InlineKeyboardButton("📤 Yuborish", callback_data="post_send")
    )
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="post_cancel"))
    bot.send_message(uid, "Post menyusi:", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "post_add_btn")
def post_add_btn(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    bot.send_message(uid, "Tugma nomini yuboring:")
    bot.register_next_step_handler(call.message, post_btn_name)


def post_btn_name(msg):
    uid = msg.from_user.id
    if uid not in ADMINS:
        return

    admin_flow[uid] = {"step": "post_btn", "name": msg.text}
    bot.send_message(uid, "URL yuboring:")
    bot.register_next_step_handler(msg, post_btn_url)


def post_btn_url(msg):
    uid = msg.from_user.id
    if uid not in ADMINS or uid not in admin_flow or admin_flow[uid].get("step") != "post_btn":
        bot.send_message(uid, "Jarayon topilmadi.")
        return

    name = admin_flow[uid]["name"]
    url = msg.text

    post_builder[uid]["buttons"].append({"name": name, "url": url})
    bot.send_message(uid, "Tugma qo‘shildi.")
    admin_flow.pop(uid, None)
    show_post_menu(uid, forward=False)


@bot.callback_query_handler(func=lambda c: c.data == "post_preview")
def post_preview(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    data = post_builder.get(uid)
    if not data or not data["text"]:
        bot.send_message(uid, "Post topilmadi.")
        return

    kb = types.InlineKeyboardMarkup()
    for b in data["buttons"]:
        kb.add(types.InlineKeyboardButton(b["name"], url=b["url"]))

    bot.send_message(uid, "Post qanday ko‘rinadi:")
    if isinstance(data["text"], str):
        bot.send_message(uid, data["text"], reply_markup=kb)
    else:
        # forward qilingan xabarni preview qilish
        try:
            bot.copy_message(uid, data["text"].chat.id, data["text"].message_id, reply_markup=kb)
        except:
            bot.send_message(uid, "Previewda xatolik yuz berdi.")


@bot.callback_query_handler(func=lambda c: c.data == "post_send")
def post_send(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    data = post_builder.get(uid)
    if not data or not data["text"]:
        bot.send_message(uid, "Post topilmadi.")
        return

    kb = types.InlineKeyboardMarkup()
    for b in data["buttons"]:
        kb.add(types.InlineKeyboardButton(b["name"], url=b["url"]))

    for user in list(all_users):
        try:
            if isinstance(data["text"], str):
                bot.send_message(user, data["text"], reply_markup=kb)
            else:
                bot.copy_message(user, data["text"].chat.id, data["text"].message_id, reply_markup=kb)
        except:
            pass

    bot.send_message(uid, "Post yuborildi.")
    post_builder.pop(uid, None)


@bot.callback_query_handler(func=lambda c: c.data == "post_cancel")
def post_cancel(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    post_builder.pop(uid, None)
    bot.send_message(uid, "Bekor qilindi.")


# ============================
# MAJBURI OBUNA (SODDA 3-TUR: IXTIYORIY HAVOLA)
# ============================
@bot.callback_query_handler(func=lambda c: c.data == "admin_subs")
def admin_subs_menu(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("3️⃣ Ixtiyoriy havola", callback_data="sub_type_3"))
    kb.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="admin_back"))

    bot.edit_message_text(
        "Majburi obuna bo‘limi (hozircha faqat ixtiyoriy havola):",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "sub_type_3")
def sub_type_3(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        return

    bot.send_message(uid, "Iltimos havola yuboring:")
    bot.register_next_step_handler(call.message, sub_type_3_url)


def sub_type_3_url(msg):
    uid = msg.from_user.id
    if uid not in ADMINS:
        return

    admin_flow[uid] = {"step": "sub3", "url": msg.text}
    bot.send_message(uid, "Tugma uchun nom yuboring:")
    bot.register_next_step_handler(msg, sub_type_3_title)


def sub_type_3_title(msg):
    uid = msg.from_user.id
    if uid not in ADMINS or uid not in admin_flow or admin_flow[uid].get("step") != "sub3":
        bot.send_message(uid, "Jarayon topilmadi.")
        return

    title = msg.text
    url = admin_flow[uid]["url"]

    mandatory_subs.append({
        "type": 3,
        "title": title,
        "url": url,
        "limit": None,
        "channel_id": None
    })

    bot.send_message(uid, "Ixtiyoriy havola majburi obunaga qo‘shildi.")
    admin_flow.pop(uid, None)


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
