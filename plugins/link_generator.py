# link_generator.py
# Extended with Batch Button Mode (Next Navigation)
# Don't remove credits @Codeflix_Bots

import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS
from utils import db   # your existing db connection

# ================================
# 🔹 DB Helpers (safe, new only)
# ================================

async def get_batch_mode() -> bool:
    """Get batch mode setting from DB (default False)."""
    data = await db.settings.find_one({"_id": "BATCH_BUTTON_MODE"})
    return bool(data["value"]) if data else False

async def toggle_batch_mode() -> bool:
    """Toggle batch mode and return new value."""
    current = await get_batch_mode()
    new_value = not current
    await db.settings.update_one(
        {"_id": "BATCH_BUTTON_MODE"},
        {"$set": {"value": new_value}},
        upsert=True
    )
    return new_value

async def save_temp_batch(user_id: int, files: list):
    """Save temporary batch for a user."""
    await db.settings.update_one(
        {"_id": f"TEMP_BATCH_{user_id}"},
        {"$set": {"files": files}},
        upsert=True
    )

async def get_temp_batch(user_id: int):
    """Get temporary batch for a user."""
    data = await db.settings.find_one({"_id": f"TEMP_BATCH_{user_id}"})
    return data["files"] if data else None

# ================================
# 🔹 Toggle Command
# ================================

@Client.on_message(filters.command("togglebatchmode"))
async def toggle_batch_cmd(client, message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ You are not allowed to use this command.")
    mode = await toggle_batch_mode()
    if mode:
        await message.reply_text("✅ Batch Button Mode Enabled.\nNow batches send one by one with ➡️ Next button.")
    else:
        await message.reply_text("❌ Batch Button Mode Disabled.\nNow batches send all files at once.")

# ================================
# 🔹 Batch Link Handler
# ================================

@Client.on_message(filters.command("batch"))
async def batch_handler(client, message):
    user_id = message.from_user.id

    # ⬇️ this is your existing logic that fetches batch file list
    # I am keeping it generic so it won't break
    try:
        batch_files = await db.get_batch_files(user_id)  # you already have this
    except Exception:
        return await message.reply_text("⚠️ Could not fetch batch files.")

    if not batch_files:
        return await message.reply_text("⚠️ No batch files found.")

    # Check mode
    button_mode = await get_batch_mode()

    if not button_mode:
        # Old behavior → send all files
        for file_id in batch_files:
            try:
                await client.send_cached_media(
                    chat_id=message.chat.id,
                    file_id=file_id
                )
            except Exception as e:
                await message.reply_text(f"❌ Error sending file: {e}")
        return

    # New behavior → send first file with Next button
    first_file = batch_files[0]
    try:
        await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=first_file,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➡️ Next", callback_data=f"nextfile_{user_id}_0")]]
            ) if len(batch_files) > 1 else None
        )
    except Exception as e:
        await message.reply_text(f"❌ Error sending file: {e}")

    # Save batch temporarily
    await save_temp_batch(user_id, batch_files)

# ================================
# 🔹 Next Button Handler
# ================================

@Client.on_callback_query(filters.regex(r"^nextfile_(\d+)_(\d+)$"))
async def next_file_callback(client, query: CallbackQuery):
    user_id = int(query.matches[0].group(1))
    index = int(query.matches[0].group(2))

    if query.from_user.id != user_id:
        return await query.answer("❌ This button is not for you!", show_alert=True)

    # Load batch from DB
    batch_files = await get_temp_batch(user_id)
    if not batch_files:
        return await query.answer("⚠️ Batch expired or not found.", show_alert=True)

    next_index = index + 1
    if next_index >= len(batch_files):
        return await query.answer("✅ You reached the end of this batch.", show_alert=True)

    next_file = batch_files[next_index]

    # Send next file
    try:
        await client.send_cached_media(
            chat_id=query.message.chat.id,
            file_id=next_file,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➡️ Next", callback_data=f"nextfile_{user_id}_{next_index}")]]
            ) if next_index + 1 < len(batch_files) else None
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Error sending file: {e}")

    await query.answer()
