# (c) Priyanshu / Codeflix-Bots
# Full start.py with Multi-Batch Next button support

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *
from utils import decode, get_messages
from config import ADMINS, FORCE_SUB_CHANNEL, LOG_CHANNEL, DELETE_TIME, DB_CHANNEL

logger = logging.getLogger(__name__)


@Client.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    await db.add_user(user_id)

    # Force subscription check
    if FORCE_SUB_CHANNEL:
        try:
            member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            if member.status in ("kicked", "banned"):
                return await message.reply_text("🚫 You are banned from using this bot.")
        except Exception:
            # Ask to join
            join_btn = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]]
            return await message.reply_text(
                "⚠️ Please join our channel first.",
                reply_markup=InlineKeyboardMarkup(join_btn)
            )

    # Decode start parameter
    if len(message.command) > 1:
        decoded = decode(message.command[1])

        # ✅ Multi-batch navigation
        if decoded.startswith("mb-"):
            ids = decoded.split("-")[1:]  # after 'mb'
            if not ids:
                return await message.reply_text("❌ Invalid multi-batch link.")
            first_id = int(ids[0]) // abs(DB_CHANNEL)
            # Store all ids in a session dict
            await db.add_multibatch_session(user_id, ids)

            # Send first file with Next button (if more remain)
            btns = []
            if len(ids) > 1:
                btns = [[InlineKeyboardButton("➡️ Next", callback_data=f"mbnext_{user_id}_1")]]
            sent = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=DB_CHANNEL,
                message_id=first_id
            )
            if btns:
                await sent.reply_text("Navigate:", reply_markup=InlineKeyboardMarkup(btns))

            # Auto delete
            if DELETE_TIME:
                await asyncio.sleep(DELETE_TIME)
                try:
                    await sent.delete()
                except: pass
            return

        # ✅ Existing single/batch file handling
        if decoded.startswith("get-"):
            parts = decoded.split("-")[1:]
            if len(parts) == 1:
                msg_id = int(parts[0]) // abs(DB_CHANNEL)
                try:
                    sent = await client.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=DB_CHANNEL,
                        message_id=msg_id
                    )
                    if DELETE_TIME:
                        await asyncio.sleep(DELETE_TIME)
                        await sent.delete()
                except Exception as e:
                    logger.error(e)
            elif len(parts) == 2:
                start_id = int(parts[0]) // abs(DB_CHANNEL)
                end_id = int(parts[1]) // abs(DB_CHANNEL)
                for mid in range(start_id, end_id + 1):
                    try:
                        sent = await client.copy_message(
                            chat_id=message.chat.id,
                            from_chat_id=DB_CHANNEL,
                            message_id=mid
                        )
                        if DELETE_TIME:
                            await asyncio.sleep(DELETE_TIME)
                            await sent.delete()
                    except Exception:
                        continue
            return

    # Default start message
    buttons = [[InlineKeyboardButton("Channel", url="https://t.me/codeflix_bots")]]
    await message.reply_text(
        f"👋 Hello {message.from_user.mention}, welcome to FilmyflixHD!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ✅ Handle Next button for multibatch
@Client.on_callback_query(filters.regex(r"^mbnext_"))
async def multibatch_next_handler(client: Client, query: CallbackQuery):
    try:
        _, user_id, idx = query.data.split("_")
        user_id = int(user_id)
        idx = int(idx)

        if query.from_user.id != user_id:
            return await query.answer("This batch is not for you.", show_alert=True)

        ids = await db.get_multibatch_session(user_id)
        if not ids or idx >= len(ids):
            return await query.answer("No more files.", show_alert=True)

        msg_id = int(ids[idx]) // abs(DB_CHANNEL)
        sent = await client.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=DB_CHANNEL,
            message_id=msg_id
        )

        # Add Next button if not last
        btns = []
        if idx + 1 < len(ids):
            btns = [[InlineKeyboardButton("➡️ Next", callback_data=f"mbnext_{user_id}_{idx+1}")]]
        if btns:
            await sent.reply_text("Navigate:", reply_markup=InlineKeyboardMarkup(btns))

        # Auto delete
        if DELETE_TIME:
            await asyncio.sleep(DELETE_TIME)
            try:
                await sent.delete()
            except: pass

    except Exception as e:
        logger.error(f"MultiBatch Next Error: {e}")
        await query.answer("❌ Error loading next file.", show_alert=True)
