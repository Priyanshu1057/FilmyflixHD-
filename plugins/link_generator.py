#(©)Codexbotz

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from asyncio import TimeoutError
from helper_func import encode, get_message_id, admin

@Bot.on_message(filters.private & admin & filters.command('batch'))
async def batch(client: Client, message: Message):
    while True:
        try:
            first_message = await client.ask(
                text="Forward the first message",
                filters=filters.forwarded | (filters.text & ~filters.forwarded),
                timeout=60
            )
        except:
            return
        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("❌ Error: This message is not from the DB channel or the link is taken.", quote=True)
            continue

    while True:
        try:
            second_message = await client.ask(
                text="Forward the second message",
                filters=filters.forwarded | (filters.text & ~filters.forwarded),
                timeout=60
            )
        except:
            return
        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("❌ Error: This message is not from the DB channel or the link is taken.", quote=True)
            continue

    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)

@Bot.on_message(filters.private & admin & filters.command("genlink"))
async def gen_link(client: Client, message: Message):
    while True:
        try:
            genlink_msg = await client.ask(text="Send me the link to generate", timeout=60)
        except:
            return
        await message.reply("🔗 Here you go!", quote=True)
        async for genlink_msg in client.stream_chat_history(message.chat.id, limit=1):
            try:
                post_msg = await genlink_msg.copy(message.chat.id, disable_notification=True)
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={post_msg.message_id}')]])
                await message.reply("<b>Here is your telegram link:</b>\n\n" + f"https://t.me/{client.username}?start={post_msg.message_id}", reply_markup=reply_markup)
            except Exception as e:
                await message.reply(f"❌ Error generating link: {e}", quote=True)
        break

@Bot.on_message(filters.private & admin & filters.command("multibatch"))
async def multibatch(client: Client, message: Message):
    collected = []
    await message.reply(
        "Send all the files/messages you want to include in the batch.\n\nPress /done when you're finished, or /cancel to abort.",
        reply_markup=ReplyKeyboardRemove()
    )

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="Waiting for files/messages...\nSend /done to finish or /cancel to abort.",
                timeout=300
            )
        except TimeoutError:
            await message.reply("❌ Batch cancelled due to inactivity.", reply_markup=ReplyKeyboardRemove())
            return

        if user_msg.text:
            text = user_msg.text.strip().lower()
            if text == "/done":
                break
            elif text == "/cancel":
                await message.reply("❌ Batch cancelled.", reply_markup=ReplyKeyboardRemove())
                return

        try:
            sent = await user_msg.copy(client.db_channel.id, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
            continue

    await message.reply("✅ Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("❌ No messages were added to batch.")
        return

    start_id = collected[0] * abs(client.db_channel.id)
    end_id = collected[-1] * abs(client.db_channel.id)
    string = f"get-{start_id}-{end_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await message.reply(f"<b>Here is your multi-batch link:</b>\n\n{link}", reply_markup=reply_markup)
