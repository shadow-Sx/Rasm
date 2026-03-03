import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keep_alive import keep_alive
import time

# -------------------------
# CONFIG
# -------------------------
import os
TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [7797502113]

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------
# BOT & DISPATCHER
# -------------------------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# -------------------------
# GLOBAL MEMORY (RAM)
# -------------------------
user_mode = {}          # {user_id: "video" / "file"}
user_rejim = {}         # {user_id: "hardoim" / "raqamli" / "qoldirish"}
user_text = {}          # {user_id: matn}
user_rasm = {}          # {user_id: file_id}
user_queue = {}         # {user_id: [video1, video2, ...]}
user_last = {}          # {user_id: timestamp}
user_ignore_limit = {}  # {user_id: True/False}

# Cheklovlar
limit_video = 0
limit_file = 0
user_today_video = {}
user_today_file = {}

# Majburi obuna URL
help_url = None

# -------------------------
# STATES
# -------------------------
class RejimState(StatesGroup):
    hardoim_text = State()
    raqamli_text = State()

class AdminState(StatesGroup):
    send_post = State()
    send_button_name = State()
    send_button_url = State()
    limit_change = State()
    remove_limit = State()
    add_help_url = State()

# ============================================================
# 2-QISM — FOYDALANUVCHI BO‘LIMI
# ============================================================

# -------------------------
# START COMMAND
# -------------------------
@dp.message(Command("start"))
async def start_cmd(msg: Message, state: FSMContext):
    user_id = msg.from_user.id

    # Foydalanuvchi uchun tugmalar
    btns = [
        [KeyboardButton(text="Fayl"), KeyboardButton(text="Video")],
        [KeyboardButton(text="Rasm")]
    ]

    # Admin bo‘lsa — boshqarish tugmasi qo‘shiladi
    if user_id in ADMINS:
        btns.append([KeyboardButton(text="Boshqarish")])

    kb = ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

    await msg.answer(
        "Iltimos menga Fayl yoki Video yuborishdan oldin \"/\" buyruqlardan foydalaning yoki pastdagi tugmalar orqali boshqaring",
        reply_markup=kb
    )

    # Foydalanuvchi holatini tozalaymiz
    user_mode.pop(user_id, None)
    user_rejim.pop(user_id, None)
    user_text.pop(user_id, None)
    user_rasm.pop(user_id, None)
    user_queue.pop(user_id, None)
    user_last.pop(user_id, None)


# -------------------------
# RASM QABUL QILISH
# -------------------------
@dp.message(F.photo)
async def rasm_qabul(msg: Message):
    user_id = msg.from_user.id
    file_id = msg.photo[-1].file_id

    user_rasm[user_id] = file_id

    await msg.answer("Rasm qabul qilindi ✅")


# -------------------------
# VIDEO / FAYL BO‘LIMINI TANLASH
# -------------------------
@dp.message(F.text == "Video")
async def video_bolim(msg: Message):
    user_id = msg.from_user.id
    user_mode[user_id] = "video"

    await rejim_tanlash(msg)



@dp.message(F.text == "Fayl")
async def fayl_bolim(msg: Message):
    user_id = msg.from_user.id
    user_mode[user_id] = "file"

    await rejim_tanlash(msg)


async def rejim_tanlash(msg: Message):
    # Inline tugmalar
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Hardoim", callback_data="rejim_hardoim")],
        [InlineKeyboardButton(text="Raqamli", callback_data="rejim_raqamli")],
        [InlineKeyboardButton(text="Shunday qoldirish", callback_data="rejim_qoldirish")]
    ])

    # Chunmadingizmi? tugmasi — faqat URL bo‘lsa ko‘rinadi
    if help_url:
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="Chunmadingizmi?", url=help_url)]
        )
    else:
        # URL yo‘q — faqat admin ko‘radi
        if msg.from_user.id in ADMINS:
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text="Chunmadingizmi?", callback_data="add_help_url")]
            )

    await msg.answer("Qanday turda nomlansin?", reply_markup=kb)


