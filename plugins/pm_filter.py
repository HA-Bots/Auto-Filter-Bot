import random
import asyncio
import re, time
import ast
import math
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, URL, BIN_CHANNEL, DELETE_TIME, AUTH_CHANNEL, LOG_CHANNEL, SUPPORT_LINK, UPDATES_LINK, PICS, \
    PROTECT_CONTENT, IMDB, AUTO_FILTER, SPELL_CHECK, IMDB_TEMPLATE, AUTO_DELETE
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, ChatAdminRequired
from utils import get_size, is_subscribed, is_check_admin, get_wish, get_shortlink, get_readable_time, get_poster, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results,delete_files
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
CAP = {}

@Client.on_callback_query(filters.regex(r"^stream"))
async def stream_downloader(bot, query):
    file_id = query.data.split('#', 1)[1]
    msg = await bot.send_cached_media(
        chat_id=BIN_CHANNEL,
        file_id=file_id)
    online = f"{URL}watch/{msg.id}"
    download = f"{URL}download/{msg.id}"
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=online),
                InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
            ],[
                InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
            ]
        ]
    ))

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    settings = await get_settings(message.chat.id)
    if settings["auto_filter"]:
        if message.text.startswith("/"):
            return
            
        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            success = False
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    if message.reply_to_message:
                        try:
                            sent_msg = await message.reply_to_message.forward(member.user.id)
                            await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>", disable_web_page_preview=True)
                            success = True
                        except:
                            pass
                    else:
                        try:
                            sent_msg = await message.forward(member.user.id)
                            await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>", disable_web_page_preview=True)
                            success = True
                        except:
                            pass
            if success:
                await message.reply_text("Report sent!")
            else:
                await message.reply_text("Something went wrong.")
            return

        elif re.findall(r'(https?://\S+)|(@\w+)', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            await message.delete()
            return await message.reply('Links not allowed here!')
        
        elif '#request' in message.text.lower():
            if message.from_user.id in ADMINS:
                return
            await client.send_message(LOG_CHANNEL, f"#Request\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ Message: {re.sub(r'#request', '', message.text.lower())}")
            await message.reply_text("Request sent!")
            return
            
        userid = message.from_user.id if message.from_user else None
        if not userid:
            search = message.text
            k = await message.reply(f"You'r anonymous admin! Sorry you can't get '{search}' from here.\nYou can get '{search}' from bot inline search.")
            await asyncio.sleep(30)
            await k.delete()
            try:
                await message.delete()
            except:
                pass
            return

        btn = await is_subscribed(client, message, settings['fsub']) # This func is for custom fsub channels
        if btn:
            btn.append(
                [InlineKeyboardButton("🔁 Request Again 🔁", callback_data="grp_checksub")]
            )
            reply_markup = InlineKeyboardMarkup(btn)
            k = await message.reply_photo(
                photo=random.choice(PICS),
                caption=f"👋 Hello {message.from_user.mention},\n\nPlease join my 'Updates Channel' and request again. 😇",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(300)
            await k.delete()
            try:
                await message.delete()
            except:
                pass
        else:
            await auto_filter(client, message)
    else:
        k = await message.reply_text('Auto Filter Off! ❌')
        await asyncio.sleep(5)
        await k.delete()
        try:
            await message.delete()
        except:
            pass

@Client.on_message(filters.private & filters.text)
async def pm_search(client, message):
    files, n_offset, total = await get_search_results(message.text, filter=True)
    if int(total) != 0:
        btn = [[
            InlineKeyboardButton("Here", url='https://t.me/SL_Films_World')
        ]]
        await message.reply_text(f'Total {total} results found in this group', reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    temp.FILES[key] = files
    settings = await get_settings(query.message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    files_link = ''
    if settings["shortlink"]:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href={await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}')}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'))
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'file#{file.file_id}')
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}")]
                  )

    btn.insert(0,
               [InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#{offset}")]
              )
    if settings["shortlink"]:
        btn.insert(0,
                   [InlineKeyboardButton("📍 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ 📍", url=settings['tutorial'])]
                  )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:

        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"ᴘᴀɢᴇs {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}",
                                  callback_data="buttons")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"ᴘᴀɢᴇs {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"{math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
                InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"next_{req}_{key}_{n_offset}")
            ]
        )
    btn.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    try:
        await query.message.edit_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^languages"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    langs = ['english', 'tamil', 'hindi', 'malayalam', 'telugu']
    btn = [
        [
            InlineKeyboardButton(
                text=lang.title(),
                callback_data=f"lang_search#{lang}#{key}#{offset}#{req}"
                ),
        ]
        for lang in langs
    ]

    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ, sᴇʟᴇᴄᴛ ʜᴇʀᴇ</b>", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(btn))


