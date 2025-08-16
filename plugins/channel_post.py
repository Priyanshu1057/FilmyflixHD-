# (©) CodeFlix_Bots

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import DISABLE_CHANNEL_BUTTON
from helper_func import encode, admin


def _mb_active(client: Client, user_id: int) -> bool:
    # Check if user is currently in /multibatch mode (session flag set by link_generator.py)
    return hasattr(client, "mb_sessions") and client.mb_sessions.get(user_id, {}).get("active", False)


@Bot.on_message(
    filters.private
    & admin
    & ~filters.command(
        [
            "start",
            "batch",
            "multibatch",
            "done",
            "cancel",
            "genlink",
            "broadcast",
            "pbroadcast",
            "add_admin",
            "deladmin",
            "admins",
            "delreq",
            "commands",
        ]
    )
)
async def channel_post(client: Client, message: Message):
    # If the admin is in multibatch mode, DO NOT auto-generate single-file links here.
    # multibatch flow handles copying & linking by itself.
    if message.from_user and _mb_active(client, message.from_user.id):
        return

    reply_text = await message.reply_text("Please Wait...!", quote=True)
    try:
        post_message = await message.copy(
            chat_id=client.db_channel.id,
            disable_notification=True
        )

        # Respect flood waits when copying large media
        try:
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)

    except Exception as e:
        await reply_text.edit_text("Something went wrong..!"); return

    converted_id = post_message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    buttons = [
        [InlineKeyboardButton("🔗 Open File", url=link)],
        [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")],
    ]

    await reply_text.edit(
        f"<b>Here is your link</b>\n\n{link}",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )

    if not DISABLE_CHANNEL_BUTTON:
        # also add same button set under the DB post (optional, original behavior)
        try:
            await post_message.edit_reply_markup(InlineKeyboardMarkup(buttons))
        except Exception:
            pass