# -------------------------
# REJIM TANLASH CALLBACK
# -------------------------
@dp.callback_query(F.data == "rejim_hardoim")
async def rejim_hardoim(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    user_rejim[user_id] = "hardoim"

    await call.message.answer("Iltimos menga fayl/video nomida qoladigan so‘zni yuboring")
    await state.set_state(RejimState.hardoim_text)


@dp.callback_query(F.data == "rejim_raqamli")
async def rejim_raqamli(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    user_rejim[user_id] = "raqamli"

    await call.message.answer(
        "Iltimos fayl nomini yozing va raqamlar joyiga {raqam} qo‘ying.\n"
        "Masalan:\n<code>Anime Naruto {raqam}</code>\n\n"
        "Agar {raqam} bo‘lmasa — avtomatik Hardoim bo‘ladi.\n\n"
        "Pastda BEKOR QILISH tugmasi bo‘ladi."
    )
    await state.set_state(RejimState.raqamli_text)


@dp.callback_query(F.data == "rejim_qoldirish")
async def rejim_qoldirish(call: CallbackQuery):
    user_id = call.from_user.id
    user_rejim[user_id] = "qoldirish"

    # Navbatni tayyorlaymiz
    user_queue[user_id] = []
    user_last[user_id] = time.time()

    await call.message.answer(
        "Shunday qoldirish rejimi tanlandi.\n"
        "Endi video/fayllarni tashlang.\n"
        "Tugatsangiz /tamom deb yozing."
    )


# -------------------------
# HARDOIM MATN QABUL QILISH
# -------------------------
@dp.message(RejimState.hardoim_text)
async def hardoim_text_qabul(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    user_text[user_id] = msg.text

    user_queue[user_id] = []
    user_last[user_id] = time.time()

    await msg.answer("Endi video/fayllarni tashlang. Tugatsangiz /tamom deb yozing.")
    await state.clear()


# -------------------------
# RAQAMLI MATN QABUL QILISH
# -------------------------
@dp.message(RejimState.raqamli_text)
async def raqamli_text_qabul(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    matn = msg.text

    if "{raqam}" not in matn:
        user_rejim[user_id] = "hardoim"

    user_text[user_id] = matn
    user_queue[user_id] = []
    user_last[user_id] = time.time()

    await msg.answer("Endi video/fayllarni tashlang. Tugatsangiz /tamom deb yozing.")
    await state.clear()


# -------------------------
# VIDEO / FAYL QABUL QILISH
# -------------------------
@dp.message(F.video | F.document)
async def media_qabul(msg: Message):
    user_id = msg.from_user.id

    # Rejim tanlanmagan bo‘lsa — e’tibor bermaymiz
    if user_id not in user_rejim:
        return

    # Navbatga qo‘shamiz
    if user_id not in user_queue:
        user_queue[user_id] = []

    if msg.video:
        user_queue[user_id].append(("video", msg.video.file_id, msg.video.file_name))
    else:
        user_queue[user_id].append(("file", msg.document.file_id, msg.document.file_name))

    # Oxirgi vaqtni yangilaymiz
    user_last[user_id] = time.time()

    await msg.answer(
        "Qabul qilindi.\n"
        "Agar yana video/fayl tashlashni reja qilgan bo‘lsangiz, iltimos yana tashlang.\n"
        "Agar tamom bo‘lsa — /tamom deb yozing."
    )


# -------------------------
# 10 SONIYALIK ESLATMA (BACKGROUND TASK)
# -------------------------
async def eslatma_checker():
    while True:
        now = time.time()
        for user_id in list(user_last.keys()):
            if now - user_last[user_id] >= 10:
                await bot.send_message(
                    user_id,
                    "Agar yana video/fayl tashlashni reja qilgan bo‘lsangiz iltimos yana tashlang.\n"
                    "Agar tamom qilgan bo‘lsangiz /tamom buyrug‘ini bering."
                )
                user_last[user_id] = now
        await asyncio.sleep(2)


# -------------------------
# /TAMOM — QAYTA ISHLASH
# -------------------------
@dp.message(Command("tamom"))
async def tamom_cmd(msg: Message):
    user_id = msg.from_user.id

    if user_id not in user_queue or len(user_queue[user_id]) == 0:
        await msg.answer("Hech qanday video/fayl qabul qilinmagan.")
        return

    await msg.answer("Qayta ishlash boshlandi...")

    rejim = user_rejim.get(user_id)
    matn = user_text.get(user_id)
    rasm = user_rasm.get(user_id)
    queue = user_queue[user_id]

    counter = 1

    for turi, file_id, old_name in queue:

        # NOM YARATISH
        if rejim == "hardoim":
            new_name = matn + ".mp4"

        elif rejim == "raqamli":
            if "{raqam}" in matn:
                new_name = matn.replace("{raqam}", str(counter)) + ".mp4"
            else:
                new_name = matn + ".mp4"

        else:  # qoldirish
            new_name = old_name

        # YUBORISH
        if turi == "video":
            await bot.send_video(
                chat_id=user_id,
                video=file_id,
                thumbnail=rasm,
                caption=new_name
            )
        else:
            await bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=new_name
            )

        counter += 1

    await msg.answer("Barcha fayllar yuborildi ✅")

    # Tozalash
    user_queue.pop(user_id, None)
    user_rejim.pop(user_id, None)
    user_text.pop(user_id, None)
    user_last.pop(user_id, None)



# ============================================================
# 3-QISM — ADMIN PANELI
# ============================================================

# -------------------------
# BOSHQARISH TUGMASI
# -------------------------
@dp.message(F.text == "Boshqarish")
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMINS:
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Majburi obuna")],
            [KeyboardButton(text="Statistika")],
            [KeyboardButton(text="Habar yuborish")],
            [KeyboardButton(text="Cheklovlar")],
            [KeyboardButton(text="Cheklovdan ozod qilish")],
            [KeyboardButton(text="Orqaga")]
        ],
        resize_keyboard=True
    )

    await msg.answer("Admin paneliga xush kelibsiz!", reply_markup=kb)


# -------------------------
# ORQAGA
# -------------------------
@dp.message(F.text == "Orqaga")
async def back_to_menu(msg: Message):
    await start_cmd(msg, None)


# -------------------------
# MAJBURI OBUNA
# -------------------------
@dp.message(F.text == "Majburi obuna")
async def majburi_obuna(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMINS:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="URL qo‘shish", callback_data="add_help_url")],
        [InlineKeyboardButton(text="URLni o‘chirish", callback_data="remove_help_url")]
    ])

    await msg.answer("Majburi obuna boshqaruvi:", reply_markup=kb)


