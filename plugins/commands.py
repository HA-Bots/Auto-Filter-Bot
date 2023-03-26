import os
import logging
import random
import asyncio
import time
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import INDEX_CHANNELS, ADMINS, AUTH_CHANNEL, SUPPORT_LINK, UPDATES_LINK, LOG_CHANNEL, STICKERS, PICS, CUSTOM_FILE_CAPTION, PROTECT_CONTENT
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection
import re
import json
import base64
logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        btn = [[
            InlineKeyboardButton('⚡️ Updates Channel ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('🔥 Support Group 🔥', url=SUPPORT_LINK)
        ]]
        s = await message.reply_sticker(sticker=random.choice(STICKERS), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(30)
        await s.delete()
        try:
            await message.delete()
        except:
            pass
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            r_j = message.from_user.mention if message.from_user else "Anonymous"
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id, total, r_j))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(message.from_user.mention, message.from_user.id))
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('✅ Start ✅', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention}",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("Make sure Bot is admin in Forcesub channel")
            return
        btn = [[
            InlineKeyboardButton("📢 Updates Channel 📢", url=invite_link.invite_link)
        ]]

        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("🔄 Try Again 🔄", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("🔄 Try Again 🔄", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention},\n\nPlease join my 'Updates Channel' and try again. 😇",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        return
    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help", "start", "admins"]:
        buttons = [[
            InlineKeyboardButton('✅ Start ✅', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention}",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    pre, file_id = message.command[1].split("_", 1)
    files_ = await get_file_details(file_id)
    if not files_:
        return await message.reply('No Such File Exist!')
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"

    btn = [[
        InlineKeyboardButton('⚡️ Updates Channel ⚡️', url=UPDATES_LINK),
        InlineKeyboardButton('🔥 Support Group 🔥', url=SUPPORT_LINK)
    ]]
    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if pre == 'filep' else False,
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_message(filters.command('index_channels') & filters.user(ADMINS))
async def channels_info(bot, message):
           
    """Send basic information of index channels"""
    if isinstance(INDEX_CHANNELS, (int, str)):
        channels = [INDEX_CHANNELS]
    elif isinstance(INDEX_CHANNELS, list):
        channels = INDEX_CHANNELS
    else:
        raise ValueError("Unexpected type of index channels")

    text = '**Indexed Channels:**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(INDEX_CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('stats'))
async def stats(bot, message):
    msg = await message.reply('Please Wait...')
    files = await Media.count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    size = await db.get_db_size()
    free = 536870912 - size
    size = get_size(size)
    free = get_size(free)
    await msg.edit(script.STATUS_TXT.format(files, users, chats, size, free))
    
    
@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure i'm present in your group!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        try:
            await message.delete()
        except:
            pass
        return

    settings = await get_settings(grp_id)

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Auto Filter',
                    callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["auto_filter"] else '❌ No',
                    callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton(
                    'Filter Button',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    'Single' if settings["button"] else 'Double',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton(
                    'File Secure',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["file_secure"] else '❌ No',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton(
                    'IMDb Poster',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["imdb"] else '❌ No',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton(
                    'Spelling Check',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["spell_check"] else '❌ No',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton(
                    'Auto Delete',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    'One Hours' if settings["auto_delete"] else '❌ No',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'
                )
            ],
            [
                InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
            ]
        ]

    if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        btn = [[
            InlineKeyboardButton("👤 Open Private Chat 👤", callback_data=f"opn_pm_setgs#{grp_id}")
        ],[
            InlineKeyboardButton("👥 Open Here 👥", callback_data=f"opn_grp_setgs#{grp_id}")
        ]]
        k = await message.reply_text(
            text="Where do you want to open the settings menu? ⚙️",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(300)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
    else:
        await message.reply_text(
            text=f"Change your settings for <b>'{title}'</b> as your wish. ⚙",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )


# add files delete features

@Client.on_message(filters.command('delete'))
async def delete(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑')
        return
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("ᴘʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('<b>ᴛʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ꜰɪʟᴇ ꜰᴏʀᴍᴀᴛ</b>')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>')
            else:
                await msg.edit('<b>ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ</b>')





