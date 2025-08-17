# link_generator.py
# Batch Next Navigation (permanent mode)
# Don't remove credits @Codeflix_Bots

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import db   # your existing db connection

# ================================
# 🔹 DB Helpers for Temporary Batch
# ================================

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
# 🔹 Batch Link Handler
# ================================

@Client.on_message(filters.command("batch"))
async def batch_handler(client, message):
    user_id = message.from_user.id

    # ⬇️ fetch batch files from DB (your repo already does this, I keep generic)
    data = await db.settings.find_one({"_id": f"BATCH_{user_id}"})
    if not data or "files" not in data:
        return await message.reply_text("⚠️ No batch files found.")

    batch_files = data["files"]
    if not batch_files:
        return await message.reply_text("⚠️ Batch is empty.")

    # Always new behavior → send first file with Next button
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
