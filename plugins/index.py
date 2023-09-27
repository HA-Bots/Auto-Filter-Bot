import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, UserIsBlocked
from info import ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
import re
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    _, ident, chat, lst_msg_id = query.data.split("#")
    if ident == 'yes':
        msg = query.message
        await msg.edit("Starting Indexing...")
        try:
            chat = int(chat)
        except:
            chat = chat
        await index_files_to_db(int(lst_msg_id), chat, msg, bot)
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.answer("Cancelling Indexing...")


@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text ) & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('Wait until previous process complete.')
    if message.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'Errors - {e}')

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("I can index only channels.")
    if message.from_user.id in ADMINS:
        buttons = [
            [
                InlineKeyboardButton('YES',
                                     callback_data=f'index#yes#{chat_id}#{last_msg_id}')
            ],
            [
                InlineKeyboardButton('CLOSE', callback_data='close_data'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(
            f'Do you want to index this channel?\n\nChannel ID or Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup)
    else:
        await message.reply("Sorry! You can't index files, You'r not my owner.")


@Client.on_message(filters.command('set_skip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    try:
        skip = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply("Skip number is invalid")
    await message.reply(f"Successfully set skip number as: <code>{skip}</code>")
    temp.CURRENT = int(skip)


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit(f"Successfully Cancelled!\n\nSaved <code>{total_files}</code> files to Database!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>")
                    break
                current += 1
                if current % 20 == 0:
                    can = [[InlineKeyboardButton('CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}')]]
                    reply = InlineKeyboardMarkup(can)
                    await msg.edit_text(
                        text=f"Total messages received: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>",
                        reply_markup=reply)
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.caption = message.caption
                sts = await save_file(media)
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to Database!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>')