@Client.on_callback_query(filters.regex(r"^lang_search"))
async def filter_languages_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
        return 

    files, l_offset, total_results = await get_search_results(search, filter=True, lang=lang)
    if not files:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return
    temp.FILES[key] = files
    settings = await get_settings(query.message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    files_link = ''
    if settings["shortlink"]:
        if settings["links"]:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href={await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}')}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'))
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'file#{file.file_id}')
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}")]
        )
    if settings["shortlink"]:
        btn.insert(0,
                   [InlineKeyboardButton("📍 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ 📍", url=settings['tutorial'])]
                  )
    
    if l_offset != "":
        btn.append(
            [InlineKeyboardButton(text=f"ᴘᴀɢᴇs 1 / {math.ceil(int(total_results) / 10)}", callback_data="buttons"),
             InlineKeyboardButton(text="ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{l_offset}#{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(cap + files_link + del_msg, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(btn))


@Client.on_callback_query(filters.regex(r"^lang_next"))
async def lang_next_page(bot, query):
    ident, req, key, lang, l_offset, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    try:
        l_offset = int(l_offset)
    except:
        l_offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    settings = await get_settings(query.message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    if not search:
        await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
        return 

    files, n_offset, total = await get_search_results(search, filter=True, offset=l_offset, lang=lang)
    if not files:
        return
    temp.FILES[key] = files
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    files_link = ''
    if settings["shortlink"]:
        if settings["links"]:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href={await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}')}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'))
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(query.message.chat.id, f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'file#{file.file_id}')
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}")]
        )
    if settings["shortlink"]:
        btn.insert(0,
                   [InlineKeyboardButton("📍 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ 📍", url=settings['tutorial'])]
                  )

    if 0 < l_offset <= 10:
        b_offset = 0
    elif l_offset == 0:
        b_offset = None
    else:
        b_offset = l_offset - 10

    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"ᴘᴀɢᴇs {math.ceil(int(l_offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons")]
        )
    elif b_offset is None:
        btn.append(
            [InlineKeyboardButton(f"ᴘᴀɢᴇs {math.ceil(int(l_offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"{math.ceil(int(l_offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    movie = await get_poster(id, id=True)
    search = movie.get('title')
    await query.answer('Check In My Database...')
    files, offset, total_results = await get_search_results(search, offset=0, filter=True)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        await bot.send_message(LOG_CHANNEL, script.NO_RESULT_TXT.format(query.message.chat.title, query.message.chat.id, query.from_user.mention, search))
        k = await query.message.edit(f"👋 Hello {query.from_user.mention},\n\nI don't find <b>'{search}'</b> in my database. 😔")
        await asyncio.sleep(60)
        await k.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
            if int(user) != 0 and query.from_user.id != int(user):
                return await query.answer(f"Hello {query.from_user.first_name},\nThis Is Not For You!", show_alert=True)
            await query.answer("Closed!")
            await query.message.delete()
            try:
                await query.message.reply_to_message.delete()
            except:
                pass
        except:
            await query.answer("Closed!")
            await query.message.delete()

    elif "groupcb" in query.data:
        group_id = query.data.split(":")[1]
        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name: **{title}**\nGroup ID: `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    elif "connectcb" in query.data:
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!', parse_mode=enums.ParseMode.MARKDOWN)
        return

    elif "disconnect" in query.data:
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return

    elif "deletecb" in query.data:
        user_id = query.from_user.id
        group_id = query.data.split(":")[1]
        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return

    elif query.data == "backcb":
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections! Connect to some groups first.",
            )
            return
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details:\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file_id}")

    elif query.data.startswith("pm_checksub"):
        ident, mc = query.data.split("#")
        btn = await is_subscribed(client, query)
        if btn:
            await query.answer(f"Hello {query.from_user.first_name},\nPlease join my updates channel and request again.", show_alert=True)
            btn.append(
                [InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"pm_checksub#{mc}")]
            )
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
            return
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start={mc}")
        await query.message.delete()
   
    elif query.data == "grp_checksub":
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nThis Is Not For You!", show_alert=True)
        settings = await get_settings(query.message.chat.id)
        btn = await is_subscribed(client, query, settings['fsub']) # This func is for custom fsub channels
        if btn:
            await query.answer(f"Hello {query.from_user.first_name},\nPlease join my updates channel and request again.", show_alert=True)
            btn.append(
                [InlineKeyboardButton("🔁 Request Again 🔁", callback_data="grp_checksub")]
            )
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
            return
        await query.answer(f"Hello {query.from_user.first_name},\nGood, Can You Request Now!", show_alert=True)
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif query.data == "buttons":
        await query.answer("⚠️")

    elif query.data == "instructions":
        await query.answer("Movie request format.\nExample:\nBlack Adam or Black Adam 2022\n\nTV Reries request format.\nExample:\nLoki S01E01 or Loki S01 E01\n\nDon't use symbols.", show_alert=True)

    elif query.data == "start":
        await query.answer('Welcome!')
        buttons = [[
            InlineKeyboardButton("+ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ +", url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('🔎 sᴇᴀʀᴄʜ ɪɴʟɪɴᴇ 🔍', switch_inline_query_current_chat='')
        ],[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('💡 Support Group 💡', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('👨‍🚒 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📚 ᴀʙᴏᴜᴛ', callback_data='my_about'),
            InlineKeyboardButton('👤 ᴏᴡɴᴇʀ', callback_data='my_owner')
        ],[
            InlineKeyboardButton('💰 ᴇᴀʀɴ ᴍᴏɴᴇʏ ʙʏ ʙᴏᴛ 💰', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, get_wish()),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "my_about":
        buttons = [[
            InlineKeyboardButton('📊 sᴛᴀᴛᴜs', callback_data='stats'),
            InlineKeyboardButton('🔋 sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', callback_data='source')
        ],[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_ABOUT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "stats":
        if query.from_user.id not in ADMINS:
            return await query.answer("ADMINS Only!", show_alert=True)
        files = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        size = await db.get_db_size()
        free = 536870912 - size
        uptime = get_readable_time(time.time() - temp.START_TIME)
        size = get_size(size)
        free = get_size(free)
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='my_about')
        ]]
        await query.message.edit_text(script.STATUS_TXT.format(files, users, chats, size, free, uptime), reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    elif query.data == "my_owner":
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('☎️ ᴄᴏɴᴛᴀᴄᴛ', url='https://t.me/Hansaka_Anuhas')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_OWNER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "earn":
        buttons = [[
            InlineKeyboardButton('‼️ ʜᴏᴡ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ sʜᴏʀᴛɴᴇʀ ‼️', callback_data='howshort')
        ],[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EARN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "howshort":
        buttons = [[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HOW_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('User Command', callback_data='user_command'),
            InlineKeyboardButton('Admin Command', callback_data='admin_command')
        ],[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "user_command":
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.USER_COMMAND_TXT,
            reply_markup=reply_markup
        )
        
    elif query.data == "admin_command":
        if query.from_user.id not in ADMINS:
            return await query.answer("ADMINS Only!", show_alert=True)
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_COMMAND_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='my_about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data.startswith("opn_pm_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        if str(grp_id) != str(grpid):
            await query.message.edit("I'm not connected to this group! Check /connections or /connect to this group.")
            return
        title = query.message.chat.title
        settings = await get_settings(grpid)
        btn = [[
            InlineKeyboardButton("⚡️ Go To Chat ⚡️", url=f"https://t.me/{temp.U_NAME}")
        ]]

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Auto Filter',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["auto_filter"] else '❌ No',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDb Poster', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spelling Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else '❌ No',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Shortlink', callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["shortlink"] else '❌ No',
                                         callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Result Page', callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}'),
                    InlineKeyboardButton('⛓ Link' if settings["links"] else '🧲 Button',
                                         callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]
            try:
                await client.send_message(
                    chat_id=userid,
                    text=f"Change your settings for <b>'{title}'</b> as your wish. ⚙",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                k = await query.message.edit_text(text="Settings menu sent in private chat. ⚙️", reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(60)
                await k.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            except UserIsBlocked:
                await query.answer('You blocked me, Please unblock me and try again.', show_alert=True)
            except PeerIdInvalid:
                await query.answer("You didn't started this bot yet, Please start me and try again.", show_alert=True)

    elif query.data.startswith("opn_grp_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        if str(grp_id) != str(grpid):
            await query.message.edit("I'm not connected to this group! Check /connections or /connect to this group.")
            return
        title = query.message.chat.title
        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Auto Filter',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["auto_filter"] else '❌ No',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDb Poster', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spelling Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else '❌ No',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Shortlink', callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["shortlink"] else '❌ No',
                                         callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Result Page', callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}'),
                    InlineKeyboardButton('⛓ Link' if settings["links"] else '🧲 Button',
                                         callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            k = await query.message.edit_text(text=f"Change your settings for <b>'{title}'</b> as your wish. ⚙", reply_markup=reply_markup)
            await asyncio.sleep(300)
            await k.delete()
            try:
                await query.message.reply_to_message.delete()
            except:
                pass

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("This Is Not For You!", show_alert=True)
            return

        if str(grp_id) != str(grpid):
            await query.message.edit("I'm not connected to this group! Check /connections or /connect to this group.")
            return

        if set_type == 'shortlink' and userid not in ADMINS:
            return await query.answer("You can't change this setting.")

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Auto Filter',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["auto_filter"] else '❌ No',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDb Poster', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spelling Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else '❌ No',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Shortlink', callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["shortlink"] else '❌ No',
                                         callback_data=f'setgs#shortlink#{settings["shortlink"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Result Page', callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}'),
                    InlineKeyboardButton('⛓ Link' if settings["links"] else '🧲 Button',
                                         callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.answer("Changed!")
            await query.message.edit_reply_markup(reply_markup)

    elif query.data == "srt_delete":
        await query.message.edit_text("Deleting...")
        result = await Media.collection.delete_many({'mime_type': 'application/x-subrip'})
        if result.deleted_count:
            await query.message.edit_text(f"Successfully deleted srt files")
        else:
            await query.message.edit_text("Nothing to delete files")

    elif query.data == "avi_delete":
        await query.message.edit_text("Deleting...")
        result = await Media.collection.delete_many({'mime_type': 'video/x-msvideo'})
        if result.deleted_count:
            await query.message.edit_text(f"Successfully deleted avi files")
        else:
            await query.message.edit_text("Nothing to delete files")
            
    elif query.data == "zip_delete":
        await query.message.edit_text("Deleting...")
        result = await Media.collection.delete_many({'mime_type': 'application/zip'})
        if result.deleted_count:
            await query.message.edit_text(f"Successfully deleted zip files")
        else:
            await query.message.edit_text("Nothing to delete files")
            
    elif query.data == "rar_delete":
        await query.message.edit_text("Deleting...")
        result = await Media.collection.delete_many({'mime_type': 'application/x-rar-compressed'})
        if result.deleted_count:
            await query.message.edit_text(f"Successfully deleted rar files")
        else:
            await query.message.edit_text("Nothing to delete files")
            
    elif query.data == "delete_all":
        files = await Media.count_documents()
        await query.answer('Deleting...')
        await Media.collection.drop()
        await query.message.edit_text(f"Successfully deleted {files} files")
        
    elif query.data.startswith("delete"):
        _, query_ = query.data.split("_")
        deleted = 0
        await query.message.edit('Deleting...')
        total, files = await delete_files(query_)
        async for file in files:
            await Media.collection.delete_one({'_id': file['_id']})
            deleted += 1
        await query.message.edit(f'Deleted {deleted} files in your database in your query {query_}')
     
    elif query.data.startswith("send_all"):
        ident, key = query.data.split("#")
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        
        files = temp.FILES.get(key)
        if not files:
            await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
            return        
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}")
        
async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        search = message.text
        files, offset, total_results = await get_search_results(search, offset=0, filter=True)
        if not files:
            if settings["spell_check"]:
                return await advantage_spell_chok(msg)
            else:
                return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    if spoll:
        await msg.message.delete()
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    temp.FILES[key] = files
    files_link = ""
    if settings["shortlink"]:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href={await get_shortlink(message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}')}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", url=await get_shortlink(message.chat.id, f'https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'))
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(message.chat.id, f'https://t.me/{temp.U_NAME}?start=all_{message.chat.id}_{key}')),
            ]
        )
    else:
        if settings['links']:
            btn = []
            for file in files:
                files_link += f"""<b>\n\n‼️ <a href=https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
        else:
            btn = [[
                InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'file#{file.file_id}')
            ]
                for file in files
            ]
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            ]
         )
    
    if offset != "":
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"ᴘᴀɢᴇs 1 / {math.ceil(int(total_results) / 10)}", callback_data="buttons"),
             InlineKeyboardButton(text="ɴᴇxᴛ »", callback_data=f"next_{req}_{key}_{offset}")]
        )
        btn.insert(0,
                   [InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#0")]
                  )
    else:
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    if settings["shortlink"]:
        btn.insert(0,
                [InlineKeyboardButton("📍 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ 📍", url=settings['tutorial'])]
                )
    btn.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>💭 ʜᴇʏ {message.from_user.mention},\n♻️ ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ {search}...</b>"
    CAP[key] = cap
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    if imdb and imdb.get('poster'):
        try:
            if settings["auto_delete"]:
                k = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            if settings["auto_delete"]:
                k = await message.reply_photo(photo=poster, caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=poster, caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            if settings["auto_delete"]:
                k = await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        if settings["auto_delete"]:
            k = await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
            await asyncio.sleep(DELETE_TIME)
            await k.delete()
            try:
                await message.delete()
            except:
                pass
        else:
            await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)

async def advantage_spell_chok(message):
    search = message.text
    google_search = search.replace(" ", "+")
    btn = [[
        InlineKeyboardButton("⚠️ Instructions ⚠️", callback_data='instructions'),
        InlineKeyboardButton("🔎 Search Google 🔍", url=f"https://www.google.com/search?q={google_search}")
    ]]
    try:
        movies = await get_poster(search, bulk=True)
    except:
        n = await message.reply_photo(photo=random.choice(PICS), caption=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return

    if not movies:
        n = await message.reply_photo(photo=random.choice(PICS), caption=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return

    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spolling#{movie.movieID}#{user}")
    ]
        for movie in movies
    ]
    buttons.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    s = await message.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {message.from_user.mention},\n\nI couldn't find the <b>'{search}'</b> you requested.\nSelect if you meant one of these? 👇", reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
    await asyncio.sleep(300)
    await s.delete()
    try:
        await message.delete()
    except:
        pass


