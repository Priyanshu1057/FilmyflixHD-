import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db   # ✅ Correct import from your repo


# -------------------------------
# Handle normal single file links
# -------------------------------
@Client.on_message(filters.command("link"))
async def link_handler(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a file to generate link!")

    file_id = message.reply_to_message.id
    chat_id = message.chat.id

    # Save in DB
    await db.files.insert_one({
        "chat_id": chat_id,
        "file_id": file_id
    })

    link = f"https://t.me/{client.username}?start=file_{file_id}"
    await message.reply(f"Here is your file link:\n{link}")


# -------------------------------
# Handle batch link generation
# -------------------------------
@Client.on_message(filters.command("batch"))
async def batch_handler(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: `/batch start_id end_id` (reply IDs from channel)")

    try:
        start = int(message.command[1])
        end = int(message.command[2])
    except Exception:
        return await message.reply("Invalid IDs. Use message IDs only.")

    files = []
    for i in range(start, end + 1):
        files.append(i)

    # Save batch in DB
    batch = await db.batches.insert_one({"files": files})
    batch_id = str(batch.inserted_id)

    link = f"https://t.me/{client.username}?start=batch_{batch_id}_0"
    await message.reply(f"Here is your batch link:\n{link}")


# -------------------------------
# Serve files when link clicked
# -------------------------------
@Client.on_message(filters.command("start"))
async def start_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Hello! Send me a link to get files.")

    arg = message.command[1]

    # Single File
    if arg.startswith("file_"):
        file_id = int(arg.split("_", 1)[1])
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=message.chat.id,
            message_id=file_id
        )

    # Batch Navigation
    elif arg.startswith("batch_"):
        parts = arg.split("_")
        batch_id = parts[1]
        index = int(parts[2])

        batch = await db.batches.find_one({"_id": db.ObjectId(batch_id)})
        if not batch:
            return await message.reply("Batch not found!")

        files = batch["files"]

        if index < 0 or index >= len(files):
            return await message.reply("Invalid file index!")

        file_id = files[index]

        # Send file
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=message.chat.id,
            message_id=file_id,
            reply_markup=gen_nav_buttons(batch_id, index, len(files))
        )


# -------------------------------
# Navigation buttons
# -------------------------------
def gen_nav_buttons(batch_id, index, total):
    buttons = []

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⏮️ Back", callback_data=f"batchnav_{batch_id}_{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("⏭️ Next", callback_data=f"batchnav_{batch_id}_{index+1}"))

    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(buttons) if buttons else None


# -------------------------------
# Callback for navigation
# -------------------------------
@Client.on_callback_query(filters.regex(r"^batchnav_"))
async def batch_nav_callback(client, cq: CallbackQuery):
    _, batch_id, index = cq.data.split("_")
    index = int(index)

    batch = await db.batches.find_one({"_id": db.ObjectId(batch_id)})
    if not batch:
        return await cq.message.reply("Batch not found!")

    files = batch["files"]
    if index < 0 or index >= len(files):
        return await cq.answer("Invalid index!", show_alert=True)

    file_id = files[index]

    # Send new file as NEW message
    await client.copy_message(
        chat_id=cq.message.chat.id,
        from_chat_id=cq.message.chat.id,
        message_id=file_id,
        reply_markup=gen_nav_buttons(batch_id, index, len(files))
    )

    await cq.answer()
