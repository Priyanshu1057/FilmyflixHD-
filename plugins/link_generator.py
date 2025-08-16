# (©) CodeFlix_Bots

from asyncio import TimeoutError
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from bot import Bot
from helper_func import encode, get_message_id, admin


def _ensure_mb_store(client: Client):
    # in-memory multibatch session store on the client
    if not hasattr(client, "mb_sessions"):
        client.mb_sessions = {}  # {user_id: {"active": True}}
    return client.mb_sessions


# ------------------------------ /batch (existing behavior) ------------------------------ #
@Bot.on_message(filters.private & admin & filters.command("batch"))
async def batch(client: Client, message: Message):
    # Ask for first message
    while True:
        try:
            first_message = await client.ask(
                chat_id=message.chat.id,
                text="📌 Forward the FIRST message from DB channel (or send its post link).",
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=120,
            )
        except TimeoutError:
            return

        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        await first_message.reply("❌ Not from your DB channel (or invalid link). Try again.", quote=True)

    # Ask for last message
    while True:
        try:
            second_message = await client.ask(
                chat_id=message.chat.id,
                text="📌 Forward the LAST message from DB channel (or send its post link).",
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=120,
            )
        except TimeoutError:
            return

        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        await second_message.reply("❌ Not from your DB channel (or invalid link). Try again.", quote=True)

    # Build range link
    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    buttons = [
        [InlineKeyboardButton("🔗 Open Batch", url=link)],
        [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")],
    ]
    await message.reply_text(f"<b>Here is your link</b>\n\n{link}", reply_markup=InlineKeyboardMarkup(buttons))


# ------------------------------ /multibatch (new) ------------------------------ #
@Bot.on_message(filters.private & admin & filters.command("multibatch"))
async def multibatch(client: Client, message: Message):
    sessions = _ensure_mb_store(client)
    uid = message.from_user.id

    # Mark user as being in multibatch mode so other handlers (like single-file auto-link)
    # will IGNORE their messages during collection.
    sessions[uid] = {"active": True}

    tip = (
        "📥 <b>Multi-Batch Mode</b>\n\n"
        "• Forward/send multiple files now (captions preserved)\n"
        "• Send <code>/done</code> to finish\n"
        "• Send <code>/cancel</code> to abort\n"
        "• Auto-cancels after 5 minutes of inactivity"
    )
    await message.reply(tip, reply_markup=ReplyKeyboardRemove())

    collected_db_ids = []

    try:
        while True:
            try:
                user_msg = await client.ask(
                    chat_id=message.chat.id,
                    text="Waiting for files… Send /done to finalize or /cancel to abort.",
                    timeout=300,  # 5 minutes inactivity timeout
                )
            except TimeoutError:
                await message.reply("❌ Batch cancelled due to inactivity (5 min).")
                return

            # Handle control commands
            if user_msg.text:
                cmd = user_msg.text.strip().lower()
                if cmd == "/cancel":
                    await message.reply("❌ Batch cancelled.")
                    return
                if cmd == "/done":
                    break

            # Copy the message to DB channel, preserving caption & markup
            try:
                copied = await user_msg.copy(
                    chat_id=client.db_channel.id,
                    disable_notification=True
                )
                collected_db_ids.append(copied.id)
            except Exception as e:
                await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
                continue

        # Finalize
        if not collected_db_ids:
            await message.reply("❌ No messages were added to batch.")
            return

        # Range link (we copy sequentially to DB channel while multibatch is active,
        # so these should be contiguous). Use first..last DB post ids.
        start_id = collected_db_ids[0] * abs(client.db_channel.id)
        end_id = collected_db_ids[-1] * abs(client.db_channel.id)
        string = f"get-{start_id}-{end_id}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"

        buttons = [
            [InlineKeyboardButton("🔗 Open Batch", url=link)],
            [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")],
        ]
        await message.reply(f"<b>Here is your multi-batch link:</b>\n\n{link}", reply_markup=InlineKeyboardMarkup(buttons))

    finally:
        # Always clear the multibatch mode for this user
        sessions.pop(uid, None)
