from pyrogram import Client, filters
import datetime
import time
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages, groups_broadcast_messages, temp
import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_callback_query(filters.regex(r'^broadcast_cancel'))
async def broadcast_cancel(bot, query):
    _, ident = query.data.split("#")
    if ident == 'users':
        await query.message.edit("Trying to cancel users broadcasting...")
        temp.USERS_CANCEL = True
    elif ident == 'groups':
        temp.GROUPS_CANCEL = True
        await query.message.edit("Trying to cancel groups broadcasting...")
               
@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def users_broadcast(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        text='Broadcasting your users messages...'
    )
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    failed =0
    temp.USERS_CANCEL = False
    success = 0
        
    async for user in users:
        if temp.USERS_CANCEL:
            await msg.edit(f"Users Successfully Broadcast Canceled!")
            break
        sts = await broadcast_messages(int(user['id']), b_msg)
        if sts == 'Success':
            success += 1
        elif sts == 'Error':
            failed += 1
        done += 1
        if not done % 20:
            btn = [[
                InlineKeyboardButton('CANCEL', callback_data=f'broadcast_cancel#users')
            ]]
            await sts.edit(f"Users broadcast in progress...\n\nTotal Users: <code>{total_users}</code>\nCompleted: <code>{done} / {total_users}</code>\nSuccess: <code>{success}</code>", reply_markup=InlineKeyboardMarkup(btn))    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.edit(f"Users broadcast completed.\nCompleted in {time_taken} seconds.\n\nTotal Users: <code>{total_users}</code>\nCompleted: <code>{done} / {total_users}</code>\nSuccess: <code>{success}</code>")
        
@Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS) & filters.reply)
async def groups_broadcast(bot, message):
    chats = await db.get_all_chats()
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        text='Broadcasting your groups messages...'
    )
    start_time = time.time()
    total_chats = await db.total_chat_count()
    done = 0
    failed =0
    temp.GROUPS_CANCEL = False
    success = 0
        
    async for chat in chats:
        if temp.GROUPS_CANCEL:
            await msg.edit(f"Groups Successfully Broadcast Canceled!")
            break
        sts = await groups_broadcast_messages(int(chat['id']), b_msg)
        if sts == 'Success':
            success += 1
        elif sts == 'Error':
            failed += 1
        done += 1
        if not done % 20:
            btn = [[
                InlineKeyboardButton('CANCEL', callback_data=f'broadcast_cancel#groups')
            ]]
            await sts.edit(f"Groups groadcast in progress...\n\nTotal Groups: <code>{total_chats}</code>\nCompleted: <code>{done} / {total_chats}</code>\nSuccess: <code>{success}</code>\nFailed: <code>{failed}</code>", reply_markup=InlineKeyboardMarkup(btn))    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.edit(f"Groups broadcast completed.\nCompleted in {time_taken} seconds.\n\nTotal Groups: <code>{total_chats}</code>\nCompleted: <code>{done} / {total_chats}</code>\nSuccess: <code>{success}</code>\nFailed: <code>{failed}</code>")


