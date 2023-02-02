import random
import asyncio
import re
import ast
import math
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, LOG_CHANNEL, SUPPORT_LINK, UPDATES_LINK, PICS, CUSTOM_FILE_CAPTION, \
    PROTECT_CONTENT, IMDB, AUTO_FILTER, SINGLE_BUTTON, SPELL_CHECK, IMDB_TEMPLATE, PM_IMDB_TEMPLATE
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, ChatAdminRequired
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    settings = await get_settings(message.chat.id)
    if settings["auto_filter"]:
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

        if AUTH_CHANNEL and not await is_subscribed(client, message):
            try:
                invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
            except ChatAdminRequired:
                logger.error("Make sure Bot is admin in Forcesub channel")
                return
            buttons = [[
                InlineKeyboardButton("📢 Updates Channel 📢", url=invite_link.invite_link)
            ],[
                InlineKeyboardButton("🔁 Request Again 🔁", callback_data="grp_checksub")
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
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
    settings = await get_settings(query.message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                )
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"✨ {get_size(file.file_size)}",
                    callback_data=f'{pre}#{file.file_id}',
                ),
                InlineKeyboardButton(
                    text=f"⚡️ {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                )
            ]
            for file in files
        ]
    btn.insert(0,
        [InlineKeyboardButton(f"✅ {search} ✅", callback_data="buttons")]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:

        btn.append(
            [InlineKeyboardButton("⏪ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"🗓 PAGES {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}",
                                  callback_data="buttons")]
        )
        btn.append(
            [InlineKeyboardButton("❌ Close ❌", callback_data="close_data")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"🗓 PAGES {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
             InlineKeyboardButton("NEXT ⏩", callback_data=f"next_{req}_{key}_{n_offset}")])
        btn.append(
            [InlineKeyboardButton("❌ Close ❌", callback_data="close_data")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⏪ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"🗓 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="buttons"),
                InlineKeyboardButton("NEXT ⏩", callback_data=f"next_{req}_{key}_{n_offset}")
            ]
        )
        btn.append(
            [
                InlineKeyboardButton("❌ Close ❌", callback_data="close_data")
            ]
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('Checking My Database...')
    files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
    if files:
        k = (movie, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        await bot.send_message(LOG_CHANNEL, script.NO_RESULT_TXT.format(query.message.chat.title, query.message.chat.id, query.from_user.mention, movie))
        k = await query.message.edit(f"👋 Hello {query.from_user.mention},\n\nI don't find <b>'{movie}'</b> in my database. 😔")
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
        files_ = await get_file_details(file_id)
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        if not files_:
            return await query.answer('No Such File Exist!', show_alert=True)
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"
    
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")

    if query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer(f"Hello {query.from_user.first_name},\nI would like to try yours, Please join my update channel and try again.", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No Such File Exist!', show_alert=True)
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"

        btn = [[
            InlineKeyboardButton('⚡️ My Updates Channel ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('🔥 My Support Chat 🔥', url=SUPPORT_LINK)
        ]]
        await query.message.delete()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False,
            reply_markup=InlineKeyboardMarkup(btn)
        )

    elif query.data == "grp_checksub":
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nThis Is Not For You!", show_alert=True)
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer(f"Hello {query.from_user.first_name},\nI would like to try yours, Please join my update channel and request again.", show_alert=True)
            return
        await query.answer(f"Hello {query.from_user.first_name},\nGood, Can You Request Now!", show_alert=True)
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif query.data == "buttons":
        await query.answer()

    elif query.data == "start":
        await query.answer('Welcome!')
        buttons = [[
            InlineKeyboardButton("➕ Add Me To Your Group ➕", url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('🔎 Inline Search 🔍', switch_inline_query_current_chat='')
        ],[
            InlineKeyboardButton('👑 My Owner 👑', callback_data='my_owner'),
            InlineKeyboardButton('ℹ️ My About ℹ️', callback_data='my_about')
        ],[
            InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "my_about":
        buttons = [[
            InlineKeyboardButton('Report Bugs and Feedback', url=SUPPORT_LINK),
            InlineKeyboardButton('Status', callback_data='status')
        ],[
            InlineKeyboardButton('🏠 Home 🏠', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_ABOUT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "my_owner":
        buttons = [[
            InlineKeyboardButton('🏠 Home 🏠', callback_data='start'),
            InlineKeyboardButton('Contact', url='https://t.me/Hansaka_Anuhas')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_OWNER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "status":
        await query.answer("Refreshing Database...")
        buttons = [[
            InlineKeyboardButton('◀️ Back', callback_data='my_about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data.startswith("opn_pm_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
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
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
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
                    InlineKeyboardButton('Welcome Message', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]

            try:
                await client.send_message(
                    chat_id=userid,
                    text=f"Change your settings for <b>'{title}'</b> as your wish. ⚙",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=enums.ParseMode.HTML
                )
                await query.message.edit_text("Settings menu sent in private chat.")
                await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await query.answer('Your blocked me, Unblock me and try again...', show_alert=True)

    elif query.data.startswith("opn_grp_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
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
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
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
                    InlineKeyboardButton('Welcome Message', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(
                text=f"Change your settings for <b>'{title}'</b> as your wish. ⚙",
                parse_mode=enums.ParseMode.HTML
            )
            await query.message.edit_reply_markup(reply_markup)

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            await query.answer("This Is Not For You!", show_alert=True)
            return

        if str(grp_id) != str(grpid):
            await query.message.edit("I'm not connected to this group! Check /connections or /connect to this group.")
            return

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
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
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
                    InlineKeyboardButton('Welcome Message', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.answer("Changed!")
            await query.message.edit_reply_markup(reply_markup)


async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                )
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"✨ {get_size(file.file_size)}",
                    callback_data=f'{pre}#{file.file_id}',
                ),
                InlineKeyboardButton(
                    text=f"⚡️ {file.file_name}",
                    callback_data=f'{pre}#{file.file_id}',
                )
            ]
            for file in files
        ]
    btn.insert(0,
        [InlineKeyboardButton(f"✅ {search} ✅", callback_data="buttons")]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"🗓 PAGES 1 / {math.ceil(int(total_results) / 10)}", callback_data="buttons"),
             InlineKeyboardButton(text="NEXT ⏩", callback_data=f"next_{req}_{key}_{offset}")]
        )
        btn.append(
            [InlineKeyboardButton("❌ Close ❌", callback_data="close_data")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="🗓 PAGES 1 / 1", callback_data="buttons")]
        )
        btn.append(
            [InlineKeyboardButton("❌ Close ❌", callback_data="close_data")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    if imdb:
        cap = IMDB_TEMPLATE.format(
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
        cap = f"✅ I Found: <code>{search}</code>\n\n🗣 Requested by: {message.from_user.mention}\n©️ Powered by: <b>{message.chat.title}</b>"
    if imdb and imdb.get('poster'):
        try:
            await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                          reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    if spoll:
        await msg.message.delete()


async def advantage_spell_chok(msg):
    search = msg.text
    search_google = search.replace(" ", "+")
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        btn = [[InlineKeyboardButton("🔎 Search Google 🔍", url=f"https://www.google.com/search?q={search_google}")]]
        k = await msg.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {msg.from_user.mention},\n\nI can't find <b>'{search}'</b> you requested. 😢</b>", reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await msg.delete()
        except:
            pass
        return
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(
        r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)',
        '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*",
                         re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match:
                gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates
    if len(gs_parsed) > 3:
        gs_parsed = gs_parsed[:3]
    if gs_parsed:
        for mov in gs_parsed:
            imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
            if imdb_s:
                movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        btn = [[InlineKeyboardButton("🔎 Search Google 🔍", url=f"https://www.google.com/search?q={search_google}")]]
        k = await msg.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {msg.from_user.mention},\n\nI can't find the <b>'{search}'</b> you requested, Check if your spellings are correct. 😉", reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await msg.delete()
        except:
            pass
        return
    SPELL_CHECK[msg.id] = movielist
    btn = [[
        InlineKeyboardButton(
            text=movie.strip(),
            callback_data=f"spolling#{user}#{k}",
        )
    ] for k, movie in enumerate(movielist)]
    btn.append([InlineKeyboardButton(text="❌ Close ❌", callback_data=f'close_data')])
    k = await msg.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {msg.from_user.mention},\n\nI couldn't find the <b>'{search}'</b> you requested.\nDid you mean one of these? 👇",
                    reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(300)
    await k.delete()
    try:
        await msg.delete()
    except:
        pass
