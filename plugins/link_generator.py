#(Â©)Codexbotz

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from asyncio import TimeoutError
import asyncio
import time
from helper_func import encode, get_message_id, admin

# Global dictionary to store multibatch sessions
multibatch_sessions = {}

@Bot.on_message(filters.private & admin & filters.command('batch'))
async def batch(client: Client, message: Message):
    while True:
        try:
            first_message = await client.ask(text = "Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60)
        except:
            return
        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("âŒ Error\n\nthis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote = True)
            continue

    while True:
        try:
            second_message = await client.ask(text = "Forward the Last Message from DB Channel (with Quotes)..\nor Send the DB Channel Post link", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60)
        except:
            return
        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("âŒ Error\n\nthis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote = True)
            continue


    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ” Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"**Here is your link**\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    while True:
        try:
            channel_message = await client.ask(text = "Forward Message from the DB Channel (with Quotes)..\nor Send the DB Channel Post link", chat_id = message.from_user.id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60)
        except:
            return
        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply("âŒ Error\n\nthis Forwarded Post is not from my DB Channel or this Link is not taken from DB Channel", quote = True)
            continue

    base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ” Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"**Here is your link**\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command("custom_batch"))
async def custom_batch(client: Client, message: Message):
    collected = []
    STOP_KEYBOARD = ReplyKeyboardMarkup([["STOP"]], resize_keyboard=True)

    await message.reply("Send all messages you want to include in batch.\n\nPress STOP when you're done.", reply_markup=STOP_KEYBOARD)

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="Waiting for files/messages...\nPress STOP to finish.",
                timeout=60
            )
        except asyncio.TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "STOP":
            break

        try:
            sent = await user_msg.copy(client.db_channel.id, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"âŒ Failed to store a message:\n`{e}`")
            continue

    await message.reply("âœ… Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("âŒ No messages were added to batch.")
        return

    start_id = collected[0] * abs(client.db_channel.id)
    end_id = collected[-1] * abs(client.db_channel.id)
    string = f"get-{start_id}-{end_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ” Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await message.reply(f"**Here is your custom batch link:**\n\n{link}", reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command("multibatch"))
async def multi_batch(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user already has an active session
    if user_id in multibatch_sessions:
        await message.reply("âŒ You already have an active multibatch session. Use /cancel to cancel it first.")
        return
    
    # Initialize session
    session_id = f"mb_{user_id}_{int(time.time())}"
    multibatch_sessions[user_id] = {
        'session_id': session_id,
        'collected': [],
        'start_time': time.time(),
        'active': True
    }
    
    await message.reply(
        "ðŸ”„ **Multibatch Session Started**\n\n"
        "ðŸ“ Forward multiple files/messages to me.\n"
        "âœ… Send /done when you're finished.\n"
        "âŒ Send /cancel to abort.\n\n"
        "â° Session will auto-expire in 5 minutes if inactive."
    )
    
    # Auto-cancel task
    asyncio.create_task(auto_cancel_session(client, user_id, session_id))


@Bot.on_message(filters.private & admin & filters.command("done"))
async def done_multibatch(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in multibatch_sessions:
        await message.reply("âŒ No active multibatch session found. Use /multibatch to start one.")
        return
    
    session = multibatch_sessions[user_id]
    if not session['active']:
        del multibatch_sessions[user_id]
        await message.reply("âŒ Session has expired. Use /multibatch to start a new one.")
        return
    
    collected = session['collected']
    session_id = session['session_id']
    
    # Clean up session
    del multibatch_sessions[user_id]
    
    if not collected:
        await message.reply("âŒ No messages were collected in this batch.")
        return
    
    # Generate link
    start_id = collected[0] * abs(client.db_channel.id)
    end_id = collected[-1] * abs(client.db_channel.id)
    string = f"get-{start_id}-{end_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    # Create multibatch format link  
    multi_batch_link = f"https://t.me/{client.username}?start=multi_batch_{session_id}_{base64_string}"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("ðŸ“¦ Batch Link", url=link)],
        [InlineKeyboardButton("ðŸ” Share URL", url=f'https://telegram.me/share/url?url={link}')]
    ])
    
    await message.reply(
        f"âœ… **Multibatch Complete!**\n\n"
        f"ðŸ“Š **Files collected:** {len(collected)}\n"
        f"ðŸ”— **Batch Link:** `{link}`\n\n"
        f"ðŸŽ¯ **Multi-Batch ID:** `{session_id}`",
        reply_markup=reply_markup
    )


@Bot.on_message(filters.private & admin & filters.command("cancel"))
async def cancel_multibatch(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in multibatch_sessions:
        await message.reply("âŒ No active multibatch session found.")
        return
    
    session = multibatch_sessions[user_id]
    collected_count = len(session['collected'])
    
    # Clean up session
    del multibatch_sessions[user_id]
    
    await message.reply(
        f"âŒ **Multibatch Session Cancelled**\n\n"
        f"ðŸ“Š Files that were collected: {collected_count}\n"
        f"ðŸ’¡ Use /multibatch to start a new session."
    )


# Handle forwarded messages for active multibatch sessions
@Bot.on_message(filters.private & admin & (filters.document | filters.video | filters.photo | filters.audio | filters.voice | filters.video_note | filters.sticker | filters.animation))
async def handle_multibatch_files(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user has active multibatch session
    if user_id not in multibatch_sessions:
        return  # Not a multibatch session, let other handlers process
    
    session = multibatch_sessions[user_id]
    if not session['active']:
        del multibatch_sessions[user_id]
        await message.reply("âŒ Session has expired. Use /multibatch to start a new one.")
        return
    
    try:
        # Copy to DB channel with preserved caption
        caption = message.caption if message.caption else None
        sent = await message.copy(
            chat_id=client.db_channel.id, 
            caption=caption,
            disable_notification=True
        )
        session['collected'].append(sent.id)
        session['start_time'] = time.time()  # Reset timeout
        
        await message.reply(
            f"âœ… **File Added to Batch**\n\n"
            f"ðŸ“Š Total files: {len(session['collected'])}\n"
            f"ðŸ†” Session ID: `{session['session_id']}`\n\n"
            f"ðŸ“ Continue adding files or send /done to finish."
        )
        
    except Exception as e:
        await message.reply(f"âŒ Failed to store file:\n`{e}`")


async def auto_cancel_session(client: Client, user_id: int, session_id: str):
    """Auto-cancel session after 5 minutes of inactivity"""
    await asyncio.sleep(300)  # 5 minutes
    
    if user_id in multibatch_sessions:
        session = multibatch_sessions[user_id]
        if session['session_id'] == session_id and session['active']:
            # Check if session is still inactive
            if time.time() - session['start_time'] >= 300:
                collected_count = len(session['collected'])
                del multibatch_sessions[user_id]
                
                try:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"â° **Multibatch Session Auto-Expired**\n\n"
                             f"ðŸ“Š Files collected: {collected_count}\n"
                             f"ðŸ’¡ Use /multibatch to start a new session."
                    )
                except Exception:
                    pass  # User might have blocked the bot