@dp.callback_query(F.data == "add_help_url")
async def add_help_url(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return

    await call.message.answer("Iltimos URL yuboring:")
    await state.set_state(AdminState.add_help_url)


@dp.message(AdminState.add_help_url)
async def save_help_url(msg: Message, state: FSMContext):
    global help_url
    help_url = msg.text

    await msg.answer("URL qo‘shildi!")
    await state.clear()


@dp.callback_query(F.data == "remove_help_url")
async def remove_help_url(call: CallbackQuery):
    global help_url
    help_url = None
    await call.message.answer("URL o‘chirildi!")


# -------------------------
# STATISTIKA
# -------------------------
@dp.message(F.text == "Statistika")
async def statistika(msg: Message):
    if msg.from_user.id not in ADMINS:
        return

    total_users = len(user_today_video) + len(user_today_file)

    await msg.answer(
        f"📊 Statistika:\n\n"
        f"Bugun video ishlatganlar: {len(user_today_video)} ta\n"
        f"Bugun fayl ishlatganlar: {len(user_today_file)} ta\n"
        f"Jami foydalanuvchilar: {total_users} ta"
    )


# -------------------------
# HABAR YUBORISH
# -------------------------
@dp.message(F.text == "Habar yuborish")
async def habar_yuborish(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMINS:
        return

    await msg.answer("Yubormoqchi bo‘lgan habaringizni yozing:")
    await state.set_state(AdminState.send_post)


@dp.message(AdminState.send_post)
async def send_post_to_all(msg: Message, state: FSMContext):
    text = msg.text

    # Barcha foydalanuvchilarga yuborish
    users = set(list(user_today_video.keys()) + list(user_today_file.keys()))

    for uid in users:
        try:
            await bot.send_message(uid, text)
        except:
            pass

    await msg.answer("Habar yuborildi!")
    await state.clear()


# -------------------------
# CHEKLOVLAR
# -------------------------
@dp.message(F.text == "Cheklovlar")
async def cheklovlar(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMINS:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Video cheklovi", callback_data="limit_video")],
        [InlineKeyboardButton(text="Fayl cheklovi", callback_data="limit_file")]
    ])

    await msg.answer("Qaysi cheklovni o‘zgartirmoqchisiz?", reply_markup=kb)


@dp.callback_query(F.data == "limit_video")
async def limit_video_set(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Video cheklovini kiriting (son):")
    await state.set_state(AdminState.limit_change)
    await state.update_data(limit_type="video")


@dp.callback_query(F.data == "limit_file")
async def limit_file_set(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Fayl cheklovini kiriting (son):")
    await state.set_state(AdminState.limit_change)
    await state.update_data(limit_type="file")


@dp.message(AdminState.limit_change)
async def save_limit(msg: Message, state: FSMContext):
    global limit_video, limit_file

    data = await state.get_data()
    limit_type = data["limit_type"]

    try:
        value = int(msg.text)
    except:
        await msg.answer("Faqat son kiriting!")
        return

    if limit_type == "video":
        limit_video = value
        await msg.answer(f"Video cheklovi {value} ga o‘rnatildi.")
    else:
        limit_file = value
        await msg.answer(f"Fayl cheklovi {value} ga o‘rnatildi.")

    await state.clear()


# -------------------------
# CHEKLOVDAN OZOD QILISH
# -------------------------
@dp.message(F.text == "Cheklovdan ozod qilish")
async def remove_limit_start(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMINS:
        return

    await msg.answer("Cheklovdan ozod qilinadigan foydalanuvchi ID sini yuboring:")
    await state.set_state(AdminState.remove_limit)


@dp.message(AdminState.remove_limit)
async def remove_limit_save(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
    except:
        await msg.answer("ID faqat son bo‘lishi kerak!")
        return

    user_ignore_limit[uid] = True

    await msg.answer(f"{uid} foydalanuvchi cheklovlardan ozod qilindi!")
    await state.clear()


# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================

async def main():
    keep_alive()  # Render Web Service Free uchun
    asyncio.create_task(eslatma_checker())  # 10s eslatma
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
