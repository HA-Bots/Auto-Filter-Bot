import logging, time
from pyrogram import Client, emoji, filters
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument, InlineQuery
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
from utils import is_subscribed, get_size, temp, get_verify_status, update_verify_status
from info import CACHE_TIME, AUTH_CHANNEL, SUPPORT_LINK, UPDATES_LINK, FILE_CAPTION, IS_VERIFY, VERIFY_EXPIRE

cache_time = 0 if AUTH_CHANNEL else CACHE_TIME

async def inline_users(query: InlineQuery):
    if query.from_user and query.from_user.id not in temp.BANNED_USERS:
        return True
    return False

@Client.on_inline_query()
async def answer(bot, query):
    """Show search results for given inline query"""

    verify_status = await get_verify_status(query.from_user.id)
    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(query.from_user.id, is_verified=False)

    btn = await is_subscribed(bot, query)
    if btn:
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text='Subscribe my channel to use the bot!',
                           switch_pm_parameter="subscribe")
        return

    
    verify_status = await get_verify_status(query.from_user.id)
    if IS_VERIFY and not verify_status['is_verified']:
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text='You not verified today!',
                           switch_pm_parameter="inline_verify")
        return
        
    if not await inline_users(query):
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text="You're not auth user :(",
                           switch_pm_parameter="start")
        return


    results = []
    string = query.query
    offset = int(query.offset or 0)
    files, next_offset, total = await get_search_results(string,
                                                  max_results=10,
                                                  offset=offset)

    for file in files:
        reply_markup = get_reply_markup()
        f_caption=FILE_CAPTION.format(
            file_name=file.file_name,
            file_size=get_size(file.file_size),
            caption=file.caption
        )
        results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=f_caption,
                description=f'Size: {get_size(file.file_size)}',
                reply_markup=reply_markup))

    if results:
        switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
        if string:
            switch_pm_text += f" for {string}"
        try:
            await query.answer(results=results,
                           is_personal = True,
                           cache_time=cache_time,
                           switch_pm_text=switch_pm_text,
                           switch_pm_parameter="start",
                           next_offset=str(next_offset))
        except Exception as e:
            logging.exception(str(e))
    else:
        switch_pm_text = f'{emoji.CROSS_MARK} No results'
        if string:
            switch_pm_text += f' for "{string}"'

        await query.answer(results=[],
                           is_personal = True,
                           cache_time=cache_time,
                           switch_pm_text=switch_pm_text,
                           switch_pm_parameter="start")


def get_reply_markup():
    buttons = [[
        InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
        InlineKeyboardButton('💡 Support Group 💡', url=SUPPORT_LINK)
    ]]
    return InlineKeyboardMarkup(buttons)
